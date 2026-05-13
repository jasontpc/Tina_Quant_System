# -*- coding: utf-8 -*-
"""Scrape Shinsegae Centum City - Official Site (Selenium)"""
import sys, os, time, re, sqlite3
sys.path.insert(0, os.path.dirname(__file__))
sys.stdout.reconfigure(encoding='utf-8')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
DB = os.path.join(DATA_DIR, 'shinsegae_centum.db')

def get_driver():
    opts = Options()
    opts.add_argument('--headless=new')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--window-size=1280,900')
    opts.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    prefs = {'profile.default_content_setting_values': {'images': 2, 'css': 2}}
    opts.add_experimental_option('prefs', prefs)
    return webdriver.Chrome(options=opts)

def try_official_site(driver):
    """Try official Korean Shinsegae site"""
    urls_to_try = [
        'https://www.shinsegae.com/store/busan-centum/guide/floor.do',
        'https://www.shinsegae.com/store/busan-centum/guide/brand.do',
        'https://www.shinsegae.com/shopping/BUSAN_CENTUM/guide/floor.do',
        'https://www.shinsegae.com/shopping/BUSAN_CENTUM/guide/brandList.do',
        'https://www.shinsegae.com/shopping/BUSAN_CENTUM/guide/storeInfo.do',
    ]
    
    for url in urls_to_try:
        print(f'Trying: {url}')
        driver.get(url)
        time.sleep(5)
        html = driver.page_source
        print(f'  Length: {len(html)}, Error: {"error" in html.lower()}')
        
        if len(html) > 5000 and 'error' not in html.lower():
            # Check for actual content
            if '층' in html or '브랜드' in html or '매장' in html:
                print(f'  ✅ FOUND CONTENT!')
                return html
            elif 'brand' in html.lower() or 'floor' in html.lower():
                print(f'  ✅ FOUND CONTENT (English)!')
                return html
    
    return None

def try_naver_place_with_api(driver):
    """Try Naver Place API approach"""
    place_id = '13067134'
    
    # Try different tab URLs
    tabs = ['floor', 'brand', 'shop', 'store', 'info']
    for tab in tabs:
        url = f'https://m.place.naver.com/place/{place_id}/{tab}'
        print(f'Naver Place tab: {tab}')
        driver.get(url)
        time.sleep(5)
        html = driver.page_source
        
        if len(html) > 5000 and 'error' not in html.lower():
            body = driver.find_element(By.TAG_NAME, 'body')
            text = body.text
            print(f'  Text length: {len(text)}')
            if len(text) > 500:
                print(f'  ✅ Content found!')
                return html, text
    
    return None, None

def try_korean_search(driver):
    """Try Korean Naver search for brand list"""
    queries = [
        '신세계백화점 센텀시티 브랜드 목록',
        '신세계 센텀시티 2층 브랜드',
        '신세계 센텀시티 매장안내',
        '신세계 센텀시티 floors brands',
    ]
    
    for q in queries:
        url = f'https://search.naver.com/search.naver?where=m&query={q}'
        print(f'Search: {q}')
        driver.get(url)
        time.sleep(4)
        html = driver.page_source
        body = driver.find_element(By.TAG_NAME, 'body')
        text = body.text
        
        print(f'  Text length: {len(text)}')
        if len(text) > 2000:
            # Save sample
            filename = f'shinsegae_search_{q[:10]}.txt'
            with open(os.path.join(DATA_DIR, filename), 'w', encoding='utf-8') as f:
                f.write(text)
            print(f'  ✅ Saved to {filename}')
            return html, text
    
    return None, None

def main():
    print('=== Shinsegae Centum City - Official Site Scrape ===\n')
    driver = get_driver()
    
    html = None
    source = ''
    
    # Try 1: Official Korean site
    print('--- Attempt 1: Official Korean Site ---')
    html = try_official_site(driver)
    if html:
        source = 'official_korean'
        print('Success: Official Korean site')
    
    # Try 2: Naver Place tabs
    if not html:
        print('\n--- Attempt 2: Naver Place Tabs ---')
        result_html, result_text = try_naver_place_with_api(driver)
        if result_html:
            html = result_html
            source = 'naver_place'
            print('Success: Naver Place')
    
    # Try 3: Naver search
    if not html:
        print('\n--- Attempt 3: Naver Search ---')
        result_html, result_text = try_korean_search(driver)
        if result_html:
            html = result_html
            source = 'naver_search'
            print('Success: Naver Search')
    
    if html:
        print(f'\n✅ Got HTML from: {source}, length: {len(html)}')
        # Save HTML
        with open(os.path.join(DATA_DIR, f'shinsegae_html_{source}.html'), 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'Saved to shinsegae_html_{source}.html')
    else:
        print('\n❌ Could not get content from any source')
        
        # Last resort: try accessing the Chinese site via Selenium with different settings
        print('\n--- Last Resort: Chinese site m.shinsegae.cn ---')
        driver.get('http://m.shinsegae.cn/m/')
        time.sleep(5)
        html2 = driver.page_source
        print(f'Chinese mobile length: {len(html2)}')
    
    driver.quit()
    print('\n=== Done ===')

if __name__ == '__main__':
    main()