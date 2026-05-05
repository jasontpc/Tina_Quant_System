# -*- coding: utf-8 -*-
"""Scrape BBQ places in Haeundae from Naver Maps"""
import sys, os, time, re, json
sys.stdout.reconfigure(encoding='utf-8')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'

def scrape_bbq():
    opts = Options()
    opts.add_argument('--headless=new')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--window-size=1280,900')
    opts.add_argument('--user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1')
    prefs = {'profile.default_content_setting_values': {'images': 1, 'css': 1}}
    opts.add_experimental_option('prefs', prefs)
    
    driver = webdriver.Chrome(options=opts)
    
    print('=== 海雲台/尾浦 燒肉店精選 ===\n')
    
    # Naver Maps search
    url = 'https://map.naver.com/v5/search/부산 해운대구 고기집'
    driver.get(url)
    time.sleep(5)
    
    # Scroll to load more
    for _ in range(3):
        driver.execute_script('window.scrollBy(0, 500)')
        time.sleep(1)
    
    html = driver.page_source
    
    # Parse store info from the page
    # Try to find store entries
    stores = []
    
    # Find entries via regex
    name_patterns = [
        r'"name"\s*:\s*"([^"]+)"',
        r'data-name="([^"]+)"',
    ]
    
    # Get body text and parse
    body = driver.find_element(By.TAG_NAME, 'body')
    text = body.text
    
    # Split by lines and find stores
    lines = text.split('\n')
    
    current_store = {}
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Store name pattern
        if any(k in line for k in ['고기', '불고기', 'BBQ', '육류', '구이', '식당', '집']) and len(line) < 60:
            # Check if it's a category or actual name
            if '검색결과' not in line and '부산' not in line[:10] and '해운대구' not in line[:10]:
                current_store['name'] = line
                
        # Address pattern
        if '부산' in line and ('구' in line or '동' in line):
            if 'road' not in current_store.get('address', '').lower():
                current_store['address'] = line[:80]
        
        # Phone pattern
        if re.match(r'0\d{1,2}-\d{3,4}-\d{4}', line):
            current_store['phone'] = line
        
        # If we have both name and address, save it
        if 'name' in current_store and len(current_store) > 1:
            if current_store not in stores:
                stores.append(current_store.copy())
            current_store = {}
    
    # Show results
    print(f'找到 {len(stores)} 間店\n')
    
    for i, s in enumerate(stores[:15], 1):
        name = s.get('name', 'N/A')
        addr = s.get('address', 'N/A')
        phone = s.get('phone', 'N/A')
        print(f'{i}. {name}')
        if addr != 'N/A':
            print(f'   地址: {addr}')
        if phone != 'N/A':
            print(f'   電話: {phone}')
        print()
    
    # Also try to find more with direct URL
    print('\n=== 嘗試直接訪問Naver Place ===')
    
    place_ids = []
    # Try to extract place IDs from the page source
    place_matches = re.findall(r'/place/(\d+)', html)
    place_ids = list(set(place_matches))[:10]
    
    print(f'Found place IDs: {len(place_ids)}')
    
    # For each place, get details
    detailed_stores = []
    for pid in place_ids[:5]:
        try:
            place_url = f'https://m.place.naver.com/place/{pid}'
            driver.get(place_url)
            time.sleep(2)
            
            body = driver.find_element(By.TAG_NAME, 'body')
            text = body.text
            
            name = ''
            address = ''
            phone = ''
            
            for line in text.split('\n'):
                line = line.strip()
                if len(line) > 2:
                    if not name and len(line) < 50:
                        name = line
                    if '부산' in line and ('구' in line):
                        address = line[:100]
                    if re.match(r'0\d{1,2}-\d{3,4}-\d{4}', line):
                        phone = line
            
            if name:
                print(f'\nPlace: {name}')
                if address:
                    print(f'  Address: {address}')
                if phone:
                    print(f'  Phone: {phone}')
                
                detailed_stores.append({
                    'name': name,
                    'address': address,
                    'phone': phone,
                    'place_id': pid,
                    'url': f'https://m.place.naver.com/place/{pid}'
                })
        except Exception as e:
            print(f'Error: {e}')
    
    driver.quit()
    
    # Save
    results = {
        'search': '부산 해운대구 고기집',
        'count': len(stores),
        'stores': stores[:20],
        'detailed': detailed_stores,
    }
    
    with open(os.path.join(DATA_DIR, 'haeundae_bbq.json'), 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f'\n✅ 已儲存: {len(stores)} 間燒肉店')

if __name__ == '__main__':
    scrape_bbq()