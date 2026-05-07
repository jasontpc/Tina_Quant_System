import re

d = open('streamlit_tw_stock.py', encoding='utf-8').read()

# Find the TW Analyze button at line 1439
lines = d.split('\n')
for i, line in enumerate(lines):
    if 'btn_tw_single' in line:
        print(f'Line {i+1}: {repr(line)}')
        for j in range(i, min(len(lines), i+5)):
            print(f'  {j+1}: {repr(lines[j])}')
        break