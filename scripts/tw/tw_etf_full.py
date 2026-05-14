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
    # 半導體/科技
    ('00881.TW', '中信關鍵半導體'),
    ('00891.TW', '中信綠能車'),
    ('00892.TW', '中信綠能車'),
    ('00895.TW', '新光半導體'),
    ('00904.TW', '統一全能科技'),
    # 金融
    ('00917.TW', 'FT台灣金融'),
    # 傳產/主題
    ('00737.TW', '國泰台灣5G+'),
    # 另類/REITs
    ('00712.TW', 'FH富時不動產'),
]

print('=' * 70)
print('  台股ETF 價格+基本面 分析 2026-05-13 10:00 GMT+8')
print('=' * 70)

hot = []
watch = []
ok = []

for ticker, name in etfs:
    try:
        y = yf.Ticker(ticker)
        h = y.history(period='3mo')
        info = y.info
        if len(h) < 30:
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

        # RSI
        gains = h['Close'].diff().clip(lower=0)
        losses = -h['Close'].diff().clip(upper=0)
        avg_gain = gains.tail(14).mean()
        avg_loss = losses.tail(14).mean()
        rs = avg_gain / avg_loss if avg_loss > 0 else 100
        rsi = 100 - (100 / (1 + rs))

        # Fundamental - PE/PB from yfinance info
        pe = info.get('trailingPE', None)
        pb = info.get('priceToBook', None)
        div_yield = info.get('dividendYield', 0) or 0
        if div_yield and div_yield < 1:
            div_yield = div_yield * 100

        nav = info.get('navPrice', None)
        aum = info.get('totalAssets', None)

        # Signal
        if rsi > 80:
            sig = 'RED'
            hot.append({'name': name, 'ticker': ticker, 'rsi': rsi, 'cur': cur, 'chg': chg, 'pe': pe, 'pb': pb, 'div': div_yield, 'high52': high52, 'low52': low52, 'dist_high': dist_high, 'ma20': ma20, 'ma60': ma60})
        elif rsi > 70:
            sig = 'YELLOW'
            watch.append({'name': name, 'ticker': ticker, 'rsi': rsi, 'cur': cur, 'chg': chg, 'pe': pe, 'pb': pb, 'div': div_yield, 'high52': high52, 'low52': low52, 'dist_high': dist_high, 'ma20': ma20, 'ma60': ma60})
        elif rsi < 45:
            sig = 'GREEN'
            ok.append({'name': name, 'ticker': ticker, 'rsi': rsi, 'cur': cur, 'chg': chg, 'pe': pe, 'pb': pb, 'div': div_yield, 'high52': high52, 'low52': low52, 'dist_high': dist_high, 'ma20': ma20, 'ma60': ma60})
        else:
            sig = 'YELLOW'
            watch.append({'name': name, 'ticker': ticker, 'rsi': rsi, 'cur': cur, 'chg': chg, 'pe': pe, 'pb': pb, 'div': div_yield, 'high52': high52, 'low52': low52, 'dist_high': dist_high, 'ma20': ma20, 'ma60': ma60})

        # Print
        pe_str = f'PE={pe:.1f}' if pe else 'PE=N/A'
        pb_str = f'PB={pb:.2f}' if pb else 'PB=N/A'
        div_str = f'殖利率={div_yield:.2f}%' if div_yield else '殖利率=N/A'
        print(f'{sig} {name}')
        print(f'  價格: {cur:.2f} ({chg:+.2f}%)  RSI={rsi:.1f}')
        print(f'  技術: MA20={ma20:.2f} MA60={ma60:.2f}  距高={dist_high:.1f}%')
        print(f'  基本: {pe_str}  {pb_str}  {div_str}')
        print()
    except Exception as e:
        print(f'ERROR {name}: {e}')

print('=' * 70)
print('SUMMARY')
print('=' * 70)

def print_group(label, items):
    print(f'\n{label} ({len(items)} 檔)')
    for i in items:
        pe_s = f"PE={i['pe']:.1f}" if i['pe'] else "PE=N/A"
        div_s = f"殖{i['div']:.1f}%" if i['div'] else "殖=N/A"
        print(f"  {i['name']} RSI={i['rsi']:.0f} {i['cur']:.2f}({i['chg']:+.1f}%) {pe_s} {div_s}")

print_group('🔴 過熱 RSI>80', hot)
print_group('🟡 偏高 RSI 70-80', watch)
print_group('🟢 落後/超賣 RSI<45', ok)