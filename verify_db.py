import sqlite3
conn = sqlite3.connect('data/yfinance.db')
cur = conn.cursor()

# Check symbols by prefix
cur.execute("SELECT symbol FROM daily_ohlcv GROUP BY symbol ORDER BY symbol")
all_syms = [r[0] for r in cur.fetchall()]
print(f"Total symbols: {len(all_syms)}")
print(f"Total rows: {cur.execute('SELECT COUNT(*) FROM daily_ohlcv').fetchone()[0]}")

us_syms = [s for s in all_syms if '.' not in s]
tw_syms = [s for s in all_syms if '.TW' in s]
print(f"US symbols: {len(us_syms)}")
print(f"TW symbols: {len(tw_syms)}")
print(f"US symbols list: {sorted(us_syms)}")
print(f"TW symbols sample (first 20): {sorted(tw_syms)[:20]}")
print(f"TW symbols sample (last 20): {sorted(tw_syms)[-20:]}")
conn.close()
