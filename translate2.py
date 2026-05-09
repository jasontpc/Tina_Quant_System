# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')

f = open(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\streamlit_tw_stock.py', 'rb')
d = f.read()
f.close()

# Send button
send_sc = b'button(f"Send ({sc}) Grade '
send_sc_new = b'button(f"\xe7\x99\xbc\xe9\x80\x81 ({sc}) \xe7\xad\x89\xe7\xb4\x9a '
d = d.replace(send_sc, send_sc_new)

# Send All button
send_all = b'button(f"Send All ({len(grade_filtered)}) Grade '
send_all_new = b'button(f"\xe7\x99\xbc\xe9\x80\x81\xe5\x85\xa8\xe9\x83\xa8 ({len(grade_filtered)}) \xe7\xad\x89\xe7\xb4\x9a '
d = d.replace(send_all, send_all_new)

# Grade Filter -> 評級篩選
d = d.replace(b'multiselect("Grade Filter"', b'multiselect("\xe8\xa9\x95\xe7\xb4\x9a\xe7\xaf\x87\xe9\x81\xb8"')

# Select All -> 全選
d = d.replace(b'"Select All"', b'"\xe5\x85\xa8\xe9\x81\xb8"')

# Select -> 選擇
d = d.replace(b'multiselect("Select"', b'multiselect("\xe9\x80\x89\xe5\x9b\x9e"')

# Send to Telegram -> 📨 發送到 Telegram
d = d.replace(b'st.expander("Send to Telegram")', b'st.expander("\xf0\x9f\x93\xa8 \xe7\x99\xbc\xe9\x80\x81\xe5\x88\xb0 Telegram")')

# CSV download -> 📥 下載 CSV
d = d.replace(b'download_button("CSV"', b'download_button("\xf0\x9f\x93\xa5 \xe4\xb8\x8b\xe8\xbc\x89 CSV"')

# analyze a stock first -> 請先分析一檔股票
d = d.replace(b'"analyze a stock first")', b'"\xe8\xab\x8b\xe5\x85\x88\xe5\x88\x86\xe6\x9e\x90\xe4\xb8\x80\xe6\xaa\x94\xe8\x82\xa1\xe7\x9b\xae"')

# Single Stock Deep Analysis -> 🔬 個股深度分析
d = d.replace(b'st.subheader("Single Stock Deep Analysis")', b'st.subheader("\xf0\x9f\x94\xac \xe5\x80\x8b\xe8\x82\xa1\xe6\xb7\xb5\xe5\xba\xa6\xe5\x88\x86\xe6\x9e\x90")')

# Stock Code -> 股票代碼
d = d.replace(b'text_input("Stock Code"', b'text_input("\xe8\x82\xa1\xe7\x9b\xae\xe4\xbb\xa3\xe7\xa2\xbc"')

# Toggle text (keep the same text but with proper encoding)
d = d.replace(
    b"st.toggle('\xe5\x88\x86\xe6\x9e\x90\xe5\xbe\x8c\xe8\x87\xaa\xe5\x8b\x95\xe7\x99\xbc\xe9\x80\x81 Telegram'",
    b"st.toggle('\xe5\x88\x86\xe6\x9e\x90\xe5\xbe\x8c\xe8\x87\xaa\xe5\x8b\x95\xe7\x99\xbc\xe9\x80\x81 Telegram'"
)

# Caption ON/OFF TW
d = d.replace(
    b"'ON = \xe8\x87\xaa\xe5\x8b\x95\xe7\x99\xbc\xe9\x80\x81' if st.session_state.get('tw_auto_send') else 'OFF = \xe6\x89\x8b\xe5\x8b\x95\xe7\x99\xbc\xe9\x80\x81'",
    b"'\xe9\x9b\xbb\xe8\x87\xaa\xe7\x99\xbc\xe9\x80\x81' if st.session_state.get('tw_auto_send') else '\xe9\x9b\xbb\xe8\x87\xaa\xe6\x89\x8b\xe5\x8b\x95\xe7\x99\xbc\xe9\x80\x81'"
)

# Caption ON/OFF US
d = d.replace(
    b"'ON = \xe8\x87\xaa\xe5\x8b\x95\xe7\x99\xbc\xe9\x80\x81' if st.session_state.get('us_auto_send') else 'OFF = \xe6\x89\x8b\xe5\x8b\x95\xe7\x99\xbc\xe9\x80\x81'",
    b"'\xe9\x9b\xbb\xe8\x87\xaa\xe7\x99\xbc\xe9\x80\x81' if st.session_state.get('us_auto_send') else '\xe9\x9b\xbb\xe8\x87\xaa\xe6\x89\x8b\xe5\x8b\x95\xe7\x99\xbc\xe9\x80\x81'"
)

# US single Analyze button
d = d.replace(b'button("Analyze", type="primary", use_container_width=True, key="btn_us_single")', b'button("\xf0\x9f\x94\x8d \xe5\x88\x86\xe6\x9e\x90", type="primary", use_container_width=True, key="btn_us_single")')

# US batch Analyze button
d = d.replace(b'button("Analyze", type="primary", use_container_width=True, key="btn_us_analyze")', b'button("\xf0\x9f\x94\x8d \xe9\x96\x8b\xe5\xa7\x9b\xe5\x88\x86\xe6\x9e\x90", type="primary", use_container_width=True, key="btn_us_analyze")')

f = open(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\streamlit_tw_stock.py', 'wb')
f.write(d)
f.close()
print('done')
