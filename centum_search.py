# -*- coding: utf-8 -*-
"""Shinsegae Centum City - Brand Search CLI Tool"""
import sqlite3, sys, os
sys.stdout.reconfigure(encoding='utf-8')

DB = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\shinsegae_centum.db'

def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def search(query=None, floor=None, category=None, subcategory=None, limit=30):
    conn = get_conn()
    cur = conn.cursor()
    
    sql = 'SELECT brand_name, brand_name_ko, brand_name_en, floor, category, subcategory FROM brands WHERE 1=1'
    params = []
    
    if floor:
        sql += ' AND floor=?'
        params.append(floor)
    if category:
        sql += ' AND (category=? OR category LIKE ?)'
        params.extend([category, f'{category}%'])
    if subcategory:
        sql += ' AND subcategory LIKE ?'
        params.append(f'%{subcategory}%')
    if query:
        like = f'%{query}%'
        sql += ' AND (brand_name LIKE ? OR brand_name_ko LIKE ? OR brand_name_en LIKE ? OR category LIKE ? OR subcategory LIKE ?)'
        params.extend([like, like, like, like, like])
    
    sql += ' ORDER BY floor, brand_name LIMIT ?'
    params.append(limit)
    
    cur.execute(sql, params)
    return [dict(r) for r in cur.fetchall()], conn

def main():
    if len(sys.argv) < 2:
        print('Usage: python centum_search.py <query> [--floor FL] [--category CAT]')
        print()
        print('Examples:')
        print('  python centum_search.py 珠寶')
        print('  python centum_search.py Nike --floor 4F')
        print('  python centum_search.py --category 運動')
        print()
        print('Total brands:', get_conn().cursor().execute('SELECT COUNT(*) FROM brands').fetchone()[0])
        get_conn().close()
        return
    
    query = None
    floor = None
    category = None
    
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == '--floor' and i+1 < len(args):
            floor = args[i+1]
            i += 2
        elif arg == '--category' and i+1 < len(args):
            category = args[i+1]
            i += 2
        elif arg == '--floor' and i+1 >= len(args):
            # next arg IS the floor value
            i += 1
        elif arg == '--help' or arg == '-h':
            print('Usage: python centum_search.py [query] [--floor FLOOR] [--category CAT] [--sub SUBCAT]')
            print('Examples:')
            print('  python centum_search.py 珠寶')
            print('  python centum_search.py --floor 2F')
            print('  python centum_search.py --category 運動')
            print('  python centum_search.py 護膚 --floor 1F')
            get_conn().close()
            return
        elif not arg.startswith('--'):
            query = arg
            i += 1
        else:
            i += 1
    
    results, conn = search(query, floor, category)
    
    if not results:
        print(f'No results for: query={query}, floor={floor}, category={category}')
        conn.close()
        return
    
    print(f'\n=== Search: "{query}" | floor={floor} | category={category} ===')
    print(f'Found: {len(results)} results\n')
    
    # Group by floor
    by_floor = {}
    for r in results:
        fl = r['floor']
        if fl not in by_floor:
            by_floor[fl] = []
        by_floor[fl].append(r)
    
    for fl in sorted(by_floor.keys()):
        print(f'[{fl}] ({len(by_floor[fl])}):')
        for r in by_floor[fl]:
            name = r['brand_name']
            ko = r['brand_name_ko']
            en = r['brand_name_en']
            cat = r['category']
            sub = r['subcategory']
            # Show Chinese name prominently
            print(f'  {name}')
            if ko and ko != name:
                print(f'    (Korean: {ko})')
            if en and en != name:
                print(f'    (EN: {en})')
            print(f'    {cat} / {sub}')
    
    conn.close()

if __name__ == '__main__':
    main()