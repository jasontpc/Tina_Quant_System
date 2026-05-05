import sqlite3

# Check daily_ohlcv schema
conn = sqlite3.connect(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\us_history.db')
c = conn.cursor()
c.execute("PRAGMA table_info(daily_ohlcv)")
print('daily_ohlcv columns:', [(r[1], r[2]) for r in c.fetchall()])

# Check for our target symbols
for sym in ['D', 'BMY', 'SO', 'DXCM']:
    c.execute(f"SELECT COUNT(*) FROM daily_ohlcv WHERE symbol='{sym}'")
    count = c.fetchone()[0]
    print(f'{sym} rows in daily_ohlcv: {count}')
    if count > 0:
        c.execute(f"SELECT date, close FROM daily_ohlcv WHERE symbol='{sym}' ORDER BY date DESC LIMIT 3")
        print(f'  Recent: {c.fetchall()}')
conn.close()

# Check us_value_growth schema
conn2 = sqlite3.connect(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\us_value_growth.db')
c2 = conn2.cursor()
c2.execute("PRAGMA table_info(fundamentals)")
print('\nus_value_growth fundamentals columns:', [(r[1], r[2]) for r in c2.fetchall()])
c2.execute("PRAGMA table_info(technicals)")
print('technicals columns:', [(r[1], r[2]) for r in c2.fetchall()])
c2.execute("PRAGMA table_info(scores)")
print('scores columns:', [(r[1], r[2]) for r in c2.fetchall()])

for sym in ['D', 'BMY', 'SO', 'DXCM']:
    c2.execute(f"SELECT * FROM fundamentals WHERE symbol='{sym}' LIMIT 1")
    row = c2.fetchone()
    print(f'{sym} fundamentals: {row}')
conn2.close()