# -*- coding: utf-8 -*-
import re

f = open(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\streamlit_tw_stock.py', 'rb')
d = f.read()
f.close()

# 1. page_config + title
d = d.replace(
    b'st.set_page_config(page_title="Tina Scanner v3.0", page_icon="[UP]", layout="wide")\r\n\r\nst.title("[UP] Tina Scanner v3.0 \xe2\x80\x94 TW+US Tech Scoring")',
    b'st.set_page_config(page_title="Tina Scanner v3.0 \xe2\x80\x94 \xe5\x8f\xb0\xe7\xbe\x8e\xe8\x82\xa1\xe6\x8a\x80\xe8\xa1\x93\xe8\xa9\x95\xe5\x88\x86", page_icon="\xf0\x9f\x93\x8a", layout="wide")\r\n\r\nst.title("\xf0\x9f\x93\x8a Tina Scanner v3.0 \xe2\x80\x94 \xe5\x8f\xb0\xe7\xbe\x8e\xe8\x82\xa1\xe6\x8a\x80\xe8\xa1\x93\xe8\xa9\x95\xe5\x88\x86\xe7\xb3\xbb\xe7\xab\xaf")'
)

# 2. tabs
d = d.replace(
    b'st.tabs(["\xf0\x9f\x93\x8a Taiwan", "\xf0\x9f\x87\xba\xf0\x9f\x87\xb8 US"])',
    b'st.tabs(["\xf0\x9f\x93\x8a \xe5\x8f\xb0\xe8\x82\xa1", "\xf0\x9f\x87\xba\xf0\x9f\x87\xb8 \xe7\xbe\x8e\xe8\x82\xa1"])'
)

# 3. m[0].metric("TWII", -> 加權指數
d = d.replace(b'm[0].metric("TWII",', b'm[0].metric("\xe5\x8a\xa0\xe6\xac\x8a\xe6\x8c\x87\xe6\x95\xb8",')

# 4. TWII RSI -> 加權指數 RSI
d = d.replace(b'm[1].metric("TWII RSI",', b'm[1].metric("\xe5\x8a\xa0\xe6\xac\x8a\xe6\x8c\x87\xe6\x95\xb8 RSI",')

# 5. TW狀態 -> 台股狀態
d = d.replace(b'm[2].metric("\xe5\x8f\xb0\xe7\x8a\xb6\xe6\x85\x8b",', b'm[2].metric("\xe5\x8f\xb0\xe8\x82\xa1\xe7\x8a\xb6\xe6\x85\x8b",')

# 6. SPY RSI -> 標普500 RSI
d = d.replace(b'm[4].metric("SPY RSI",', b'm[4].metric("\xe6\xa8\x99\xe6\x99\xae500 RSI",')

# 7. US狀態 -> 美股狀態
d = d.replace(b'm[5].metric("\xe7\xbe\x8e\xe7\x8a\xb6\xe6\x85\x8b",', b'm[5].metric("\xe7\xbe\x8e\xe8\x82\xa1\xe7\x8a\xb6\xe6\x85\x8b",')

# 8. Filters -> 🔍 篩選器
d = d.replace(b'st.header("Filters")', b'st.header("\xf0\x9f\x94\x8d \xe7\xaf\x87\xe9\x81\xb8\xe5\x99\xa8")')

# 9. "Category" -> "類別"
d = d.replace(b'selectbox("Category"', b'selectbox("\xe9\xa1\x9e\xe5\x88\xa5"')

# 10. Score Min -> 最低評分
d = d.replace(b'slider("Score Min"', b'slider("\xe6\x9c\x80\xe4\xbd\x8e\xe8\xa9\x95\xe5\x88\x86"')

# 11. RSI Max -> RSI 上限
d = d.replace(b'slider("RSI Max"', b'slider("RSI \xe4\xb8\x8a\xe9\x99\x90"')

# 12. {len(codes)} stocks -> 檔股票
d = d.replace(b'f"{len(codes)} stocks"', b'f"{len(codes)} \xe6\xaa\x94\xe8\x82\xa1\xe7\x9b\xae"')

# 13. button("Analyze" -> 🔍 開始分析
d = d.replace(b'button("Analyze", type="primary", use_container_width=True, key="btn_tw_analyze")', b'button("\xf0\x9f\x94\x8d \xe9\x96\x8b\xe5\xa7\x9b\xe5\x88\x86\xe6\x9e\x90", type="primary", use_container_width=True, key="btn_tw_analyze")')

# 14. Done X stocks in Ys -> 完成 X 檔股票，耗時 Y秒
d = d.replace(b'st.info(f"Done {len(results)} stocks in {elapsed:.1f}s")', b'st.info(f"\xe5\xae\x8c\xe6\x88\x90 {len(results)} \xe6\xaa\x94\xe8\x82\xa1\xe7\x9b\xae\uff0c\xe8\x80\x97\xe6\x99\x82 {elapsed:.1f}\xe7\xa7\x92")')

# 15. X stocks | Y after filter -> 共 X 檔 | 篩選後 Y 檔
d = d.replace(b'st.success(f"{len(results)} stocks | {len(filtered)} after filter")', b'st.success(f"\xe5\x85\xb1 {len(results)} \xe6\xaa\x94 | \xe7\xaf\x87\xe9\x81\xb8\xe5\xbe\x8c {len(filtered)} \xe6\xaa\x94")')

f = open(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\streamlit_tw_stock.py', 'wb')
f.write(d)
f.close()
print('done')
