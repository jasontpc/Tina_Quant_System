# -*- coding: utf-8 -*-
"""Naver Place - Olive Young Store DB (Clean)"""
import sys, os, time, re, sqlite3
sys.path.insert(0, os.path.dirname(__file__))
sys.stdout.reconfigure(encoding='utf-8')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'

def get_driver():
    opts = Options()
    opts.add_argument('--headless=new')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--window-size=390,844')
    opts.add_argument('--user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1')
    prefs = {'profile.default_content_setting_values': {'images': 2, 'css': 2}}
    opts.add_experimental_option('prefs', prefs)
    return webdriver.Chrome(options=opts)

def init_db():
    db = os.path.join(DATA_DIR, 'naver_places.db')
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute('DROP TABLE IF EXISTS places')
    cur.execute('''CREATE TABLE places (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        place_id TEXT UNIQUE,
        name TEXT, category TEXT, address TEXT,
        road_address TEXT, lat REAL, lng REAL,
        phone TEXT, review_count INTEGER, rating REAL,
        business_hours TEXT, place_url TEXT,
        scraped_at TEXT
    )''')
    conn.commit()
    return conn

def save_place(conn, info):
    cur = conn.cursor()
    cur.execute('''INSERT OR REPLACE INTO places 
        (place_id, name, category, address, road_address, lat, lng, phone, review_count, rating, business_hours, place_url, scraped_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (info.get('place_id'), info.get('name'), info.get('category'), info.get('address'),
         info.get('road_address'), info.get('lat'), info.get('lng'), info.get('phone'),
         info.get('review_count'), info.get('rating'), info.get('hours'), info.get('place_url'),
         info.get('scraped_at', time.strftime('%Y-%m-%d %H:%M'))))
    conn.commit()

def parse_body_for_stores(text):
    """Parse real store names from body text"""
    stores = []
    lines = text.split('\n')
    
    # Known real Olive Young store patterns
    real_patterns = [
        '올리브영 해운대엘시티점',
        '올리브영 부산장산역점',
        '올리브영 해운대중앙점',
        '올리브영 부산센텀점',
        '올리브영 부산벡스코점',
        '올리브영 센텀중앙로점',
        '올리브영 해운대역점',
        '올리브영 이마트해운대점',
        '올리브영 부산반여1동점',
        '올리브영 부산당감점',
        '올리브영 딜라이트프로젝트 해운대점',
    ]
    
    found = set()
    for line in lines:
        line = line.strip()
        for p in real_patterns:
            if p in line and p not in found:
                # Extract hours if present
                hours = None
                idx = lines.index(line) if line in lines else -1
                if idx >= 0 and idx < len(lines)-1:
                    next_line = lines[idx+1].strip()
                    if '영업 중' in next_line or '营业' in next_line:
                        hours = next_line
                    elif '해운대구' in next_line:
                        pass  # this is address, not hours
                
                # Extract address from context
                addr = None
                for offset in range(1, 6):
                    if idx+offset < len(lines):
                        cand = lines[idx+offset].strip()
                        if '해운대구' in cand or '부산' in cand:
                            addr = cand
                            break
                
                stores.append({'name': p, 'hours': hours, 'address': addr})
                found.add(p)
                break
    
    return stores

def scrape_detail(place_id, driver):
    """Scrape detail page for a place"""
    url = f'https://m.place.naver.com/place/{place_id}/home'
    driver.get(url)
    time.sleep(4)
    
    info = {'place_id': place_id, 'place_url': url}
    html = driver.page_source
    
    # Try to extract from HTML
    for pat, key in [
        (r'"displayName"\s*:\s*"([^"]+)"', 'name'),
        (r'"roadAddress"\s*:\s*"([^"]+)"', 'road_address'),
        (r'"latitude"\s*:\s*([0-9.]+)', 'lat'),
        (r'"longitude"\s*:\s*([0-9.]+)', 'lng'),
        (r'"phone"\s*:\s*"([^"]+)"', 'phone'),
        (r'"reviewCount"\s*:\s*([0-9]+)', 'review_count'),
        (r'"rating"\s*:\s*([0-9.]+)', 'rating'),
    ]:
        m = re.search(pat, html)
        if m:
            v = m.group(1)
            if key in ('lat', 'lng'):
                info[key] = float(v)
            elif key in ('review_count',):
                info[key] = int(v)
            elif key in ('rating',):
                info[key] = float(v)
            else:
                info[key] = v
    
    # Get body for hours/address
    try:
        body = driver.find_element(By.TAG_NAME, 'body')
        text = body.text
        lines = text.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            if '영업시간' in line or '영업 중' in line:
                if i+1 < len(lines):
                    next_l = lines[i+1].strip()
                    if '시' in next_l or ':' in next_l or '종료' in next_l:
                        info['hours'] = next_l
            if '주소' in line and i+1 < len(lines):
                next_l = lines[i+1].strip()
                if '부산' in next_l or '해운대' in next_l:
                    info['address'] = next_l
    except: pass
    
    info['scraped_at'] = time.strftime('%Y-%m-%d %H:%M')
    return info

def main():
    print('=== Olive Young Korea Store DB (Clean) ===\n')
    conn = init_db()
    driver = get_driver()
    
    # Search queries
    queries = [
        '올리브영 해운대',
        '올리브영 부산 해운대구',
        '올리브영 센텀',
    ]
    
    all_stores = {}
    for q in queries:
        print(f'\n--- Search: {q} ---')
        url = f'https://search.naver.com/search.naver?where=m&query={q}&sm=mtb_htop'
        driver.get(url)
        time.sleep(4)
        
        body = driver.find_element(By.TAG_NAME, 'body')
        text = body.text
        
        stores = parse_body_for_stores(text)
        print(f'Stores found: {len(stores)}')
        for s in stores:
            name = s['name']
            if name not in all_stores:
                all_stores[name] = s
            print(f"  {name} | {s.get('hours','N/A')} | {s.get('address','N/A')}")
    
    print(f'\n=== Unique real stores: {len(all_stores)} ===')
    
    # Now scrape each store's detail page
    # Known place IDs from Naver search
    place_id_map = {
        '올리브영 해운대엘시티점': '1233549799',
        '올리브영 부산장산역점': '36949208',
        '올리브영 해운대중앙점': '1928195404',
        '올리브영 부산센텀점': '1339619226',
    }
    
    for name, s in all_stores.items():
        pid = place_id_map.get(name)
        if pid:
            print(f'\n--- Scraping detail: {name} ({pid}) ---')
            detail = scrape_detail(pid, driver)
            detail['name'] = name
            detail['category'] = '올리브영'
            detail['hours'] = s.get('hours') or detail.get('hours')
            detail['address'] = s.get('address') or detail.get('road_address') or detail.get('address')
            print(f"  Name: {detail.get('name', 'N/A')}")
            print(f"  Address: {detail.get('road_address', detail.get('address', 'N/A'))}")
            print(f"  Phone: {detail.get('phone', 'N/A')}")
            print(f"  Hours: {detail.get('hours', 'N/A')}")
            save_place(conn, detail)
        else:
            # Save with partial info
            info = {
                'name': name,
                'category': '올리브영',
                'hours': s.get('hours'),
                'address': s.get('address'),
                'place_url': f'https://m.place.naver.com/search?query={name}',
                'scraped_at': time.strftime('%Y-%m-%d %H:%M')
            }
            save_place(conn, info)
            print(f'\n--- Saved (no detail): {name} ---')
    
    driver.quit()
    
    # Final stats
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM places')
    print(f'\nDB total: {cur.fetchone()[0]} places')
    
    print('\n=== Final Stores ===')
    cur.execute('SELECT name, address, phone, business_hours FROM places ORDER BY name')
    for r in cur.fetchall():
        print(f'  {r[0]} | {r[1]} | {r[2]} | {r[3]}')
    
    conn.close()
    print('\n=== Done ===')

if __name__ == '__main__':
    main()