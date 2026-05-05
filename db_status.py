# -*- coding: utf-8 -*-
import sys, os, sqlite3, yfinance as yf
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'

print('=== Database Status ===\n')

# tw_history
conn = sqlite3.connect(os.path.join(DATA_DIR, 'tw_history.db'))
cur = conn.cursor()
last = cur.execute('SELECT MAX(date) FROM daily_ohlcv').fetchone()[0]
stock_cnt = cur.execute('SELECT COUNT(*) FROM stocks').fetchone()[0]
conn.close()
print(f'tw_history: {stock_cnt} stocks, last: {last}')

# etf_history  
conn2 = sqlite3.connect(os.path.join(DATA_DIR, 'etf_history.db'))
cur2 = conn2.cursor()
last_etf = cur2.execute('SELECT MAX(date) FROM daily_ohlcv').fetchone()[0]
etf_cnt = cur2.execute('SELECT COUNT(*) FROM etf_list').fetchone()[0]
conn2.close()
print(f'etf_history: {etf_cnt} ETFs, last: {last_etf}')

# fugle
conn3 = sqlite3.connect(os.path.join(DATA_DIR, 'fugle.db'))
cur3 = conn3.cursor()
quote_cnt = cur3.execute('SELECT COUNT(*) FROM quote_latest').fetchone()[0]
# Get columns
cols = [r[1] for r in cur3.execute('PRAGMA table_info(quote_latest)').fetchall()]
print(f'fugle: {quote_cnt} quotes, cols: {cols}')

# Check if we can get timestamp
if 'timestamp' in cols:
    last_ts = cur3.execute('SELECT MAX(timestamp) FROM quote_latest').fetchone()[0]
else:
    last_ts = cur3.execute('SELECT MAX(date) FROM quote_latest').fetchone()[0]
conn3.close()
print(f'fugle last: {last_ts}')

print(f'\nToday: {datetime.now().strftime("%Y-%m-%d")}')
print(f'Market likely closed (Sunday)')
print('\n=== Update Needed? ===')

today = datetime.now().strftime('%Y-%m-%d')
yesterday = (datetime.now() - timedelta(1)).strftime('%Y-%m-%d')

for db, last_date, name in [
    ('tw_history', last, '台股歷史'),
    ('etf_history', last_etf, 'ETF歷史'),
    ('fugle', last_ts, 'Fugle報價'),
]:
    needs = last_date != today if last_date else True
    print(f'  {"YES" if needs else "NO"} - {name} ({db}) last={last_date}')