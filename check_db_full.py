import sqlite3
conn = sqlite3.connect('data/tina_master.db')
cur = conn.cursor()

# Get distinct symbols count
cur.execute("SELECT COUNT(DISTINCT symbol) FROM MarketData")
print(f'Distinct symbols: {cur.fetchone()[0]}')

# Get total records
cur.execute("SELECT COUNT(*) FROM MarketData")
print(f'Total records: {cur.fetchone()[0]}')

# Get top 20 symbols by record count
cur.execute('''
SELECT symbol, COUNT(*) as records 
FROM MarketData 
GROUP BY symbol 
ORDER BY records DESC 
LIMIT 20
''')
top20 = cur.fetchall()
print('\nTop 20 by record count:')
for row in top20:
    print(f'  {row[0]}: {row[1]} records')

# Check recent data date range
cur.execute("SELECT MIN(date), MAX(date) FROM MarketData")
dates = cur.fetchone()
print(f'\nDate range: {dates[0]} to {dates[1]}')

# Check Assets table
cur.execute("SELECT * FROM Assets LIMIT 5")
assets = cur.fetchall()
print('\nAssets sample:')
for row in assets:
    print(f'  {row}')

# Check SignalLogs table
cur.execute("PRAGMA table_info(SignalLogs)")
print('\nSignalLogs columns:')
for col in cur.fetchall():
    print(f'  {col[1]} {col[2]}')

# Check DailyStats table
cur.execute("PRAGMA table_info(DailyStats)")
print('\nDailyStats columns:')
for col in cur.fetchall():
    print(f'  {col[1]} {col[2]}')

conn.close()