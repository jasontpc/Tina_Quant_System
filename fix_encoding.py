# Fix unicode in script
with open(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\scripts\tw500_backtest.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('\u2264', '<=').replace('\u2192', '->').replace('\u2019', "'").replace('\u2018', "'")

with open(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\scripts\tw500_backtest.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed unicode characters")