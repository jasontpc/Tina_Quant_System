# -*- coding: utf-8 -*-
f = open(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\streamlit_tw_stock.py', 'rb')
d = f.read()
f.close()

# analyze a stock first -> 請先分析一檔股票 (inside st.warning)
d = d.replace(
    b'st.warning("Please analyze a stock first")',
    b'st.warning("\xe8\xab\x8b\xe5\x85\x88\xe5\x88\x86\xe6\x9e\x90\xe4\xb8\x80\xe6\xaa\x94\xe8\x82\xa1\xe7\x9b\xae")'
)

# Single Stock Deep Analysis -> 🔬 個股深度分析 (the comment line)
d = d.replace(
    b'Single Stock Deep Analysis ---\r\n',
    b'\xe5\x80\x8b\xe8\x82\xa1\xe6\xb7\xb5\xe5\xba\xa6\xe5\x88\x86\xe6\x9e\x90 ---\r\n'
)

f = open(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\streamlit_tw_stock.py', 'wb')
f.write(d)
f.close()
print('done')
