d = open('streamlit_tw_stock.py', encoding='utf-8').read()
lines = d.split('\n')

# Find line 99 (push_telegram) by actual line number
for i, line in enumerate(lines):
    if line.strip() == 'def push_telegram(message):':
        print(f'push_telegram at line {i+1}')
        for j in range(i, min(len(lines), i+20)):
            print(f'{j+1}: {lines[j]}')
        break