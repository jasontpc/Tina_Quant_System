# -*- coding: utf-8 -*-
import json
from pathlib import Path
from datetime import datetime

base = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
leo_dir = base / 'teams' / 'leadtrades' / 'leos'

BASELINE = '2026-05-07'

trades_file = leo_dir / 'leos_trades.json'
with open(trades_file, encoding='utf-8') as f:
    data = json.load(f)

trades = data.get('trades', [])
stats = data.get('stats', {})

print(f'=== Leo v6.5 成績報告（{BASELINE} 起）===')
print(f'總交易筆數: {len(trades)}')
if stats:
    print(f'Stats keys: {list(stats.keys())}')

# Filter trades by baseline date (check entry_date and exit_date)
open_trades = []  # entry >= baseline, no exit or exit >= baseline
closed_trades = []  # exit >= baseline

for t in trades:
    entry = t.get('entry_date', '')
    exit_d = t.get('exit_date', None)
    
    # Check if entry is >= baseline
    if entry < BASELINE and exit_d is not None and exit_d < BASELINE:
        # old closed trade - skip
        continue
    
    if exit_d is None or exit_d == '':
        open_trades.append(t)
    else:
        closed_trades.append(t)

print(f'\n📊 成績概況（{BASELINE} 起）')
print(f'───')
print(f'在倉（entry >= {BASELINE}，仍未出倉）: {len(open_trades)} 檔')
print(f'已出（exit_date >= {BASELINE}）: {len(closed_trades)} 檔')
total = len(open_trades) + len(closed_trades)
print(f'總計: {total} 檔')

# Win rate for closed trades
wins = sum(1 for t in closed_trades if t.get('pnl_pc', 0) > 0)
losses = sum(1 for t in closed_trades if t.get('pnl_pc', 0) < 0)
net = sum(t.get('pnl_pc', 0) for t in closed_trades)

if closed_trades:
    print(f'\n🚪 已出倉（{len(closed_trades)} 檔）')
    print(f'  贏: {wins} / 輸: {losses} / 勝率: {wins/(wins+losses)*100:.1f}%' if wins+losses > 0 else '  N/A')
    for t in closed_trades[:10]:
        pct = t.get('pnl_pc', 0)
        status = '🟢' if pct > 0 else '🔴'
        print(f'  {status} {t.get("symbol","?")} ret={pct:.2f}% exit={t.get("exit_date","?")}')
    if len(closed_trades) > 10:
        print(f'  ...還有 {len(closed_trades)-10} 檔')

if open_trades:
    invested = sum(t.get('amount', 0) for t in open_trades)
    print(f'\n📌 在倉（{len(open_trades)} 檔，總投入 NT$ {invested:,.0f}）')
    for t in open_trades[:10]:
        print(f'  📌 {t.get("symbol","?")} entry={t.get("entry_date","?")} price={t.get("entry_price","?")} shares={t.get("shares","?")} amount={t.get("amount",0):,.0f}')
    if len(open_trades) > 10:
        print(f'  ...還有 {len(open_trades)-10} 檔')

# Historical stats from the file
print(f'\n📈 歷史參考（全部時間）')
if 'win_rate' in stats:
    print(f'  歷史勝率: {stats["win_rate"]:.1f}%')
if 'total_pnl' in stats:
    print(f'  歷史總PnL: {stats["total_pnl"]}')
if 'total_trades' in stats:
    print(f'  歷史總交易: {stats["total_trades"]}')

print(f'\nDone')