# -*- coding: utf-8 -*-
import sqlite3, os

BASE = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System"

print("=== Financial History DB ===")
db = os.path.join(BASE, "data", "financial_history.db")
if os.path.exists(db):
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cur.fetchall()]
    print("Tables:", tables)
    for t in tables:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        print(f"  {t}: {cur.fetchone()[0]} rows")
    print()
    print("Sample quarterly data:")
    cur.execute("SELECT stock, quarter, revenue, gross_profit, net_income, eps, gross_margin, operating_margin, net_margin FROM quarterly_financials ORDER BY stock, quarter DESC LIMIT 20")
    cols = ["stock","quarter","revenue","gross_profit","net_income","eps","gross_margin","op_margin","net_margin"]
    print(" | ".join(f"{c[:12]:>12}" for c in cols))
    for row in cur.fetchall():
        print(" | ".join(f"{str(v)[:12]:>12}" if v else f"{'N/A':>12}" for v in row))
    conn.close()
else:
    print("DB not found:", db)

print()
print("=== Trade History DB - Sample ===")
db2 = os.path.join(BASE, "data", "tw_history.db")
conn = sqlite3.connect(db2)
cur = conn.cursor()
cur.execute("SELECT symbol, date, close, rsi_14, zone FROM daily_ohlcv WHERE symbol='2330' ORDER BY date DESC LIMIT 5")
print("2330 latest prices:")
for row in cur.fetchall():
    print(f"  {row}")
conn.close()

db3 = os.path.join(BASE, "data", "us_history.db")
conn = sqlite3.connect(db3)
cur = conn.cursor()
cur.execute("SELECT symbol, date, close, rsi_14 FROM daily_ohlcv WHERE symbol='D' ORDER BY date DESC LIMIT 5")
print("\nD (US) latest prices:")
for row in cur.fetchall():
    print(f"  {row}")
conn.close()