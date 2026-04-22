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

def bt(params, stocks, inst_map, use_inst=False, inst_days=3):
    all_trades = []
    for code in stocks:
        try:
            h = yf.Ticker(code+'.TW').history(start='2026-01-01', end='2026-03-31')
            if len(h) < 25: continue
            cl, vol = list(h['Close']), list(h['Volume'])
            
            for i in range(25, len(cl)):
                rs = rsi(cl[:i+1])
                ma20 = np.mean(cl[i-20:i])
                atr = calc_atr(h, i)
                date_str = str(h.index[i])[:10]
                
                if rs >= params.get('max_rsi', 65): continue
                if cl[i] < ma20: continue
                if atr < params.get('min_atr', 30): continue
                
                if use_inst and code in inst_map:
                    f_days, t_days = 0, 0
                    for d in range(1, inst_days+1):
                        dt = (pd.to_datetime(date_str) - pd.Timedelta(days=d)).strftime('%Y-%m-%d')
                        if dt in inst_map[code]:
                            if inst_map[code][dt][0] > 0: f_days += 1
                            if inst_map[code][dt][1] > 0: t_days += 1
                    if max(f_days, t_days) < 1: continue
                elif use_inst:
                    continue
                
                entry = h['Open'].iloc[i+1] if i+1 < len(h) else cl[i]
                exit_p = cl[min(i+6,len(cl)-1)]
                ret = (exit_p / entry - 1) * 100 - 0.45
                all_trades.append(ret)
        except:
            pass
        time.sleep(0.05)
    return all_trades

stocks = ['2330','2454','3034','2002','1301','1326','1216','2610','2891','2881',
    '5871','6505','3665','3017','2345','6230','3583','2360','6139','3189',
    '2308','2474','3033','3338','3702','4938','5880','6770','8046','8454',
    '8478','8499','3711','4961','2379','2451','2201','2207','2231','2352',
    '2353','2354','2356','2371','2373','2376','2383','2385','2392','2393',
    '2401','2402','2404','2412','2420','2423','2425','2426','2427','2428',
    '2429','2430','2431','2432','2433','2434','2436','2438','2439','4952',
    '6415','6183','2618','2630','2892','2884','2886','2887','2890']

blacklist = ['2615', '1590', '2382', '2317', '2303', '3008', '3231', '2408', '3443', '6446', '6669']
stocks = [s for s in stocks if s not in blacklist]

print('='*60)
print(' Q1 2026 信號數量優化')
print('='*60)

inst_map = load_inst()

configs = [
    ('RSI<65', {'max_rsi': 65, 'min_atr': 30}),
    ('RSI<68', {'max_rsi': 68, 'min_atr': 30}),
    ('RSI<70', {'max_rsi': 70, 'min_atr': 30}),
    ('ATR>=25', {'max_rsi': 65, 'min_atr': 25}),
    ('ATR>=20', {'max_rsi': 65, 'min_atr': 20}),
    ('Inst 1d', {'max_rsi': 65, 'min_atr': 30}),
]

results = []
for name, params in configs:
    trades = bt(params, stocks, inst_map, use_inst=('Inst' in name), inst_days=1 if 'Inst' in name else 3)
    if trades:
        wins = len([t for t in trades if t > 0])
        wr = wins / len(trades) * 100
        avg = np.mean(trades)
        print('%s: %d signals, WR=%.1f%%, Avg=%+.2f%%' % (name, len(trades), wr, avg))
        results.append({'name': name, 'wr': wr, 'signals': len(trades), 'avg': avg})

results.sort(key=lambda x: x['signals'], reverse=True)
print()
print('='*60)
print(' 排序 (按信號數)')
print('='*60)
for r in results:
    print('%s: %d signals, WR=%.1f%%' % (r['name'], r['signals'], r['wr']))