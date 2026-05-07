d = open('streamlit_tw_stock.py', encoding='utf-8').read()
lines = d.split('\n')

# Find US single stock analyze block and show remaining part
for i, line in enumerate(lines):
    if i > 1930 and i < 2050:
        if any(k in line for k in ['metric', 'metric', 'MA20', 'MACD', 'Vol', 'BIAS', 'RSI', 'K/D', 'BB', 'tier_display', 'score_detail', 'msg = (']):
            print(f'{i+1}: {line[:100]}')