# -*- coding: utf-8 -*-
"""P1-2: daily_performance 擴展 Schema"""
import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB = r'C:\Users\USER\.openclaw\agents\ray\ray_wisdom.db'
conn = sqlite3.connect(DB)
c = conn.cursor()

print('=== P1-2: daily_performance Schema 擴展 ===')

# 先看現有欄位
c.execute("PRAGMA table_info(daily_performance)")
cols = [r[1] for r in c.fetchall()]
print(f'現有欄位: {cols}')

new_cols = [
    ("balance", "REAL"),             # 帳戶餘額
    ("equity", "REAL"),               # 總資產
    ("drawdown_pct", "REAL"),         # 當日最大回撤
    ("position_count", "INTEGER"),   # 持倉檔數
    ("cash_ratio", "REAL"),           # 現金比例
    ("note", "TEXT"),
]
for col, typ in new_cols:
    try:
        c.execute(f"ALTER TABLE daily_performance ADD COLUMN {col} {typ}")
        print(f'  + {col} column added')
    except:
        print(f'  {col}: already exists')

conn.commit()

# 查看現有數據
c.execute("SELECT date, pnl_ratio, sharpe_1d, balance, equity FROM daily_performance LIMIT 5")
rows = c.fetchall()
print(f'\n現有數據 ({len(rows)} rows):')
for r in rows:
    print(f'  {r}')

conn.close()
print('\n✅ P1-2 完成')