# -*- coding: utf-8 -*-
f = open(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\streamlit_tw_stock.py', 'rb')
d = f.read()
f.close()

# TW狀態 -> 台股狀態
d = d.replace(
    b'm[2].metric("\xe5\x8f\xb0\xe7\x8b\x80\xe6\x85\x8b",',
    b'm[2].metric("\xe5\x8f\xb0\xe8\x82\xa1\xe7\x8a\xb6\xe6\x85\x8b",'
)

# US狀態 -> 美股狀態
d = d.replace(
    b'm[5].metric("\xe7\xbe\x8e\xe7\x8b\x80\xe6\x85\x8b",',
    b'm[5].metric("\xe7\xbe\x8e\xe8\x82\xa1\xe7\x8a\xb6\xe6\x85\x8b",'
)

# btn_tw_single: Analyze -> 🔍 分析
d = d.replace(
    b'button("Analyze", type="primary", use_container_width=True, key="btn_tw_single")',
    b'button("\xf0\x9f\x94\x8d \xe5\x88\x86\xe6\x9e\x90", type="primary", use_container_width=True, key="btn_tw_single")'
)

# stocks info -> 檔股票
d = d.replace(
    b'f"{len(codes)} stocks"',
    b'f"{len(codes)} \xe6\xaa\x94\xe8\x82\xa1\xe7\x9b\xae"'
)

# analyze a stock first -> 請先分析一檔股票
d = d.replace(
    b'"analyze a stock first")',
    b'"\xe8\xab\x8b\xe5\x85\x88\xe5\x88\x86\xe6\x9e\x90\xe4\xb8\x80\xe6\xaa\x94\xe8\x82\xa1\xe7\x9b\xae"'
)

# Single Stock Deep Analysis -> 🔬 個股深度分析
d = d.replace(
    b'st.subheader("Single Stock Deep Analysis")',
    b'st.subheader("\xf0\x9f\x94\xac \xe5\x80\x8b\xe8\x82\xa1\xe6\xb7\xb5\xe5\xba\xa6\xe5\x88\x86\xe6\x9e\x90")'
)

# CSV download -> 📥 下載 CSV
d = d.replace(
    b'download_button("CSV"',
    b'download_button("\xf0\x9f\x93\xa5 \xe4\xb8\x8b\xe8\xbc\x89 CSV"'
)

# Select All -> 全選
d = d.replace(
    b'"Select All"',
    b'"\xe5\x85\xa8\xe9\x81\xb8"'
)

f = open(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\streamlit_tw_stock.py', 'wb')
f.write(d)
f.close()
print('done')
