# -*- coding: utf-8 -*-
"""
123優化 — 填補 empty tables（使用正確欄位）
1. daily_performance
2. positions_log
3. trades_log
"""
import sys, sqlite3, json, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB = 'ray_wisdom.db'
conn = sqlite3.connect(DB)
c = conn.cursor()

print('=== 123優化 ===')
print()

today = time.strftime("%Y-%m-%d")
now = time.strftime("%Y-%m-%d %H:%M:%S")

# 1. daily_performance — 寫入示範（使用正確欄位）
try:
    c.execute(f"INSERT INTO daily_performance (date, symbol, pnl_ratio, sharpe_1d, note) VALUES (?, ?, ?, ?, ?)",
        (today, "PORTFOLIO", 0.015, 1.2, "Demo entry - Ray system initialized"))
    conn.commit()
    print("   daily_performance: 寫入成功")
except Exception as e:
    print(f"   daily_performance: {e}")

# 2. positions_log — 寫入示範（使用正確欄位）
try:
    c.execute(f"INSERT INTO positions_log (entry_date, symbol, entry_price, shares, stop_loss, target_price, status, rsi_entry, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (today, "VTI", 250.5, 100, 235.0, 275.0, "OPEN", 55, "DCA demo"))
    conn.commit()
    print("   positions_log: 寫入成功")
except Exception as e:
    print(f"   positions_log: {e}")

# 3. trades_log — 寫入示範（使用正確欄位）
try:
    c.execute(f"INSERT INTO trades_log (trade_date, symbol, action, price, shares, amount, strategy, pnl_pct, holding_days, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (today, "VOO", "BUY", 480.2, 50, 24010, "DCA", 0.0, 0, "Demo trade"))
    conn.commit()
    print("   trades_log: 寫入成功")
except Exception as e:
    print(f"   trades_log: {e}")

# 驗證
print()
c.execute("SELECT COUNT(*) FROM daily_performance")
dp = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM positions_log")
pl = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM trades_log")
tl = c.fetchone()[0]

print(f"daily_performance: {dp} 筆")
print(f"positions_log: {pl} 筆")
print(f"trades_log: {tl} 筆")

# 顯示內容
if dp > 0:
    c.execute("SELECT date, symbol, pnl_ratio, sharpe_1d FROM daily_performance ORDER BY id DESC LIMIT 3")
    print()
    print("daily_performance 最新:")
    for r in c.fetchall():
        print(f"   {r}")

if pl > 0:
    c.execute("SELECT entry_date, symbol, entry_price, shares, status FROM positions_log ORDER BY id DESC LIMIT 3")
    print()
    print("positions_log 最新:")
    for r in c.fetchall():
        print(f"   {r}")

if tl > 0:
    c.execute("SELECT trade_date, symbol, action, price, shares FROM trades_log ORDER BY id DESC LIMIT 3")
    print()
    print("trades_log 最新:")
    for r in c.fetchall():
        print(f"   {r}")

conn.close()
print()
print("=== 123優化完成 ===")