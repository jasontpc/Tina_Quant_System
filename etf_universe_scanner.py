# -*- coding: utf-8 -*-
"""
ETF Universe Scanner — 高股息 / 價值 / 成長 ETF 專用掃描器
==========================================================
功能：
1. 專為 ETF 設計的篩選指標
2. 高股息：殖利率 + 季配頻率 + 規模
3. 價值型：P/E、P/B、折價/溢價
4. 成長型：近1年/3年報酬 + 追蹤誤差
5. 防禦型：波動率、夏普比率、最大回撤
6. 寫入 reports/etf/{date}_{category}_{strategy}.json

用法：
  python etf_universe_scanner.py --universe tw_etf --strategy dividend  # 台股高股息
  python etf_universe_scanner.py --universe us_etf --strategy value      # 美股價值型
  python etf_universe_scanner.py --universe us_etf --strategy growth     # 美股成長型
  python etf_universe_scanner.py --universe tw_etf --strategy all         # 台股全策略
"""

import sys, json, sqlite3
import yfinance as yf
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent / 'stores'))
try:
    from brain_aware_executor import BrainAwareExecutor
    BRAIN_AWARE = True
except Exception as e:
    print(f'[BrainAware] Import skipped: {e}')
    BRAIN_AWARE = False

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
DATA_DIR = BASE_DIR / 'data'
DB_PATH = DATA_DIR / 'yfinance.db'
REPORTS_DIR = BASE_DIR / 'reports'
ETF_REPORT_DIR = REPORTS_DIR / 'etf'

UNIVERSE_QUERIES = {
    'tw_etf':      "SELECT symbol FROM symbols WHERE universe_group LIKE 'tw_etf_%' LIMIT 100",
    'us_etf':      "SELECT symbol FROM symbols WHERE universe_group LIKE 'us_etf_%' LIMIT 200",
    'us_etf_growth': "SELECT symbol FROM symbols WHERE universe_group LIKE 'us_etf_%' AND universe_group='us_etf_成長型' LIMIT 100",
    'us_etf_value':  "SELECT symbol FROM symbols WHERE universe_group LIKE 'us_etf_%' AND universe_group='us_etf_價值型' LIMIT 100",
    'us_etf_dividend': "SELECT symbol FROM symbols WHERE universe_group LIKE 'us_etf_%' AND universe_group='us_etf_高股息' LIMIT 100",
}

# 台股 ETF 篩選門檻
TW_ETF_THRESHOLDS = {
    'dividend': {
        'dividend_yield': (4.0, 999),   # 殖利率 > 4%
        'nav': (10, None),              # 淨值 > 10
        'aum': (5e8, None),             # 規模 > 5億
        'expense_ratio': (None, 0.5),   # 費用率 < 0.5%
    },
    'value': {
        'pe': (5, 20),
        'pb': (0.5, 2.0),
        'nav': (10, None),
        'discount': (0, 5),             # 折價 < 5%
    },
    'growth': {
        'return_1y': (5, None),
        'return_3y': (10, None),
        'tracking_error': (None, 2.0),
    },
    'low_vol': {
        'volatility': (None, 15),
        'max_drawdown': (None, -10),
        'sharpe': (0.5, None),
    },
}

# 美股 ETF 篩選門檻
US_ETF_THRESHOLDS = {
    'dividend': {
        'dividend_yield': (3.0, 999),
        'aum': (1e9, None),
        'expense_ratio': (None, 0.3),
    },
    'value': {
        'pe': (10, 25),
        'pb': (0.8, 3.0),
        'price': (10, 500),
    },
    'growth': {
        'return_1y': (8, None),
        'return_3y': (20, None),
        'return_5y': (30, None),
    },
    'low_vol': {
        'volatility': (None, 18),
        'sharpe': (0.8, None),
        'max_drawdown': (None, -15),
    },
    'semiconductor': {
        'return_1y': (5, None),
        'aum': (5e8, None),
        'expense_ratio': (None, 0.5),
    },
}

def get_etf_symbols(conn, universe: str) -> List[str]:
    query = UNIVERSE_QUERIES.get(universe, f"SELECT symbol FROM symbols WHERE universe_group LIKE '{universe}%' LIMIT 100")
    cur = conn.cursor()
    try:
        cur.execute(query)
        return [r[0] for r in cur.fetchall()]
    except:
        # Fallback
        cur.execute(f"SELECT symbol FROM symbols WHERE universe_group LIKE '{universe}%' LIMIT 200")
        return [r[0] for r in cur.fetchall()]

def fetch_etf_data(symbols: List[str]) -> List[Dict]:
    """用 yfinance 抓取 ETF 數據"""
    results = []
    batch_size = 20
    
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i+batch_size]
        print(f'  Fetching ETF batch {i//batch_size+1}: {batch[:3]}...')
        
        try:
            tickers = yf.Tickers(' '.join(batch))
            for sym in batch:
                try:
                    t = tickers.tickers.get(sym)
                    if not t:
                        continue
                    info = t.info or {}
                    hist = t.history(period='1y', auto_adjust=True)
                    
                    # ETF 基本資料
                    price = info.get('regularMarketPrice') or info.get('currentPrice')
                    nav = info.get('navPrice') or info.get('netAssetValue')
                    dividend_yield = info.get('dividendYield') or 0
                    if dividend_yield:
                        # yfinance 有的已轉%，有的是小數，統一處理
                        if dividend_yield > 1:  # 已經是 % 單位
                            dividend_yield = dividend_yield
                        else:  # 小數形式，轉為 %
                            dividend_yield = dividend_yield * 100
                        # 上限 cap，防止异常值
                        dividend_yield = min(dividend_yield, 30)
                    
                    expense_ratio = info.get('expenseRatio') or info.get('annualReportExpenseRatio') or 0
                    if expense_ratio and expense_ratio > 1:
                        expense_ratio *= 100  # 轉換為 %
                    
                    aum = info.get('totalAssets') or 0
                    
                    # 報酬率
                    if len(hist) >= 252:
                        price_1y_ago = hist['Close'].iloc[-252]
                        price_now = hist['Close'].iloc[-1]
                        return_1y = (price_now - price_1y_ago) / price_1y_ago * 100
                        
                        # 3年（需要足夠數據）
                        if len(hist) >= 756:
                            price_3y_ago = hist['Close'].iloc[-756]
                            return_3y = (price_now - price_3y_ago) / price_3y_ago * 100
                        else:
                            return_3y = 0
                        
                        # 5年
                        if len(hist) >= 1260:
                            price_5y_ago = hist['Close'].iloc[-1260]
                            return_5y = (price_now - price_5y_ago) / price_5y_ago * 100
                        else:
                            return_5y = 0
                        
                        # 波動率
                        daily_returns = hist['Close'].pct_change().dropna()
                        volatility = daily_returns.std() * np.sqrt(252) * 100
                        
                        # 最大回撤
                        cummax = hist['Close'].cummax()
                        drawdown = (hist['Close'] - cummax) / cummax * 100
                        max_drawdown = drawdown.min()
                        
                        # 夏普比率（假設無風險利率 4%）
                        rf = 4.0
                        excess_return = return_1y - rf
                        sharpe = excess_return / volatility if volatility > 0 else 0
                    else:
                        return_1y = return_3y = return_5y = 0
                        volatility = max_drawdown = sharpe = 0
                    
                    results.append({
                        'symbol': sym,
                        'price': price,
                        'nav': nav,
                        'dividend_yield': dividend_yield,
                        'expense_ratio': expense_ratio,
                        'aum': aum,
                        'return_1y': return_1y,
                        'return_3y': return_3y,
                        'return_5y': return_5y,
                        'volatility': volatility,
                        'max_drawdown': max_drawdown,
                        'sharpe': sharpe,
                        'fund_type': info.get('fundType', 'ETF'),
                        'tracking_error': info.get('trackingError'),
                        'error': None
                    })
                except Exception as e:
                    results.append({'symbol': sym, 'error': str(e)[:100]})
        except Exception as e:
            print(f'Batch error: {e}')
            for sym in batch:
                results.append({'symbol': sym, 'error': str(e)[:100]})
    
    return results

def score_etf(etf: Dict, strategy: str, universe: str) -> float:
    """根據策略評分"""
    thresholds = TW_ETF_THRESHOLDS if 'tw' in universe else US_ETF_THRESHOLDS
    params = thresholds.get(strategy, thresholds['dividend'])
    
    score = 50  # 基礎分
    
    # 殖利率評分
    dy = etf.get('dividend_yield', 0) or 0
    if strategy == 'dividend':
        if dy >= 4.0:
            score += 30 * min(dy / 8.0, 1.0)
        elif dy >= 2.0:
            score += 15
        # 規模評分
        aum = etf.get('aum', 0) or 0
        if aum >= 1e9:
            score += 10
        elif aum >= 5e8:
            score += 5
        # 費用率評分
        er = etf.get('expense_ratio', 0) or 999
        if er <= 0.1:
            score += 10
        elif er <= 0.3:
            score += 5
    
    # 價值評分
    elif strategy == 'value':
        pe = etf.get('pe', 999) or 999
        pb = etf.get('pb', 999) or 999
        if 5 <= pe <= 20:
            score += 25 * (1 - abs(pe - 12) / 8)
        if 0.5 <= pb <= 2.0:
            score += 25 * (1 - abs(pb - 1.25) / 0.75)
        # 折價溢價
        price = etf.get('price') or etf.get('nav') or 0
        nav = etf.get('nav') or price
        if nav and price:
            discount = (price - nav) / nav * 100
            if -2 <= discount <= 2:
                score += 10  # 合理折溢價
    
    # 成長評分
    elif strategy == 'growth':
        r1 = etf.get('return_1y', 0) or 0
        r3 = etf.get('return_3y', 0) or 0
        if r1 >= 10:
            score += 35 * min(r1 / 30, 1.0)
        elif r1 >= 0:
            score += r1 * 2
        if r3 >= 15:
            score += 25 * min(r3 / 50, 1.0)
        elif r3 >= 0:
            score += r3 * 0.5
        sharpe = etf.get('sharpe', 0) or 0
        if sharpe >= 1.0:
            score += 15
        elif sharpe >= 0.5:
            score += sharpe * 15
    
    # 低波動評分
    elif strategy == 'low_vol':
        vol = etf.get('volatility', 999) or 999
        sharpe = etf.get('sharpe', 0) or 0
        if vol <= 12:
            score += 30 * (1 - vol / 12)
        elif vol <= 18:
            score += 15
        if sharpe >= 1.0:
            score += 25
        elif sharpe >= 0.5:
            score += sharpe * 25
        md = etf.get('max_drawdown', 0) or 0
        if md >= -10:
            score += 15
    
    # 半導體AI評分
    elif strategy == 'semiconductor':
        r1 = etf.get('return_1y', 0) or 0
        if r1 >= 15:
            score += 40 * min(r1 / 40, 1.0)
        elif r1 >= 0:
            score += r1 * 1.5
        sharpe = etf.get('sharpe', 0) or 0
        if sharpe >= 0.8:
            score += 20
        vol = etf.get('volatility', 999) or 999
        if vol <= 25:
            score += 10
    
    return max(0, min(100, score))

def format_etf_picks(etfs: List[Dict], universe: str, strategy: str) -> str:
    """格式化 ETF 推薦"""
    if not etfs:
        return f'{universe.upper()} {strategy.upper()} ETF：無合適標的'
    
    strategy_names = {
        'dividend': '高股息',
        'value': '價值型',
        'growth': '成長型',
        'low_vol': '低波動防禦',
        'semiconductor': '半導體/AI',
        'all': '全方位'
    }
    name = strategy_names.get(strategy, strategy)
    
    lines = [
        f'📊 {universe.upper()} {name} ETF 掃描結果',
        f'掃描檔數：{len(etfs)} | 高品質（≥60分）：{len([e for e in etfs if e["score"] >= 60])} 檔',
        '',
        '🏆 Top Picks：',
    ]
    
    for i, etf in enumerate(etfs[:5], 1):
        price = etf.get('price') or etf.get('nav') or 0
        dy = etf.get('dividend_yield', 0) or 0
        r1 = etf.get('return_1y', 0) or 0
        vol = etf.get('volatility', 0) or 0
        er = etf.get('expense_ratio', 0) or 0
        
        price_str = f'${price:.2f}' if price else 'N/A'
        dy_str = f'{dy:.1f}%' if dy else 'N/A'
        r1_str = f'{r1:+.1f}%' if r1 else 'N/A'
        vol_str = f'波動{vol:.1f}%' if vol else ''
        er_str = f'費用{er:.2f}%' if er else ''
        
        lines.append(f'{i}. {etf["symbol"]} {price_str}')
        lines.append(f'   {etf["score"]:.0f}分 | 殖利率{dy_str} | 1年報酬{r1_str}')
        if vol_str or er_str:
            lines.append(f'   {vol_str} {er_str}')
    
    return '\n'.join(lines)

def save_etf_report(universe: str, strategy: str, scored: List[Dict], today: str):
    """寫入 ETF 報告 JSON"""
    ETF_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    filepath = ETF_REPORT_DIR / f'{today}_{universe}_{strategy}.json'
    
    report = {
        'date': today,
        'universe': universe,
        'strategy': strategy,
        'total_scanned': len(scored),
        'top_picks': scored[:15],
        'summary': {
            'high_score_count': len([s for s in scored if s['score'] >= 60]),
            'avg_dividend_yield': np.mean([s.get('dividend_yield', 0) or 0 for s in scored]).round(2),
            'avg_return_1y': np.mean([s.get('return_1y', 0) or 0 for s in scored]).round(2),
        }
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    return filepath

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--universe', '-u', default='us_etf',
                       choices=['tw_etf', 'us_etf', 'us_etf_growth', 'us_etf_value', 'us_etf_dividend'])
    parser.add_argument('--strategy', '-s', default='dividend',
                       choices=['dividend', 'value', 'growth', 'low_vol', 'semiconductor', 'all'])
    parser.add_argument('--limit', '-l', type=int, default=None)
    args = parser.parse_args()
    
    today = datetime.now().strftime('%Y-%m-%d')
    universe = args.universe
    strategy = args.strategy
    
    print(f'=== ETF Universe Scanner ===')
    print(f'Universe: {universe}')
    print(f'Strategy: {strategy}')
    print(f'Date: {today}')
    
    # === Brain-Aware: Job 執行前脈絡讀取 ===
    brain = None
    if BRAIN_AWARE:
        universe_map = {'tw_etf': 'TW', 'us_etf': 'US'}
        brain = BrainAwareExecutor(
            job_name=f'{universe}_etf_scanner',
            universe=universe_map.get(universe, 'MULTI'),
            job_type='scanner'
        )
        ctx = brain.before_execute()
        if ctx['patterns']:
            print(f'[Brain] Relevant patterns: {len(ctx["patterns"])}')
        if ctx['active_positions']:
            print(f'[Brain] Active positions: {len(ctx["active_positions"])}')
    
    # 讀取 Universe 清單
    conn = sqlite3.connect(str(DB_PATH))
    symbols = get_etf_symbols(conn, args.universe)
    conn.close()
    
    if args.limit:
        symbols = symbols[:args.limit]
    
    print(f'Symbols to scan: {len(symbols)}')
    
    # 抓取數據
    print('Fetching ETF data...')
    etfs = fetch_etf_data(symbols)
    valid = [e for e in etfs if not e.get('error') and (e.get('price') or e.get('nav'))]
    print(f'Valid data: {len(valid)}/{len(etfs)}')
    
    # 評分
    print('Scoring...')
    for e in valid:
        e['score'] = score_etf(e, args.strategy, args.universe)
    
    valid.sort(key=lambda x: x['score'], reverse=True)
    
    # 存報告
    filepath = save_etf_report(args.universe, args.strategy, valid, today)
    print(f'Report: {filepath}')
    
    # 輸出摘要
    summary = format_etf_picks(valid, args.universe, args.strategy)
    print('\n' + summary)
    
    # === Brain-Aware: Job 執行後寫入短期記憶 ===
    if brain:
        strategy_name_map = {'dividend': 'dividend', 'value': 'value', 'growth': 'growth', 'low_vol': 'low_vol', 'semiconductor': 'semiconductor'}
        brain.after_execute(
            success=True,
            summary=f'{universe.upper()} {strategy} ETF 掃描：{len(valid)}檔中 {len([e for e in valid if e["score"]>=60])} 檔高品質',
            signals=[
                {
                    'symbol': e['symbol'],
                    'action': 'buy' if e['score'] >= 60 else 'watch',
                    'price': e.get('price') or e.get('nav'),
                    'score': e['score'],
                    'reason': f'{strategy}評分{e["score"]:.0f}分，殖利率{e.get("dividend_yield",0):.1f}%',
                    'strength': min(10, e['score'] / 10),
                    'strategy': strategy,
                    'universe': universe
                }
                for e in valid[:5]
            ],
            metrics={
                'total_scanned': len(valid),
                'high_quality': len([e for e in valid if e['score'] >= 60]),
                'strategy': strategy,
                'universe': universe,
                'avg_dividend_yield': round(np.mean([e.get('dividend_yield',0) or 0 for e in valid if e.get('dividend_yield')]), 1)
            },
            output_file=str(filepath)
        )
    
    print('\nDONE')

if __name__ == '__main__':
    main()