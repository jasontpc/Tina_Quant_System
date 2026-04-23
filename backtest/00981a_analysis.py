# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import numpy as np
import sqlite3

DB = 'skills/stock-analyzer/scripts/tina_master.db'

print('='*70)
print(' 00981A 主動統一台股增長 - 分析 (2026-04-23)')
print('='*70)

h = yf.Ticker('00981A.TW').history(period='90d')
if len(h) < 30:
    print('資料不足')
else:
    p = list(h['Close'])
    current = float(p[-1])
    prev = float(p[-2])
    change = (current / prev - 1) * 100
    
    ma5 = np.mean(p[-5:])
    ma10 = np.mean(p[-10:])
    ma20 = np.mean(p[-20:])
    ma60 = np.mean(p[-60:]) if len(p) >= 60 else np.mean(p)
    
    bias = (current / ma20 - 1) * 100
    
    d = np.diff(p)
    g = np.where(d > 0, d, 0)
    l = np.where(d > 0, 0, -d)
    ag = np.mean(g[-14:])
    al = np.mean(l[-14:])
    rs = 100 - (100 / (1 + ag / al)) if al != 0 else 50
    
    trs = []
    for i in range(-15, 0):
        hi = float(h['High'].iloc[i])
        lo = float(h['Low'].iloc[i])
        cl_p = float(h['Close'].iloc[i-1])
        trs.append(max(hi-lo, abs(hi-cl_p), abs(lo-cl_p)))
    atr = np.mean(trs)
    atr_pct = atr / current * 100
    
    vol = list(h['Volume'])
    vr = vol[-1] / np.mean(vol[-5:]) if np.mean(vol[-5:]) > 0 else 0
    
    ma5_icon = '↑' if current > ma5 else '↓'
    ma10_icon = '↑' if current > ma10 else '↓'
    ma20_icon = '↑' if current > ma20 else '↓'
    
    print()
    print('【技術面】')
    print(f' 現價: {current:.2f} ({change:+.2f}%)')
    print(f' MA5:  {ma5:.2f} {ma5_icon}')
    print(f' MA10: {ma10:.2f} {ma10_icon}')
    print(f' MA20: {ma20:.2f} {ma20_icon}')
    print(f' MA60: {ma60:.2f}')
    print(f' RSI:  {rs:.1f}')
    print(f' ATR:  {atr:.3f} ({atr_pct:.2f}%)')
    print(f' VR:   {vr:.2f}')
    print(f' Bias: {bias:+.2f}%')
    print()
    print(f' 交叉: MA5>MA20? {"是" if ma5 > ma20 else "否"}')
    print()
    print('【v4.21 評估】')
    print(f'  RSI < 70:     {"Y" if rs < 70 else "N"} ({rs:.1f})')
    print(f'  ATR >= 0.5%:  {"Y" if atr_pct >= 0.5 else "N"} ({atr_pct:.2f}%)')
    print(f'  MA20 > MA60: {"Y" if ma20 > ma60 else "N"}')
    print(f'  Bias < 10%:   {"Y" if abs(bias) < 10 else "N"} ({bias:.2f}%)')
    print(f'  VR >= 1.0:    {"Y" if vr >= 1.0 else "N"} ({vr:.2f})')

print()
print('='*70)
print('【法人資金】')
print('='*70)

conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute('SELECT date, foreign_net, trust_net FROM MarketData WHERE symbol = ? ORDER BY date DESC LIMIT 10', ('00981A',))
rows = cur.fetchall()
conn.close()

f_sum = t_sum = 0
for date, f, t in rows:
    f_str = '%+10.0f' % f if f else '-'
    t_str = '%+10.0f' % t if t else '-'
    f_a = '↑' if f and f > 0 else '↓' if f and f < 0 else ' '
    t_a = '↑' if t and t > 0 else '↓' if t and t < 0 else ' '
    print(f' {date}  {f_str} {f_a}  {t_str} {t_a}')
    if f: f_sum += f
    if t: t_sum += t

print()
print(f' 法人近10日: 外資 {f_sum:+,.0f} | 投信 {t_sum:+,.0f}')
print()
print('='*70)