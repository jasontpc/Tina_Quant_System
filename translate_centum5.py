# -*- coding: utf-8 -*-
"""Final cleanup - remove generic category items"""
import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')

db = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\shinsegae_centum.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

# Remove generic category items (not brand names)
non_brands = ['寢具', '餐具', 'Playender Box', 'Cuckoo', 'Coffee Bean']
for nb in non_brands:
    cur.execute('DELETE FROM brands WHERE brand_name=?', (nb,))
    if cur.rowcount > 0:
        print(f'Removed: {nb}')

# 9F - only keep real stores/services, remove generic restaurant types
# Keep: KidZania, golf range, Spa - remove generic categories

# Also delete 9F entries that are just category names
cur.execute("DELETE FROM brands WHERE floor='9F' AND brand_name NOT IN ('KidZania')")

# Delete 10F (Spa category, not brand) and keep 11F
cur.execute("DELETE FROM brands WHERE floor='10F'")

conn.commit()

# Final check
print('\n=== FINAL DATABASE ===')
print(f'Floors: {cur.execute("SELECT COUNT(*) FROM floors").fetchone()[0]}')
print(f'Brands: {cur.execute("SELECT COUNT(*) FROM brands").fetchone()[0]}')

print('\nFLOORS:')
cur.execute('SELECT floor, name_ko, description FROM floors ORDER BY floor')
for r in cur.fetchall():
    print(f'  [{r[0]}] {r[1]}')
    print(f'       {r[2]}')

print('\nBRANDS BY FLOOR:')
for fl in ['B2', 'B1', '1F', '2F', '3F', '4F', '5F', '6F', '7F', '8F', '9F', '10F', '11F']:
    cur.execute('SELECT brand_name FROM brands WHERE floor=? ORDER BY brand_name', (fl,))
    rows = cur.fetchall()
    if rows:
        print(f'  [{fl}] ({len(rows)}):')
        for r in rows:
            print(f'    {r[0]}')
    else:
        print(f'  [{fl}]: (none - category floor)')

conn.close()
print('\n=== DONE ===')