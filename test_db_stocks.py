# Quick diagnostic: what stock codes are actually in the DB and what works
import sqlite3
import yfinance as yf
import time

DB_PATH = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\tw_stock_registry.db"
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("""
    SELECT code, name_cn, industry
    FROM stock_registry
    WHERE market = 'twse'
      AND industry NOT LIKE '%ETF%'
      AND industry NOT LIKE '%指數股票%'
      AND code GLOB '[0-9][0-9][0-9][0-9]*'
      AND LENGTH(code) BETWEEN 4 AND 6
    ORDER BY code
""")
rows = cur.fetchall()
conn.close()

stocks = [{"code": r[0], "name": r[1], "industry": r[2]} for r in rows]
print(f"Numeric 4-6 digit TWSE stocks: {len(stocks)}")

# Test a few
for s in stocks[:10]:
    sym = f"{s['code']}.TW"
    try:
        t = yf.Ticker(sym)
        df = t.history(start='2024-01-01', end='2024-12-31', auto_adjust=True, timeout=5)
        print(f"{sym} ({s['name']}): {len(df)} rows")
    except Exception as e:
        print(f"{sym}: ERROR {e}")
    time.sleep(0.3)