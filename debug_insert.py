# Count actual ? characters in VALUES string
import re

with open(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\vogel\build_vogel_db.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find VALUES (...) 
# The values tuple has 37 items: (d['date'], 'TX', main_cd, d.get('open'), d.get('max'), d.get('min'), c,
# d.get('volume'), d.get('open_interest'), d.get('spread'), d.get('spread_per'),
# sma5, sma10, sma20, sma60, sma120, ema12, ema26, bb_u, bb_m, bb_l,
# rsi14, rsi7, rsi28, macd_l, macd_s, macd_h, atr14, atr30, kk, kd, kj, wr, cci20, None, zone)

# Let's find the VALUES line
lines = content.split('\n')
for i, line in enumerate(lines):
    if 'VALUES' in line and '?' in line:
        print(f'Line {i}: {line[:100]}')
        # Count ?
        count = line.count('?')
        print(f'? count in this line: {count}')

# Also count the tuple items
for i, line in enumerate(lines):
    if "(d['date'], 'TX'" in line:
        print(f'\nTuple line {i}:')
        print(line[:200])