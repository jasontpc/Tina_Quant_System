import sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
import yfinance as yf
from datetime import datetime

DATA_DIR = Path(__file__).parent
DB_FILE = DATA_DIR / 'tw_margin.db'

# Check schema
conn = sqlite3.connect(str(DB_FILE))
cur = conn.execute('SELECT sql FROM sqlite_master WHERE name=?', ('indicators',))
schema = cur.fetchone()[0]
print('Schema:', schema)
print()

# Get stocks
cur = conn.execute('SELECT symbol, name FROM stocks LIMIT 5')
for row in cur: print(row)
conn.close()

# Try update manually
sym = '2330'
t = yf.Ticker(f'{sym}.TW')
h = t.history(period='60d', timeout=10)
print(f'History length: {len(h)}')
closes = h['Close'].tolist()
print(f'Close prices (last 3): {closes[-3:]}')

# Calculate RSI
import pandas as pd
deltas = pd.Series(closes).diff()
gain = deltas.clip(lower=0).rolling(14).mean()
loss = (-deltas.clip(upper=0)).rolling(14).mean()
rs = gain / loss
rsi = 100 - (100 / (1 + rs))
rsi_val = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0
print(f'RSI: {rsi_val}')

# MA
ma20 = sum(closes[-20:]) / min(20, len(closes))
ma60 = sum(closes[-60:]) / min(60, len(closes))
ma200 = sum(closes[-200:]) / min(200, len(closes))
print(f'MA20: {ma20}, MA60: {ma60}, MA200: {ma200}')

price_chg = (closes[-1] - closes[-2]) / closes[-2] * 100
margin_ratio = 0.08

# Test insert
conn = sqlite3.connect(str(DB_FILE))
today = datetime.now().strftime('%Y-%m-%d')
data = (sym, today, rsi_val, rsi_val, rsi_val, ma20, ma60, ma200, 0.0, 1.0, price_chg, margin_ratio)
print(f'Data tuple: {len(data)} values - {data}')

try:
    conn.execute('''
        INSERT OR REPLACE INTO indicators
        (symbol, date, rsi14, rsi30, rsi50, ma20, ma60, ma200, volatility, beta, price_chg, margin_ratio)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', data)
    conn.commit()
    print('INSERT SUCCESS!')
except Exception as e:
    print(f'INSERT FAILED: {e}')

# Verify
cur = conn.execute('SELECT symbol, date, rsi14, price_chg FROM indicators WHERE symbol=?', (sym,))
row = cur.fetchone()
print(f'Verified: {row}')
conn.close()