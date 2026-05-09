# -*- coding: utf-8 -*-
import json
from pathlib import Path
from datetime import datetime

base = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
leo_dir = base / 'teams' / 'leadtrades' / 'leos'

# Main trade data
trades_file = leo_dir / 'leos_trades.json'
with open(trades_file, encoding='utf-8') as f:
    trades = json.load(f)

print(f'=== leos_trades.json ===')
print(f'Type: {type(trades)}')
if isinstance(trades, list):
    print(f'Count: {len(trades)}')
    if len(trades) > 0:
        print(f'First item keys: {list(trades[0].keys())}')
        print(f'Sample: {trades[0]}')
elif isinstance(trades, dict):
    print(f'Keys: {list(trades.keys())}')

# Also check leos_analysis_v65.json - the latest report
analysis_file = leo_dir / 'leos_analysis_v65.json'
with open(analysis_file, encoding='utf-8') as f:
    analysis = json.load(f)
print(f'\n=== leos_analysis_v65.json ===')
if isinstance(analysis, dict):
    print(f'Keys: {list(analysis.keys())}')
    # Check for positions/stats
    for k in ['positions', 'open_positions', 'closed_positions', 'performance', 'summary', 'stats']:
        if k in analysis:
            v = analysis[k]
            if isinstance(v, list):
                print(f'  {k}: {len(v)} items')
            else:
                print(f'  {k}: {str(v)[:300]}')

print('\nDone')