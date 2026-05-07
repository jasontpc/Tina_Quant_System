d = open('streamlit_tw_stock.py', encoding='utf-8').read()
lines = d.split('\n')

# Find the TW send button and show surrounding lines
for i, line in enumerate(lines):
    if 'DEBUG: TW Send' in line or ('col1.button' in line and 'Send Telegram' in line):
        print(f'=== Line {i+1} ===')
        for j in range(max(0,i-2), min(len(lines), i+8)):
            print(f'{j+1}: {lines[j][:120]}')
        print()