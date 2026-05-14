import json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SIM_FILE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leo\reports\sim_trades.json'
OUTPUT_FILE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leo\reports\leo_backtest_report_v2.json'

with open(SIM_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

trades = data.get('trades', [])
period = data.get('backtest_period', 'N/A')

# Compute per-trade pnl if missing
for t in trades:
    if t.get('pnl') is None and t.get('exit_price') and t.get('entry_price'):
        entry = float(t['entry_price'])
        exit = float(t['exit_price'])
        direction = t.get('direction', 1)
        t['pnl_pct'] = round((exit - entry) / entry * 100 * direction, 3)

wins = [t for t in trades if t.get('pnl_pct', 0) > 0]
losses = [t for t in trades if t.get('pnl_pct', 0) <= 0]
total = len(trades)
wr = len(wins) / total * 100 if total > 0 else 0
avg_ret = sum(t.get('pnl_pct', 0) for t in trades) / total if total > 0 else 0
avg_win = sum(t['pnl_pct'] for t in wins) / len(wins) if wins else 0
avg_loss = sum(t['pnl_pct'] for t in losses) / len(losses) if losses else 0

by_stock = {}
for t in trades:
    sym = t.get('symbol', 'UNKNOWN')
    if sym not in by_stock:
        by_stock[sym] = {'trades': 0, 'wins': 0, 'total_pnl': 0}
    by_stock[sym]['trades'] += 1
    pnl = t.get('pnl_pct', 0)
    by_stock[sym]['total_pnl'] += pnl
    if pnl > 0:
        by_stock[sym]['wins'] += 1

stock_reports = []
for sym, s in by_stock.items():
    wr_s = s['wins'] / s['trades'] * 100 if s['trades'] > 0 else 0
    avg_s = s['total_pnl'] / s['trades'] if s['trades'] > 0 else 0
    stock_reports.append({
        'ticker': sym,
        'total_trades': s['trades'],
        'wins': s['wins'],
        'losses': s['trades'] - s['wins'],
        'win_rate': round(wr_s, 1),
        'avg_return': round(avg_s, 3),
        'total_return': round(s['total_pnl'], 2)
    })

stock_reports.sort(key=lambda x: x['win_rate'], reverse=True)

report = {
    'date': '2026-05-14',
    'backtest_period': period,
    'performance': {
        'total_trades': total,
        'wins': len(wins),
        'losses': len(losses),
        'win_rate': round(wr, 2),
        'avg_return': round(avg_ret, 3),
        'avg_win': round(avg_win, 3),
        'avg_loss': round(avg_loss, 3),
    },
    'params': {
        'RSI_Period': 14,
        'RSI_Entry_Min': 30,
        'RSI_Entry_Max': 60,
        'Hold_Days': 3,
        'Take_Profit_ATR': 2.0,
        'Stop_Loss_ATR': 2.0,
        'Trailing_ATR': 1.5,
        'Score_Min': 30,
        'ADX_Threshold': 15
    },
    'by_stock': stock_reports,
}

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print(f'Report: {OUTPUT_FILE}')
print(f'Total: {total} trades | WR: {wr:.1f}% | Avg: {avg_ret:.3f}%')
for s in stock_reports:
    print(f"  {s['ticker']} | {s['total_trades']} trades | WR {s['win_rate']}% | Avg {s['avg_return']:+.3f}%")