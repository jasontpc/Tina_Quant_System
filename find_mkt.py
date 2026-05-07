d = open('streamlit_tw_stock.py', encoding='utf-8').read()
lines = d.split('\n')

# Find the market summary section - look for TWII RSI and S&P500 together
for i, line in enumerate(lines):
    if '[ERR]' in line or 'err.*過熱' in line.lower():
        print(f'Line {i+1}: {line[:100]}')
        for j in range(max(0,i-5), min(len(lines), i+5)):
            print(f'  {j+1}: {lines[j][:100]}')
        print()