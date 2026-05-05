# -*- coding: utf-8 -*-
import json
from datetime import datetime

d = json.load(open(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\ray\autonomous_trades.json', encoding='utf-8'))
print('Last update:', d.get('last_update'))
print('Total trades:', len(d.get('trades', [])))
print('Strategy:', d.get('strategy', 'N/A'))

# Count by type
trades = d.get('trades', [])
types = {}
for t in trades:
    k = t.get('type', 'unknown')
    types[k] = types.get(k, 0) + 1
print('By type:', types)

# Count by ETF
from collections import Counter
etfs = Counter(t.get('etf_id') for t in trades)
print('Top 5 ETFs:', etfs.most_common(5))

# Recent trades
recent = [t for t in sorted(trades, key=lambda x: x.get('timestamp',''), reverse=True)][:3]
for t in recent:
    ts = t['timestamp']
    eid = t['etf_id']
    typ = t['type']
    act = t.get('action','N/A')
    print(f'  {ts} | {eid} | {typ} | {act}')