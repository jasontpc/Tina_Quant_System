# -*- coding: utf-8 -*-
"""Rebuild floors table with official English names"""
import sqlite3, sys, os, time
sys.stdout.reconfigure(encoding='utf-8')

DB = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\shinsegae_centum.db'

conn = sqlite3.connect(DB)
cur = conn.cursor()

# Check if floors table exists
try:
    cur.execute('SELECT COUNT(*) FROM floors')
    count = cur.fetchone()[0]
    print(f'Floors table exists with {count} rows')
except:
    print('Creating floors table...')
    cur.execute('''CREATE TABLE floors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        floor TEXT, name_ko TEXT, name_en TEXT,
        description TEXT, scraped_at TEXT
    )''')
    conn.commit()

# Official floor data from en.shinsegae.cn
FLOORS = [
    {'floor': 'B2', 'name_ko': '地下二樓', 'name_en': 'B2', 'description': 'Hyper Ground / Parking'},
    {'floor': 'B1', 'name_ko': '地下一樓', 'name_en': 'B1', 'description': 'Fashion Acc / Food Market / Handbags / Event Hall'},
    {'floor': '1F', 'name_ko': '一樓', 'name_en': '1F', 'description': 'Foreign Famous Brand / Cosmetics / Spa Land'},
    {'floor': '2F', 'name_ko': '二樓', 'name_en': '2F', 'description': "Foreign Famous Brand / Watches / Women's Boutique"},
    {'floor': '3F', 'name_ko': '三樓', 'name_en': '3F', 'description': 'Contemporary / Lingerie / Shoe'},
    {'floor': '4F', 'name_ko': '四樓', 'name_en': '4F', 'description': 'New Contemporary / Lingerie / Ice Rink'},
    {'floor': '5F', 'name_ko': '五樓', 'name_en': '5F', 'description': "Men's / Cine de Chef"},
    {'floor': '6F', 'name_ko': '六樓', 'name_en': '6F', 'description': "Golf / Kid's Wear / Shinsegae Gallery & Academy"},
    {'floor': '7F', 'name_ko': '七樓', 'name_en': '7F', 'description': 'Home Appliances (Home Fashion & Electronics) / CGV'},
    {'floor': '8F', 'name_ko': '八樓', 'name_en': '8F', 'description': 'Lifestyle: Furniture & Interior'},
    {'floor': '9F', 'name_ko': '九樓', 'name_en': '9F', 'description': 'Restaurant / SHINSEGAE CULTURE HALL / ZOORAJI / CS'},
    {'floor': '10F', 'name_ko': '十樓', 'name_en': '10F', 'description': 'Trinity Sports Club & Spa'},
    {'floor': '11F', 'name_ko': '十一樓', 'name_en': '11F', 'description': 'Golf Range'},
]

now = time.strftime('%Y-%m-%d %H:%M')

# Clear and rebuild
cur.execute('DELETE FROM floors')
for f in FLOORS:
    cur.execute('INSERT INTO floors (floor, name_ko, name_en, description, scraped_at) VALUES (?, ?, ?, ?, ?)',
        (f['floor'], f['name_ko'], f['name_en'], f['description'], now))

conn.commit()

print('\n=== FLOORS TABLE ===')
cur.execute('SELECT floor, name_en, name_ko, description FROM floors ORDER BY floor')
for r in cur.fetchall():
    print(f'  [{r[0]}] {r[1]} | {r[2]} | {r[3]}')

print(f'\nTotal: {cur.execute("SELECT COUNT(*) FROM floors").fetchone()[0]} floors')
print(f'Brands: {cur.execute("SELECT COUNT(*) FROM brands").fetchone()[0]} brands')

conn.close()
print('\nDone!')