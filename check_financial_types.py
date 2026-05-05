# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, 'scripts')
from finmind_safe import finmind_get

data = finmind_get('TaiwanStockFinancialStatements', data_id='2330', start_date='2025-01-01', end_date='2026-05-02')
types = {}
for row in data.get('data', []):
    t = row['type']
    if t not in types:
        types[t] = []
    types[t].append(row)

for t, rows in types.items():
    print(f'{t}: {len(rows)} records')
    for r in rows[:2]:
        print(f'  {r["date"]}: {r["value"]}')