import re

d = open('streamlit_tw_stock.py', encoding='utf-8').read()

# Check TELEGRAM_BOT_TOKEN assignments
matches = list(re.finditer(r'TELEGRAM_BOT_TOKEN\s*=', d))
print(f'TELEGRAM_BOT_TOKEN assignments: {len(matches)}')
for m in matches:
    print(f'  at {m.start()}: {d[m.start():m.start()+100]}')

# Check if there are multiple assignments
assign_lines = []
lines = d.split('\n')
for i, line in enumerate(lines):
    if 'TELEGRAM_BOT_TOKEN' in line and '=' in line and 'def ' not in line:
        print(f'Line {i+1}: {line.strip()}')

# The error URL has: /bot{'tg_bot_token': '8614615741:AAHEMV6da...'}/sendMessage
# This suggests TELEGRAM_BOT_TOKEN = str({'tg_bot_token': '8614615741:...'})
# Which would happen if st.secrets returns the nested dict and str() is called on it

# Let's check if there's any str() conversion anywhere near TELEGRAM_BOT_TOKEN
for i, line in enumerate(lines):
    if 'TELEGRAM_BOT_TOKEN' in line and 'str(' in line:
        print(f'str() near TELEGRAM_BOT_TOKEN at line {i+1}: {line}')