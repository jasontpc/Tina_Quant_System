import sqlite3
import os

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data/tina_master.db')
print(f"DB Path: {db_path}")
print(f"DB exists: {os.path.exists(db_path)}")

conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print(f"Tables: {tables}")

# Check for tier tables
for t in ['tier1', 'tier2', 'tier3', 'Tier1', 'Tier2', 'Tier3']:
    try:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        count = cur.fetchone()[0]
        print(f"  {t}: {count} rows")
    except:
        print(f"  {t}: NOT FOUND")

# Check latest date in MarketData
try:
    cur.execute("SELECT MAX(date) FROM MarketData")
    max_date = cur.fetchone()[0]
    print(f"Latest MarketData date: {max_date}")
except:
    print("MarketData: NOT FOUND or empty")

# Check latest date in DailyStats
try:
    cur.execute("SELECT MAX(date) FROM DailyStats")
    max_date = cur.fetchone()[0]
    print(f"Latest DailyStats date: {max_date}")
except:
    print("DailyStats: NOT FOUND or empty")

conn.close()
