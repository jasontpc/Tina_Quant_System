import re

d = open('streamlit_tw_stock.py', encoding='utf-8').read()
lines = d.split('\n')

# Show around the TW push_telegram (line ~1581+4)
for i in range(1577, 1600):
    if i < len(lines):
        line = lines[i]
        ind = len(line) - len(line.lstrip())
        print(f'{i+1} ({ind:2d}): {line[:120]}')

print()
print('=== US push_telegram around 2036 ===')
for i in range(2028, 2060):
    if i < len(lines):
        line = lines[i]
        ind = len(line) - len(line.lstrip())
        print(f'{i+1} ({ind:2d}): {line[:120]}')