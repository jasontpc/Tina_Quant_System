d = open('streamlit_tw_stock.py', encoding='utf-8').read()

# FIX 3: The actual pattern uses f"{f_v:+,.0f}" not f"{f_v:+,}"
old3 = 'if inst:\n                f_v = inst.get("foreign",0); t_v = inst.get("trust",0); d_v = inst.get("dealer",0)\n                i1,i2,i3 = st.columns(3)\n                i1.metric("Foreign", f"{f_v:+,.0f}")\n                i2.metric("Trust",   f"{t_v:+,.0f}")\n                i3.metric("Dealer",  f"{d_v:+,.0f}")'
new3 = 'f_v = inst.get("foreign",0); t_v = inst.get("trust",0); d_v = inst.get("dealer",0)\n            i1,i2,i3 = st.columns(3)\n            i1.metric("Foreign", f"{f_v:+,.0f}")\n            i2.metric("Trust",   f"{t_v:+,.0f}")\n            i3.metric("Dealer",  f"{d_v:+,.0f}")'

if old3 in d:
    d = d.replace(old3, new3, 1)
    print('FIX 3: TW single stock inst gate removed!')
else:
    print('FIX 3: STILL not found')

open('streamlit_tw_stock.py', 'w', encoding='utf-8').write(d)

# Verify
d2 = open('streamlit_tw_stock.py', encoding='utf-8').read()
idx = d2.find('if inst:\n                f_v')
print(f'FIX3 still present: {idx >= 0}')
print(f'File written, size: {len(d2)} chars')