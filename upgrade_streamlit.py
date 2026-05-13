"""
streamlit_tw_stock.py — UI Upgrade Script
Targets ad283b9 baseline (syntax-clean) and applies:
1. Page title v3.1 + CSS
2. st.toast notifications
3. st.dataframe column_config (with correct indentation!)
4. st.title v3.1
"""

import re

path = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\streamlit_tw_stock.py"
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
i = 0
while i < len(lines):
    l = lines[i]
    
    # 1. Replace page title line (around line 1411)
    if 'st.set_page_config(page_title="Tina Scanner v3.0", page_icon="[UP]"' in l:
        # Add CSS before this line, then replace the title
        css = """st.markdown("\"\"\"
<style>
.metric-card { background-color:white; padding:20px; border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,0.08); border-left:5px solid #1E88E5; }
[data-testid="stMainBlockContainer"] { padding-top:1rem; }
</style>
\"\"\", unsafe_allow_html=True)

"""
        new_lines.append(css)
        new_lines.append(l.replace('Tina Scanner v3.0', 'Tina Scanner v3.1').replace('"[UP]"', '"📈"'))
        i += 1
        continue

    # 2. st.title update (around line after set_page_config)
    if l.strip().startswith("st.title(\"[UP] Tina Scanner v3.0"):
        new_lines.append(l.replace('v3.0', 'v3.1'))
        i += 1
        continue

    # 3. Add TW toast after st.success (in analyze_tw block, ~line 1655)
    if 'st.success(f"{len(results)} stocks | {len(filtered)} after filter")' in l and 'icon' not in l:
        new_lines.append(l)
        # Add toast with same indent
        indent = len(l) - len(l.lstrip())
        new_lines.append(' ' * indent + 'st.toast(f"掃描完成！ {len(results)} 檔 ({len(filtered)} 通過篩選)", icon="✅")\n')
        i += 1
        continue

    # 4. Add US toast (~line 2326)
    if 'st.success(f"{len(results)} stocks | {len(filtered)} after filter")' in l and 'icon' not in l and i > 2000:
        new_lines.append(l)
        indent = len(l) - len(l.lstrip())
        new_lines.append(' ' * indent + 'st.toast(f"掃描完成！ {len(results)} 檔 ({len(filtered)} 通過篩選)", icon="✅")\n')
        i += 1
        continue

    # 5. Replace old st.dataframe calls with column_config version
    # Find the pattern: 'st.dataframe(df, width='stretch', height=600, hide_index=True)'
    if "st.dataframe(df, width='stretch', height=600, hide_index=True)" in l:
        indent = len(l) - len(l.lstrip())
        indent4 = ' ' * indent
        indent8 = ' ' * (indent + 4)
        indent12 = ' ' * (indent + 8)
        indent16 = ' ' * (indent + 12)
        new_cfg = f"""{indent4}st.dataframe(
{indent8}df,
{indent8}column_config={{
{indent12}"Score": st.column_config.NumberColumn("評分", format="%.0f", min_value=0, max_value=1000),
{indent12}"Chg%": st.column_config.TextColumn("漲跌%"),
{indent12}"RSI":  st.column_config.TextColumn("RSI"),
{indent12}"Tier": st.column_config.TextColumn("評級"),
{indent12}"Code": st.column_config.TextColumn("代碼"),
{indent12}"Price": st.column_config.NumberColumn("現價", format="%.2f"),
{indent12}"MA":   st.column_config.TextColumn("MA20>60"),
{indent12}"F":    st.column_config.TextColumn("外資"),
{indent12}"T":    st.column_config.TextColumn("投信"),
{indent12}"Vol":  st.column_config.TextColumn("量比"),
{indent8}}},
{indent8}use_container_width=True,
{indent8}hide_index=True,
{indent4})
"""
        new_lines.append(new_cfg)
        i += 1
        continue

    # 6. Telegram toast notifications
    if 'st.success(f"Sent {sc} stocks ({len(chunks)} msgs)")' in l and 'icon' not in l:
        new_lines.append(l)
        indent = len(l) - len(l.lstrip())
        new_lines.append(' ' * indent + 'st.toast(f"已發送 {sc} 檔分析到 Telegram", icon="📤")\n')
        i += 1
        continue
    if 'st.success(f"Sent {len(grade_filtered)} stocks ({len(chunks)} msgs)")' in l and 'icon' not in l:
        new_lines.append(l)
        indent = len(l) - len(l.lstrip())
        new_lines.append(' ' * indent + 'st.toast(f"已發送 {len(grade_filtered)} 檔到 Telegram", icon="📤")\n')
        i += 1
        continue
    if l.strip() == 'st.success("Telegram sent!")' and 'icon' not in l:
        new_lines.append(l)
        indent = len(l) - len(l.lstrip())
        new_lines.append(' ' * indent + 'st.toast("已發送單一股票分析到 Telegram", icon="📤")\n')
        i += 1
        continue

    new_lines.append(l)
    i += 1

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

# Verify
import ast
with open(path, encoding='utf-8') as f:
    src = f.read()
try:
    ast.parse(src)
    print("Syntax OK")
except SyntaxError as e:
    print(f"SyntaxError: line {e.lineno}: {e.msg}")
    lines2 = src.split('\n')
    for j in range(max(0, e.lineno-3), min(len(lines2), e.lineno+2)):
        print(f"{j+1}: {lines2[j]}")
