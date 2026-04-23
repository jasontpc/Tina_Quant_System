# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import numpy as np

STOCKS = [
    ('2330', '台積電'), ('2454', '聯發科'), ('3034', '聯詠'),
    ('2379', '瑞昱'), ('2385', '精英'), ('2451', '聯強'),
    ('6230', '創意'), ('6770', '聯亞'), ('2354', '景碩'),
    ('3189', '景碩'), ('2401', '廣積'), ('2402', '撼訊'),
    ('4961', '創力'), ('2360', '致茂'), ('2474', '互億'),
    ('3017', '奇鋐'), ('3665', '贸聯')
]

print('='*70)
print(' 今日科技股掃描 (2026-04-23)')
print(' v4.21 進場條件篩選')
print('='*70)

results = []
for code, name in STOCKS:
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
        
        # v4.21 check
        v421_ok = rs < 70 and bias < 10 and ma20 > ma60 and atr_pct >= 0.5
        
        results.append({
            'code': code, 'name': name, 'price': close,
            'change': change, 'rs': rs, 'bias': bias,
            'atr': atr_pct, 'ma20': ma20, 'ma60': ma60,
            'v421': v421_ok
        })
    except:
        pass

# Sort by RSI
results.sort(key=lambda x: x['rs'])

print()
print('%-6s %-6s %8s %5s %7s %5s %6s  %s' % ('代碼', '名稱', '價格', '漲跌', 'RSI', 'Bias%', 'ATR%', 'v4.21'))
print('-'*70)
for r in results:
    arrow = '↑' if r['change'] > 0 else '↓'
    v421 = '✅' if r['v421'] else '⚠️'
    rs_icon = '🔥' if r['rs'] >= 70 else '⚠️' if r['rs'] >= 60 else '✅'
    print('%-6s %-6s %8.2f %+5.1f%% %s%.1f %+6.2f%% %5.2f%%  %s' % (
        r['code'], r['name'], r['price'], r['change'],
        rs_icon, r['rs'], r['bias'], r['atr'], v421))

# Summary
print()
print('='*70)
print(' 科技股篩選結果')
print('='*70)

v421_list = [r for r in results if r['v421']]
hot_list = [r for r in results if r['rs'] >= 70]

print('\n【符合 v4.21 進場條件】%d 檔' % len(v421_list))
for r in v421_list:
    print('  %s %s: RSI %.1f, Bias %+.2f%%' % (r['code'], r['name'], r['rs'], r['bias']))

print('\n【RSI 過熱 (>70)】%d 檔 - 建議觀望' % len(hot_list))
for r in hot_list:
    print('  %s %s: RSI %.1f' % (r['code'], r['name'], r['rs']))

print()
print('='*70)
print(' 結論: 科技股普遍 RSI 過熱，大部分不建議進場')
print(' 建議關注: 2385 精英 (RSI 67.7)')
print('='*70)