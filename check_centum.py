# -*- coding: utf-8 -*-
import sqlite3, sys, re
sys.stdout.reconfigure(encoding='utf-8')
db = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\shinsegae_centum.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

# Remove junk brands (Chinese chars, too short, obvious noise)
junk_patterns = ['在会上', '几家', '女人', '마街上', 'システム', '게스', '的系统', '会上', '마무',
                 '리캘', '논논', '在', '르', '루이', '마', '트윈', '가gear', '리바', '가', '리']

for junk in junk_patterns:
    cur.execute('DELETE FROM brands WHERE brand_name LIKE ?', (f'%{junk}%',))

# Fix garbled names
fixes = {
    '신세계 갤�러리': '신세계 갤러리',
    '보calia': '보테가',
    'CNC': 'CGV',
    '에스트': '에스티로더',
    '에센?': '에센',
    '스웨디시': '스위스 퍼펙션',
    '르라보': '르라보',
}
for old, new in fixes.items():
    cur.execute('UPDATE brands SET brand_name=? WHERE brand_name=?', (new, old))

conn.commit()

# Print final stats
print('=== FINAL SHINSEGAE CENTUM CITY DB ===\n')
print('FLOORS:')
cur.execute('SELECT floor, name_ko, description FROM floors ORDER BY floor')
for r in cur.fetchall():
    print(f'  [{r[0]}] {r[1]}')
    print(f'       {r[2]}')

print('\nBRANDS BY FLOOR:')
cur.execute('SELECT floor, COUNT(*) FROM brands GROUP BY floor ORDER BY floor')
for r in cur.fetchall():
    print(f'  [{r[0]}] {r[1]} brands')

print(f'\nTotal: {cur.execute("SELECT COUNT(*) FROM brands").fetchone()[0]} brands')
print(f'Floors: {cur.execute("SELECT COUNT(*) FROM floors").fetchone()[0]}')

print('\nTOP BRANDS BY FLOOR:')
for fl in ['1F', '2F', '3F', '4F', '5F', 'B1']:
    print(f'\n[{fl}]:')
    cur.execute('SELECT brand_name FROM brands WHERE floor=? ORDER BY brand_name LIMIT 15', (fl,))
    for r in cur.fetchall():
        print(f'  {r[0]}')
    if cur.execute('SELECT COUNT(*) FROM brands WHERE floor=?', (fl,)).fetchone()[0] > 15:
        print(f'  ... and more')

conn.close()