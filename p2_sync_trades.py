# -*- coding: utf-8 -*-
"""P2-2: trades_log 同步 positions_log 平倉記錄"""
import sqlite3, sys
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB = r'C:\Users\USER\.openclaw\agents\ray\ray_wisdom.db'
conn = sqlite3.connect(DB)
c = conn.cursor()

print('=== P2-2: trades_log 同步 ===')

# 擴展 trades_log 欄位
c.execute("PRAGMA table_info(trades_log)")
existing_cols = [r[1] for r in c.fetchall()]
extra = [("days_held", "INTEGER"), ("sharpe_30d", "REAL"), ("mdd_30d", "REAL"), ("strategy", "TEXT")]
for col, typ in extra:
    if col not in existing_cols:
        try:
            c.execute(f"ALTER TABLE trades_log ADD COLUMN {col} {typ}")
            print(f'  + {col} added')
        except:
            pass

conn.commit()

# 找出 positions_log 中已平倉的記錄
c.execute("SELECT symbol, entry_date, close_date, entry_price, close_price, shares, pnl_pct, close_reason FROM positions_log WHERE close_date IS NOT NULL AND close_price IS NOT NULL")
closed = c.fetchall()
print(f'已平倉 positions_log: {len(closed)} rows')
for r in closed:
    print(f'  {r}')

# 同步到 trades_log
c.execute("SELECT symbol, trade_date FROM trades_log")
existing_trades = set()
for r in c.fetchall():
    existing_trades.add((r[0], r[1]))

inserted = 0
for pos in closed:
    sym, entry_date, close_date, entry_px, close_px, shares, pnl_pct, close_reason = pos
    key = (sym, close_date)
    if key not in existing_trades and close_date and close_px:
        holding_days = 0
        if entry_date and close_date:
            try:
                holding_days = (datetime.strptime(close_date, '%Y-%m-%d') - datetime.strptime(entry_date, '%Y-%m-%d')).days
            except:
                holding_days = 0
        pnl_abs = (close_px - entry_px) * shares if shares and entry_px else 0
        c.execute('''INSERT INTO trades_log (trade_date, symbol, action, price, shares, amount, strategy, pnl_pct, pnl_abs, holding_days, close_reason)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
            (close_date, sym, 'SELL', close_px, shares or 0, (close_px or 0)*(shares or 0),
             'TinaCron', pnl_pct or 0, pnl_abs, holding_days, close_reason or ''))
        inserted += 1

conn.commit()
c.execute("SELECT COUNT(*) FROM trades_log")
total = c.fetchone()[0]
print(f'trades_log: {total} rows (新增 {inserted})')
conn.close()
print('P2-2 完成')