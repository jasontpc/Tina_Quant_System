# -*- coding: utf-8 -*-
"""
TW Learning Engine — 主動學習引擎
分析篩選結果與市場實際走勢，根據進場表現動態調整篩選權重
"""

import sqlite3
import yfinance as yf
import pandas as pd
import json
import csv
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
DATA_DIR = BASE_DIR / 'data'
REPORT_DIR = BASE_DIR / 'reports'
SCRIPT_DIR = BASE_DIR / 'scripts'

DB_PATH = DATA_DIR / 'tw_value_growth.db'
BUY_LOG_PATH = DATA_DIR / 'tw_buy_log.csv'
LEARNING_CONFIG_PATH = DATA_DIR / 'tw_learning_config.json'
SCREENER_LOG_PATH = DATA_DIR / 'tw_screener_log.json'

# 4檔完全通過篩選的股票專屬策略
STOCK_STRATEGIES = {
    '5203': {'style': '價值成長', 'rsi_enter_max': 55, 'stop_loss': -0.05, 'take_profit': 0.15, 'max_hold_days': 45},
    '2303': {'style': '價值',    'rsi_enter_max': 60, 'stop_loss': -0.08, 'take_profit': 0.12, 'max_hold_days': 60},
    '2884': {'style': '價值超賣','rsi_enter_max': 40, 'stop_loss': -0.07, 'take_profit': 0.20, 'max_hold_days': 90},
    '2885': {'style': '穩健',    'rsi_enter_max': 65, 'stop_loss': -0.06, 'take_profit': 0.15, 'max_hold_days': 50},
}

# 動態市場環境閾值
MARKET_REGIME = {
    'bull':  {'rsi_enter_adj': +5,  'bias20_max': 20, 'vol_surge': 1.3, 'pe_max_adj': 5},
    'normal':{'rsi_enter_adj': 0,   'bias20_max': 15, 'vol_surge': 1.5, 'pe_max_adj': 0},
    'bear':  {'rsi_enter_adj': -10, 'bias20_max': 10, 'vol_surge': 2.0, 'pe_max_adj': -5},
}


# ===================== 工具函式 =====================

def load_learning_config():
    defaults = {
        'version': '1.0',
        'layer_weights': {
            'base': {'price_max': 100, 'vol_min': 500000, 'mcap_min': 1e9},
            'fund':  {'pe_max': 30, 'pe_min': 0, 'roe_min': 5, 'rev_growth_min': 0, 'op_margin_min': 0, 'debt_ratio_max': 80, 'div_yield_min': 0},
            'tech':  {'rsi_min': 30, 'rsi_max': 70, 'bias20_max': 15, 'vol_surge': 1.5}
        },
        'market_regime': 'normal',
        'trade_count': 0,
        'win_count': 0,
        'total_return': 0.0,
        'avg_return': 0.0,
        'updated_at': ''
    }
    if LEARNING_CONFIG_PATH.exists():
        with open(LEARNING_CONFIG_PATH, 'r', encoding='utf-8') as f:
            return {**defaults, **json.load(f)}
    return defaults

def save_learning_config(cfg):
    cfg['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M')
    with open(LEARNING_CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

def get_twii_regime():
    """根據加權指數判斷市場環境（牛市/正常/熊市）"""
    try:
        idx = yf.Ticker('^TWII')
        h = idx.history(period='3mo')
        if h is None or h.empty:
            return 'normal'
        prices = h['Close']
        ma20 = prices.rolling(20).mean().iloc[-1]
        ma60 = prices.rolling(60).mean().iloc[-1] if len(prices) >= 60 else ma20
        price = prices.iloc[-1]
        mom20 = (price / prices.iloc[-21] - 1) * 100 if len(prices) >= 21 else 0
        
        if price > ma20 > ma60 and mom20 > 5:
            return 'bull'
        elif price < ma20 or mom20 < -5:
            return 'bear'
        return 'normal'
    except:
        return 'normal'

def calc_rsi(prices, period=14):
    if len(prices) < period:
        return None
    delta = pd.Series(prices).diff()
    gain = delta.where(delta > 0, 0).ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = gain / loss
    return float((100 - (100 / (1 + rs))).iloc[-1])

def init_buy_log():
    """初始化買入記錄 CSV"""
    if not BUY_LOG_PATH.exists():
        with open(BUY_LOG_PATH, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['日期', '時間', '股票', '進場價', '數量', '原因', '分數', 'RSI', '預期目標', '備註',
                        '出场價', '出场日期', '報酬率', '結果', '持有天數', '停損發生', '停利發生'])
    return BUY_LOG_PATH.exists()

def log_buy(date, time, stock, entry_price, qty, reason, score, rsi, target, note):
    with open(BUY_LOG_PATH, 'a', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow([date, time, stock, entry_price, qty, reason, score, rsi, target, note,
                   '', '', '', '', '', 0, 0])

def update_buy_log(stock, exit_price, exit_date, return_pct, result, hold_days, stop_loss_hit, take_profit_hit):
    """更新買入記錄的出场欄位"""
    rows = []
    updated = False
    with open(BUY_LOG_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            if row['股票'] == stock and row['出场價'] == '':
                row['出场價'] = exit_price
                row['出场日期'] = exit_date
                row['報酬率'] = f'{return_pct:.2%}'
                row['結果'] = result
                row['持有天數'] = hold_days
                row['停損發生'] = 1 if stop_loss_hit else 0
                row['停利發生'] = 1 if take_profit_hit else 0
                updated = True
            rows.append(row)
    
    if updated:
        with open(BUY_LOG_PATH, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
    return updated

def get_stock_performance(symbol, entry_price, entry_date):
    """追蹤進場後股價表現"""
    try:
        t = yf.Ticker(f'{symbol}.TW')
        h = t.history(start=entry_date, period='6mo')
        if h is None or h.empty:
            return None
        
        current_price = float(h['Close'].iloc[-1])
        current_date = h.index[-1].strftime('%Y-%m-%d')
        return_pct = (current_price / entry_price - 1)
        
        prices = h['Close'].reset_index(drop=True)
        rsi = calc_rsi(prices.values, 14)
        high = float(h['High'].max())
        low = float(h['Low'].min())
        
        return {
            'current_price': current_price,
            'current_date': current_date,
            'return_pct': return_pct,
            'rsi': rsi,
            'high_since_entry': high,
            'low_since_entry': low
        }
    except:
        return None

def analyze_failure_patterns():
    """分析失敗交易模式"""
    if not BUY_LOG_PATH.exists():
        return {'total_trades': 0, 'patterns': {}}
    
    failures = []
    with open(BUY_LOG_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['结果'] in ('失敗', '停損', '虧損'):
                failures.append(row)
    
    patterns = {
        'rsi_overbought': 0,  # RSI > 70 進場
        'high_bias': 0,       # BIAS20 > 15% 進場
        'low_volume': 0,       # 成交量不足進場
        'poor_fundamental': 0,# 基本面惡化
        'market_crash': 0,     # 大盤系統性風險
    }
    
    for f in failures:
        note = f.get('備註', '') + f.get('備註2', '')
        if 'RSI過高' in note or float(f.get('RSI', 0)) > 65:
            patterns['rsi_overbought'] += 1
        if 'BIAS過高' in note:
            patterns['high_bias'] += 1
        if '成交量不足' in note:
            patterns['low_volume'] += 1
        if '基本面惡化' in note:
            patterns['poor_fundamental'] += 1
        if '大盤下跌' in note:
            patterns['market_crash'] += 1
    
    return {'total_trades': len(failures), 'patterns': patterns}

def generate_learning_report():
    """產出學習報告（勝率、平均報酬、優化建議）"""
    if not BUY_LOG_PATH.exists():
        return None
    
    trades = []
    with open(BUY_LOG_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        trades = list(reader)
    
    if not trades:
        return None
    
    closed = [t for t in trades if t['出场價'] != '']
    total = len(closed)
    if total == 0:
        return None
    
    wins = [t for t in closed if float(t['報酬率'].replace('%','')) > 0]
    win_rate = len(wins) / total * 100
    
    returns = [float(t['報酬率'].replace('%','')) for t in closed]
    avg_return = sum(returns) / len(returns)
    
    stop_loss_count = sum(1 for t in closed if t['停損發生'] == '1')
    take_profit_count = sum(1 for t in closed if t['停利發生'] == '1')
    
    hold_days = [int(t['持有天數']) for t in closed if t['持有天數'].isdigit()]
    avg_hold = sum(hold_days) / len(hold_days) if hold_days else 0
    
    # 各股票勝率
    stock_stats = {}
    for t in closed:
        s = t['股票']
        if s not in stock_stats:
            stock_stats[s] = {'wins': 0, 'total': 0, 'returns': []}
        stock_stats[s]['total'] += 1
        if float(t['報酬率'].replace('%','')) > 0:
            stock_stats[s]['wins'] += 1
        stock_stats[s]['returns'].append(float(t['報酬率'].replace('%','')))
    
    report = {
        'report_date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'total_trades': total,
        'win_count': len(wins),
        'win_rate': f'{win_rate:.1f}%',
        'avg_return': f'{avg_return:.2f}%',
        'stop_loss_count': stop_loss_count,
        'take_profit_count': take_profit_count,
        'avg_hold_days': f'{avg_hold:.1f}',
        'stock_stats': {
            s: {
                'win_rate': f'{d["wins"]*100/d["total"]:.1f}%',
                'avg_return': f'{sum(d["returns"])/len(d["returns"]):.2f}%',
                'trade_count': d['total']
            }
            for s, d in stock_stats.items()
        },
        'failure_patterns': analyze_failure_patterns()
    }
    
    return report


# ===================== 主要功能 =====================

def check_positions_and_update():
    """檢查所有未出场倉位，計算報酬率，更新课程"""
    if not BUY_LOG_PATH.exists():
        return []
    
    updates = []
    rows = []
    with open(BUY_LOG_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    
    for row in rows:
        if row['股票'] and row['出场價'] == '':
            stock = row['股票']
            entry_price = float(row['進場價'])
            entry_date = row['日期']
            
            perf = get_stock_performance(stock, entry_price, entry_date)
            if not perf:
                continue
            
            strat = STOCK_STRATEGIES.get(stock, {})
            stop_loss = strat.get('stop_loss', -0.05)
            take_profit = strat.get('take_profit', 0.15)
            max_hold = strat.get('max_hold_days', 60)
            
            return_pct = perf['return_pct']
            hold_days = (datetime.now() - datetime.strptime(entry_date, '%Y-%m-%d')).days
            
            stop_loss_hit = return_pct <= stop_loss
            take_profit_hit = return_pct >= take_profit
            max_hold_hit = hold_days >= max_hold
            
            # 自動出场條件
            should_exit = stop_loss_hit or take_profit_hit or max_hold_hit
            
            if should_exit:
                result = '停利' if take_profit_hit else ('停損' if stop_loss_hit else '到期')
                update_buy_log(stock, perf['current_price'], perf['current_date'],
                             return_pct, result, hold_days, stop_loss_hit, take_profit_hit)
                updates.append({
                    'stock': stock, 'exit_price': perf['current_price'],
                    'exit_date': perf['current_date'], 'return_pct': return_pct,
                    'result': result, 'hold_days': hold_days
                })
    
    return updates

def scan_for_entries():
    """根據學習引擎調整後的參數，掃描進場機會"""
    cfg = load_learning_config()
    regime = get_twii_regime()
    adj = MARKET_REGIME.get(regime, MARKET_REGIME['normal'])
    
    print(f'[LE] 市場環境: {regime} | RSI 進場調整: {adj["rsi_enter_adj"]}')
    
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute('SELECT symbol, price, rsi_14, bias20, total_score, ma_align_text FROM scores ORDER BY total_score DESC LIMIT 30')
    rows = cur.fetchall()
    conn.close()
    
    candidates = []
    for row in rows:
        sym, price, rsi, bias20, score, ma_align = row
        if rsi is None or bias20 is None:
            continue
        
        # 動態 RSI 閾值
        rsi_max = 70 + adj['rsi_enter_adj']
        rsi_min = 30
        
        if rsi < rsi_min or rsi > rsi_max:
            continue
        if bias20 > adj['bias20_max']:
            continue
        
        strat = STOCK_STRATEGIES.get(sym, {})
        rsi_enter_max = strat.get('rsi_enter_max', 60)
        if rsi > rsi_enter_max:
            continue
        
        candidates.append({
            'symbol': sym, 'price': price, 'rsi': rsi,
            'bias20': bias20, 'score': score, 'ma_align': ma_align,
            'strategy': strat.get('style', '一般')
        })
    
    return candidates

def run_learning_cycle():
    """執行一次學習循環"""
    print('=' * 60)
    print(f'TW LEARNING ENGINE — {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print('=' * 60)
    print()
    
    # 1. 檢查並更新倉位
    print('[1] 檢查未出场倉位...')
    updates = check_positions_and_update()
    if updates:
        for u in updates:
            print(f'  {u["stock"]}: 出场 ${u["exit_price"]:.2f} | 報酬 {u["return_pct"]:.2%} | {u["result"]}')
    else:
        print('  無倉位需更新')
    
    # 2. 分析失敗模式
    print()
    print('[2] 失敗模式分析...')
    fp = analyze_failure_patterns()
    print(f'  總失敗交易: {fp["total_trades"]}')
    for k, v in fp['patterns'].items():
        print(f'    {k}: {v}')
    
    # 3. 調整篩選權重
    print()
    print('[3] 調整篩選權重...')
    cfg = load_learning_config()
    
    if fp['total_trades'] >= 5:
        if fp['patterns'].get('rsi_overbought', 0) >= 2:
            cfg['layer_weights']['tech']['rsi_max'] = max(60, cfg['layer_weights']['tech'].get('rsi_max', 70) - 5)
            print(f'  → RSI 最大值調降至 {cfg["layer_weights"]["tech"]["rsi_max"]}（過度進場問題）')
        if fp['patterns'].get('high_bias', 0) >= 2:
            cfg['layer_weights']['tech']['bias20_max'] = max(10, cfg['layer_weights']['tech'].get('bias20_max', 15) - 2)
            print(f'  → BIAS20 最大值調降至 {cfg["layer_weights"]["tech"]["bias20_max"]}（過度偏離問題）')
        if fp['patterns'].get('market_crash', 0) >= 1:
            cfg['market_regime'] = 'bear'
            print('  → 市場環境設為熊市（系統性風險）')
    
    save_learning_config(cfg)
    
    # 4. 掃描進場機會
    print()
    print('[4] 掃描進場機會（學習後參數）...')
    candidates = scan_for_entries()
    for c in candidates[:5]:
        print(f'  {c["symbol"]}: ${c["price"]:.2f} | RSI={c["rsi"]:.1f} | Score={c["score"]:.0f} | {c["strategy"]}')
    
    # 5. 產出學習報告
    print()
    print('[5] 產出學習報告...')
    report = generate_learning_report()
    if report:
        print(f'  勝率: {report["win_rate"]} | 平均報酬: {report["avg_return"]} | 交易次數: {report["total_trades"]}')
        print(f'  停損次数: {report["stop_loss_count"]} | 停利次数: {report["take_profit_count"]}')
        print(f'  平均持有: {report["avg_hold_days"]} 天')
        for s, st in report['stock_stats'].items():
            print(f'    {s}: 勝率 {st["win_rate"]} | 報酬 {st["avg_return"]} | 交易 {st["trade_count"]}次')
        
        # 保存報告
        report_path = REPORT_DIR / f'tw_learning_report_{datetime.now().strftime("%Y%m%d")}.json'
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f'  報告已保存: {report_path.name}')
    
    print()
    print('=' * 60)
    return {'candidates': candidates, 'report': report, 'position_updates': updates}


if __name__ == '__main__':
    init_buy_log()
    result = run_learning_cycle()
    print()
    print(f'學習循環完成。掃描到 {len(result["candidates"])} 個候選進場機會。')