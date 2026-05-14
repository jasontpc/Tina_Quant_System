import re, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
with open(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\streamlit_tw_stock.py", 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

# Find all tab-like structures
tabs = [(m.start(), content[max(0,m.start()-100):m.start()+200]) for m in re.finditer(r'tab\d|st\.tab|tabs\[|st_radio|selectbox', content)]
for i, (pos, ctx) in enumerate(tabs[:10]):
    print(f"[{i}] pos={pos}")
    print(f"  ctx: {ctx.replace(chr(10),' ')}")
    print()