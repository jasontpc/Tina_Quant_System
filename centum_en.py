# -*- coding: utf-8 -*-
"""Scrape Centum City from English site"""
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
    
    driver = webdriver.Chrome(options=opts)
    
    # Found URL: https://en.shinsegae.cn/store/introduce.do?storeSeq=3
    print('Loading Centum City page...')
    driver.get('https://en.shinsegae.cn/store/introduce.do?storeSeq=3')
    time.sleep(5)
    
    html = driver.page_source
    print(f'Length: {len(html)}')
    
    # Get text
    body = driver.find_element(By.TAG_NAME, 'body')
    text = body.text
    print(f'Text length: {len(text)}')
    
    # Save
    with open(os.path.join(DATA_DIR, 'shinsegae_centum_en.html'), 'w', encoding='utf-8') as f:
        f.write(html)
    print('Saved HTML')
    
    # Print text sample
    print('\nText sample:')
    for line in text.split('\n')[:80]:
        line = line.strip()
        if line:
            print(f'  {line[:100]}')
    
    # Find floor guide links
    links = driver.find_elements(By.TAG_NAME, 'a')
    floor_links = []
    for link in links:
        try:
            href = link.get_attribute('href') or ''
            text_l = link.text or ''
            if 'floor' in href.lower() or 'brand' in href.lower() or 'guide' in href.lower() or 'store' in href.lower():
                if 'shinsegae' in href.lower() or href.startswith('/'):
                    floor_links.append(f'{text_l[:30]} -> {href[:100]}')
        except:
            pass
    
    print(f'\n\nFloor/Guide links ({len(floor_links)}):')
    for l in floor_links[:20]:
        print(f'  {l}')
    
    driver.quit()
    print('\nDone')

if __name__ == '__main__':
    main()