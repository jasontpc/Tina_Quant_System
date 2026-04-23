# -*- coding: utf-8 -*-
"""
Marcus - Top100+ 最終版
目標: 突破 100 檔，擴充藍籌覆蓋
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
from datetime import datetime

DB = 'data/tina_master.db'

# ============== 擴充股票池 ==============

# Tier1: 科技/AI 領頭羊 (30檔)
TIER1_AI = [
    '2330', '2454', '2317', '2303', '3034', '2379', '3008', '2382',
    '3231', '3717', '4938', '2345', '3017', '6230', '2451', '3665',
    '4961', '6477', '3406', '2385', '5521', '6153', '2458', '2377',
    '6515', '6533', '6531', '2492', '2474', '3532',
]

# Tier2: 相關供應鏈 (30檔)
TIER2_SUPPLY = [
    '1590', '2308', '2344', '2401', '2404', '3033', '3686', '3702',
    '4935', '4952', '5215', '5469', '6139', '6183', '6257', '6415',
    '6446', '6770', '8046', '8081', '9917', '2481', '3545', '3593',
    '4722', '4968', '6239', '8261', '9955', '3532',
]

# Tier3: 藍籌/高股息/傳產/金融 (45檔)
TIER3_BLUE = [
    # 金控
    '2881', '2882', '2884', '2885', '2886', '2887', '2891', '2892', '2890',
    # 官股行庫
    '2801', '2812', '2834', '5871',
    # 傳產
    '1301', '1326', '2002', '1216', '1215', '2610', '2603',
    '2609', '2630', '3035', '3044', '3413', '3481', '2409', '4904',
    '2412', '3045', '6213', '6505', '9914', '9921', '1536', '6605',
    '2471', '2498', '3543', '4746', '8464', '2707', '9945',
]

BLACKLIST = ['2615', '1590', '2382', '2317', '2303', '3008', '3231', '2408', '3443', '6446', '6669', '2597']

TIER1 = [s for s in TIER1_AI if s not in BLACKLIST][:30]
TIER2 = [s for s in TIER2_SUPPLY if s not in BLACKLIST][:30]
TIER3 = [s for s in TIER3_BLUE if s not in BLACKLIST][:45]

ALL_STOCKS = TIER1 + TIER2 + TIER3
print(f"Tier1 (AI/科技): {len(TIER1)} 檔")
print(f"Tier2 (供應鏈): {len(TIER2)} 檔")
print(f"Tier3 (藍籌): {len(TIER3)} 檔")
print(f"總計: {len(ALL_STOCKS)} 檔")

# ============== 法人資料載入 ==============
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
    except:
        pass
    return inst

# ============== 技術指標 ==============
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

# ============== 回測引擎 ==============
def backtest_top100(inst_map, days=180):
    end_date = '2026-04-23'
    start_date = (pd.to_datetime(end_date) - pd.Timedelta(days=days)).strftime('%Y-%m-%d')
    
    all_trades = {'tier1': [], 'tier2': [], 'tier3': [], 'all': []}
    failed = []
    
    tier_map = {}
    for s in TIER1: tier_map[s] = 'tier1'
    for s in TIER2: tier_map[s] = 'tier2'
    for s in TIER3: tier_map[s] = 'tier3'
    
    for idx, code in enumerate(ALL_STOCKS):
        try:
            h = yf.Ticker(code+'.TW').history(start=start_date, end=end_date)
            if len(h) < 30: 
                failed.append(code)
                continue
            cl = list(h['Close'])
            vol = list(h['Volume'])
            
            for i in range(25, len(cl)-6):
                rs = rsi(cl[:i+1])
                ma20 = np.mean(cl[i-19:i+1])
                ma60 = np.mean(cl[i-59:i+1]) if i >= 60 else np.mean(cl[:i+1])
                atr = calc_atr(h, i)
                macd_val, signal_val = macd_signal(cl[:i+1])
                date_str = str(h.index[i])[:10]
                vr = vol[i] / np.mean(vol[i-19:i+1]) if np.mean(vol[i-19:i+1]) > 0 else 0
                
                # 通用技術面條件
                if not (40 <= rs <= 70): continue
                if ma20 <= ma60: continue
                if cl[i] < ma20: continue
                if not (macd_val > signal_val): continue
                if atr < 30: continue
                
                tier = tier_map.get(code, 'tier3')
                
                if tier == 'tier2':
                    # 法人輔助
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
                    # 藍籌: 放寬條件，不要求 VR
                    if rs > 68: continue
                    if atr < 20: continue
                
                entry = h['Open'].iloc[i+1] if i+1 < len(h) else cl[i]
                exit_p = cl[min(i+6, len(cl)-1)]
                ret = (exit_p / entry - 1) * 100 - 0.45
                
                trade = {
                    'ret': ret, 'rsi': rs, 'atr': atr, 'vr': vr,
                    'bias': (cl[i]/ma20-1)*100, 'code': code, 'tier': tier
                }
                
                all_trades[tier].append(trade)
                all_trades['all'].append(trade)
                
        except Exception as e:
            failed.append(code)
        time.sleep(0.05)
        
        if (idx + 1) % 25 == 0:
            print(f"  已處理 {idx+1}/{len(ALL_STOCKS)} 檔...")
    
    return all_trades, failed

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
            'max_win': max([x['ret'] for x in t]) if t else 0,
            'max_loss': min([x['ret'] for x in t]) if t else 0
        }
    return results

# ============== 主程式 ==============
print('='*70)
print(' Marcus Top100+ 最終版')
print('='*70)

inst_map = load_inst()
print(f"\n法人資料覆蓋: {len(inst_map)} 檔")

print('\n[ 回測中 (180天)... ]')
trades, failed = backtest_top100(inst_map, days=180)
results = analyze(trades)

print(f"\n無法取得資料的股票 ({len(failed)} 檔): {failed}")

print('\n' + '='*70)
print(' 回測結果 (180天)')
print('='*70)

for tier in ['tier1', 'tier2', 'tier3', 'all']:
    r = results[tier]
    if r:
        tier_name = {'tier1': 'Tier1 科技/AI', 'tier2': 'Tier2 供應鏈', 'tier3': 'Tier3 藍籌', 'all': '整體'}[tier]
        print(f'\n{tier_name}:')
        print(f'  總交易: {r["total"]} | 勝: {r["wins"]} | 敗: {r["losses"]}')
        print(f'  勝率: {r["wr"]:.1f}%')
        print(f'  平均報酬: {r["avg"]:+.2f}%')
        print(f'  最大獲利: {r["max_win"]:+.2f}%')
        print(f'  最大虧損: {r["max_loss"]:+.2f}%')
    else:
        print(f'\n{tier}: 無交易資料')

print('\n' + '='*70)

# Save results
output = {
    'date': '2026-04-23',
    'stocks_tested': len(ALL_STOCKS),
    'stocks_failed': len(failed),
    'failed_codes': failed,
    'inst_coverage': len(inst_map),
    'stock_list': {
        'tier1': TIER1,
        'tier2': TIER2,
        'tier3': TIER3
    },
    'results': {k: v for k, v in results.items() if v}
}
with open('reports/marcus_top100_results.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print('結果已儲存到 reports/marcus_top100_results.json')
