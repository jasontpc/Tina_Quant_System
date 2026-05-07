import json
with open('teams/leadtrades/leos/leos_trades.json', encoding='utf-8') as f:
    data = json.load(f)

# Show 2382 trade exit records (Jo sold 2382)
closed_2382 = [t for t in data['trades'] if t.get('symbol') == '2382' and t.get('status') == 'closed']
print(f'Closed 2382 trades: {len(closed_2382)}')
for t in closed_2382:
    print(f"  Exit: {t.get('exit_price')} @ {t.get('exit_time')} | PnL: {t.get('pnl'):,.0f} ({t.get('pnl_pct'):+.2f}%) | Reason: {t.get('exit_reason')}")

# Open 2382 positions
open_2382 = [t for t in data['trades'] if t.get('symbol') == '2382' and t.get('status') == 'open']
print(f"\nOpen 2382 positions: {len(open_2382)}")
for t in open_2382:
    print(f"  Entry: {t.get('entry_price')} x {t.get('shares')}股 = {t.get('amount'):,.0f}")

# All closed stats
closed = [t for t in data['trades'] if t.get('status') == 'closed']
total_pnl = sum(t.get('pnl', 0) for t in closed)
wins = [t for t in closed if t.get('pnl', 0) > 0]
losses = [t for t in closed if t.get('pnl', 0) < 0]
print(f"\nAll Closed: {len(closed)} | Wins: {len(wins)} | Losses: {len(losses)} | Win rate: {len(wins)/len(closed)*100:.1f}%")
print(f"Total PnL: NT${total_pnl:,+}")
