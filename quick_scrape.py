# -*- coding: utf-8 -*-
"""Quick scrape of Shinsegae CN site"""
import sys, os, time, re
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
    
    print('Starting Chrome...')
    driver = webdriver.Chrome(options=opts)
    
    # Try the main page first
    print('Loading m.shinsegae.cn/m/ ...')
    driver.get('http://m.shinsegae.cn/m/')
    time.sleep(3)
    
    html = driver.page_source
    print(f'Main page length: {len(html)}')
    
    # Get all text
    try:
        body = driver.find_element(By.TAG_NAME, 'body')
        text = body.text
        print(f'Text length: {len(text)}')
        print('\nBody text sample:')
        for line in text.split('\n')[:50]:
            line = line.strip()
            if line:
                print(f'  {line[:100]}')
    except Exception as e:
        print(f'Body error: {e}')
    
    # Save HTML
    with open(os.path.join(DATA_DIR, 'shinsegae_cn_main.html'), 'w', encoding='utf-8') as f:
        f.write(html)
    print('\nSaved HTML')
    
    # Try to find store links
    links = driver.find_elements(By.TAG_NAME, 'a')
    store_links = []
    for link in links:
        try:
            href = link.get_attribute('href') or ''
            text = link.text or ''
            if 'centum' in href.lower() or '센텀' in text or 'busan' in href.lower():
                store_links.append(f'{text[:30]} -> {href[:80]}')
        except:
            pass
    
    print(f'\nFound {len(store_links)} store links:')
    for l in store_links[:10]:
        print(f'  {l}')
    
    driver.quit()
    print('\nDone')

if __name__ == '__main__':
    main()