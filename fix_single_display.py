"""Fix the else: dead code issue in TW and US single stock sections"""
with open('streamlit_tw_stock.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and fix the pattern:
# 1452 8 '        if r:'
# 1454 12 "            st.session_state['single_result'] = r"
# 1455 8 '        else:'
# 1456 12 "            st.warning(...)"
# 1457 12 "            st.stop()"
# 1459 12 "            bd = r.get('score_breakdown', {})"
#  ... all display code at indent 12 inside else (dead code)
#
# Fix:
# 1. Change '        else:' to '            else:' (12 spaces)
# 2. Change '            st.stop()' to '                st.stop()' (16 spaces)
# 3. Dedent bd + display code from indent 12 to indent 8

fixed = 0
for i, line in enumerate(lines):
    if line.rstrip() == '        else:':
        # Check previous non-blank line is '        if r:'
        prev = i - 1
        while prev >= 0 and lines[prev].strip() == '':
            prev -= 1
        if prev >= 0 and lines[prev].rstrip() == '        if r:':
            # Check next line is st.warning
            next_line_idx = i + 1
            while next_line_idx < len(lines) and lines[next_line_idx].strip() == '':
                next_line_idx += 1
            if next_line_idx < len(lines) and 'st.warning' in lines[next_line_idx]:
                # Find the st.stop() line
                stop_idx = next_line_idx + 1
                while stop_idx < len(lines) and lines[stop_idx].strip() == '':
                    stop_idx += 1
                if stop_idx < len(lines) and lines[stop_idx].rstrip() == '            st.stop()':
                    # Find bd line
                    bd_idx = stop_idx + 1
                    while bd_idx < len(lines) and lines[bd_idx].strip() == '':
                        bd_idx += 1
                    if bd_idx < len(lines) and 'bd = r.get' in lines[bd_idx]:
                        # Find end of display section (dedent to <= 8)
                        end_idx = bd_idx
                        while end_idx < len(lines):
                            stripped = lines[end_idx].rstrip()
                            if stripped == '':
                                end_idx += 1
                                continue
                            indent = len(lines[end_idx]) - len(lines[end_idx].lstrip())
                            if indent <= 8:
                                break
                            end_idx += 1

                        print(f"Fixing TW/US single else at line {i+1}")
                        print(f"  else: {i+1}, warning: {next_line_idx+1}, stop: {stop_idx+1}")
                        print(f"  bd: {bd_idx+1}, end: {end_idx+1}")

                        # 1. Fix else indent
                        lines[i] = '            else:\n'

                        # 2. Fix st.stop() indent
                        lines[stop_idx] = '                st.stop()\n'

                        # 3. Dedent bd + display section
                        for k in range(bd_idx, end_idx):
                            if lines[k].strip():
                                lines[k] = '        ' + lines[k].lstrip()

                        fixed += 1

print(f"Fixed {fixed} instances")

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
