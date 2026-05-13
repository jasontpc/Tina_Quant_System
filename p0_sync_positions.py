# -*- coding: utf-8 -*-
"""P0-1: positions_log 同步 position_tracker.json（匹配實際 Schema）"""
import sqlite3, json, os, sys
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

POS_FILE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\position_tracker.json'
DB = r'C:\Users\USER\.openclaw\agents\ray\ray_wisdom.db'

print('=== P0: positions_log 同步 ===')

# 先擴展 Schema（加入 current_price 等缺失欄位）
conn = sqlite3.connect(DB)
c = conn.cursor()
try:
    c.execute("ALTER TABLE positions_log ADD COLUMN current_price REAL")
    print('  + current_price column added')
except:
    pass
try:
    c.execute("ALTER TABLE positions_log ADD COLUMN days_held INTEGER DEFAULT 0")
    print('  + days_held column added')
except:
    pass
try:
    c.execute("ALTER TABLE positions_log ADD COLUMN name TEXT")
    print('  + name column added')
except:
    pass
conn.commit()

# 讀取 position_tracker.json
if not os.path.exists(POS_FILE):
    print(f'ERROR: {POS_FILE} not found')
    sys.exit(1)

with open(POS_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

positions = data.get('positions', [])
print(f'找到 {len(positions)} 個持倉 from position_tracker.json')

# 讀取現有
c.execute('SELECT symbol, status FROM positions_log')
existing = {r[0]: r[1] for r in c.fetchall()}
print(f'現有 positions_log: {existing}')

# 讀取完整行
c.execute('SELECT * FROM positions_log')
rows = c.fetchall()
col_names = [d[0] for d in c.description]
print(f'positions_log columns: {col_names}')

inserted = 0
updated = 0
today = datetime.now().strftime('%Y-%m-%d')

for p in positions:
    sym = p['symbol']
    entry_price = p['cost']
    shares = p['shares']
    stop_loss = p['stop_loss']
    target_price = p['target']
    status_val = 'open'
    current_price = p['current_price']
    pnl_pct = p['pnl_pct']
    days_held = p.get('days_held', 0)
    name = p.get('name', sym)
    note = f"synced from position_tracker.json at {today}"

    if sym in existing:
        cols = 'entry_price=?, shares=?, stop_loss=?, target_price=?, current_price=?, pnl_pct=?, days_held=?, status=?, name=?'
        vals = (entry_price, shares, stop_loss, target_price, current_price, pnl_pct, days_held, status_val, name, sym)
        c.execute(f'UPDATE positions_log SET {cols} WHERE symbol=?', vals)
        updated += 1
        print(f'  UPDATE: {sym}')
    else:
        c.execute('''INSERT INTO positions_log
            (entry_date, symbol, entry_price, shares, stop_loss, target_price, current_price, status, pnl_pct, days_held, name, note)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
            (today, sym, entry_price, shares, stop_loss, target_price, current_price, status_val, pnl_pct, days_held, name, note))
        inserted += 1
        print(f'  INSERT: {sym}')

conn.commit()

# 驗證結果
c.execute('SELECT symbol, entry_price, shares, current_price, stop_loss, target_price, status, pnl_pct, days_held FROM positions_log')
rows = c.fetchall()
print(f'\npositions_log 最終 ({len(rows)} rows):')
for r in rows:
    id_, sym, entry, cur, stop, target, status_v, pnl, days = r
    p = f'{pnl:+.2f}%' if pnl is not None else 'N/A'
    d = days if days is not None else 0
    print(f'  id={id_} {sym}: entry={entry} cur={cur} stop={stop} target={target} status={status_v} pnl={p} days={d}')

conn.close()
print(f'\n✅ 完成：新增 {inserted} / 更新 {updated}')