# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import numpy as np

ETFS = [
    ('0050', '元大台灣50'),
    ('00830', '富邦NASDAQ'),
    ('00891', '中信關鍵半導體'),
    ('00927', '永豐優息存股'),
    ('00713', '元大高息低波'),
    ('0056', '元大高股息'),
]

print('='*75)
print(' ETF 技術分析 + K線形態 (2026-04-23)')
print('='*75)

for code, name in ETFS:
    try:
        h = yf.Ticker(code + '.TW').history(period='60d')
        if len(h) < 30:
            continue
        
        prices = list(h['Close'])
        
        current = float(prices[-1])
        prev = float(prices[-2])
        change = (current / prev - 1) * 100
        
        print()
        print(f'【{code} {name}】 現價: {current:.2f} ({change:+.2f}%)')
        print('-'*60)
        
        # 近期K線形態 (5根)
        ktypes = []
        for i in range(-5, 0):
            o = float(h['Open'].iloc[i])
            c = float(h['Close'].iloc[i])
            if c > o:
                ktypes.append('陽')
            elif c < o:
                ktypes.append('陰')
            else:
                ktypes.append('十')
        print(f'  近期K線: {" ".join(ktypes)}')
        
        # 5日趨勢
        last5 = prices[-5:]
        if all(last5[j] < last5[j+1] for j in range(4)):
            trend = '▲ 5連漲'
        elif all(last5[j] > last5[j+1] for j in range(4)):
            trend = '▼ 5連跌'
        else:
            trend = '→ 震盪'
        print(f'  趨勢: {trend}')
        
        # MA
        ma5 = np.mean(prices[-5:])
        ma10 = np.mean(prices[-10:])
        ma20 = np.mean(prices[-20:])
        ma60 = np.mean(prices[-60:]) if len(prices) >= 60 else ma20
        
        ma20_above = '↑' if current > ma20 else '↓'
        ma5_above = '↑' if current > ma5 else '↓'
        print(f'  MA5: {ma5:.2f} {ma5_above} | MA20: {ma20:.2f} {ma20_above} | MA60: {ma60:.2f}')
        
        # 交叉判斷
        if ma5 > ma20:
            cross = '黃金交叉'
        elif ma5 < ma20:
            cross = '死亡交叉'
        else:
            cross = '糾結'
        print(f'  交叉: {cross}')
        
        # RSI
        d = np.diff(prices)
        g = np.where(d > 0, d, 0)
        l = np.where(d > 0, 0, -d)
        ag = np.mean(g[-14:])
        al = np.mean(l[-14:])
        rs = 100 - (100 / (1 + ag / al)) if al != 0 else 50
        
        if rs >= 85:
            rs_icon = '過熱'
        elif rs >= 70:
            rs_icon = '偏高'
        elif rs >= 50:
            rs_icon = '適中'
        else:
            rs_icon = '低檔'
        print(f'  RSI: {rs_icon} ({rs:.1f})')
        
        # ATR
        trs = []
        for i in range(-14, 0):
            hi = float(h['High'].iloc[i])
            lo = float(h['Low'].iloc[i])
            cl_p = float(h['Close'].iloc[i-1])
            trs.append(max(hi-lo, abs(hi-cl_p), abs(lo-cl_p)))
        atr = np.mean(trs)
        atr_pct = atr / current * 100
        print(f'  ATR: {atr:.2f} ({atr_pct:.2f}%)')
        
        # Volume
        vol = list(h['Volume'])
        vr = vol[-1] / np.mean(vol[-5:]) if np.mean(vol[-5:]) > 0 else 0
        if vr > 1.5:
            vr_icon = '放量'
        elif vr > 1.0:
            vr_icon = '平量'
        else:
            vr_icon = '縮量'
        print(f'  量能: {vr_icon} (VR={vr:.2f})')
        
        # K線型態
        last_o = float(h['Open'].iloc[-1])
        last_c = float(h['Close'].iloc[-1])
        body = abs(last_c - last_o)
        h_range = float(h['High'].iloc[-1]) - float(h['Low'].iloc[-1])
        body_ratio = body / h_range if h_range > 0 else 0
        
        if last_c > last_o and body_ratio > 0.7:
            k_pattern = '長紅燭'
        elif last_c < last_o and body_ratio > 0.7:
            k_pattern = '長黑燭'
        elif last_c > last_o:
            k_pattern = '小紅燭'
        elif last_c < last_o:
            k_pattern = '小黑燭'
        else:
            k_pattern = '十字燭'
        print(f'  今日型態: {k_pattern}')
        
        # 評估分數
        score = 0
        if rs < 70:
            score += 2
        elif rs < 85:
            score += 1
        
        if current > ma20:
            score += 2
        if ma5 > ma20:
            score += 1
        if atr_pct >= 0.5:
            score += 1
        if vr >= 1.0:
            score += 1
        
        if score >= 6:
            eval_icon = '✅ 推薦買入'
        elif score >= 4:
            eval_icon = '🟡 觀望'
        else:
            eval_icon = '❌ 不建議'
        print(f'  評估: {eval_icon} (分數: {score}/8)')
        
    except Exception as e:
        print(f'{code}: ERROR - {e}')

print()
print('='*75)
print(' 評估標準: RSI<70 + 站上MA20 + 多頭排列 + ATR充足 + 量能支撐')
print('='*75)