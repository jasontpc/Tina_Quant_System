d = open('streamlit_tw_stock.py', encoding='utf-8').read()
lines = d.split('\n')

# Find the TW analyze block and show full structure
for i, line in enumerate(lines):
    if 'if do_single or st.session_state.get' in line and 'tw_analyzed' in line:
        print(f"TW block starts at line {i+1}")
        for j in range(i, min(len(lines), i+15)):
            l = lines[j]
            print(f"  {j+1} ({len(l)-len(l.lstrip())} spaces): {l[:100]}")
        break

print()
for i, line in enumerate(lines):
    if 'if do_us_single or st.session_state.get' in line and 'us_analyzed' in line:
        print(f"US block starts at line {i+1}")
        for j in range(i, min(len(lines), i+15)):
            l = lines[j]
            print(f"  {j+1} ({len(l)-len(l.lstrip())} spaces): {l[:100]}")
        break