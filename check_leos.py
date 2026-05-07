import json

d = open('teams/leadtrades/leos/leos_trades.json', encoding='utf-8').read()
data = json.loads(d)
print('Stats:', data.get('stats', {}))
print('Open positions:', len(data.get('trades', [])))
trades = data.get('trades', [])
for t in trades[:5]:
    code = t.get('code', '?')
    entry = t.get('entry_price', 0)
    pnl = t.get('pnl_pct', 0)
    print(f'  {code} entry={entry} pnl={pnl}%')

# Now check leos_v65.py for US stock support
d2 = open('teams/leadtrades/leos/leos_v65.py', encoding='utf-8').read()
# Check if it has US stock symbols
us_symbols = ['NVDA', 'AMD', 'INTC', 'AVGO', 'MU', 'MSFT', 'GOOGL', 'META', 'TSLA', 'AMZN', 'AAPL', 'QCOM', 'MRVL', 'SMCI', 'GE', 'CAT']
found = [s for s in us_symbols if s in d2]
print(f'\nUS symbols in leos_v65.py: {found}')

# Check if it has TW symbols
tw_symbols = ['2330', '2454', '2317', '2379', '2376', '2382', '3665', '3034']
found_tw = [s for s in tw_symbols if s in d2]
print(f'TW symbols in leos_v65.py: {found_tw}')