# -*- coding: utf-8 -*-
"""Fix remaining Korean items - v2"""
import sqlite3, sys, re
sys.stdout.reconfigure(encoding='utf-8')

db = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\shinsegae_centum.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

# Fix remaining Korean items
fixes = {
    '레노': 'Reno',
    'antoine': 'Antoine',
    '신세계 갤러리': '新世界 Gallery',
    '골프': '高爾夫',
    '아동': '兒童',
}

for old, new in fixes.items():
    cur.execute('UPDATE brands SET brand_name=? WHERE brand_name=? OR brand_name_ko=?', (new, old, old))
    cur.execute('UPDATE floors SET description=? WHERE description LIKE ?', (new, f'%{old}%'))
    if cur.rowcount > 0:
        print(f'Fixed: {old} → {new} ({cur.rowcount})')

# Fix 6F description
cur.execute("UPDATE floors SET description='高爾夫/兒童/新世界 Gallery, 新世界 Academy, KidZania' WHERE floor='6F'")

conn.commit()

# Find remaining Korean by checking unicode range
def has_korean(text):
    if not text: return False
    return bool(re.search(r'[가-힣]', text))

print('\n=== CHECK REMAINING KOREAN IN BRANDS ===')
cur.execute('SELECT brand_name, brand_name_ko FROM brands')
korean_items = [(r[0], r[1]) for r in cur.fetchall() if has_korean(r[0]) or has_korean(r[1])]
if korean_items:
    for name, name_ko in korean_items:
        print(f'  KOREAN: {name} / {name_ko}')
        # Try to fix
        cur.execute("DELETE FROM brands WHERE brand_name=? OR brand_name_ko=?", (name, name))
else:
    print('  None! All translated.')

print('\n=== FLOORS ===')
cur.execute('SELECT floor, name_ko, description FROM floors ORDER BY floor')
for r in cur.fetchall():
    print(f'[{r[0]}] {r[1]} | {r[2]}')

print(f'\nTotal brands: {cur.execute("SELECT COUNT(*) FROM brands").fetchone()[0]}')

# Print all brands by floor
print('\n=== ALL BRANDS BY FLOOR ===')
for fl in ['B2', 'B1', '1F', '2F', '3F', '4F', '5F', '6F', '7F', '8F', '9F', '10F', '11F']:
    cur.execute('SELECT brand_name FROM brands WHERE floor=? ORDER BY brand_name', (fl,))
    rows = cur.fetchall()
    if rows:
        print(f'\n[{fl}] ({len(rows)} brands):')
        for r in rows:
            print(f'  {r[0]}')

conn.close()