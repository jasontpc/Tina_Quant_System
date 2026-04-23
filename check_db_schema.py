import sqlite3
conn = sqlite3.connect('data/tina_master.db')
cur = conn.cursor()

# Get all tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()
print('Tables:', [t[0] for t in tables])

# Check institutional table structure
cur.execute("PRAGMA table_info(institutional)")
print('\ninstitutional columns:')
for col in cur.fetchall():
    print(f'  {col[1]} {col[2]}')

# Get sample data
cur.execute("SELECT * FROM institutional LIMIT 3")
rows = cur.fetchall()
print('\nSample institutional data:')
for row in rows:
    print(f'  {row}')

conn.close()