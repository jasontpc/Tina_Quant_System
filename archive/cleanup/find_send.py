data = open('streamlit_tw_stock.py', 'r', encoding='utf-8').read()
idx = data.find('if col1.button("Send Telegram"')
count = 0
while idx >= 0 and count < 10:
    print(f'At {idx}: {repr(data[idx-30:idx+200])}')
    print()
    idx = data.find('if col1.button("Send Telegram"', idx+1)
    count += 1