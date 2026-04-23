# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import numpy as np
import sqlite3

DB = 'skills/stock-analyzer/scripts/tina_master.db'

for code, name in [('3231','緯創'), ('3034','聯詠')]:
    print('='*60)
    print(' ' + code + ' ' + name)
    print('='*60)
    
    h = yf.Ticker(code+'.TW').history(period='90d')
    p = list(h['Close'])
    current = float(p[-1])
    prev = float(p[-2])
    change = (current/prev-1)*100
    
    ma20 = np.mean(p[-20:])
    ma60 = np.mean(p[-60:]) if len(p) >= 60 else ma20
    bias = (current/ma20-1)*100
    
    d = np.diff(p)
    g = np.where(d > 0, d, 0)
    l = np.where(d > 0, 0, -d)
    ag = np.mean(g[-14:])
    al = np.mean(l[-14:])
    rs = 100-(100/(1+ag/al)) if al != 0 else 50
    
    trs = []
    for i in range(-15,0):
        hi = float(h['High'].iloc[i])
        lo = float(h['Low'].iloc[i])
        cl_p = float(h['Close'].iloc[i-1])
        trs.append(max(hi-lo,abs(hi-cl_p),abs(lo-cl_p)))
    atr = np.mean(trs)
    atr_pct = atr/current*100
    
    vol = list(h['Volume'])
    vr = vol[-1]/np.mean(vol[-5:]) if np.mean(vol[-5:]) > 0 else 0
    
    arrow = '▲' if change > 0 else '▼' if change < 0 else '―'
    
    print(' 現價: ' + str(current) + ' (' + arrow + str(round(change,2)) + '%)')
    print(' RSI: ' + str(round(rs,1)))
    print(' Bias: ' + str(round(bias,2)) + '%')
    print(' ATR: ' + str(round(atr_pct,2)) + '%')
    print(' VR: ' + str(round(vr,2)))
    print(' MA20: ' + str(round(ma20,2)) + ' | MA60: ' + str(round(ma60,2)))
    print()
    
    rsi_ok = rs < 70
    atr_ok = atr_pct >= 0.5
    ma_ok = ma20 > ma60
    bias_ok = abs(bias) < 10
    
    print(' v4.21:')
    print('  RSI<70:     ' + ('Y' if rsi_ok else 'N') + ' (' + str(round(rs,1)) + ')')
    print('  ATR>=0.5%:  ' + ('Y' if atr_ok else 'N') + ' (' + str(round(atr_pct,2)) + '%)')
    print('  MA20>MA60:  ' + ('Y' if ma_ok else 'N'))
    print('  Bias<10%:   ' + ('Y' if bias_ok else 'N') + ' (' + str(round(bias,2)) + '%)')
    print()
    
    all_ok = rsi_ok and atr_ok and ma_ok and bias_ok
    if all_ok:
        print(' 結論: ✅ 完全符合，可考慮進場')
    else:
        fails = []
        if not rsi_ok: fails.append('RSI')
        if not atr_ok: fails.append('ATR')
        if not ma_ok: fails.append('MA')
        if not bias_ok: fails.append('Bias')
        print(' 結論: 🟡 部分符合 (' + ', '.join(fails) + ' 未達)')
    
    print()
    
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('SELECT date, foreign_net, trust_net FROM MarketData WHERE symbol = ? ORDER BY date DESC LIMIT 5', (code,))
    rows = cur.fetchall()
    conn.close()
    
    f_sum = t_sum = 0
    for date, f, t in rows:
        f_a = '↑' if f and f > 0 else '↓' if f and f < 0 else '-'
        t_a = '↑' if t and t > 0 else '↓' if t and t < 0 else '-'
        f_str = str(round(f)) if f else '0'
        t_str = str(round(t)) if t else '0'
        print(' ' + str(date) + '  f:' + f_str + f_a + '  t:' + t_str + t_a)
        if f: f_sum += f
        if t: t_sum += t
    print('  法人近5日: 外資 ' + str(round(f_sum)) + ' | 投信 ' + str(round(t_sum)))
    print()

print('='*60)