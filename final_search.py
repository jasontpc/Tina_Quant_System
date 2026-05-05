# -*- coding: utf-8 -*-
"""Final search optimization"""
import sqlite3, sys, os
sys.stdout.reconfigure(encoding='utf-8')

DB = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\shinsegae_centum.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

def search_all(q, limit=30):
    like = f'%{q}%'
    cur.execute('''SELECT brand_name, floor, category, subcategory FROM brands 
        WHERE brand_name LIKE ? OR brand_name_ko LIKE ? OR brand_name_en LIKE ?
             OR category LIKE ? OR subcategory LIKE ?
        ORDER BY brand_name LIMIT ?''',
        (like, like, like, like, like, limit))
    return cur.fetchall()

# Quick stats
print('=== Final DB Stats ===')
cur.execute('SELECT COUNT(*) FROM brands')
print(f'Total brands: {cur.fetchone()[0]}')

cur.execute('SELECT category, COUNT(*) FROM brands GROUP BY category ORDER BY COUNT(*) DESC')
print('\nBy category:')
for r in cur.fetchall():
    print(f'  {r[0]}: {r[1]}')

print('\nBy floor:')
cur.execute('SELECT floor, COUNT(*) FROM brands GROUP BY floor ORDER BY floor')
for r in cur.fetchall():
    print(f'  {r[0]}: {r[1]}')

# Test searches
print('\n=== Search Tests ===')
tests = ['珠寶', '腕錶', '化妝品', '護膚', '精品', '男裝', '西裝', '運動鞋', '戶外', '童裝', '高爾夫', '家具', '餐廳']
for q in tests:
    rows = search_all(q)
    print(f'\n"{q}": {len(rows)} results')
    for r in rows[:8]:
        print(f'  [{r[0]}] {r[2]}/{r[3]}')
    if len(rows) > 8:
        print(f'  ... and {len(rows)-8} more')

# Show complete floor-by-floor
print('\n\n=== Complete Brand List ===')
floors_order = ['B2', 'B1', '1F', '2F', '3F', '4F', '5F', '6F', '7F', '8F', '9F', '10F', '11F']
for fl in floors_order:
    cur.execute('SELECT brand_name, category, subcategory FROM brands WHERE floor=? ORDER BY brand_name', (fl,))
    rows = cur.fetchall()
    if rows:
        print(f'\n[{fl}] ({len(rows)} brands):')
        for r in rows:
            print(f'  {r[0]} ({r[1]}/{r[2]})')

conn.close()