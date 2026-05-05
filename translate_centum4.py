# -*- coding: utf-8 -*-
"""Final brand name fix - clean garbled/unrecognized names"""
import sqlite3, sys, re
sys.stdout.reconfigure(encoding='utf-8')

db = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\shinsegae_centum.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

# Fix garbled / unrecognizable brand names
fixes = {
    'Radaacio': 'Radaci',
    'Mil': 'Mill',
    'Tom Blighton': '上海牌',  # Tom Blighton = 上海牌 (ShangHai watch brand)
    'Louvement': 'Le Movement',
    'Edên Hoe': 'Eden Hoe',
    'DeHells': 'The Helps',
    'Playender Box': 'Playender Box',
    'Cuckoo': 'Cuckoo',
    'Antoine': 'Antoine',
    'Eviuso': 'Evius',
    'Mull': 'Mul',
    'Ppappa': 'Ppappa',
    'Boss': 'BOSS',
}

for old, new in fixes.items():
    cur.execute('UPDATE brands SET brand_name=? WHERE brand_name=?', (new, old))
    if cur.rowcount > 0:
        print(f'Fixed: {old} → {new}')

# Delete restaurant category entries (generic, not specific brands)
generic_restaurants = ['中式料理', '日式料理', '西式料理', '韓式料理', '自助餐', '咖啡廳', '客戶服務中心']
for r in generic_restaurants:
    cur.execute('DELETE FROM brands WHERE brand_name=?', (r,))
    if cur.rowcount > 0:
        print(f'Removed: {r}')

# Re-add Samsung and LG to 7F and 8F (they belong there)
cur.execute('SELECT COUNT(*) FROM brands WHERE brand_name IN ("三星電子", "LG電子")')
if cur.fetchone()[0] == 0:
    cur.execute("INSERT INTO brands (floor, brand_name, brand_name_ko, category, scraped_at) VALUES ('7F', '三星電子', 'Samsung', 'Electronics', '2026-04-28')")
    cur.execute("INSERT INTO brands (floor, brand_name, brand_name_ko, category, scraped_at) VALUES ('7F', 'LG電子', 'LG', 'Electronics', '2026-04-28')")
    cur.execute("INSERT INTO brands (floor, brand_name, brand_name_ko, category, scraped_at) VALUES ('8F', '三星電子', 'Samsung', 'Electronics', '2026-04-28')")
    cur.execute("INSERT INTO brands (floor, brand_name, brand_name_ko, category, scraped_at) VALUES ('8F', 'LG電子', 'LG', 'Electronics', '2026-04-28')")
    print('Re-added Samsung and LG to 7F, 8F')

conn.commit()

# Print final
print('\n=== FINAL SHINSEGAE CENTUM CITY ===\n')
print('FLOORS:')
cur.execute('SELECT floor, name_ko, description FROM floors ORDER BY floor')
for r in cur.fetchall():
    print(f'  [{r[0]}] {r[1]}')
    print(f'       {r[2]}')

print(f'\nTotal brands: {cur.execute("SELECT COUNT(*) FROM brands").fetchone()[0]}')

print('\nALL BRANDS BY FLOOR:')
for fl in ['B2', 'B1', '1F', '2F', '3F', '4F', '5F', '6F', '7F', '8F', '9F', '10F', '11F']:
    cur.execute('SELECT brand_name FROM brands WHERE floor=? ORDER BY brand_name', (fl,))
    rows = cur.fetchall()
    if rows:
        print(f'\n  [{fl}] ({len(rows)}):')
        for r in rows:
            print(f'    {r[0]}')

conn.close()