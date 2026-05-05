# Final verification
import sqlite3, os, subprocess, json

BASE = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System"
DATA_DIR = f"{BASE}\\data"

print("=== Financial DB ===")
db = os.path.join(DATA_DIR, "financial_history.db")
conn = sqlite3.connect(db)
cur = conn.cursor()

print("Quarterly sample (2330):")
cur.execute("SELECT quarter, revenue, gross_profit, net_income, eps, gross_margin, operating_margin, net_margin FROM quarterly_financials WHERE stock='2330' AND revenue IS NOT NULL ORDER BY quarter DESC LIMIT 4")
for r in cur.fetchall():
    print("  ", r)

print("\nAnnual sample (2330):")
cur.execute("SELECT year, revenue, gross_profit, net_income, eps FROM annual_financials WHERE stock='2330' ORDER BY year")
for r in cur.fetchall():
    print("  ", r)

conn.close()

print("\n=== Trade DB ===")
db2 = os.path.join(DATA_DIR, "tw_history.db")
conn2 = sqlite3.connect(db2)
cur2 = conn2.cursor()
cur2.execute("SELECT date, close, rsi_14, zone FROM daily_ohlcv WHERE symbol='2330' ORDER BY date DESC LIMIT 3")
print("2330 latest:")
for r in cur2.fetchall():
    print(" ", r)
conn2.close()

print("\n=== New Scripts ===")
for name in ["unused_scripts_finder.py", "trade_history_updater.py", "financial_data_fetcher.py", "db_maintenance.py", "full_db_updater.py"]:
    import os.path
    path = os.path.join(BASE, "scripts", name)
    if os.path.exists(path):
        print(f"  OK: scripts/{name} ({os.path.getsize(path)} bytes)")
    else:
        print(f"  MISSING: scripts/{name}")

print("\n=== Cron Jobs ===")
r = subprocess.run(["openclaw", "cron", "list", "--json"], capture_output=True, text=True)
if r.returncode == 0:
    jobs = json.loads(r.stdout)
    tina = [j for j in jobs if "Tina" in j.get("name","")]
    for j in tina:
        print(f"  {j['name']} | {j['schedule']['expr']}")