d = open('streamlit_tw_stock.py', encoding='utf-8').read()
lines = d.split('\n')

# Find line 60 (TELEGRAM_BOT_TOKEN assignment)
for i in range(58, 68):
    print(f'{i+1}: {lines[i]}')