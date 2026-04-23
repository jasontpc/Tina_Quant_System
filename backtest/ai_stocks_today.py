# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import numpy as np

print('='*75)
print(' 今日科技/AI股建議 (2026-04-23 10:17)')
print('='*75)

AI_STOCKS = [
    ('2330', '台積電'),
    ('2454', '聯發科'),
    ('3034', '聯詠'),
    ('2379', '瑞昱'),
    ('2385', '群光'),
    ('6230', '創意'),
    ('3017', '奇鋐'),
    ('3665', '贸聯'),
    ('2451', '聯強'),
    ('3231', '緯創'),
    ('4938', '和碩'),
    ('3583', '辛耘'),
    ('2360', '致茂'),
]

print()
print('%-6s %-8s %8s %6s %5s %7s %6s  %s' % ('代碼', '名稱', '現價', '漲跌', 'RSI', 'Bias%', 'ATR%', '評估'))
print('-'*75)

results = []
for code, name in AI_STOCKS:
    try:
        h = yf.Ticker(code + '.TW').history(period='65d')
        if len(h) < 60:
            continue
        
        p = list(h['Close'])
        current = float(p[-1])
        prev = float(p[-2])
        change = (current / prev - 1) * 100
        
        ma20 = np.mean(p[-20:])
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
        
        results.append({
            'code': code, 'name': name, 'price': current,
            'change': change, 'rs': rs, 'bias': bias, 'atr': atr_pct
        })
    except:
        pass

results.sort(key=lambda x: x['rs'])

for r in results:
    arrow = '▲' if r['change'] > 0 else '▼' if r['change'] < 0 else '―'
    
    if r['rs'] >= 85:
        rs_icon = '🔴'
        rs_text = '過熱'
    elif r['rs'] >= 70:
        rs_icon = '🟠'
        rs_text = '高'
    elif r['rs'] >= 50:
        rs_icon = '🟡'
        rs_text = '中'
    else:
        rs_icon = '🟢'
        rs_text = '低'
    
    # v4.21 評估
    if r['rs'] < 70 and abs(r['bias']) < 10 and r['atr'] >= 0.5:
        eval_icon = '✅ 可進'
    elif r['rs'] >= 85:
        eval_icon = '⚠️ 過熱'
    elif r['rs'] >= 70:
        eval_icon = '🟡 觀望'
    else:
        eval_icon = '🟡 待觀'
    
    print('%-6s %-8s %8.2f %s%.1f%% %s%.0f %+6.1f%% %5.2f%%  %s' % (
        r['code'], r['name'], r['price'], arrow, r['change'],
        rs_icon, r['rs'], r['bias'], r['atr'], eval_icon))

print()
print('='*75)
print(' RSI 熱度: 🔴85+ 🟠70-84 🟡50-69 🟢<50')
print(' v4.21: RSI<70 + Bias<10% + ATR>=0.5%')
print('='*75)

# Summary
print()
print('【結論】')
print('-'*40)
low_rsi = [r for r in results if r['rs'] < 70]
hot = [r for r in results if r['rs'] >= 85]

if low_rsi:
    print('✅ 可考慮:')
    for r in low_rsi:
        print(f'  {r["code"]} {r["name"]} RSI {r["rs"]:.0f}')

if hot:
    print()
    print('⚠️ 過熱避免:')
    for r in hot:
        print(f'  {r["code"]} {r["name"]} RSI {r["rs"]:.0f}')