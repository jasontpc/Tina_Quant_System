# -*- coding: utf-8 -*-
"""最終驗證：所有 Schema 變更"""
import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
db = r'C:\Users\USER\.openclaw\agents\ray\ray_wisdom.db'
conn = sqlite3.connect(db)
c = conn.cursor()

print('=== 最終 Schema 驗證 ===')
tables = ['backtest_reports','wisdom_corrections','signals_log','positions_log','trades_log','daily_performance']
for t in tables:
    c.execute(f"PRAGMA table_info({t})")
    cols = [r[1] for r in c.fetchall()]
    c.execute(f"SELECT COUNT(*) FROM {t}")
    cnt = c.fetchone()[0]
    print(f'\n[{t}] {cnt} rows')
    print(f'  {cols}')

conn.close()