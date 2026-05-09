# -*- coding: utf-8 -*-
import json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

base = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
leo_dir = base / 'teams' / 'leadtrades' / 'leos'
BASELINE = '2026-05-07'

trades_file = leo_dir / 'leos_trades.json'
with open(trades_file, encoding='utf-8') as f:
    data = json.load(f)

trades = data.get('trades', [])
stats = data.get('stats', {})

print(f'=== Leo v6.5 Performance Report ({BASELINE}+) ===')
print(f'Total trades: {len(trades)}')

# Stats from the file (full history)
total_all = stats.get('total', 0)
wins_all = stats.get('wins', 0)
losses_all = stats.get('losses', 0)
pnl_all = stats.get('total_pnl', 0)
win_rate_all = wins_all / total_all * 100 if total_all > 0 else 0

print(f'\n[Historical Reference - ALL TIME]')
print(f'  Total: {total_all} | Wins: {wins_all} | Losses: {losses_all}')
print(f'  Win Rate: {win_rate_all:.1f}%')
print(f'  Total PnL: {pnl_all}')

# Filter by baseline
open_trades = []
closed_since = []

for t in trades:
    entry = t.get('entry_date', '')
    exit_d = t.get('exit_date')
    
    # Skip old closed trades (both before baseline)
    if entry < BASELINE and exit_d and exit_d < BASELINE:
        continue
    
    if exit_d is None or exit_d == '' or exit_d >= BASELINE:
        open_trades.append(t)

# Separate open vs closed since baseline
still_open = [t for t in open_trades if t.get('exit_date') is None or t.get('exit_date') == '']
exited_since = [t for t in open_trades if t.get('exit_date') and t.get('exit_date') >= BASELINE]

print(f'\n[Performance Since {BASELINE}]')
print(f'  Still open (entry >= {BASELINE}): {len(still_open)}')
print(f'  Exited (exit >= {BASELINE}): {len(exited_since)}')
print(f'  Total counted: {len(still_open) + len(exited_since)}')

wins_since = sum(1 for t in exited_since if t.get('pnl_pc', 0) > 0)
losses_since = sum(1 for t in exited_since if t.get('pnl_pc', 0) < 0)
pnl_since = sum(t.get('pnl', 0) for t in exited_since)

if exited_since:
    wr_since = wins_since / (wins_since + losses_since) * 100 if (wins_since + losses_since) > 0 else 0
    print(f'\n  Exited trades: {len(exited_since)} | Win: {wins_since} | Loss: {losses_since} | WR: {wr_since:.1f}%')
    print(f'  PnL (exited): {pnl_since}')

invested = sum(t.get('amount', 0) for t in still_open)
if still_open:
    print(f'\n  Open positions: {len(still_open)} | Invested: {invested:,.0f}')

# Show sample
if still_open[:5]:
    print('  Sample open:')
    for t in still_open[:5]:
        print(f'    {t.get("symbol")} entry={t.get("entry_date")} price={t.get("entry_price")} shares={t.get("shares")}')

print('\nDone')