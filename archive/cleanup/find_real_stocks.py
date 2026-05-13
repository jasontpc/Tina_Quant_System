import sqlite3
import yfinance as yf
import time

DB_PATH = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\tw_stock_registry.db"
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Only proper 4-digit numeric codes (real common stocks)
cur.execute("""
    SELECT code, name_cn, industry
    FROM stock_registry
    WHERE market = 'twse'
      AND code GLOB '[0-9][0-9][0-9][0-9]'
      AND name_cn NOT LIKE '%R1'
      AND name_cn NOT LIKE '%R2'
      AND name_cn NOT LIKE '%RP%'
      AND name_cn NOT LIKE '%TDR%'
      AND name_cn NOT LIKE '%牛%'
      AND name_cn NOT LIKE '%購%'
      AND name_cn NOT LIKE '%售%'
      AND name_cn NOT LIKE '%權證%'
      AND industry NOT LIKE '%ETF%'
      AND industry NOT LIKE '%指數股票%'
      AND industry NOT LIKE '%其他%'
    LIMIT 30
""")
rows = cur.fetchall()
conn.close()

ok = []
for r in rows:
    sym = f"{r[0]}.TW"
    try:
        t = yf.Ticker(sym)
        df = t.history(start='2024-01-01', end='2024-12-31', auto_adjust=True, timeout=5)
        if len(df) > 100:
            ok.append({'code': r[0], 'name': r[1], 'industry': r[2], 'rows': len(df)})
            print(f"{sym} ({r[1]}): {len(df)} rows - OK")
        else:
            print(f"{sym} ({r[1]}): {len(df)} rows - SKIP")
    except Exception as e:
        print(f"{sym}: ERROR {e}")
    time.sleep(0.3)

print(f"\nTotal OK: {len(ok)} / {len(rows)}")
print("Sample codes:", [x['code'] for x in ok[:10]])