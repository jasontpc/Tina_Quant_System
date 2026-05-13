d = open('streamlit_tw_stock.py', encoding='utf-8').read()
lines = d.split('\n')

# Find TW batch results display - look for where rows are built for the results table
# Search for 'rows.append' or 'st.dataframe' after the analyze section
for i, line in enumerate(lines):
    if 'rows.append' in line or 'st.dataframe' in line.lower():
        if i > 1230 and i < 1300:
            print(f'Line {i+1}: {line[:120]}')
            # Show surrounding context
            for j in range(max(0,i-5), min(len(lines), i+10)):
                print(f'  {j+1}: {lines[j][:100]}')
            print()

# Also find where Foreign/Trust is added to rows in batch display
for i, line in enumerate(lines):
    if ('foreign' in line.lower() and 'append' in line) or ('trust' in line.lower() and 'append' in line):
        if i > 1240 and i < 1280:
            print(f'Row build line {i+1}: {line[:120]}')