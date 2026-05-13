# -*- coding: utf-8 -*-
"""Navigate to Centum City floor guide"""
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
    
    # Load main page
    print('Loading main page...')
    driver.get('http://m.shinsegae.cn/m/')
    time.sleep(3)
    
    # Find the Centum City link
    links = driver.find_elements(By.TAG_NAME, 'a')
    centum_url = None
    for link in links:
        try:
            href = link.get_attribute('href') or ''
            text = link.text or ''
            if 'centum' in href.lower() or 'CENTUM' in text:
                centum_url = href
                print(f'Found: {text} -> {href}')
                break
        except:
            pass
    
    # Also check for onclick handlers
    if not centum_url:
        buttons = driver.find_elements(By.CSS_SELECTOR, '[onclick]')
        for btn in buttons:
            try:
                onclick = btn.get_attribute('onclick') or ''
                if 'centum' in onclick.lower():
                    print(f'Found onclick: {onclick[:100]}')
            except:
                pass
    
    # Try direct URL patterns
    url_patterns = [
        'http://m.shinsegae.cn/m/store/BUSAN_CENTUM/floor.do',
        'http://m.shinsegae.cn/m/shopping/BUSAN_CENTUM/guide/floor.do',
        'http://m.shinsegae.cn/m/store/BUSAN_CENTUM/guide/floor',
        'http://m.shinsegae.cn/m/store/centum/floor',
        'http://m.shinsegae.cn/m/centumcity/floor',
    ]
    
    for url in url_patterns:
        print(f'\nTrying: {url}')
        driver.get(url)
        time.sleep(3)
        html = driver.page_source
        text_len = len(driver.find_element(By.TAG_NAME, 'body').text)
        print(f'  Length: html={len(html)}, text={text_len}')
        
        if text_len > 500:
            body = driver.find_element(By.TAG_NAME, 'body')
            text = body.text
            print(f'\n  Text sample:')
            for line in text.split('\n')[:30]:
                line = line.strip()
                if line:
                    print(f'    {line[:80]}')
            
            # Save if useful
            with open(os.path.join(DATA_DIR, f'shinsegae_cn_{url.split("/")[-1]}.html'), 'w', encoding='utf-8') as f:
                f.write(html)
            print(f'\n  Saved!')
    
    driver.quit()
    print('\nDone')

if __name__ == '__main__':
    main()