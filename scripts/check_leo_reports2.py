import json

sim = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leo\reports\sim_trades.json'
with open(sim, 'r', encoding='utf-8') as f:
    d = json.load(f)

print('Type:', type(d))
print('Keys:', list(d.keys()))
print()
print('backtest_period:', d.get('backtest_period'))
stats = d.get('stats', {})
trades = d.get('trades', [])
print('Total trades:', len(trades))
print()
print('=== Stats ===')
if isinstance(stats, dict):
    for k, v in stats.items():
        print(f'  {k}: {v}')
else:
    print(stats)

# Show first 3 trades
print('\n=== Sample Trades ===')
for t in trades[:3]:
    print(f"  {t.get('symbol','?')} entry={t.get('entry_price')} exit={t.get('exit_price')} pnl={t.get('pnl_pct')}")