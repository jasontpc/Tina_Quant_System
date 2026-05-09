# -*- coding: utf-8 -*-
import json
from pathlib import Path

base = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
leo_dir = base / 'teams' / 'leadtrades' / 'leos'

# Leo v6.5 stores current positions in aggressive_entry_config.json
config_file = leo_dir / 'aggressive_entry_config.json'
with open(config_file, encoding='utf-8') as f:
    config = json.load(f)
print('=== aggressive_entry_config.json ===')
print(f'Keys: {list(config.keys())}')
for k, v in config.items():
    if isinstance(v, list) and len(v) > 0:
        print(f'  {k}: {len(v)} items, sample={v[0] if v else "empty"}')
    else:
        print(f'  {k}: {str(v)[:200]}')

# Also check ai_infra_analysis.json
infra_file = base / 'data' / 'ai_infra_analysis.json'
with open(infra_file, encoding='utf-8') as f:
    infra = json.load(f)
print('\n=== ai_infra_analysis.json ===')
if isinstance(infra, list) and len(infra) > 0:
    print(f'Type: list, {len(infra)} items')
    print(f'First: {infra[0]}')
elif isinstance(infra, dict):
    print(f'Keys: {list(infra.keys())}')

print('\nDone')