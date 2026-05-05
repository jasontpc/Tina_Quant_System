import sqlite3
import json

# Check us_history.db
conn = sqlite3.connect(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\us_history.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
print('us_history tables:', [r[0] for r in c.fetchall()])
c.execute("PRAGMA table_info(stock_daily)")
print('us_history stock_daily columns:', [r[1] for r in c.fetchall()])
conn.close()

# Check us_fundamental_v2.db
conn2 = sqlite3.connect(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\us_fundamental_v2.db')
c2 = conn2.cursor()
c2.execute("SELECT name FROM sqlite_master WHERE type='table'")
print('us_fundamental_v2 tables:', [r[0] for r in c2.fetchall()])
c2.execute("PRAGMA table_info(fundamentals)")
print('fundamentals columns:', [r[1] for r in c2.fetchall()])

# Check which symbols are in fundamental db
c2.execute("SELECT DISTINCT symbol FROM fundamentals LIMIT 20")
print('Sample symbols in fundamental:', [r[0] for r in c2.fetchall()])

# Check for our target symbols
for sym in ['D', 'BMY', 'SO', 'DXCM']:
    c2.execute(f"SELECT * FROM fundamentals WHERE symbol='{sym}' LIMIT 1")
    row = c2.fetchone()
    print(f'{sym}: {row}')
conn2.close()

# Check us_value_growth.db
conn3 = sqlite3.connect(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\us_value_growth.db')
c3 = conn3.cursor()
c3.execute("SELECT name FROM sqlite_master WHERE type='table'")
print('us_value_growth tables:', [r[0] for r in c3.fetchall()])
conn3.close()