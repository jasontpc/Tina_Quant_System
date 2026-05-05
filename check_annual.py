# Check annual financials
import sqlite3, os

BASE = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System"
db = os.path.join(BASE, "data", "financial_history.db")
conn = sqlite3.connect(db)
cur = conn.cursor()

print("Annual financials sample:")
cur.execute("SELECT stock, year, revenue, gross_profit, net_income, eps FROM annual_financials ORDER BY stock, year LIMIT 20")
for row in cur.fetchall():
    print(f"  {row}")

print("\nQuarterly for 2330 latest:")
cur.execute("SELECT quarter, revenue, gross_profit, operating_income, net_income, eps, gross_margin, op_margin, net_margin FROM quarterly_financials WHERE stock='2330' ORDER BY quarter DESC LIMIT 6")
cols = ["qtr", "rev", "gp", "oi", "ni", "eps", "gm", "om", "nm"]
print(" | ".join(f"{c:>14}" for c in cols))
for row in cur.fetchall():
    print(" | ".join(f"{str(v)[:14]:>14}" if v else f"{'N/A':>14}" for v in row))

conn.close()