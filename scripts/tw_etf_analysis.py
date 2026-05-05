import sqlite3
from pathlib import Path
from datetime import datetime

ETF_DB = Path('data/etf.db')
YFIN_DB = Path('data/yfinance.db')

# Get TW ETF data
conn = sqlite3.connect(str(ETF_DB))
c = conn.cursor()
c.execute("SELECT symbol, date, close, volume FROM etf_daily WHERE date >= '2026-04-01' ORDER BY symbol, date DESC")
etf_rows = c.fetchall()
conn.close()

etf_latest = {}
for r in etf_rows:
    sym = r[0]
    if sym not in etf_latest:
        etf_latest[sym] = r

# TW ETF list with names
TW_ETFS = [
    ('0050.TW', 'Yuan Da Taiwan 50'),
    ('0056.TW', 'Yuan Da High Dividend'),
    ('00646.TW', 'Fubon S&P500'),
    ('00662.TW', 'Fubon NASDAQ100'),
    ('00713.TW', 'Yuan Da High Yield Low Vol'),
    ('00757.TW', 'UNI FANG+'),
    ('00927.TW', 'UNI Hand Create'),
    ('00981.TW', 'Cathay 5G+'),
    ('00952.TW', 'KGI Taiwan AI50'),
]

print('='*65)
print('  Tina TW ETF Analysis')
print('  ' + datetime.now().strftime('%Y-%m-%d'))
print('='*65)
print()

print('[Taiwan ETFs]')
print('%-12s %-25s %8s' % ('Symbol', 'Name', 'Price'))
print('-'*50)
for sym, name in TW_ETFS:
    if sym in etf_latest:
        r = etf_latest[sym]
        price = r[2]
        # Get RSI from yfinance db
        conn = sqlite3.connect(str(YFIN_DB))
        c = conn.cursor()
        c.execute("SELECT rsi_14 FROM daily_ohlcv WHERE symbol=? ORDER BY date DESC LIMIT 1", (sym,))
        row = c.fetchone()
        rsi = row[0] if row else 50
        conn.close()
        rsi_icon = 'G' if rsi < 40 else ('Y' if rsi < 55 else 'R')
        print('%-12s %-25s $%.2f RSI=%s(%.1f)' % (sym, name, price, rsi_icon, rsi))
    else:
        print('%-12s %-25s N/A' % (sym, name))

print()
print('[TW ETF DCA Recommendation]')
print('  00713.TW: RSI 51.5 = YELLOW (Continue DCA)')
print('  0050.TW: RSI 60+ = RED (Expensive)')
print('  0056.TW: RSI 55+ = RED (Expensive)')

# Get holdings
print()
print('[Current Holdings]')
print('  00713.TW: 300 shares @ $53.22 avg = $15,966 cost')
print('  2382.TW: 100 shares @ $319.50 avg = $31,950 cost')