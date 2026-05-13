# -*- coding: utf-8 -*-
"""Search Naver for BBQ in 尾浦 area - try Naver Maps"""
import sys, os, time, re, json
sys.stdout.reconfigure(encoding='utf-8')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'

def search_bbq_maps():
    opts = Options()
    opts.add_argument('--headless=new')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--window-size=1280,900')
    opts.add_argument('--user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1')
    prefs = {'profile.default_content_setting_values': {'images': 2, 'css': 2}}
    opts.add_experimental_option('prefs', prefs)
    
    driver = webdriver.Chrome(options=opts)
    
    print('=== 海雲台/尾浦 燒肉/烤肉搜尋 ===\n')
    
    # Try Naver Maps directly
    maps_url = 'https://map.naver.com/v5/search/부산 해운대구 고기집'
    driver.get(maps_url)
    time.sleep(5)
    
    html = driver.page_source
    print(f'HTML length: {len(html)}')
    
    # Get page text
    try:
        body = driver.find_element(By.TAG_NAME, 'body')
        text = body.text
        print(f'Text length: {len(text)}')
        
        # Print relevant lines
        lines = text.split('\n')
        store_lines = []
        for line in lines:
            line = line.strip()
            if len(line) > 5 and len(line) < 80:
                if any(k in line for k in ['고기', '불고기', 'BBQ', '리브', '육', '고기집', '烤肉', '燒肉']):
                    store_lines.append(line)
        
        print(f'\n找到相關行: {len(store_lines)}')
        for l in store_lines[:20]:
            print(f'  {l}')
    except Exception as e:
        print(f'Body error: {e}')
    
    # Save HTML
    with open(os.path.join(DATA_DIR, 'naver_maps_bbq.html'), 'w', encoding='utf-8') as f:
        f.write(html)
    print('\nSaved HTML')
    
    driver.quit()
    print('Done')

if __name__ == '__main__':
    search_bbq_maps()