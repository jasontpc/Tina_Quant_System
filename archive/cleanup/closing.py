# -*- coding: utf-8 -*-
import sys, sqlite3, requests
sys.stdout.reconfigure(encoding='utf-8')

db = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\vogel_indicators.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

print('=== 今日?盤???3:50?===\n')

# TX from indicators DB
cur.execute('SELECT date, close, bb_upper, bb_middle, bb_lower, rsi_14, atr_14, zone FROM daily ORDER BY date DESC LIMIT 1')
row = cur.fetchone()
if row:
    print(f'TX?貨（{row[0]}?')
    print(f'  ?盤: {row[1]:.0f}')
    print(f'  BB Upper: {row[2]:.0f} | Middle: {row[3]:.0f} | Lower: {row[4]:.0f}')
    print(f'  RSI(14): {row[5]:.1f}')
    print(f'  ATR(14): {row[6]:.0f}')
    print(f'  Zone: {row[7]}')
    
    close = row[1]
    bb_u = row[2]
    bb_l = row[4]
    rsi = row[5]
    atr = row[6]
    
    # Signal
    print(f'\n訊?評估:')
    if close >= bb_u:
        print(f'  SHORT: BB Upper突破（close {close:.0f} >= {bb_u:.0f}?)
    elif close <= bb_l:
        print(f'  LONG: BB Lower觸碰（close {close:.0f} <= {bb_l:.0f}?)
    else:
        print(f'  NO_SIGNAL: BB??內（?突破 {bb_u:.0f} ???{bb_l:.0f}?)
        print(f'  SHORT?: +{bb_u - close:.0f}?| LONG?: -{close - bb_l:.0f}?)

conn.close()

# Get TWII close
try:
    token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjJ9.1LHB4yKHeZFoXStyjK2W9F6X3nZLMA1IfPWpDVlv6K0'
    r = requests.get('https://api.finmindtrade.com/api/v4/data', params={
        'dataset': 'TaiwanFuturesDaily', 'data_id': 'TX',
        'start_date': '2026-04-28', 'end_date': '2026-04-28', 'token': token
    }, timeout=10)
    if r.status_code == 200:
        d = r.json()
        if d.get('status') == 200 and d['data']['data']:
            latest = d['data']['data'][-1]
            print(f'\nFinMind TX: {latest.get("date")} close={latest.get("close")} RSI={latest.get("rsi_14", "N/A")}')
except Exception as e:
    print(f'FinMind: {e}')

print('\n')

# Stock prices
stocks = [
    ('2330', '????, 2215, -3.5),
    ('2454', '?發?, 2615, +6.7),
    ('2303', '?電', 75, +3.6),
    ('2317', '鴻海', 226, -1.1),
    ('3034', '緯?', 412, -0.7),
    ('2382', '??', 321, -1.7),
    ('3665', '穎崴', 2630, -3.0),
]

print('=== Nana ?選?收???===')
print(f'{"??":<6} {"?稱":<8} {"?盤":>8} {"漲?":>8} {"觀察???}')
print('-' * 60)

for code, name, price, chg in stocks:
    if abs(chg) > 3:
        note = '?? 波??
    elif code == '2454' and chg > 5:
        note = '? ?能很強但???
    elif chg > 0:
        note = '~ 中性??
    else:
        note = '~ 中?
    
    sig = '+' if chg > 0 else ''
    print(f'{code:<6} {name:<8} {price:>8.0f} {sig}{chg:>7.1f}%  {note}')

print('\n')

# ETF DCA
etfs = [
    ('0050', '?大?灣50', 92.00, -1.2, 77),
    ('00646', '富邦S&P500', 70.95, +0.6, 66),
    ('00662', '富邦NASDAQ100', 110.30, +0.0, 100),
    ('00757', '統?大FANG+', 121.55, +1.0, 110),
    ('00713', '?大高息低波', 53.00, -0.1, 51),
    ('0056', '?大高股??, 41.11, +0.5, 38),
    ('00927', '統??創??', 29.90, +1.6, 25),
]

print('=== Ray ETF DCA 觀?===')
print(f'{"?":<6} {"?稱":<12} {"?盤":>8} {"?離":>8} {"觀察???}')
print('-' * 60)

for code, name, price, chg, ideal in etfs:
    diff = ((price - ideal) / ideal) * 100
    if diff < 0:
        note = f'???扣 {diff:.0f}%'
    elif diff < 5:
        note = f'輕微?? {diff:.0f}%'
    elif diff < 15:
        note = f'?? {diff:.0f}%'
    else:
        note = f'?? ?貴 {diff:.0f}%'
    
    sig = '+' if chg > 0 else ''
    print(f'{code:<6} {name:<12} {price:>8.2f} {diff:>+7.0f}%  {note}')
