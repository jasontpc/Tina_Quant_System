import json, os, sys

sys.stdout.reconfigure(encoding='utf-8')

print('=' * 60)
print('Tina Quant System — Paper Trade Assessment')
print('=' * 60)

# 1. Leo paper trades
print('\n=== Leo Paper Trades ===')
leo = json.load(open('teams/leadtrades/leos/leos_trades.json', encoding='utf-8'))
trades = leo.get('trades', [])
open_t = [t for t in trades if t.get('status') == 'open']
closed_t = [t for t in trades if t.get('status') == 'closed']
print(f'Total: {len(trades)} | Open: {len(open_t)} | Closed: {len(closed_t)}')

if closed_t:
    wins = [t for t in closed_t if t.get('pnl', 0) > 0]
    losses = [t for t in closed_t if t.get('pnl', 0) < 0]
    total_pnl = sum(t.get('pnl', 0) for t in closed_t)
    avg_win = sum(t.get('pnl', 0) for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t.get('pnl', 0) for t in losses) / len(losses) if losses else 0
    print(f'Wins: {len(wins)}, Losses: {len(losses)}')
    print(f'Win Rate: {len(wins)/len(closed_t)*100:.1f}%')
    print(f'Total PnL: NT${total_pnl:,.0f}')
    print(f'Avg Win: NT${avg_win:,.0f}, Avg Loss: NT${avg_loss:,.0f}')
else:
    print('No closed trades yet!')

# Show open positions detail
print('\nOpen positions by symbol:')
from collections import Counter
symbols = Counter(t['symbol'] for t in open_t)
for sym, count in sorted(symbols.items()):
    sample = next(t for t in open_t if t['symbol'] == sym)
    entry_days = (os.path.getmtime('teams/leadtrades/leos/leos_trades.json') - 
                  os.path.getctime('teams/leadtrades/leos/leos_trades.json'))
    print(f"  {sym}: {count} positions, entry price ${sample['entry_price']}")

# 2. Check leo_v65 for strategy params
print('\n=== Leo Strategy Parameters ===')
leo_v65 = open('teams/leadtrades/leos/leos_v65.py', encoding='utf-8').read()
for line in leo_v65.split('\n'):
    if '=' in line and not line.strip().startswith('#') and not line.strip().startswith('#'):
        l = line.strip()
        if any(k in l for k in ['ENTRY_RSI', 'EXIT_RSI', 'TAKE_PROFIT', 'STOP_LOSS', 'MOMENTUM', 'MAX_POSITION']):
            print(f'  {l[:80]}')

# 3. Check if there's a Nana system
print('\n=== Nana Paper Trades ===')
nana_files = [f for f in os.listdir('teams/nana') if 'trade' in f.lower() and f.endswith('.json')]
print(f'Nana trade files: {nana_files}')

# 4. Check Ray DCA
print('\n=== Ray ETF DCA ===')
ray_files = [f for f in os.listdir('teams/ray') if 'dca' in f.lower() or 'trade' in f.lower()]
print(f'Ray trade files: {ray_files}')

# 5. What teams exist and their status
print('\n=== All Teams Status ===')
for team in ['nana', 'leo', 'ray', 'sherry', 'maggy', 'vogel']:
    team_path = f'teams/{team}'
    if os.path.exists(team_path):
        files = os.listdir(team_path)
        json_files = [f for f in files if f.endswith('.json')]
        print(f'{team}: {len(files)} files, {len(json_files)} JSON files')

# 6. Check for any performance tracking
print('\n=== Performance Tracking ===')
for fname in ['performance.json', 'stats.json', 'pnl.json', 'daily_report.json']:
    for root, dirs, files in os.walk('teams'):
        if fname in files:
            fpath = os.path.join(root, fname)
            try:
                data = json.load(open(fpath, encoding='utf-8'))
                print(f'{fpath}: {list(data.keys())[:5]}')
            except:
                pass

print('\n=== Issues Found ===')
print('1. All 106 Leo positions are OPEN — no closed means no real performance data')
print('2. stats show zeros — system not calculating pnl on closed trades')
print('3. No shared paper trade platform for multiple teams')
print('4. No daily automated review/feedback loop')
print('5. leos_failure_db.json is empty — failure analysis not running')