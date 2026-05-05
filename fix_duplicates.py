# -*- coding: utf-8 -*-
"""
Fix duplicate quarters - keeps the record with the most data (non-null values)
"""
import sqlite3, os

BASE = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System"
db_path = os.path.join(BASE, "data", "financial_history.db")

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Find all duplicates
cur.execute("""
    SELECT stock, quarter, COUNT(*) as cnt
    FROM quarterly_financials
    GROUP BY stock, quarter
    HAVING COUNT(*) > 1
""")
dups = cur.fetchall()
print(f"Found {len(dups)} duplicate quarters")

# For each duplicate, keep the one with more non-null values
for stock, quarter, cnt in dups:
    cur.execute("""
        SELECT id, revenue, gross_profit, operating_income, net_income, eps
        FROM quarterly_financials
        WHERE stock=? AND quarter=?
        ORDER BY
            (CASE WHEN revenue IS NOT NULL THEN 1 ELSE 0 END) +
            (CASE WHEN gross_profit IS NOT NULL THEN 1 ELSE 0 END) +
            (CASE WHEN operating_income IS NOT NULL THEN 1 ELSE 0 END) +
            (CASE WHEN net_income IS NOT NULL THEN 1 ELSE 0 END) +
            (CASE WHEN eps IS NOT NULL THEN 1 ELSE 0 END) DESC,
            id DESC
    """, (stock, quarter))
    rows = cur.fetchall()
    keep_id = rows[0][0]
    remove_ids = [r[0] for r in rows[1:]]

    print(f"  {stock} {quarter}: keeping id={keep_id}, removing {remove_ids}")
    cur.execute("""
        DELETE FROM quarterly_financials
        WHERE id IN ({})
    """.format(",".join("?" * len(remove_ids))), remove_ids)

conn.commit()

# Verify
cur.execute("""
    SELECT stock, quarter, COUNT(*) as cnt
    FROM quarterly_financials
    GROUP BY stock, quarter
    HAVING COUNT(*) > 1
""")
remaining = cur.fetchall()
print(f"Remaining duplicates: {len(remaining)}")

# Also do annual dedup
cur.execute("""
    SELECT stock, year, COUNT(*) as cnt
    FROM annual_financials
    GROUP BY stock, year
    HAVING COUNT(*) > 1
""")
annual_dups = cur.fetchall()
print(f"Annual duplicates: {len(annual_dups)}")

for stock, year, cnt in annual_dups:
    cur.execute("""
        SELECT id, revenue, gross_profit, operating_income, net_income, eps
        FROM annual_financials
        WHERE stock=? AND year=?
        ORDER BY
            (CASE WHEN revenue IS NOT NULL THEN 1 ELSE 0 END) +
            (CASE WHEN gross_profit IS NOT NULL THEN 1 ELSE 0 END) +
            (CASE WHEN operating_income IS NOT NULL THEN 1 ELSE 0 END) +
            (CASE WHEN net_income IS NOT NULL THEN 1 ELSE 0 END) +
            (CASE WHEN eps IS NOT NULL THEN 1 ELSE 0 END) DESC,
            id DESC
    """, (stock, year))
    rows = cur.fetchall()
    keep_id = rows[0][0]
    remove_ids = [r[0] for r in rows[1:]]
    print(f"  Annual {stock} {year}: keeping id={keep_id}, removing {remove_ids}")
    cur.execute(f"DELETE FROM annual_financials WHERE id IN ({','.join('?'*len(remove_ids))})", remove_ids)

conn.commit()
conn.close()
print("Done.")