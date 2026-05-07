d = open('streamlit_tw_stock.py', encoding='utf-8').read()

# Find the exact structure of the TW single stock section
# The DEBUG is at 12-space indent and is inside the 'else' of 'if r:'
# But we need to make sure it's ABOVE the button, not accidentally moved

# Let's look at the exact structure around TW DEBUG
idx_tw = d.find('DEBUG: TW Send button rendering now')
# find the line number
lines = d.split('\n')
tw_line = next(i for i, l in enumerate(lines) if 'DEBUG: TW Send button rendering now' in l)
print(f'TW DEBUG at line {tw_line+1}, indent {len(lines[tw_line]) - len(lines[tw_line].lstrip())} spaces')

# Check indentation of surrounding lines
for i in range(tw_line - 3, tw_line + 3):
    line = lines[i]
    print(f'  {i+1}: ({len(line)-len(line.lstrip())} spaces) {repr(line[:80])}')

print()
# Now check US DEBUG
idx_us = d.find('DEBUG: US Send button rendering now')
us_line = next(i for i, l in enumerate(lines) if 'DEBUG: US Send button rendering now' in l)
print(f'US DEBUG at line {us_line+1}, indent {len(lines[us_line]) - len(lines[us_line].lstrip())} spaces')
for i in range(us_line - 3, us_line + 3):
    line = lines[i]
    print(f'  {i+1}: ({len(line)-len(line.lstrip())} spaces) {repr(line[:80])}')