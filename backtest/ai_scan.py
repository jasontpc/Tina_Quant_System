# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import numpy as np

# AI概念股
AI_STOCKS = [
    ('2330', '台積電'),      # 半導體
    ('2454', '聯發科'),      # IC設計/AI
    ('3034', '聯詠'),       # AI運算
    ('2379', '瑞昱'),       # AI/IC
    ('2385', '精英'),       # AI伺服器
    ('6230', '創意'),       # AI晶片
    ('3017', '奇鋐'),       # AI散熱
    ('3665', '贸聯'),      # AI連接器
    ('2451', '聯強'),       # AI通路
    ('2402', '撼訊'),       # AI顯示卡
    ('3583', '辛耘'),       # AI設備
    ('4961', '創力'),       # AI零组件
    ('2360', '致茂'),      # AI測試
    ('3189', '景碩'),       # AI PCB
    ('3229', '泰鼎-KY'),    # AI PCB
    ('4938', '和碩'),      # AI代工
    ('3231', '緯創'),       # AI代工
    ('2474', '互億'),       # AI硬體
]

print('='*70)
print(' 今日AI股掃描 (2026-04-23)')
print(' v4.21 進場條件 + RSI 熱度圖')
print('='*70)

results = []
for code, name in AI_STOCKS:
    try:
        h = yf.Ticker(code+'.TW').history(period='65d')
        if len(h) < 60: continue
        
        close = float(h['Close'].iloc[-1])
        prev = float(h['Close'].iloc[-2])
        change = (close / prev - 1) * 100
        
        cl = list(h['Close'])
        ma20 = np.mean(cl[-20:])
        ma60 = np.mean(cl[-60:])
        bias = (close / ma20 - 1) * 100
        
        d = np.diff(cl)
        g = np.where(d > 0, d, 0)
        l = np.where(d > 0, 0, -d)
        ag = np.mean(g[-14:])
        al = np.mean(l[-14:])
        rs = 100 - (100 / (1 + ag / al)) if al != 0 else 50
        
        trs = []
        for i in range(-15, 0):
            hi = float(h['High'].iloc[i])
            lo = float(h['Low'].iloc[i])
            cl_prev = float(h['Close'].iloc[i-1])
            trs.append(max(hi-lo, abs(hi-cl_prev), abs(lo-cl_prev)))
        atr = np.mean(trs) if trs else 30
        atr_pct = atr / close * 100
        
        v421_ok = rs < 70 and abs(bias) < 10 and ma20 > ma60 and atr_pct >= 0.5
        
        results.append({
            'code': code, 'name': name, 'price': close,
            'change': change, 'rs': rs, 'bias': bias,
            'atr': atr_pct, 'v421': v421_ok
        })
    except:
        pass

results.sort(key=lambda x: x['rs'])

print()
print('%-6s %-8s %8s %6s %6s %6s %s' % ('代碼', '名稱', '價格', 'RSI', 'Bias%', 'ATR%', '評估'))
print('-'*65)

for r in results:
    arrow = '↑' if r['change'] > 0 else '↓'
    
    # RSI 熱度圖
    if r['rs'] >= 85:
        rs_icon = '🔴'
    elif r['rs'] >= 70:
        rs_icon = '🟠'
    elif r['rs'] >= 60:
        rs_icon = '🟡'
    elif r['rs'] >= 50:
        rs_icon = '🟢'
    else:
        rs_icon = '🔵'
    
    # v4.21 評估
    if r['v421']:
        status = '✅ 可進場'
    elif r['rs'] >= 70:
        status = '⚠️ RSI高'
    elif abs(r['bias']) >= 10:
        status = '⚠️ 偏離大'
    else:
        status = '⚠️ 待觀察'
    
    print('%-6s %-8s %8.2f %s%.1f %+6.2f%% %5.2f%%  %s' % (
        r['code'], r['name'], r['price'],
        rs_icon, r['rs'], r['bias'], r['atr'], status))

# Summary
print()
print('='*70)
print(' AI股篩選結果')
print('='*70)

v421_list = [r for r in results if r['v421']]
hot_list = [r for r in results if r['rs'] >= 70]

print('\n【✅ 符合 v4.21 進場條件】%d 檔' % len(v421_list))
for r in v421_list:
    print('  %s %s: RSI %.1f, Bias %+.2f%%' % (r['code'], r['name'], r['rs'], r['bias']))

print('\n【🟠 RSI 過熱 (>70)】%d 檔 - 建議觀望' % len(hot_list))
for r in hot_list:
    print('  %s %s: RSI %.1f' % (r['code'], r['name'], r['rs']))

print()
print('='*70)
print(' RSI 熱度圖: 🔵<50 🟢50-59 🟡60-69 🟠70-84 🔴85+')
print('='*70)