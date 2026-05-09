# -*- coding: utf-8 -*-
import json
from pathlib import Path

base = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
backtest_file = base / 'data' / 'backtest_results.json'
track_dir = base / 'teams' / 'leadtrades' / 'leos'

print('=== backtest_results.json ===')
with open(backtest_file, encoding='utf-8') as f:
    data = json.load(f)

print(f'Type: {type(data)}')
if isinstance(data, list):
    print(f'Length: {len(data)}')
    if len(data) > 0:
        print(f'First item keys: {list(data[0].keys()) if isinstance(data[0], dict) else data[0]}')
        print(f'Sample: {data[0]}')
elif isinstance(data, dict):
    print(f'Keys: {list(data.keys())}')
    for k, v in data.items():
        if isinstance(v, list):
            print(f'  {k}: {len(v)} items')
        else:
            print(f'  {k}: {str(v)[:200]}')

# Check track files
print('\n=== track files ===')
for f in sorted(track_dir.glob('*_track.json'))[:5]:
    with open(f, encoding='utf-8') as fp:
        content = json.load(fp)
    print(f'{f.name}: {content}')

print('\nDone')