d = open('streamlit_tw_stock.py', encoding='utf-8').read()
lines = d.split('\n')

# Show lines around the form section to understand the context
for i in range(1158, 1175):
    print(f'{i+1}: {lines[i]}')