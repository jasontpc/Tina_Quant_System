# -*- coding: utf-8 -*-
"""Update Shinsegae Centum City DB with official floor guide"""
import sqlite3, sys, os, time
sys.stdout.reconfigure(encoding='utf-8')

DB = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\shinsegae_centum.db'

# Official English floor names
FLOORS_EN = {
    '11F': {'name_en': '11F', 'name_ko': '11층', 'description': 'Golf Range'},
    '10F': {'name_en': '10F', 'name_ko': '10층', 'description': 'Trinity Sports Club & Spa'},
    '9F': {'name_en': '9F', 'name_ko': '9층', 'description': 'Restaurant / SHINSEGAE CULTURE HALL / ZOORAJI / CS'},
    '8F': {'name_en': '8F', 'name_ko': '8층', 'description': 'Lifestyle: Furniture & Interior'},
    '7F': {'name_en': '7F', 'name_ko': '7층', 'description': 'Home Appliances (Home Fashion & Electronics) / CGV'},
    '6F': {'name_en': '6F', 'name_ko': '6층', 'description': "Golf / Kid's Wear / Shinsegae Gallery & Academy"},
    '5F': {'name_en': '5F', 'name_ko': '5층', 'description': "Men's / Cine de Chef"},
    '4F': {'name_en': '4F', 'name_ko': '4층', 'description': 'New Contemporary / Lingerie / Ice Rink'},
    '3F': {'name_en': '3F', 'name_ko': '3층', 'description': 'Contemporary / Lingerie / Shoe'},
    '2F': {'name_en': '2F', 'name_ko': '2층', 'description': 'Foreign Famous Brand/ Watches / Women\'s Boutique'},
    '1F': {'name_en': '1F', 'name_ko': '1층', 'description': 'Foreign Famous Brand / Cosmetics / Spa Land'},
    'B1': {'name_en': 'B1', 'name_ko': '지하 1층', 'description': 'Fashion Acc / Food Market / Handbags / Event Hall'},
    'B2': {'name_en': 'B2', 'name_ko': '지하 2층', 'description': 'Hyper Ground / Parking'},
}

conn = sqlite3.connect(DB)
cur = conn.cursor()

# Update floors with official English names and descriptions
for floor_code, info in FLOORS_EN.items():
    cur.execute('''UPDATE floors SET 
        name_en=?, description=? 
        WHERE floor=?''',
        (info['name_en'], info['description'], floor_code))
    if cur.rowcount > 0:
        print(f'Updated: [{floor_code}] {info["name_en"]} - {info["description"]}')

conn.commit()

# Show all floors
print('\n=== OFFICIAL FLOOR GUIDE ===')
cur.execute('SELECT floor, name_en, name_ko, description FROM floors ORDER BY floor')
for r in cur.fetchall():
    print(f'  [{r[0]}] {r[1]} | {r[2]} | {r[3]}')

conn.close()
print('\nDone!')