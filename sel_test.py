# -*- coding: utf-8 -*-
import sys, os, time, re
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
    opts.add_argument('--window-size=1280,900')
    opts.add_argument('--user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1')
    prefs = {'profile.default_content_setting_values': {'images': 2, 'css': 2}}
    opts.add_experimental_option('prefs', prefs)
    return webdriver.Chrome(options=opts)

def main():
    driver = get_driver()
    
    print('Testing Shinsegae CN site...')
    
    # Test main page
    urls = [
        'http://m.shinsegae.cn/m/',
        'http://m.shinsegae.cn/m/store',
        'http://shinsegae.cn/',
    ]
    
    for url in urls:
        print(f'\n--- {url} ---')
        driver.get(url)
        time.sleep(5)
        html = driver.page_source
        print(f'Length: {len(html)}')
        
        if len(html) > 1000:
            # Check for store links
            if 'centum' in html.lower() or '센텀' in html:
                print('Found Centum City reference!')
                # Find links
                links = re.findall(r'href="([^"]*)"', html)
                store_links = [l for l in links if 'centum' in l.lower() or 'busan' in l.lower()]
                print(f'Store links: {store_links[:10]}')
            
            # Save
            fname = url.split('/')[-1].replace('.', '_') + '.html'
            with open(os.path.join(DATA_DIR, fname), 'w', encoding='utf-8') as f:
                f.write(html)
            print(f'Saved: {fname}')
            
            # Print body text sample
            try:
                body = driver.find_element(By.TAG_NAME, 'body')
                text = body.text
                print(f'\nText sample ({len(text)} chars):')
                for line in text.split('\n')[:30]:
                    line = line.strip()
                    if line:
                        print(f'  {line[:80]}')
            except:
                pass
    
    driver.quit()

if __name__ == '__main__':
    main()