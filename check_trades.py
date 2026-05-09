# -*- coding: utf-8 -*-
import sqlite3
from datetime import datetime, timedelta

db_path = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\sherry_sim_trades.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Baseline date: yesterday (2026-05-07)
baseline = '2026-05-07'
today = '2026-05-08'

print(f'=== 成績計算基準：從 {baseline} 開始累積 ===\n')

# ── 1. 已出倉（出倉日 >= 2026-05-07）─────────────────────────────
# 這些是「已經結算的交易」，勝率/PnL 從昨天開始算
cur.execute("""
SELECT symbol, entry_date, exit_date, return_pct, return_amount, exit_reason
FROM closed_positions
WHERE exit_date >= ?
ORDER BY exit_date DESC
""", (baseline,))
closed = cur.fetchall()
print(f'【已出倉】從 {baseline} 起的新結算交易: {len(closed)} 筆')
wins = sum(1 for c in closed if c[3] > 0)
losses = sum(1 for c in closed if c[3] < 0)
total_pnl = sum(c[4] for c in closed if c[4] is not None)
win_rate = wins / len(closed) * 100 if closed else 0
print(f'  贏: {wins} / 輸: {losses} / 勝率: {win_rate:.1f}%')
print(f'  累計PnL: NT$ {total_pnl:,.0f}')
for c in closed:
    print(f'  {c[0]} exit={c[2]} ret={c[3]:.2f}% pnl={c[4]:,.0f} reason={c[5]}')
print()

# ── 2. 仍在倉（入庫日晚於 baseline，且未出倉）────────────────────
# 這些「已入倉」的倉位，計入績效（攤入成本）
cur.execute("""
SELECT symbol, entry_date, entry_price, shares, amount, entry_rsi, updated_at
FROM open_positions
WHERE entry_date >= ?
ORDER BY entry_date DESC
""", (baseline,))
open_since_baseline = cur.fetchall()
print(f'\n【已入倉】從 {baseline} 起的新開倉（尚未出倉）: {len(open_since_baseline)} 筆')
for o in open_since_baseline:
    print(f'  {o[0]} entry={o[1]} price={o[2]:.2f} shares={o[3]:.2f} amount={o[4]:,.0f} RSI={o[5]:.1f}')

# ── 3. 全部仍在倉（不管何時開的，總倉位）─────────────────────────
cur.execute('SELECT COUNT(*) FROM open_positions')
total_open = cur.fetchone()[0]
cur.execute('SELECT COUNT(*) FROM closed_positions')
total_closed = cur.fetchone()[0]
print(f'\n【總倉位】目前在倉: {total_open} 筆 / 歷史已結算: {total_closed} 筆')

# ── 4. 昨日收盤前年均表現（ benchmark ）─────────────────────────
print('\n=== 昨日收盤資料 ===')
cur.execute("""
SELECT symbol, close_price, rsi_14, volume_ratio, sector
FROM market_snapshots
WHERE date = ?
ORDER BY symbol
LIMIT 20
""", (today,))
snapshots = cur.fetchall()
if snapshots:
    print(f'Snapshot samples: {len(snapshots)}')
    for s in snapshots:
        print(f'  {s}')
else:
    print('market_snapshots 表無資料（可能結構不同）')

# ── 5. Summary ─────────────────────────────────────────────────
print('\n=== Jo 的新規則摘要 ===')
print(f'基準日期: {baseline}')
print(f'已出倉（exit_date >= {baseline}）: {len(closed)} 筆 → 計入勝率/PnL')
print(f'已入倉（entry_date >= {baseline} 且 still open）: {len(open_since_baseline)} 筆 → 計入倉位')
print(f'之前已出倉（exit_date < {baseline}）: 不計入成績')

conn.close()