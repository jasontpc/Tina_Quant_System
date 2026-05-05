import sqlite3
conn = sqlite3.connect('data/tina_master.db')
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM MarketData WHERE close IS NULL')
null_close = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM MarketData')
total = c.fetchone()[0]
print(f'MarketData: {total} rows, close NULL: {null_close} ({null_close/total*100:.1f}%)' if total > 0 else 'N/A')
c.execute('SELECT COUNT(*) FROM SignalLogs')
print(f'SignalLogs: {c.fetchone()[0]} rows')
conn.close()
