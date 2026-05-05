# Check Vogel build script
with open(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\vogel\build_vogel_db.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Count columns in CREATE TABLE
import re
create_match = re.search(r'CREATE TABLE IF NOT EXISTS daily \((.*?)\)', content, re.DOTALL)
if create_match:
    cols = [c.strip() for c in create_match.group(1).split(',')]
    print(f'CREATE TABLE columns: {len(cols)}')
    for i, c in enumerate(cols, 1):
        print(f'  {i}. {c}')

# Count placeholders in VALUES
vals_match = re.search(r'VALUES \((.*?)\)\n', content, re.DOTALL)
if vals_match:
    placeholders = vals_match.group(1).count('?')
    print(f'\nVALUES ? count: {placeholders}')