# -*- coding: utf-8 -*-
"""
市值前100大個股 - 180天回測 (簡化版)
技術面: KDJ + MACD + MA
籌碼面: 外資/投信買超
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import warnings
warnings.filterwarnings('ignore')
import yfinance as yf
yf.suppress_errors=True
import numpy as np
import sqlite3
import pandas as pd
import time

DB = 'skills/stock-analyzer/scripts/tina_master.db'

STOCKS = ['2330','2454','3034','2002','1301','1326','1216','2610','2891','2881',
    '5871','6505','3665','3017','2345','6230','3583','2360','6139','3189',
    '2308','2474','3033','3338','3702','4938','5880','6770','8046','8454',
    '8478','8499','3711','4961','2379','2451','2201','2207','2231','2352',
    '2353','2354','2356','2371','2373','2376','2383','2385','2392','2393',
    '2401','2402','2404','2412','2420','2423','2425','2426','2427','2428',
    '2429','2430','2431','2432','2433','2434','2436','2438','2439','4952',
    '6415','6183','2618','2630','2892','2884','2886','2887','2890']

BLACKLIST = ['2615', '1590', '2382', '2317', '2303', '3008', '3231', '2408', '3443', '6446', '6669', '2597']
STOCKS = [s for s in STOCKS if s not in BLACKLIST][:100]

def load_inst():
    inst = {}
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('SELECT symbol, date, foreign_net, trust_net FROM MarketData')
    for sym, date, f, t in cur.fetchall():
        if sym not in inst: inst[sym] = {}
        inst[sym][date] = (f or 0, t or 0)
    conn.close()
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

def backtest(inst_map, days=180):
    end_date = '2026-04-23'
    start_date = (pd.to_datetime(end_date) - pd.Timedelta(days=days)).strftime('%Y-%m-%d')
    
    all_trades = []
    for code in STOCKS:
        try:
            h = yf.Ticker(code+'.TW').history(start=start_date, end=end_date)
            if len(h) < 30: continue
            cl, vol = list(h['Close']), list(h['Volume'])
            
            for i in range(25, len(cl)-6):
                rs = rsi(cl[:i+1])
                ma20 = np.mean(cl[i-19:i+1])
                atr = calc_atr(h, i)
                date_str = str(h.index[i])[:10]
                
                # === 技術面進場條件 (簡化) ===
                # 1. RSI < 70
                if rs >= 70: continue
                # 2. 價格站上 MA20
                if cl[i] < ma20: continue
                # 3. ATR 足夠
                if atr < 30: continue
                
                # === 籌碼面進場條件 ===
                if code in inst_map:
                    f_days, t_days = 0, 0
                    for dd in range(1, 4):
                        dt = (pd.to_datetime(date_str) - pd.Timedelta(days=dd)).strftime('%Y-%m-%d')
                        if dt in inst_map[code]:
                            if inst_map[code][dt][0] > 0: f_days += 1
                            if inst_map[code][dt][1] > 0: t_days += 1
                    # 法人至少1天買超
                    if max(f_days, t_days) < 1: continue
                else:
                    continue
                
                entry = h['Open'].iloc[i+1] if i+1 < len(h) else cl[i]
                exit_p = cl[min(i+6, len(cl)-1)]
                ret = (exit_p / entry - 1) * 100 - 0.45
                
                all_trades.append({
                    'ret': ret, 'rsi': rs, 'atr': atr, 'code': code
                })
        except:
            pass
        time.sleep(0.05)
    return all_trades

def analyze(trades):
    if not trades: return None
    wins = [t for t in trades if t['ret'] > 0]
    losses = [t for t in trades if t['ret'] <= 0]
    return {
        'total': len(trades), 'wins': len(wins), 'losses': len(losses),
        'wr': len(wins)/len(trades)*100,
        'avg': np.mean([t['ret'] for t in trades]),
        'max_win': max([t['ret'] for t in trades]) if trades else 0,
        'max_loss': min([t['ret'] for t in trades]) if trades else 0
    }

print('='*70)
print(' 市值前100大個股 - 180天回測 (簡化版)')
print(' 技術面: RSI + MA20 + ATR')
print(' 籌碼面: 外資/投信買超')
print('='*70)

inst_map = load_inst()

print('\n[ 回測中 (180天: %s 至 %s)...]' % ('2025-10-23', '2026-04-23'))
trades = backtest(inst_map, days=180)
result = analyze(trades)

if result:
    print('\n'+'='*70)
    print(' 回測結果 (180天)')
    print('='*70)
    print(' 總交易次數: %d' % result['total'])
    print(' 勝利: %d' % result['wins'])
    print(' 失敗: %d' % result['losses'])
    print(' 勝率: %.1f%%' % result['wr'])
    print(' 平均報酬: %+.2f%%' % result['avg'])
    print(' 最大獲利: %+.2f%%' % result['max_win'])
    print(' 最大虧損: %+.2f%%' % result['max_loss'])
else:
    print(' 無交易資料')
print('='*70)