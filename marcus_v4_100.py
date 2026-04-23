# -*- coding: utf-8 -*-
"""
Marcus - Top100+ v4 (藍籌放寬版)
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import warnings
warnings.filterwarnings('ignore')
import yfinance as yf
yf.suppress_errors = True
import numpy as np
import sqlite3
import pandas as pd
import time
import json

DB = 'data/tina_master.db'

# ============== 股票池 ==============
TIER1_AI = [
    '2330', '2454', '2317', '2303', '3034', '2379', '3008', '2382',
    '3231', '3717', '4938', '2345', '3017', '6230', '2451', '3665',
    '4961', '6477', '3406', '2385', '5521', '6153', '2458', '2377',
    '6515', '6533', '6531', '2492', '2474', '3532',
]

TIER2_SUPPLY = [
    '1590', '2308', '2344', '2401', '2404', '3033', '3686', '3702',
    '4935', '4952', '5215', '5469', '6139', '6183', '6257', '6415',
    '6446', '6770', '8046', '8081', '9917', '2481', '3545', '3593',
    '4722', '4968', '6239', '8261', '9955', '3532',
]

TIER3_BLUE = [
    '2881', '2882', '2884', '2885', '2886', '2887', '2891', '2892', '2890',
    '2801', '2812', '2834', '5871',
    '1301', '1326', '2002', '1216', '1215', '2610', '2603',
    '2609', '2630', '3035', '3044', '3413', '3481', '2409', '4904',
    '2412', '3045', '6213', '6505', '9914', '9921', '1536', '6605',
    '2471', '2498', '3543', '4746', '8464', '2707', '9945',
]

BLACKLIST = ['2615', '1590', '2382', '2317', '2303', '3008', '3231', '2408', '3443', '6446', '6669', '2597']

TIER1 = [s for s in TIER1_AI if s not in BLACKLIST][:30]
TIER2 = [s for s in TIER2_SUPPLY if s not in BLACKLIST][:30]
TIER3 = [s for s in TIER3_BLUE if s not in BLACKLIST][:50]

ALL_STOCKS = TIER1 + TIER2 + TIER3
print(f"Tier1: {len(TIER1)} | Tier2: {len(TIER2)} | Tier3: {len(TIER3)} | 總計: {len(ALL_STOCKS)}")

def load_inst():
    inst = {}
    try:
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute('SELECT symbol, date, foreign_net, trust_net FROM MarketData')
        for sym, date, f, t in cur.fetchall():
            if sym not in inst: inst[sym] = {}
            inst[sym][date] = (f or 0, t or 0)
        conn.close()
    except: pass
    return inst

def rsi(p):
    d = np.diff(p)
    g = np.where(d > 0, d, 0)
    l = np.where(d > 0, 0, -d)
    ag = np.mean(g[-14:])
    al = np.mean(l[-14:])
    return 100 - (100 / (1 + ag / al)) if al != 0 else 50

def calc_atr(h, i):
    high = list(h['High'].iloc[max(0,i-14):i+1])
    low = list(h['Low'].iloc[max(0,i-14):i+1])
    close = list(h['Close'].iloc[max(0,i-14):i+1])
    tr = [max(high[j]-low[j], abs(high[j]-close[j-1]), abs(low[j]-close[j-1])) for j in range(1, len(high))]
    return np.mean(tr[-14:]) if len(tr) >= 14 else 30

def macd_signal(p):
    ema12 = pd.Series(p).ewm(span=12).mean()
    ema26 = pd.Series(p).ewm(span=26).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9).mean()
    return macd.iloc[-1], signal.iloc[-1]

def backtest(inst_map, days=180):
    end_date = '2026-04-23'
    start_date = (pd.to_datetime(end_date) - pd.Timedelta(days=days)).strftime('%Y-%m-%d')
    
    all_trades = {'tier1': [], 'tier2': [], 'tier3': [], 'all': []}
    tier_map = {}
    for s in TIER1: tier_map[s] = 'tier1'
    for s in TIER2: tier_map[s] = 'tier2'
    for s in TIER3: tier_map[s] = 'tier3'
    
    for idx, code in enumerate(ALL_STOCKS):
        try:
            h = yf.Ticker(code+'.TW').history(start=start_date, end=end_date)
            if len(h) < 30: continue
            cl, vol = list(h['Close']), list(h['Volume'])
            
            for i in range(25, len(cl)-6):
                rs = rsi(cl[:i+1])
                ma20 = np.mean(cl[i-19:i+1])
                ma60 = np.mean(cl[i-59:i+1]) if i >= 60 else np.mean(cl[:i+1])
                atr = calc_atr(h, i)
                macd_val, signal_val = macd_signal(cl[:i+1])
                date_str = str(h.index[i])[:10]
                vr = vol[i] / np.mean(vol[i-19:i+1]) if np.mean(vol[i-19:i+1]) > 0 else 0
                
                tier = tier_map.get(code, 'tier3')
                
                # 通用: RSI 40-70, MA20>MA60, price>MA20, MACD多頭, ATR足夠
                if not (40 <= rs <= 70): continue
                if ma20 <= ma60: continue
                if cl[i] < ma20: continue
                if not (macd_val > signal_val): continue
                if atr < 30: continue
                
                if tier == 'tier2':
                    if code in inst_map:
                        has_inst = False
                        for d in range(1, 4):
                            dt = (pd.to_datetime(date_str) - pd.Timedelta(days=d)).strftime('%Y-%m-%d')
                            if dt in inst_map[code]:
                                f_net, t_net = inst_map[code][dt]
                                if f_net > 0 or t_net > 0:
                                    has_inst = True
                                    break
                        if not has_inst: continue
                    else:
                        if rs > 60: continue
                        
                elif tier == 'tier3':
                    # 藍籌: MA20<=MA60也可接受(放寬)，但需更嚴格RSI
                    if ma20 <= ma60:  # 放寬多頭趨勢要求
                        if rs > 55: continue  # 更嚴格的RSI
                        if vr < 1.2: continue
                    if rs > 68: continue
                    if atr < 20: continue
                
                entry = h['Open'].iloc[i+1] if i+1 < len(h) else cl[i]
                exit_p = cl[min(i+6, len(cl)-1)]
                ret = (exit_p / entry - 1) * 100 - 0.45
                
                trade = {'ret': ret, 'rsi': rs, 'atr': atr, 'vr': vr,
                         'bias': (cl[i]/ma20-1)*100, 'code': code, 'tier': tier}
                
                all_trades[tier].append(trade)
                all_trades['all'].append(trade)
                
        except: pass
        time.sleep(0.05)
        if (idx + 1) % 25 == 0:
            print(f"  {idx+1}/{len(ALL_STOCKS)}...")
    return all_trades

def analyze(trades):
    results = {}
    for key in ['tier1', 'tier2', 'tier3', 'all']:
        t = trades[key]
        if not t:
            results[key] = None
            continue
        wins = [x for x in t if x['ret'] > 0]
        losses = [x for x in t if x['ret'] <= 0]
        results[key] = {
            'total': len(t), 'wins': len(wins), 'losses': len(losses),
            'wr': len(wins)/len(t)*100,
            'avg': np.mean([x['ret'] for x in t]),
            'max_win': max([x['ret'] for x in t]),
            'max_loss': min([x['ret'] for x in t])
        }
    return results

# Main
print('='*70)
print(' Marcus Top100+ v4')
print('='*70)

inst_map = load_inst()
print(f"法人資料: {len(inst_map)} 檔")

print('\n[ 回測中... ]')
trades = backtest(inst_map, days=180)
results = analyze(trades)

print('\n' + '='*70)
print(' 結果')
print('='*70)
for tier in ['tier1', 'tier2', 'tier3', 'all']:
    r = results[tier]
    if r:
        name = {'tier1': 'Tier1 科技', 'tier2': 'Tier2 供應鏈', 'tier3': 'Tier3 藍籌', 'all': '整體'}[tier]
        print(f'\n{name}:')
        print(f'  交易: {r["total"]} | 勝: {r["wins"]} | 敗: {r["losses"]} | 勝率: {r["wr"]:.1f}%')
        print(f'  平均: {r["avg"]:+.2f}% | 最大: {r["max_win"]:+.2f}% | 最小: {r["max_loss"]:+.2f}%')

print('\n' + '='*70)

output = {
    'date': '2026-04-23',
    'stocks_tested': len(ALL_STOCKS),
    'inst_coverage': len(inst_map),
    'results': {k: v for k, v in results.items() if v}
}
with open('reports/marcus_top100_results.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print(f'完成! {len(ALL_STOCKS)} 檔測試')
