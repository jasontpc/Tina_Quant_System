import json, os

# Check leos_trades.json structure
path = 'teams/leadtrades/leos/leos_trades.json'
with open(path, encoding='utf-8') as f:
    data = json.load(f)
trades = data['trades']
print(f'Total positions: {len(trades)}')
print(f'Stats in file: {data["stats"]}')

closed = [t for t in trades if t.get('status') == 'closed']
open_pos = [t for t in trades if t.get('status') == 'open']
print(f'Closed: {len(closed)}, Open: {len(open_pos)}')

# Real stats
real_wins = sum(1 for t in closed if t.get('pnl', 0) > 0)
real_losses = sum(1 for t in closed if t.get('pnl', 0) < 0)
real_pnl = sum(t.get('pnl', 0) for t in closed)
print(f'Real: wins={real_wins}, losses={real_losses}, PnL={real_pnl:,.0f}')
print(f'File wins: {data["stats"].get("wins",0)}, File losses: {data["stats"].get("losses",0)}')
print(f'Stats inaccurate: {data["stats"].get("wins",0) != real_wins}')

# US stock prices issue
us_stocks = ['NVDA', 'AMD', 'QCOM', 'META', 'MSFT', 'AMZN', 'GOOGL', 'AVGO']
us_open = [t for t in open_pos if t.get('symbol','') in us_stocks]
print()
print('US open positions (check current_price field):')
for t in us_open:
    entry = t.get('entry_price', 0)
    current = t.get('current_price', 'N/A')
    pnl_pct = t.get('pnl_pct', 'N/A')
    print(f'  {t["symbol"]}: entry={entry}, current={current}, pnl_pct={pnl_pct}')

# Nana DB check
print()
nana_trades_path = 'teams/nana/autonomous_trades.json'
if os.path.exists(nana_trades_path):
    with open(nana_trades_path, encoding='utf-8') as f:
        nana_data = json.load(f)
    nana_trades = nana_data.get('trades', nana_data) if isinstance(nana_data, dict) else nana_data
    if isinstance(nana_trades, dict):
        nana_trades = nana_trades.get('trades', [])
    print(f'Nana trades: {len(nana_trades)}')
    if nana_trades:
        print(f'Nana sample: {json.dumps(nana_trades[0], ensure_ascii=False)[:200]}')

# Ray DB check
ray_trades_path = 'teams/ray/autonomous_trades.json'
if os.path.exists(ray_trades_path):
    with open(ray_trades_path, encoding='utf-8') as f:
        ray_data = json.load(f)
    ray_trades = ray_data.get('trades', ray_data) if isinstance(ray_data, dict) else ray_data
    if isinstance(ray_trades, dict):
        ray_trades = ray_trades.get('trades', [])
    print(f'Ray trades: {len(ray_trades)}')

# Check cron error jobs
print()
print('=== Cron Error Jobs ===')
cron_errors = ['27597611-a29c-4921-bfe5-bdddf77498f6', '618aa329-0e53-4909-9657-83b9fa844b4f']
for jid in cron_errors:
    print(f'  {jid}: needs investigation')
