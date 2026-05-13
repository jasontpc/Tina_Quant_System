# -*- coding: utf-8 -*-
"""P1-1: wisdom_corrections 擴展 Schema（reason + lesson_type）"""
import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB = r'C:\Users\USER\.openclaw\agents\ray\ray_wisdom.db'
conn = sqlite3.connect(DB)
c = conn.cursor()

print('=== P1-1: wisdom_corrections Schema 擴展 ===')

# 新增欄位
new_cols = [
    ("lesson_type", "TEXT DEFAULT 'system'"),  # system / stock / macro / emotion
    ("reason", "TEXT"),                          # 失敗的具體原因
    ("market_regime", "TEXT"),                  # bull / bear / volatile / calm
    ("updated_at", "DATETIME"),                 # 最後更新時間
]
for col, typ in new_cols:
    try:
        c.execute(f"ALTER TABLE wisdom_corrections ADD COLUMN {col} {typ}")
        print(f'  + {col} column added')
    except Exception as e:
        print(f'  {col}: already exists or error: {e}')

conn.commit()

# 顯示 confidence=0 的 rows（需要補 reason）
c.execute("SELECT id, symbol, diagnosis, confidence FROM wisdom_corrections WHERE confidence = 0.0 LIMIT 10")
zero_conf = c.fetchall()
print(f'\nconfidence=0 的 rows: {len(zero_conf)} (需要補 reason)')
for r in zero_conf[:5]:
    print(f'  id={r[0]} [{r[1]}]: {r[2][:60]}')

# 自動推斷 lesson_type（基於 symbol 與 meta_label）
c.execute("SELECT id, symbol, meta_label FROM wisdom_corrections WHERE lesson_type IS NULL")
null_type = c.fetchall()
print(f'\nlesson_type 為空: {len(null_type)} rows')

for row in null_type:
    vid, sym, ml = row
    # 根據 symbol/內容推斷 lesson_type
    if sym and sym not in ('WEB_SOURCE', 'SYSTEM', None):
        lt = 'stock'
    elif sym == 'WEB_SOURCE' or ml and 'web' in str(ml).lower():
        lt = 'macro'
    else:
        lt = 'system'
    c.execute("UPDATE wisdom_corrections SET lesson_type=? WHERE id=?", (lt, vid))

conn.commit()
c.execute("SELECT lesson_type, COUNT(*) FROM wisdom_corrections GROUP BY lesson_type")
print('lesson_type 分佈:')
for r in c.fetchall():
    print(f'  {r[0] or "null"}: {r[1]} rows')

conn.close()
print('\n✅ P1-1 完成')