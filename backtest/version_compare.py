# -*- coding: utf-8 -*-
"""
Tina 版本比較回測
v4.21 vs v4.3 vs v4.22
市值前100大
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import numpy as np
import sqlite3

DB = 'skills/stock-analyzer/scripts/tina_master.db'

# Top 100 (精簡版常見股)
TOP100 = [
    '2330','2454','2317','2382','3034','2379','2451','2308','2345','2353',
    '2395','2401','2421','2449','2474','2492','2610','2880','2881','2882',
    '2883','2884','2885','2886','2887','2888','2891','2892','3008','3033',
    '3044','3189','3229','3231','3443','3481','3665','3717','4938','4958',
    '4961','5871','5880','6409','6415','6505','6669','6770','8016','8046',
    '8105','8233','8261','8341','8464','8478','8926','8996','9945','1234',
    '2312','2327','2337','2344','2385','2390','2515','2527','2603','2609',
    '2707','2823','2834','2855','2912','2939','3029','3045','3088','3105',
    '3234','3257','3294','3305','3380','3416','3443','3533','3557','3593',
    '3596','3610','3673','3686','3702','3711','3722','4001','4002','4904'
]

def get_ma20_ma60(h):
    close = h['Close'].values
    ma20 = np.mean(close[-20:])
    ma60 = np.mean(close[-60:]) if len(close) >= 60 else close[-1]
    return ma20, ma60

def get_rsi(h):
    close = h['Close'].values
    d = np.diff(close)
    g = np.where(d > 0, d, 0)
    l = np.where(d > 0, 0, -d)
    ag = np.mean(g[-14:])
    al = np.mean(l[-14:])
    return 100 - (100 / (1 + ag / al)) if al != 0 else 50

def get_atr(h):
    close = h['Close'].values
    trs = []
    for i in range(-15, 0):
        hi = float(h['High'].iloc[i])
        lo = float(h['Low'].iloc[i])
        cl_prev = float(h['Close'].iloc[i-1])
        trs.append(max(hi-lo, abs(hi-cl_prev), abs(lo-cl_prev)))
    return np.mean(trs)

def check_inst(code, days=3):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('''
        SELECT COUNT(*) FROM MarketData
        WHERE symbol = ? AND date >= date('now', '-' || ? || ' days')
        AND (foreign_net > 0 OR trust_net > 0)
    ''', (code, days))
    count = cur.fetchone()[0]
    conn.close()
    return count >= 1

def analyze(code, version):
    try:
        h = yf.Ticker(code + '.TW').history(period='180d')
        if len(h) < 60:
            return None
        
        close = float(h['Close'].iloc[-1])
        prev = float(h['Close'].iloc[-2])
        change = (close / prev - 1) * 100
        
        ma20, ma60 = get_ma20_ma60(h)
        rsi = get_rsi(h)
        atr = get_atr(h)
        atr_pct = atr / close * 100
        
        inst = check_inst(code)
        
        # 各版本條件
        if version == 'v4.21':
            ok = rsi < 70 and atr_pct >= 0.5 and ma20 > ma60 and inst
        elif version == 'v4.3':
            ok = 40 <= rsi <= 70 and atr_pct >= 0.3 and inst
        elif version == 'v4.22':
            ok = rsi < 75 and ma20 > ma60 and inst
        else:
            ok = False
        
        return {
            'code': code,
            'price': close,
            'change': change,
            'rsi': rsi,
            'atr': atr_pct,
            'ma20': ma20,
            'ma60': ma60,
            'inst': inst,
            'ok': ok
        }
    except:
        return None

def run_backtest(version):
    results = []
    for code in TOP100:
        r = analyze(code, version)
        if r:
            results.append(r)
    
    signals = [r for r in results if r['ok']]
    signals.sort(key=lambda x: x['change'], reverse=True)
    
    return signals, results

# 執行三版本
for v in ['v4.21', 'v4.3', 'v4.22']:
    print()
    print('='*60)
    print(' ' + v + ' 版本回測')
    print('='*60)
    
    signals, all_stocks = run_backtest(v)
    
    # 統計
    total = len(all_stocks)
    signal_count = len(signals)
    win_count = len([s for s in signals if s['change'] > 0])
    win_rate = win_count / signal_count * 100 if signal_count > 0 else 0
    avg_change = np.mean([s['change'] for s in signals]) if signal_count > 0 else 0
    
    print()
    print(' 總股票: ' + str(total) + ' 檔')
    print(' 符合條件: ' + str(signal_count) + ' 檔 (' + str(round(signal_count/total*100,1)) + '%)')
    print(' 上漲: ' + str(win_count) + ' 檔 (' + str(round(win_rate,1)) + '%)')
    print(' 平均漲跌: ' + str(round(avg_change,2)) + '%')
    
    if signal_count > 0:
        print()
        print(' 前5名:')
        for i, s in enumerate(signals[:5], 1):
            icon = '▲' if s['change'] > 0 else '▼'
            print('  ' + str(i) + '. ' + s['code'] + ' ' + str(round(s['price'])) + ' ' + icon + str(round(abs(s['change']),1)) + '% RSI=' + str(round(s['rsi'])))
    
    print()

print('='*60)
print(' 版本比較總結')
print('='*60)