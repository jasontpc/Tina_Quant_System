d = open('streamlit_tw_stock.py', encoding='utf-8').read()
lines = d.split('\n')

# Find _get_secret and show the full function
for i, line in enumerate(lines):
    if 'def _get_secret' in line:
        print(f'Starts at line {i+1}')
        for j in range(i, min(len(lines), i+35)):
            print(f'{j+1}: {lines[j]}')
        break