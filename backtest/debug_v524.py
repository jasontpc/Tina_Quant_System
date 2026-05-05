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
    return np.mean(tr[-14:]) if len(tr) >= 14 else 30

def kdj(h, i, n=9):
    low_n = h['Low'].iloc[max(0,i-n):i+1].min()
    high_n = h['High'].iloc[max(0,i-n):i+1].max()
    close = h['Close'].iloc[i]
    rsv = (close - low_n) / (high_n - low_n) * 100 if high_n != low_n else 50
    k = 50
    d = 50
    j = 3 * k - 2 * d
    # EMA-style smoothing
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
print('Loaded inst data for %d symbols' % len(inst_map))
print('ETF_POOL has inst data:', [k for k in ETF_POOL if k in inst_map])
print('STOCK_POOL has inst data:', [k for k in STOCK_POOL if k in inst_map])

# Test single stock
code = '0050'
h = yf.Ticker(code + '.TW').history(period='1y')
cl = list(h['Close'].values)
vol = list(h['Volume'].values)
print('\nTesting %s: %d rows, first RSI=%.1f' % (code, len(cl), rsi(cl[:30])))

trades_found = 0
for i in range(25, len(cl)-6):
    rs = rsi(cl[:i+1])
    ma20 = np.mean(cl[i-19:i+1])
    ma60 = np.mean(cl[i-59:i+1]) if i >= 60 else np.mean(cl[:i+1])
    atr = calc_atr(h, i)
    k, d, j = kdj(h, i)
    macd_val, signal_val = macd(cl[:i+1])
    date_str = str(h.index[i])[:10]
    
    cond_rsi = 40 <= rs <= 70
    cond_ma = ma20 > ma60 * 0.98
    cond_price = cl[i] >= ma20 * 0.98
    cond_kdj = k > d and j > 0
    cond_macd = macd_val > signal_val
    cond_atr = atr >= 20
    
    has_inst = code in inst_map
    if has_inst:
        f_days, t_days = 0, 0
        for dd in range(1, 4):
            dt = (pd.to_datetime(date_str) - pd.Timedelta(days=dd)).strftime('%Y-%m-%d')
            if dt in inst_map[code]:
                if inst_map[code][dt][0] > 0: f_days += 1
                if inst_map[code][dt][1] > 0: t_days += 1
        cond_inst = f_days >= 1 or t_days >= 1
    else:
        cond_inst = True
    
    if all([cond_rsi, cond_ma, cond_price, cond_kdj, cond_macd, cond_atr, cond_inst]):
        trades_found += 1
        if trades_found <= 3:
            print('Trade at i=%d: RSI=%.1f, K=%.1f, D=%.1f, MACD=%.4f, ATR=%.1f' % (i, rs, k, d, macd_val, atr))
            print('  MA20=%.2f, MA60=%.2f, cond_ma=%s, cond_kdj=%s, cond_macd=%s' % (ma20, ma60, cond_ma, cond_kdj, cond_macd))

print('Total trades for %s: %d' % (code, trades_found))
