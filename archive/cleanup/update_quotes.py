# -*- coding: utf-8 -*-
"""Update stock quotes from yfinance"""
import sys, yfinance, sqlite3
sys.stdout.reconfigure(encoding='utf-8')

DB = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\fugle.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

stocks = ['2330.TW', '2454.TW', '2303.TW', '2317.TW', '3034.TW', '2382.TW', '3665.TW']
names = {'2330.TW':'台積電','2454.TW':'聯發科','2303.TW':'聯電','2317.TW':'鴻海','3034.TW':'緯穎','2382.TW':'廣達','3665.TW':'穎崴'}

print('=== 更新 Fugle 即時報價 ===\n')

for sym in stocks:
    try:
        t = yfinance.Ticker(sym)
        info = t.fast_info
        price = info.get('lastPrice') or info.get('regularMarketPrice')
        prev = info.get('previousClose')
        open_p = info.get('open')
        high = info.get('dayHigh')
        low = info.get('dayLow')
        chg = ((price - prev) / prev * 100) if price and prev else 0
        
        code = sym.replace('.TW', '')
        
        print(f'{code}: {price:.0f} ({chg:+.1f}%)')
        
        # Update DB - correct columns
        cur.execute('''INSERT OR REPLACE INTO quote_latest 
            (symbol, price, change, change_percent, open, high, low, close, volume, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)''',
            (code, price, price - prev, chg, open_p, high, low, price, 0))
        
    except Exception as e:
        print(f'{code}: error {e}')

conn.commit()

# Verify
cur.execute('SELECT symbol, price, change_percent FROM quote_latest ORDER BY symbol')
print('\n=== 更新後報價 ===')
for r in cur.fetchall():
    print(f'{r[0]}: {r[1]:.0f} ({r[2]:+.1f}%)')

conn.close()
print('\n完成!')