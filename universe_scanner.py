# -*- coding: utf-8 -*-
"""
Universe Scanner — 通用多 Universe 策略掃描器
============================================
功能：
1. 支援台股 500 / S&P 500 / Nasdaq 100 / SOX 30 四個 Universe
2. 價值策略：P/E、P/B、殖利率
3. 成長策略：營收 YoY、EPS 增速
4. 動能策略：均線多頭排列、RSI 適中
5. 寫入 reports/{universe}/{date}.json
6. 交付 top picks 摘要給 Jo

用法：
  python universe_scanner.py --universe tw500 --strategy value    # 台股價值
  python universe_scanner.py --universe sp500 --strategy growth  # S&P500 成長
  python universe_scanner.py --universe nasdaq100 --strategy momentum  # Nasdaq 動能
  python universe_scanner.py --universe sox30 --strategy revenue # SOX 營收加速
"""

import sys, json, sqlite3
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent / 'stores'))
try:
    from brain_aware_executor import BrainAwareExecutor, after_scanner
    BRAIN_AWARE = True
except Exception as e:
    print(f'[BrainAware] Import skipped: {e}')
    BRAIN_AWARE = False

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
DATA_DIR = BASE_DIR / 'data'
REPORTS_DIR = BASE_DIR / 'reports'
DB_PATH = DATA_DIR / 'yfinance.db'

UNIVERSE_QUERIES = {
    'tw500':   "SELECT symbol FROM symbols WHERE universe_group = 'tw500' LIMIT 500",
    'sp500':   "SELECT symbol FROM symbols WHERE universe_group = 'sp500' LIMIT 500",
    'nasdaq100': "SELECT symbol FROM symbols WHERE universe_group = 'nasdaq100' LIMIT 100",
    'sox30':   "SELECT symbol FROM symbols WHERE universe_group = 'sox30' LIMIT 30",
}

STRATEGY_PARAMS = {
    'value': {
        'name': '價值投資',
        'metrics': ['pe_ratio', 'pb_ratio', 'dividend_yield'],
        'weight': [0.4, 0.3, 0.3],
        'thresholds': {
            'pe_ratio': (5, 25),
            'pb_ratio': (0.5, 3.0),
            'dividend_yield': (2.0, 8.0)
        }
    },
    'growth': {
        'name': '成長投資',
        'metrics': ['revenue_growth', 'eps_growth', 'profit_margin'],
        'weight': [0.4, 0.35, 0.25],
        'thresholds': {
            'revenue_growth': (10, None),
            'eps_growth': (5, None),
        }
    },
    'momentum': {
        'name': '動能投資',
        'metrics': ['ma20_slope', 'rsi', 'volume_ratio'],
        'weight': [0.4, 0.3, 0.3],
        'thresholds': {
            'rsi': (40, 70),
            'volume_ratio': (1.0, None)
        }
    },
    'revenue': {
        'name': '營收加速',
        'metrics': ['revenue_qoq', 'revenue_acceleration', 'gross_margin'],
        'weight': [0.4, 0.4, 0.2],
        'thresholds': {
            'revenue_qoq': (2, None),
        }
    }
}

def get_symbols(conn, universe: str) -> List[str]:
    query = UNIVERSE_QUERIES.get(universe, UNIVERSE_QUERIES['tw500'])
    cur = conn.cursor()
    cur.execute(query)
    return [r[0] for r in cur.fetchall()]

def fetch_metrics(symbols: List[str]) -> List[Dict]:
    """用 yfinance 批量抓取基本面 + 技術面數據"""
    results = []
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 批次處理，每批 20 檔
    batch_size = 20
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i+batch_size]
        batch_str = ' '.join(batch)
        print(f'  Fetching batch {i//batch_size+1}: {batch[:3]}...')
        
        try:
            tickers = yf.Tickers(batch_str)
            for sym in batch:
                try:
                    t = tickers.tickers[sym]
                    info = t.info or {}
                    hist = t.history(period='60d', auto_adjust=True)
                    
                    # 基本面
                    pe = info.get('trailingPE') or info.get('forwardPE')
                    pb = info.get('priceToBook')
                    div_yield = info.get('dividendYield')
                    rev_growth = info.get('revenueGrowth')
                    eps_growth = info.get('earningsGrowth')
                    profit_margin = info.get('profitMargins')
                    
                    # 營收 QoQ（需要季度資料，這裡用代理）
                    rev_qoq = info.get('revenueQuarterlyGrowth', 0)
                    gross_margin = info.get('grossMargins')
                    
                    # 技術面
                    if len(hist) >= 20:
                        close = hist['Close']
                        ma20 = close.rolling(20).mean().iloc[-1]
                        ma60 = close.rolling(60).mean().iloc[-1] if len(hist) >= 60 else ma20
                        
                        delta = close.diff()
                        gain = delta.clip(lower=0).rolling(14).mean().iloc[-1]
                        loss = (-delta.clip(upper=0)).rolling(14).mean().iloc[-1]
                        rs = gain / loss if loss != 0 else 100
                        rsi = 100 - (100 / (1 + rs))
                        
                        current_price = close.iloc[-1]
                        ma20_slope = (ma20 - close.iloc[-20]) / close.iloc[-20] * 100 if len(close) >= 20 else 0
                        
                        # 成交量
                        vol_avg20 = hist['Volume'].rolling(20).mean().iloc[-1]
                        vol_today = hist['Volume'].iloc[-1]
                        vol_ratio = vol_today / vol_avg20 if vol_avg20 > 0 else 1.0
                        
                        # 均線多頭
                        ma_bullish = bool(current_price > ma20 and ma20 > ma60)
                        
                        price_20d_ago = close.iloc[-20] if len(close) >= 20 else current_price
                        price_change = (current_price - price_20d_ago) / price_20d_ago * 100 if price_20d_ago else 0
                    else:
                        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
                        ma20 = ma60 = rsi = ma20_slope = vol_ratio = price_change = 0
                        ma_bullish = False
                    
                    results.append({
                        'symbol': sym,
                        'price': current_price,
                        'pe_ratio': pe,
                        'pb_ratio': pb,
                        'dividend_yield': (div_yield * 100) if div_yield else 0,
                        'revenue_growth': (rev_growth * 100) if rev_growth else 0,
                        'eps_growth': (eps_growth * 100) if eps_growth else 0,
                        'revenue_qoq': (rev_qoq * 100) if rev_qoq else 0,
                        'profit_margin': (profit_margin * 100) if profit_margin else 0,
                        'gross_margin': (gross_margin * 100) if gross_margin else 0,
                        'rsi': float(rsi) if rsi else 50,
                        'ma20_slope': float(ma20_slope),
                        'volume_ratio': float(vol_ratio),
                        'ma_bullish': ma_bullish,
                        'price_change_20d': float(price_change),
                        'analyst_target': info.get('targetMeanPrice'),
                        'analyst_rating': info.get('recommendationKey'),
                        'fetch_date': today,
                        'error': None
                    })
                except Exception as e:
                    results.append({'symbol': sym, 'error': str(e)[:100]})
        except Exception as e:
            print(f'Batch error: {e}')
            for sym in batch:
                results.append({'symbol': sym, 'error': str(e)[:100]})
    
    # 清理 delisted / 無報價的符號
    cleaned = []
    for r in results:
        err = r.get('error', '')
        if err and ('delisted' in err or 'no price data' in err or '404' in err):
            continue
        # 確保 numpy 型別可 JSON 序列化
        for k, v in r.items():
            if isinstance(v, (np.bool_,)):
                r[k] = bool(v)
            elif isinstance(v, (np.integer,)):
                r[k] = int(v)
            elif isinstance(v, (np.floating,)):
                r[k] = float(v)
        cleaned.append(r)
    
    return cleaned

def score_stocks(metrics: List[Dict], strategy: str) -> List[Dict]:
    """根據策略評分"""
    params = STRATEGY_PARAMS.get(strategy, STRATEGY_PARAMS['value'])
    scored = []
    
    for m in metrics:
        if m.get('error') or m.get('price') is None:
            continue
        
        score = 0
        details = {}
        
        if strategy == 'value':
            # 價值評分：P/E 越低越好（在合理區間）、P/B 越低越好、殖利率越高越好
            pe = m.get('pe_ratio') or 999
            pb = m.get('pb_ratio') or 999
            dy = m.get('dividend_yield') or 0
            
            if 5 <= pe <= 25:
                score += 40 * (1 - (pe - 5) / 20)
                details['pe_ok'] = True
            elif pe and pe < 5:
                score += 40
                details['pe_ok'] = True
            else:
                details['pe_ok'] = False
            
            if pb and 0.5 <= pb <= 3.0:
                score += 30 * (1 - (pb - 0.5) / 2.5)
                details['pb_ok'] = True
            elif pb and pb < 0.5:
                score += 30
                details['pb_ok'] = True
            else:
                details['pb_ok'] = False
            
            if dy >= 2.0:
                score += 30 * min(dy / 6.0, 1.0)
                details['dy_ok'] = True
            else:
                details['dy_ok'] = False
        
        elif strategy == 'growth':
            rg = m.get('revenue_growth') or 0
            eg = m.get('eps_growth') or 0
            pm = m.get('profit_margin') or 0
            
            if rg >= 10:
                score += 40 * min(rg / 40, 1.0)
            elif rg >= 0:
                score += rg * 2
            
            if eg >= 5:
                score += 35 * min(eg / 30, 1.0)
            elif eg >= 0:
                score += eg * 3
            
            if pm >= 15:
                score += 25
            elif pm >= 5:
                score += 25 * (pm / 15)
            
            details['revenue_growth'] = rg
            details['eps_growth'] = eg
        
        elif strategy == 'momentum':
            rsi = m.get('rsi') or 50
            slope = m.get('ma20_slope') or 0
            vol_r = m.get('volume_ratio') or 1
            bullish = m.get('ma_bullish', False)
            
            if 40 <= rsi <= 70:
                score += 30
            elif rsi < 40:
                score += 20
            elif rsi > 70:
                score += 10  # Overbought，降低分數
            
            if slope > 0:
                score += 40 * min(slope / 10, 1.0)
            
            if vol_r >= 1.2:
                score += 30 * min(vol_r / 2, 1.0)
            elif vol_r >= 1.0:
                score += 15
            
            if bullish:
                score += 20
            
            details['rsi'] = rsi
            details['slope'] = slope
        
        elif strategy == 'revenue':
            rq = m.get('revenue_qoq') or 0
            gm = m.get('gross_margin') or 0
            
            if rq >= 5:
                score += 50 * min(rq / 20, 1.0)
            elif rq >= 2:
                score += 25 + (rq - 2) * 5
            
            if gm >= 40:
                score += 50
            elif gm >= 20:
                score += 50 * (gm / 40)
            
            details['revenue_qoq'] = rq
            details['gross_margin'] = gm
        
        scored.append({
            'symbol': m['symbol'],
            'price': m.get('price'),
            'score': round(score, 1),
            'details': details,
            'analyst_target': m.get('analyst_target'),
            'analyst_rating': m.get('analyst_rating'),
            'rsi': m.get('rsi'),
            'ma_bullish': m.get('ma_bullish'),
            'pe_ratio': m.get('pe_ratio'),
            'revenue_growth': m.get('revenue_growth'),
        })
    
    # 排序
    scored.sort(key=lambda x: x['score'], reverse=True)
    return scored

def save_report(universe: str, strategy: str, scored: List[Dict], today: str):
    """寫入 JSON 報告"""
    report_dir = REPORTS_DIR / universe
    report_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f'{today}_{strategy}.json'
    filepath = report_dir / filename
    
    report = {
        'date': today,
        'universe': universe,
        'strategy': strategy,
        'strategy_name': STRATEGY_PARAMS[strategy]['name'],
        'total_scanned': len(scored),
        'top_picks': scored[:20],  # Top 20
        'summary': {
            'high_score_count': len([s for s in scored if s['score'] >= 60]),
            'medium_score_count': len([s for s in scored if 40 <= s['score'] < 60]),
        }
    }
    
    def json_safe(obj):
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return str(obj)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=json_safe)
    
    return filepath, report

def format_top_picks(scored: List[Dict], universe: str, strategy: str) -> str:
    """格式化給 Jo 的摘要"""
    if not scored:
        return f'{universe} {strategy}: 無合適標的'
    
    params = STRATEGY_PARAMS[strategy]
    lines = [
        f'📊 {universe.upper()} {params["name"]} 掃描結果',
        f'掃描檔數：{len(scored)} | 高品質（≥60分）：{len([s for s in scored if s["score"]>=60])} 檔',
        '',
        '🏆 Top Picks：',
    ]
    
    for i, s in enumerate(scored[:5], 1):
        price = s.get('price', 'N/A')
        score = s['score']
        rsi = s.get('rsi', 'N/A')
        pe = s.get('pe_ratio')
        
        price_str = f'${price:.2f}' if isinstance(price, (int, float)) else str(price)
        rsi_str = f'RSI={rsi:.0f}' if isinstance(rsi, float) else ''
        pe_str = f'P/E={pe:.1f}' if isinstance(pe, float) and pe and pe < 999 else ''
        
        target = s.get('analyst_target')
        target_str = f'→ ${target:.0f}' if isinstance(target, (int, float)) else ''
        
        lines.append(f'{i}. {s["symbol"]} {price_str} {rsi_str} {pe_str}')
        lines.append(f'   {score}分 {target_str} {"📈" if s.get("ma_bullish") else "📊"}')
    
    lines.append('')
    lines.append(f'完整報告：reports/{universe}/{datetime.now().strftime("%Y%m%d")}_{strategy}.json')
    
    return '\n'.join(lines)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--universe', '-u', default='tw500',
                        choices=['tw500', 'sp500', 'nasdaq100', 'sox30'])
    parser.add_argument('--strategy', '-s', default='value',
                        choices=['value', 'growth', 'momentum', 'revenue'])
    parser.add_argument('--limit', '-l', type=int, default=None,
                        help='限制掃描檔數（測試用）')
    args = parser.parse_args()
    
    today = datetime.now().strftime('%Y-%m-%d')
    universe = args.universe
    strategy = args.strategy
    
    print(f'=== Universe Scanner ===')
    print(f'Universe: {universe}')
    print(f'Strategy: {strategy}')
    print(f'Date: {today}')
    
    # === Brain-Aware: Job 執行前脈絡讀取 ===
    brain = None
    if BRAIN_AWARE:
        brain = BrainAwareExecutor(
            job_name=f'{universe}_scanner',
            universe=universe.upper().replace('NASDAQ100', 'US_NASDAQ').replace('SOX30', 'SOX'),
            job_type='scanner'
        )
        ctx = brain.before_execute()
        # 若有相關 Pattern，可注入到掃描邏輯（這裡只印出摘要）
        if ctx['patterns']:
            print(f'[Brain] Relevant patterns found: {len(ctx["patterns"])}')
        if ctx['active_positions']:
            print(f'[Brain] Active positions in universe: {len(ctx["active_positions"])}')
    
    # 讀取 Universe 清單
    conn = sqlite3.connect(str(DB_PATH))
    symbols = get_symbols(conn, universe)
    conn.close()
    
    if args.limit:
        symbols = symbols[:args.limit]
    
    print(f'Symbols to scan: {len(symbols)}')
    
    # 抓取數據
    print('Fetching metrics...')
    metrics = fetch_metrics(symbols)
    valid = [m for m in metrics if not m.get('error')]
    print(f'Valid data: {len(valid)}/{len(metrics)}')
    
    # 評分
    print('Scoring...')
    scored = score_stocks(valid, strategy)
    print(f'Top score: {scored[0]["score"] if scored else "N/A"}')
    
    # 存報告
    filepath, report = save_report(universe, strategy, scored, today)
    print(f'Report: {filepath}')
    
    # 輸出摘要
    summary = format_top_picks(scored, universe, strategy)
    print('\n' + summary)
    
    # === Brain-Aware: Job 執行後寫入短期記憶 ===
    if brain:
        brain.after_execute(
            success=True,
            summary=f"{universe.upper()} {strategy}掃描：{len(valid)}檔中 {len([s for s in scored if s['score']>=60])} 檔高品質",
            signals=[
                {
                    'symbol': s['symbol'],
                    'action': 'buy' if s['score'] >= 60 else 'watch',
                    'price': s.get('price'),
                    'score': s['score'],
                    'reason': f"{strategy}評分{s['score']}分",
                    'strength': min(10, s['score'] / 10),
                    'strategy': strategy,
                    'universe': universe
                }
                for s in scored[:5]
            ],
            metrics={
                'total_scanned': len(valid),
                'high_quality': len([s for s in scored if s['score'] >= 60]),
                'strategy': strategy,
                'universe': universe
            },
            output_file=str(filepath)
        )
    
    print('\nDONE')

if __name__ == '__main__':
    main()
