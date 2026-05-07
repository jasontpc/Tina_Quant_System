d = open('streamlit_tw_stock.py', encoding='utf-8').read()

# Find US analyze block
idx = d.find("us_do_single")
print(f"us_do_single first found at: {idx}")

# Find the full US analyze block
# Look for pattern around the US single stock
idx2 = d.find("if us_do_single:")
if idx2 < 0:
    idx2 = d.find("if us_do_single:\n")
print(f"if us_do_single: at {idx2}")

# Show context around the US analyze
if idx2 >= 0:
    print(repr(d[idx2:idx2+500]))
else:
    # Try to find it differently
    for m in __import__('re').finditer(r'if us_do_single', d):
        print(f"us_do_single at {m.start()}: {repr(d[m.start():m.start()+100])}")