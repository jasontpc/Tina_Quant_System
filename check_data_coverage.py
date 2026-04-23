import sqlite3, json
conn = sqlite3.connect('data/tina_master.db')
cur = conn.cursor()

# Get stock coverage stats
cur.execute('''
SELECT 
  COUNT(DISTINCT code) as total_symbols,
  COUNT(*) as total_records
FROM stock_daily
''')
stats = cur.fetchone()

# Get symbols with institutional data
cur.execute('''
SELECT COUNT(DISTINCT code) 
FROM institutional 
WHERE date >= date('now', '-30 days')
''')
inst_count = cur.fetchone()[0]

print(f'Stock daily symbols: {stats[0]}, records: {stats[1]}')
print(f'Symbols with recent inst data: {inst_count}')

# Get top 20 symbols by trade count
cur.execute('''
SELECT code, name, COUNT(*) as trades
FROM stock_daily 
GROUP BY code 
ORDER BY trades DESC 
LIMIT 20
''')
top20 = cur.fetchall()
print('\nTop 20 symbols by record count:')
for row in top20:
    print(f'  {row[0]} {row[1]}: {row[2]} records')

# Check institutional data coverage
cur.execute('''
SELECT i.code, s.name, COUNT(i.*) as inst_records
FROM institutional i
JOIN stock_daily s ON i.code = s.code
WHERE i.date >= date('now', '-60 days')
GROUP BY i.code
ORDER BY inst_records DESC
LIMIT 20
''')
inst_top = cur.fetchall()
print('\nTop 20 by institutional records:')
for row in inst_top:
    print(f'  {row[0]} {row[1]}: {row[2]} inst records')

# Find symbols missing institutional data
cur.execute('''
SELECT code, name FROM stock_daily
WHERE code NOT IN (
  SELECT DISTINCT code FROM institutional 
  WHERE date >= date('now', '-60 days')
)
GROUP BY code
ORDER BY COUNT(*) DESC
LIMIT 20
''')
missing = cur.fetchall()
print('\nSymbols missing institutional data (top 20):')
for row in missing:
    print(f'  {row[0]} {row[1]}')

conn.close()