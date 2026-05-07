"""Fix the form body indentation - fix_form_us.py ran but indentation was wrong"""
with open('streamlit_tw_stock.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Current state (wrong):
# 1604:         with st.form(key="grade_filter_us"):  ← indent 8, body is ALSO 8 (WRONG)
# 1605:         st.markdown("**Grade**")              ← should be 12
# 
# Fix: Increase indent of body lines from 8 to 12 (inside the with block)
# Lines 1605-1616 are inside the form and need indent 12

for i in range(1604, 1617):
    stripped = lines[i].rstrip()
    if stripped and not stripped.startswith('#'):
        current_indent = len(lines[i]) - len(lines[i].lstrip())
        if current_indent == 8:
            lines[i] = '            ' + lines[i].lstrip()  # 12 spaces

with open('streamlit_tw_stock.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

import subprocess
r = subprocess.run(['python', '-m', 'py_compile', 'streamlit_tw_stock.py'],
                   capture_output=True, text=True,
                   cwd='C:\\Users\\USER\\.openclaw\\workspace\\Tina_Quant_System')
if r.returncode == 0:
    print("Syntax OK!")
else:
    print(f"Syntax Error: {r.stderr[:200]}")
