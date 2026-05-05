import sqlite3
conn = sqlite3.connect('data/twse_data.db')
cur = conn.cursor()

# Latest 5mins data
cur.execute("""
SELECT tradedate, traded_time, bid_count_acc, bid_vol_acc, ask_count_acc, ask_vol_acc, trade_count, trade_vol, trade_value
FROM twse_mi_5mins 
WHERE tradedate = '20260504'
ORDER BY traded_time DESC 
LIMIT 5
""")
print('=== Latest 5 rows for 20260504 ===')
for r in cur.fetchall():
    print(r)

# Time range
cur.execute("SELECT MIN(traded_time), MAX(traded_time) FROM twse_mi_5mins WHERE tradedate='20260504'")
print('\nTime range for 20260504:', cur.fetchall())

# Market index
cur.execute('SELECT * FROM twse_mi_index ORDER BY date DESC LIMIT 10')
print('\n=== MI_INDEX ===')
for r in cur.fetchall():
    print(r)

conn.close()
