# -*- coding: utf-8 -*-
"""Final cleanup and translation"""
import sqlite3, sys, re
sys.stdout.reconfigure(encoding='utf-8')

db = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\shinsegae_centum.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

def has_korean(text):
    if not text: return False
    return bool(re.search(r'[가-힣]', text))

# Fix remaining Korean items
fixes = {
    '보tega': 'Bottega Veneta',
    '구찌': '古馳',
    '톰브лей튼': 'Tom Blighton',
    '아이린': 'Airin',
    '레ノ': 'Reno',
    '나이키': 'Nike',
    '아디다스': 'Adidas',
    '신세계아카데미': '新世界 Academy',
    '쿠쿠': 'Cuckoo',
    '식기': '餐具',
    '침구': '寢具',
    '플레이인더박스': 'Playender Box',
    '씨jg': 'CGV',
    '커피빈': 'Coffee Bean',
    '고객서비스센터': '客戶服務中心',
    '스파': 'Spa',
    '퓨어': 'Pure',
    '골프레인지': 'Golf Range',
    '연습장': '練習場',
    '新世界 Academy': '新世界 Academy',
    '三星電子': '三星電子',
    'LG전자': 'LG電子',
    'LG電子': 'LG電子',
}

for old, new in fixes.items():
    cur.execute('UPDATE brands SET brand_name=?, brand_name_ko=? WHERE brand_name=? OR brand_name_ko=?', (new, new, old, old))
    if cur.rowcount > 0:
        print(f'Fixed: {old} → {new}')

# Remove duplicates (keep first occurrence)
print('\nRemoving duplicates...')
cur.execute('SELECT id, floor, brand_name FROM brands ORDER BY rowid')
seen = set()
dups = []
for r in cur.fetchall():
    key = (r[1], r[2])
    if key in seen:
        dups.append(r[0])
    else:
        seen.add(key)

for did in dups:
    cur.execute('DELETE FROM brands WHERE id=?', (did,))
    print(f'  Removed duplicate id={did}')
print(f'Total removed: {len(dups)}')

# Delete obvious non-brand entries
non_brands = ['、顧客服務中心', '、Spa', 'Pure', '、三星電子', '、LG電子', '、CGV', '、客戶服務中心',
              '、餐具', '、寢具', '、Cuckoo', '、Playender Box', '、Coffee Bean', '、客戶服務中心',
              'LG電子', '三星電子']
for nb in non_brands:
    cur.execute('DELETE FROM brands WHERE brand_name=? OR brand_name_ko=?', (nb, nb))
    if cur.rowcount > 0:
        print(f'Removed non-brand: {nb}')

conn.commit()

# Show remaining Korean
print('\n=== REMAINING KOREAN ===')
cur.execute('SELECT brand_name, brand_name_ko FROM brands')
korean = [(r[0], r[1]) for r in cur.fetchall() if has_korean(r[0]) or has_korean(r[1])]
for n, k in korean:
    print(f'  {n} / {k}')
print(f'Remaining: {len(korean)}')

print('\n=== FLOORS ===')
cur.execute('SELECT floor, name_ko, description FROM floors ORDER BY floor')
for r in cur.fetchall():
    print(f'[{r[0]}] {r[1]} | {r[2]}')

print(f'\nTotal brands: {cur.execute("SELECT COUNT(*) FROM brands").fetchone()[0]}')

print('\n=== ALL BRANDS ===')
for fl in ['B2', 'B1', '1F', '2F', '3F', '4F', '5F', '6F', '7F', '8F', '9F', '10F', '11F']:
    cur.execute('SELECT brand_name FROM brands WHERE floor=? ORDER BY brand_name', (fl,))
    rows = cur.fetchall()
    if rows:
        print(f'\n[{fl}] ({len(rows)}):')
        for r in rows:
            print(f'  {r[0]}')

conn.close()