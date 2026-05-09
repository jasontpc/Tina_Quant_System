# -*- coding: utf-8 -*-
import json
from pathlib import Path

base = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leadtrades\leos')
with open(base / 'leos_trades.json', encoding='utf-8') as f:
    data = json.load(f)

# Check a sample trade's actual fields
print('=== Sample trade fields ===')
for i, t in enumerate(data['trades'][:3]):
    print(f'Trade {i}: symbol={t.get("symbol")}')
    print(f'  All keys: {list(t.keys())}')
    print(f'  entry_date={t.get("entry_date")} date={t.get("date")} entry={t.get("entry")}')
    print(f'  entry_price={t.get("entry_price")} price={t.get("price")}')
    print(f'  exit_date={t.get("exit_date")}')
    print(f'  amount={t.get("amount")} shares={t.get("shares")}')
    print()