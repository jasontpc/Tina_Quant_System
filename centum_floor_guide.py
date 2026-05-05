# -*- coding: utf-8 -*-
"""Scrape full Centum City floor guide and brand list"""
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8')
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'

def main():
    opts = Options()
    opts.add_argument('--headless=new')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--window-size=1280,900')
    opts.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    prefs = {'profile.default_content_setting_values': {'images': 1, 'css': 1}}
    opts.add_experimental_option('prefs', prefs)
    
    driver = webdriver.Chrome(options=opts)
    
    # Load the Centum City page
    url = 'https://en.shinsegae.cn/store/introduce.do?storeSeq=3'
    print('Loading:', url)
    driver.get(url)
    time.sleep(5)
    
    # Scroll down to get all content
    for i in range(5):
        driver.execute_script('window.scrollBy(0, 500)')
        time.sleep(0.5)
    
    html = driver.page_source
    body = driver.find_element(By.TAG_NAME, 'body')
    text = body.text
    
    # Save HTML
    with open(os.path.join(DATA_DIR, 'shinsegae_centum_en_full.html'), 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f'HTML length: {len(html)}')
    print(f'Text length: {len(text)}')
    
    # Find Floor Guide section
    lines = text.split('\n')
    in_floor = False
    floor_data = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        if 'Floor Guide' in line or 'floor guide' in line.lower():
            in_floor = True
        if in_floor:
            floor_data.append(line)
            if len(floor_data) > 50 and 'ENTERTAINMENT' in line:
                break
    
    print('\n=== FLOOR GUIDE ===')
    for line in floor_data[:50]:
        print(f'  {line}')
    
    # Try to find brand/shop links
    nav_links = driver.find_elements(By.CSS_SELECTOR, 'nav a, .gnb a, .lnb a')
    print(f'\n=== NAV LINKS ({len(nav_links)}) ===')
    for link in nav_links[:20]:
        try:
            href = link.get_attribute('href') or ''
            text_l = link.text.strip()
            if text_l:
                print(f'  {text_l[:30]} -> {href[:80]}')
        except:
            pass
    
    # Try to find shopping/brand page
    brand_urls = [
        'https://en.shinsegae.cn/store/brand.do?storeSeq=3',
        'https://en.shinsegae.cn/store/shopping.do?storeSeq=3',
        'https://en.shinsegae.cn/store/storeList.do?storeSeq=3',
        'https://en.shinsegae.cn/store/tenant.do?storeSeq=3',
    ]
    
    print('\n=== TRYING BRAND PAGES ===')
    for brand_url in brand_urls:
        driver.get(brand_url)
        time.sleep(3)
        body2 = driver.find_element(By.TAG_NAME, 'body')
        text2 = body2.text
        print(f'{brand_url.split("/")[-1]}: html={len(driver.page_source)}, text={len(text2)}')
        if len(text2) > 500:
            with open(os.path.join(DATA_DIR, f'brand_{brand_url.split("/")[-1].replace("?","_")}.html'), 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
    
    driver.quit()
    print('\nDone')

if __name__ == '__main__':
    import time
    main()