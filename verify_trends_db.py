# Verify DB
import sqlite3, os
db = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\stock_trends.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("Tables:", [t[0] for t in cur.fetchall()])

cur.execute("SELECT COUNT(*) FROM watchlist")
print("Watchlist:", cur.fetchone()[0], "stocks")

cur.execute("SELECT COUNT(*) FROM technical_indicators")
print("Technical records:", cur.fetchone()[0])

print("\nTop RSI stocks (OVERBOUGHT):")
cur.execute("""SELECT w.symbol, w.name, t.rsi_14, t.trend_zone 
    FROM watchlist w 
    JOIN technical_indicators t ON w.symbol = t.symbol 
    WHERE t.date = (SELECT MAX(date) FROM technical_indicators)
    AND t.trend_zone = 'OVERBOUGHT'
    ORDER BY t.rsi_14 DESC LIMIT 10""")
for r in cur.fetchall():
    print(f"  {r[0]} {r[1]}: RSI={r[2]}")

print("\nOVERSOLD stocks:")
cur.execute("""SELECT w.symbol, w.name, t.rsi_14, t.trend_zone 
    FROM watchlist w 
    JOIN technical_indicators t ON w.symbol = t.symbol 
    WHERE t.date = (SELECT MAX(date) FROM technical_indicators)
    AND t.trend_zone = 'OVERSOLD'
    ORDER BY t.rsi_14 ASC LIMIT 10""")
for r in cur.fetchall():
    print(f"  {r[0]} {r[1]}: RSI={r[2]}")

conn.close()
print("\n[Done]")