import sqlite3

# Check tina_master.db MarketData
conn = sqlite3.connect('C:/Users/USER/.openclaw/workspace/Tina_Quant_System/data/tina_master.db')
cur = conn.cursor()

# Count symbols
cur.execute('SELECT COUNT(DISTINCT symbol) FROM MarketData')
total_symbols = cur.fetchone()[0]
print(f'tina_master.db MarketData: {total_symbols} unique symbols')

# List all symbols
cur.execute('SELECT DISTINCT symbol FROM MarketData ORDER BY symbol')
symbols = [r[0] for r in cur.fetchall()]
print(f'Symbols: {symbols}')

# Check date range
cur.execute('SELECT MIN(date), MAX(date) FROM MarketData')
min_d, max_d = cur.fetchone()
print(f'Date range: {min_d} to {max_d}')

# Row count per symbol
cur.execute('SELECT symbol, COUNT(*) as cnt FROM MarketData GROUP BY symbol ORDER BY cnt DESC LIMIT 20')
for sym, cnt in cur.fetchall():
    print(f'  {sym}: {cnt} rows')

conn.close()
print()

# Check institutional_history.db
conn2 = sqlite3.connect('C:/Users/USER/.openclaw/workspace/skills/stock-analyzer/scripts/institutional_history.db')
cur2 = conn2.cursor()

cur2.execute('SELECT COUNT(DISTINCT stock_id) FROM institutional_history')
inst_symbols = cur2.fetchone()[0]
print(f'institutional_history.db: {inst_symbols} unique symbols')

cur2.execute('SELECT MIN(date), MAX(date) FROM institutional_history')
min_d2, max_d2 = cur2.fetchone()
print(f'Date range: {min_d2} to {max_d2}')

conn2.close()
