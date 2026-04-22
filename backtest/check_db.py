# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3

DB = 'skills/stock-analyzer/scripts/tina_master.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

# Get tables
cur.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = cur.fetchall()
print('Tables:', [t[0] for t in tables])

# Check MarketData count
cur.execute('SELECT COUNT(*) FROM MarketData')
print('MarketData rows:', cur.fetchone()[0])

# Sample institutional data
cur.execute('SELECT symbol, date, foreign_net, trust_net, dealer_net FROM MarketData LIMIT 5')
print('Sample data:')
for row in cur.fetchall():
    print(' ', row)

conn.close()
