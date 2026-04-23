import sqlite3
conn = sqlite3.connect('data/tina_master.db')
cur = conn.cursor()

# Get MarketData columns
cur.execute("PRAGMA table_info(MarketData)")
print('MarketData columns:')
for col in cur.fetchall():
    print(f'  {col[1]} {col[2]}')

# Get sample data
cur.execute("SELECT * FROM MarketData LIMIT 3")
rows = cur.fetchall()
print('\nSample MarketData:')
for row in rows:
    print(f'  {row}')

# Get distinct codes count
cur.execute("SELECT COUNT(DISTINCT code) FROM MarketData")
print(f'\nDistinct codes: {cur.fetchone()[0]}')

# Get total records
cur.execute("SELECT COUNT(*) FROM MarketData")
print(f'Total records: {cur.fetchone()[0]}')

# Check Assets table
cur.execute("PRAGMA table_info(Assets)")
print('\nAssets columns:')
for col in cur.fetchall():
    print(f'  {col[1]} {col[2]}')

# Check Strategies table
cur.execute("PRAGMA table_info(Strategies)")
print('\nStrategies columns:')
for col in cur.fetchall():
    print(f'  {col[1]} {col[2]}')

conn.close()