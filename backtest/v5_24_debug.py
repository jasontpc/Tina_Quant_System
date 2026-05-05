# -*- coding: utf-8 -*-
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
import json
from datetime import datetime

DB = 'skills/stock-analyzer/scripts/tina_master.db'

ETF_POOL = ['0050','0056','00646','00662','00713','00891','00900','00902']
BLACKLIST = ['2451','2330','1605','6230','2454','2308','3034','3413','2458','2379','8081']
STOCK_POOL = ['2382','2884','2474','2303','2317','2353','2377','2345','3717','4938','3017']
ALL_CANDIDATES = ETF_POOL + [s for s in STOCK_POOL if s not in BLACKLIST]

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
    atr = np.mean(tr[-14:]) if len(tr) >= 14 else 30
    return (atr / close[-1]) * 100 if close[-1] > 0 else 0

def kdj(h, i, n=9):
    low_n = h['Low'].iloc[max(0,i-n):i+1].min()
    high_n = h['High'].iloc[max(0,i-n):i+1].max()
    close = h['Close'].iloc[i]
    rsv = (close - low_n) / (high_n - low_n) * 100 if high_n != low_n else 50
    k = 50
    d = 50
    j = 3 * k - 2 * d
    k = 2/3 * 50 + 1/3 * rsv
    d = 2/3 * 50 + 1/3 * k
    j = 3 * k - 2 * d
    return k, d, j

def macd(p, fast=12, slow=26, signal=9):
    ema_fast = pd.Series(p).ewm(span=fast).mean()
    ema_slow = pd.Series(p).ewm(span=slow).mean()
    macd_val = ema_fast - ema_slow
    signal_line = macd_val.ewm(span=signal).mean()
    return macd_val.iloc[-1], signal_line.iloc[-1]

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

inst_map = load_inst()

def backtest_v524(inst_map, days=300):
    end_date = '2026-04-23'
    start_date = (pd.to_datetime(end_date) - pd.Timedelta(days=days)).strftime('%Y-%m-%d')
    
    all_trades = []
    stock_stats = {}
    
    for code in ALL_CANDIDATES:
        try:
            tk = yf.Ticker(code + '.TW' if code.isdigit() else code)
            h = tk.history(period='1y')
            if len(h) < 30: 
                print('[%s] 資料不足 %d rows' % (code, len(h)))
                continue
            cl = list(h['Close'].values)
            vol = list(h['Volume'].values)
            
            stock_stats[code] = {'total': 0, 'wins': 0, 'losses': 0, 'rets': []}
            
            trades_count = 0
            for i in range(25, len(cl)-6):
                rs = rsi(cl[:i+1])
                ma20 = np.mean(cl[i-19:i+1])
                ma60 = np.mean(cl[i-59:i+1]) if i >= 60 else np.mean(cl[:i+1])
                atr = calc_atr(h, i)
                k, d, j = kdj(h, i)
                macd_val, signal_val = macd(cl[:i+1])
                date_str = str(h.index[i])[:10]
                
                # === 進場條件 ===
                if not (40 <= rs <= 70): continue
                if ma20 <= ma60 * 0.98: continue
                if cl[i] < ma20 * 0.98: continue
                if not (k > d and j > 0): continue
                if not (macd_val > signal_val): continue
                if atr < 0.3: continue
                
                # === 法人條件 ===
                has_inst = code in inst_map
                if has_inst:
                    f_days, t_days = 0, 0
                    for dd in range(1, 4):
                        dt = (pd.to_datetime(date_str) - pd.Timedelta(days=dd)).strftime('%Y-%m-%d')
                        if dt in inst_map[code]:
                            if inst_map[code][dt][0] > 0: f_days += 1
                            if inst_map[code][dt][1] > 0: t_days += 1
                    if f_days < 1 and t_days < 1: continue
                else:
                    # ETF without inst data - allow
                    if code not in ETF_POOL: continue
                
                entry = h['Open'].iloc[i+1] if i+1 < len(h) else cl[i]
                exit_p = cl[min(i+6, len(cl)-1)]
                ret = (exit_p / entry - 1) * 100 - 0.45
                
                all_trades.append({'ret': ret, 'code': code, 'rsi': rs})
                stock_stats[code]['total'] += 1
                stock_stats[code]['rets'].append(ret)
                if ret > 0:
                    stock_stats[code]['wins'] += 1
                else:
                    stock_stats[code]['losses'] += 1
                trades_count += 1
            print('[%s] %d rows, %d trades found' % (code, len(cl), trades_count))
        except Exception as e:
            print('[%s] Error: %s' % (code, str(e)))
        time.sleep(0.1)
    
    return all_trades, stock_stats

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
print(' Tina v5.24 - 自動化循環第36輪')
print('='*70)

trades, stats = backtest_v524(inst_map, days=300)
result = analyze(trades)

if result:
    print('\n[ v5.24 總結果 ]')
    print('  總交易筆數: %d' % result['total'])
    print('  勝率 (WR): %.1f%%' % result['wr'])
    print('  平均報酬 (Avg): %.2f%%' % result['avg'])
else:
    print('[錯誤] 無交易資料')
    result = {'total': 0, 'wr': 0, 'avg': 0, 'max_win': 0, 'max_loss': 0}
