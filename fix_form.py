"""Fix grade filter forms for both TW and US tabs"""
with open('streamlit_tw_stock.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
i = 0
fixed = 0

while i < len(lines):
    stripped = lines[i].rstrip()
    
    # Detect the TW grade filter start: st.markdown("**Grade**") followed by g1,g2,g3,g4,gall columns
    if stripped == '        st.markdown("**Grade**")' and i+1 < len(lines) and 'g1, g2, g3, g4, gall = st.columns' in lines[i+1].rstrip():
        # This is TW tab grade filter (inside col_side of tw_tab)
        # Check we are in tw_tab context by looking back
        context = ''.join(lines[max(0,i-20):i])
        if 'with col_side:' in context and 'tw_tab' in context:
            print(f"Found TW grade filter at line {i+1}")
            new_lines.append('            with st.form(key="grade_filter_tw"):\n')
            i += 1
            # Add all lines inside the form until us_grade listcomp
            while i < len(lines):
                stripped_inner = lines[i].rstrip()
                if stripped_inner == '        tw_grade = [g for g, on in zip(["A","B","C","D"], [g_a, g_b, g_c, g_d]) if on]':
                    # Close the form after this line
                    new_lines.append(lines[i])
                    new_lines.append('\n')
                    i += 1
                    fixed += 1
                    break
                elif 'gall.button' in stripped_inner and 'form_submit_button' not in stripped_inner:
                    # Replace with form_submit_button
                    new_lines.append(lines[i].replace('gall.button', 'gall.form_submit_button'))
                    i += 1
                else:
                    new_lines.append(lines[i])
                    i += 1
        else:
            new_lines.append(lines[i])
            i += 1
    
    # Detect the US grade filter start: st.markdown("**Grade**") followed by u1,u2,u3,u4,uall columns
    elif stripped == '        st.markdown("**Grade**")' and i+1 < len(lines) and 'u1, u2, u3, u4, uall = st.columns' in lines[i+1].rstrip():
        # This is US tab grade filter (inside col_side of us_tab)
        context = ''.join(lines[max(0,i-20):i])
        if 'with col_side:' in context and 'us_tab' in context:
            print(f"Found US grade filter at line {i+1}")
            new_lines.append('            with st.form(key="grade_filter_us"):\n')
            i += 1
            while i < len(lines):
                stripped_inner = lines[i].rstrip()
                if stripped_inner == '        us_grade = [g for g, on in zip(["A","B","C","D"], [u_a, u_b, u_c, u_d]) if on]':
                    new_lines.append(lines[i])
                    new_lines.append('\n')
                    i += 1
                    fixed += 1
                    break
                elif 'uall.button' in stripped_inner and 'form_submit_button' not in stripped_inner:
                    new_lines.append(lines[i].replace('uall.button', 'uall.form_submit_button'))
                    i += 1
                else:
                    new_lines.append(lines[i])
                    i += 1
        else:
            new_lines.append(lines[i])
            i += 1
    else:
        new_lines.append(lines[i])
        i += 1

print(f"Fixed {fixed} grade filter sections")

with open('streamlit_tw_stock.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

import subprocess
r = subprocess.run(['python', '-m', 'py_compile', 'streamlit_tw_stock.py'],
                   capture_output=True, text=True,
                   cwd='C:\\Users\\USER\\.openclaw\\workspace\\Tina_Quant_System')
if r.returncode == 0:
    print("Syntax OK!")
else:
    print(f"Syntax Error: {r.stderr[:300]}")
