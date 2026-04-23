import sqlite3
conn = sqlite3.connect('data/tina_master.db')
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM MarketData')
print('Total rows:', cur.fetchone()[0])
cur.execute('SELECT COUNT(*) FROM MarketData WHERE symbol = ?', ('2330',))
print('2330 rows:', cur.fetchone()[0])
cur.execute('SELECT symbol, COUNT(*) FROM MarketData GROUP BY symbol ORDER BY COUNT(*) DESC LIMIT 10')
print('Top symbols by count:')
for r in cur.fetchall():
    print(r)
conn.close()
