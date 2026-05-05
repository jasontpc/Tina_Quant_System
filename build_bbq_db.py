# -*- coding: utf-8 -*-
"""Build Haeundae BBQ restaurant database"""
import sys, sqlite3, json, re
sys.stdout.reconfigure(encoding='utf-8')

DB = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\haeundae_bbq.db'
JSON_FILE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\haeundae_bbq.json'

def build_bbq_db():
    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    stores = data.get('stores', [])
    
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    cur.execute('''CREATE TABLE IF NOT EXISTS restaurants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, name_ko TEXT, address TEXT,
        phone TEXT, category TEXT,
        area TEXT, scraped_at TEXT
    )''')
    
    cur.execute('DELETE FROM restaurants')
    
    # Filter and clean stores
    for s in stores:
        name = s.get('name', '')
        addr = s.get('address', '')
        phone = s.get('phone', '')
        
        # Clean name (remove category suffix)
        name_clean = re.sub(r'^(.+?)(육류|고기요리|한식|일식|중식|소고기|돼지|갈비|구이)$', r'\1', name).strip()
        name_ko = name_clean
        
        # Category
        if '돼지' in name or '갈비' in name:
            cat = '돼지갈비'
        elif '소고기' in name or '암소' in name:
            cat = '소고기'
        elif '양고기' in name or '羊肉' in name:
            cat = '羊肉'
        elif '삼겹' in name:
            cat = '삼겹살'
        else:
            cat = '고기집'
        
        # Area
        area = '해운대구'
        if '좌동' in addr:
            area = '해운대구 좌동'
        if '우동' in addr or '센텀' in addr:
            area = '해운대구 우동/센텀'
        if '장산' in addr:
            area = '해운대구 장산'
        
        if name_clean and len(name_clean) > 2:
            cur.execute('INSERT INTO restaurants (name, name_ko, address, phone, category, area) VALUES (?, ?, ?, ?, ?, ?)',
                (name_clean, name_ko, addr, phone, cat, area))
    
    conn.commit()
    
    # Show results
    print('=== 尾浦/海雲台 燒肉店資料庫 ===\n')
    cur.execute('SELECT category, COUNT(*) FROM restaurants GROUP BY category')
    for r in cur.fetchall():
        print(f'  {r[0]}: {r[1]}間')
    
    cur.execute('SELECT id, name, address, phone, category FROM restaurants ORDER BY id')
    rows = cur.fetchall()
    
    print(f'\n總共: {len(rows)}間\n')
    print(f'{"#":<3} {"店名":<30} {"類別":<10} {"地址"}')
    print('-' * 80)
    for r in rows[:20]:
        print(f'{r[0]:<3} {r[1]:<30} {r[4]:<10} {r[2][:40]}')
    
    conn.close()
    
    # Save as JSON for easy reading
    output = []
    conn2 = sqlite3.connect(DB)
    cur2 = conn2.cursor()
    cur2.execute('SELECT name, name_ko, address, phone, category, area FROM restaurants ORDER BY id')
    for r in cur2.fetchall():
        output.append({
            'name': r[0],
            'name_ko': r[1],
            'address': r[2],
            'phone': r[3],
            'category': r[4],
            'area': r[5],
        })
    conn2.close()
    
    with open(JSON_FILE.replace('.json', '_clean.json'), 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f'\n✅ 資料庫已建立: {DB}')

if __name__ == '__main__':
    build_bbq_db()