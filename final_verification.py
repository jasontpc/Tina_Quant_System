# -*- coding: utf-8 -*-
"""Final verification of all new scripts"""
import sqlite3, os, json
from datetime import datetime

BASE = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System"
DATA_DIR = f"{BASE}\\data"

print("=" * 60)
print("FINAL VERIFICATION - Tina Quant System DB Update")
print("=" * 60)

# 1. Financial History DB
print("\n[1] Financial History DB")
db = os.path.join(DATA_DIR, "financial_history.db")
conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM quarterly_financials")
q_cnt = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM annual_financials")
a_cnt = cur.fetchone()[0]
cur.execute("""
    SELECT stock, quarter, revenue, gross_profit, net_income, eps, gross_margin, operating_margin, net_margin
    FROM quarterly_financials WHERE revenue IS NOT NULL
    ORDER BY stock, quarter DESC LIMIT 15
""")
print(f"  Quarterly records: {q_cnt}")
print(f"  Annual records: {a_cnt}")
print(f"  Sample (2330 latest):")
cur.execute("""
    SELECT quarter, revenue, gross_profit, operating_income, net_income, eps, gross_margin, operating_margin, net_margin
    FROM quarterly_financials WHERE stock='2330' AND revenue IS NOT NULL
    ORDER BY quarter DESC LIMIT 4
""")
hdrs = ["Qtr","Revenue","GrossProfit","OpIncome","NetIncome","EPS","GM","OM","NM"]
print("  " + " | ".join(f"{h:>12}" for h in hdrs))
for r in cur.fetchall():
    print("  " + " | ".join(f"{str(round(v,2) if v else 'N/A')[:12]:>12}" for v in r))
conn.close()

# 2. Trade History DB
print("\n[2] Trade History DB (tw_history)")
db2 = os.path.join(DATA_DIR, "tw_history.db")
conn2 = sqlite3.connect(db2)
cur2 = conn2.cursor()
cur2.execute("SELECT COUNT(*) FROM daily_ohlcv WHERE symbol='2330'")
tw_rows = cur2.fetchone()[0]
cur2.execute("SELECT date, close, rsi_14, zone FROM daily_ohlcv WHERE symbol='2330' ORDER BY date DESC LIMIT 3")
print(f"  2330 OHLCV records: {tw_rows}")
for r in cur2.fetchall():
    print(f"  {r}")
conn2.close()

print("\n[3] Trade History DB (us_history)")
db3 = os.path.join(DATA_DIR, "us_history.db")
conn3 = sqlite3.connect(db3)
cur3 = conn3.cursor()
cur3.execute("SELECT COUNT(*) FROM daily_ohlcv WHERE symbol='D'")
us_rows = cur3.fetchone()[0]
cur3.execute("SELECT symbol, date, close, rsi_14, kdj_k FROM daily_ohlcv WHERE symbol='D' ORDER BY date DESC LIMIT 3")
print(f"  D (US) OHLCV records: {us_rows}")
for r in cur3.fetchall():
    print(f"  {r}")
conn3.close()

# 4. New Scripts
print("\n[4] New Scripts Created")
scripts = [
    ("scripts/unused_scripts_finder.py", "Scan for unused scripts"),
    ("scripts/trade_history_updater.py", "Update trade history + indicators"),
    ("scripts/financial_data_fetcher.py", "Fetch financial data, EPS, margins"),
    ("scripts/db_maintenance.py", "VACUUM, integrity check, cleanup"),
    ("scripts/full_db_updater.py", "Master orchestrator for all DB updates"),
]
for path, desc in scripts:
    full = os.path.join(BASE, path)
    if os.path.exists(full):
        size = os.path.getsize(full)
        print(f"  ✓ {path} ({size} bytes) - {desc}")
    else:
        print(f"  ✗ {path} NOT FOUND")

# 5. Cron Jobs
print("\n[5] Cron Jobs Created")
import subprocess
result = subprocess.run(["openclaw", "cron", "list", "--json"], capture_output=True, text=True)
if result.returncode == 0:
    try:
        jobs = json.loads(result.stdout)
        target_jobs = [j for j in jobs if "Tina" in j.get("name","")]
        for j in target_jobs:
            print(f"  ✓ {j['name']} | {j['schedule']['expr']} | next={datetime.fromtimestamp(j['state']['nextRunAtMs']/1000).strftime('%Y-%m-%d %H:%M')}")
    except:
        pass

print("\n[6] Configs Created")
configs = [
    "configs/financial_update_schedule.json",
    "configs/db_maintenance_config.json",
]
for c in configs:
    full = os.path.join(BASE, c)
    if os.path.exists(full):
        print(f"  ✓ {c}")
    else:
        print(f"  ✗ {c} NOT FOUND")

print("\n" + "=" * 60)
print("VERIFICATION COMPLETE")
print("=" * 60)