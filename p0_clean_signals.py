# -*- coding: utf-8 -*-
"""P0-2: signals_log 清理（全部未核准信號都是最近 48 小時內，保留但標記）
策略：設定 48 小時自動過期閾值，48 小時後未核准自動標記為 expired"""
import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB = r'C:\Users\USER\.openclaw\agents\ray\ray_wisdom.db'
conn = sqlite3.connect(DB)
c = conn.cursor()

print('=== P0-2: signals_log 清理 ===')

# 全部都是最近 48 小時內的信號，標記為 expired 而非刪除
# 48 小時前未核准 = 過期
try:
    c.execute("ALTER TABLE signals_log ADD COLUMN signal_status TEXT DEFAULT 'pending'")
    print('  + signal_status column added')
    conn.commit()
except:
    print('  signal_status already exists')

# 標記已過期（48小時前且未核准）
c.execute("UPDATE signals_log SET signal_status='expired' WHERE approved=0 AND timestamp < datetime('now', '-48 hours')")
conn.commit()
expired = c.rowcount
print(f'  標記為 expired (48h+ 未核准): {expired} rows')

# 保留 48 小時內的 pending
c.execute("UPDATE signals_log SET signal_status='pending' WHERE approved=0 AND timestamp >= datetime('now', '-48 hours')")
conn.commit()
pending = c.rowcount
print(f'  標記為 pending (48h內): {pending} rows')

# 統計
c.execute("SELECT signal_status, COUNT(*) FROM signals_log GROUP BY signal_status")
print('清理後狀態:')
for r in c.fetchall():
    print(f'  {r[0]}: {r[1]} rows')

conn.close()
print('P0-2 完成')