# -*- coding: utf-8 -*-
"""Update TX prices from yfinance"""
import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8')

# Try yfinance TX
try:
    import yfinance as yf
    # TX is Taiwan Futures, let's try different symbols
    syms = ['TXF2026.F', 'TX.F', 'TWFRONT2026.F']
    for sym in syms:
        try:
            t = yf.Ticker(sym)
            hist = t.history(period='5d')
            if len(hist) > 0:
                print(f'{sym}: {hist.tail(1)["Close"].values[0]:.0f}')
            else:
                print(f'{sym}: no data')
        except Exception as e:
            print(f'{sym}: error {e}')
except Exception as e:
    print(f'yfinance error: {e}')

# Check what we already have in vogel_indicators
db = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\vogel_indicators.db'
conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute('SELECT date, close, bb_upper, bb_lower, rsi_14, zone FROM daily ORDER BY date DESC LIMIT 3')
print('\n=== 現有 TX 資料 ===')
for r in cur.fetchall():
    print(f'{r[0]}: close={r[1]:.0f} BB_U={r[2]:.0f} BB_L={r[3]:.0f} RSI={r[4]:.1f} zone={r[5]}')
conn.close()