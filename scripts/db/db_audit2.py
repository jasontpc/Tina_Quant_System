# -*- coding: utf-8 -*-
import sqlite3, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

db = r'C:\Users\USER\.openclaw\agents\ray\ray_wisdom.db'
conn = sqlite3.connect(db)
c = conn.cursor()

print('=== 欄位審計 ===')
for table in ['backtest_reports','wisdom_corrections','signals_log','positions_log','trades_log','daily_performance','token_history']:
    c.execute(f"PRAGMA table_info({table})")
    cols = [(r[1], r[2]) for r in c.fetchall()]
    c.execute(f"SELECT COUNT(*) FROM {table}")
    cnt = c.fetchone()[0]
    print(f'\n[{table}] ({cnt} rows)')
    for name, typ in cols:
        print(f'  {name}: {typ}')

print()
print('=== 資料品質審計 ===')

# wisdom_corrections 結構
c.execute("SELECT * FROM wisdom_corrections LIMIT 2")
wc_cols = [d[0] for d in c.description]
print(f'wisdom_corrections columns: {wc_cols}')

# signals_log 結構
c.execute("SELECT * FROM signals_log LIMIT 2")
sl_cols = [d[0] for d in c.description]
print(f'signals_log columns: {sl_cols}')

# backtest_reports 結構
c.execute("SELECT * FROM backtest_reports LIMIT 2")
br_cols = [d[0] for d in c.description]
print(f'backtest_reports columns: {br_cols}')

print()
print('=== backtest_reports 數值品質 ===')
c.execute("SELECT COUNT(*) FROM backtest_reports WHERE sharpe_ratio IS NULL OR sharpe_ratio = 0")
bad_sharpe = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM backtest_reports WHERE sharpe_ratio > 0")
good_sharpe = c.fetchone()[0]
print(f'  Sharpe=0 or NULL: {bad_sharpe} / {bad_sharpe+good_sharpe}')

print()
print('=== wisdom_corrections 信心分布 ===')
c.execute("SELECT confidence, COUNT(*) FROM wisdom_corrections GROUP BY confidence ORDER BY confidence")
for r in c.fetchall():
    print(f'  confidence={r[0]}: {r[1]} rows')

print()
print('=== signals_log 待審核統計 ===')
c.execute("SELECT approved, COUNT(*) FROM signals_log GROUP BY approved")
for r in c.fetchall():
    print(f'  approved={r[0]}: {r[1]} rows')

conn.close()
print()
print('=== 腳本缺失分析 ===')
print('1. daily_performance 只有 28 rows（預計需 100+ rows 才有統計意義）')
print('2. positions_log 只有 1 row（模擬倉持倉未同步？）')
print('3. trades_log 只有 1 row（實戰交易未記錄？）')
print('4. wisdom_corrections 只有 67 rows（目標應有 200+）')
print('5. backtest_reports 1057 rows OK，但 sharpe_ratio 有效率需確認')