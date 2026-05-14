# -*- coding: utf-8 -*-
import yfinance as yf

etfs = [
    # 藍籌/市值型
    ('0050.TW', '元大台灣50'),
    ('0051.TW', '元大中型100'),
    ('006203.TW', '元大MSCI台灣'),
    ('00922.TW', 'FT台灣Smart Base'),
    ('00692.TW', '富邦台灣ESG'),
    # 高股息
    ('0056.TW', '元大高股息'),
    ('00900.TW', '富邦特選大盤'),
    ('00701.TW', 'FT台灣高股息'),
    ('00891.TW', '中信關鍵半導體'),
    # 半導體/科技
    ('00881.TW', '中信關鍵半導體'),
    ('00892.TW', '中信綠能車'),
    ('00895.TW', '新光半導體'),
    ('00904.TW', '統一全能科技'),
    # 金融
    ('00857.TW', '元大台灣金融'),
    ('00917.TW', 'FT台灣金融'),
    # 傳產/主題
    ('00737.TW', '國泰台灣5G+'),
    ('00890.TW', '中信小資高息'),
    ('00901.TW', 'FH永續高息'),
    # 債券ETF
    ('00687B.TW', '元大美債20年'),
    ('00679B.TW', '元大美債7-10'),
    ('00719B.TW', '國泰20年美債'),
    ('00720B.TW', '元大投資級公司債'),
    # 另類/REITs
    ('00712.TW', 'FH富時不動產'),
    ('00753B.TW', '中信美國公債20年'),
]

print('=' * 65)
print('  台股ETF 全市場掃描 2026-05-13 09:55 GMT+8')
print('=' * 65)

hot = []
watch = []
ok = []

for ticker, name in etfs:
    try:
        y = yf.Ticker(ticker)
        h = y.history(period='3mo')
        if len(h) < 30:
            print(f'{name}: 數據不足')
            continue

        cur = h['Close'].iloc[-1]
        prev = h['Close'].iloc[-2]
        chg = (cur - prev) / prev * 100
        ma20 = h['Close'].tail(20).mean()
        ma60 = h['Close'].tail(60).mean()
        vol = h['Volume'].iloc[-1]
        vol20 = h['Volume'].tail(20).mean()
        high52 = h['High'].max()
        low52 = h['Low'].min()
        dist_high = (cur - high52) / high52 * 100

        gains = h['Close'].diff().clip(lower=0)
        losses = -h['Close'].diff().clip(upper=0)
        avg_gain = gains.tail(14).mean()
        avg_loss = losses.tail(14).mean()
        rs = avg_gain / avg_loss if avg_loss > 0 else 100
        rsi = 100 - (100 / (1 + rs))

        if rsi > 80:
            sig = 'RED'
            hot.append((name, ticker, rsi, cur, chg))
        elif rsi > 70:
            sig = 'YELLOW'
            watch.append((name, ticker, rsi, cur, chg))
        elif rsi < 40:
            sig = 'GREEN'
            ok.append((name, ticker, rsi, cur, chg))
        else:
            sig = 'YELLOW'
            watch.append((name, ticker, rsi, cur, chg))

        print(f'{name} ({ticker})')
        print(f'  {cur:.2f} ({chg:+.2f}%) MA20={ma20:.2f} RSI={rsi:.1f} dist_high={dist_high:.1f}%')
    except Exception as e:
        print(f'{name}: Error - {e}')

print()
print('=' * 65)
print('SIGNAL SUMMARY')
print('=' * 65)
print(f'RED (RSI>80 過熱): {len(hot)}檔')
for n,t,r,c,g in hot:
    print(f'  {n} RSI={r:.1f} {c:.2f} ({g:+.2f}%)')
print()
print(f'YELLOW (RSI 70-80): {len(watch)}檔')
for n,t,r,c,g in watch:
    print(f'  {n} RSI={r:.1f} {c:.2f} ({g:+.2f}%)')
print()
print(f'GREEN (RSI<40 超賣/落後): {len(ok)}檔')
for n,t,r,c,g in ok:
    print(f'  {n} RSI={r:.1f} {c:.2f} ({g:+.2f}%)')