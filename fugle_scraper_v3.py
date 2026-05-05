# -*- coding: utf-8 -*-
"""
Fugle 爬蟲 v3 - 修正價格解析邏輯
從 body text 中找到「第二個 close」後的個股數據
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time, json, sqlite3, os, re

DB_PATH = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\fugle.db"
STOCK_FILE = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\nana\stock_names.json"
OUTPUT_DIR = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\fugle_scrape"

def create_driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.binary_location = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--window-size=1920,3000')
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(20)
    return driver

def parse_body_text(text):
    """解析 body text，找到第一個 close 後的個股數據
    格式: close → 股票名 → TW → 股票代號 → 價格 → 漲跌% → close
    """
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    # 找到第一個 close（標記個股價格區段開始）
    close_idx = None
    for i, line in enumerate(lines):
        if line == 'close':
            close_idx = i
            break
    
    if close_idx is None:
        return None
    
    # close 與下一個 close 之间的內容是個股數據
    section = lines[close_idx:]
    
    data = {}
    
    # 解析格式: close → 名稱 → TW → 代號 → 價格 → 漲跌%
    # 依序解析
    idx = 1  # 跳過 close
    if idx < len(section):
        data['name'] = section[idx]  # 股票名
    idx += 1
    if idx < len(section):
        data['market'] = section[idx]  # TW
    idx += 1
    if idx < len(section) and re.match(r'^\d{4}$', section[idx]):
        data['symbol'] = section[idx]  # 股票代號
    idx += 1
    if idx < len(section):
        price_m = re.search(r'([\d,]+(?:\.\d+)?)', section[idx])
        if price_m:
            data['price'] = float(price_m.group(1).replace(',',''))
    idx += 1
    if idx < len(section):
        pct_m = re.search(r'([+\-]?\d+\.\d+)%', section[idx])
        if pct_m:
            data['change_pct'] = float(pct_m.group(1))
    
    # 找 RSI
    for i, line in enumerate(section):
        if line == 'RSI' and i+1 < len(section):
            rsi_m = re.search(r'\d+', section[i+1])
            if rsi_m:
                data['rsi'] = int(rsi_m.group())
    
    # 找 MA
    for i, line in enumerate(section):
        if line == '5MA' and i+1 < len(section):
            m = re.search(r'[\d,]+(?:\.\d+)?', section[i+1])
            if m: data['ma5'] = float(m.group().replace(',',''))
        elif line == '10MA' and i+1 < len(section):
            m = re.search(r'[\d,]+(?:\.\d+)?', section[i+1])
            if m: data['ma10'] = float(m.group().replace(',',''))
        elif line == '20MA' and i+1 < len(section):
            m = re.search(r'[\d,]+(?:\.\d+)?', section[i+1])
            if m: data['ma20'] = float(m.group().replace(',',''))
    
    return data

def scrape_stock(driver, symbol, name):
    try:
        url = f'https://www.fugle.tw/ai/B00112/{symbol}'
        driver.get(url)
        time.sleep(3)
        
        body = driver.find_element(By.TAG_NAME, 'body')
        text = body.text
        
        data = {
            'symbol': symbol,
            'name': name,
            'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        parsed = parse_body_text(text)
        data['data'] = parsed if parsed else {}
        
        return data
        
    except Exception as e:
        return {'symbol': symbol, 'name': name, 'error': str(e)}

def update_db(symbol, data):
    if 'error' in data or not data.get('data'):
        return False
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        d = data['data']
        cur.execute("""
            INSERT OR REPLACE INTO quote_latest 
            (symbol, price, change_percent, rsi_14, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'))
        """, (symbol, d.get('price'), d.get('change_pct'), d.get('rsi')))
        conn.commit()
        conn.close()
        return True
    except:
        return False

def save_scrape(symbol, data):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, f"{symbol}.json"), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    print('=== Fugle 爬蟲 v3 ===')
    print(f'時間: {time.strftime("%Y-%m-%d %H:%M:%S")}')
    
    with open(STOCK_FILE, encoding='utf-8') as f:
        stocks = json.load(f)
    exclude = {'2888', '5882', '3008', '2330'}
    stock_list = [(k, v) for k, v in stocks.items() if k not in exclude]
    print(f'股票數量: {len(stock_list)}')
    
    driver = create_driver()
    success = errors = 0
    
    try:
        for i, (sym, name) in enumerate(stock_list[:30]):
            print(f'[{i+1}/{min(30,len(stock_list))}] {sym} {name}...', end=' ')
            data = scrape_stock(driver, sym, name)
            d = data.get('data', {})
            
            if d.get('price') and d.get('change_pct') is not None:
                update_db(sym, data)
                save_scrape(sym, data)
                print(f"${d.get('price')} ({d.get('change_pct'):+.2f}%) RSI={d.get('rsi','?')} MA5={d.get('ma5','?')}")
                success += 1
            else:
                print(f"ERROR: no price parsed. data={d}")
                errors += 1
            
            time.sleep(0.3)
        
        print(f'\n成功: {success}, 失敗: {errors}')
        
    finally:
        driver.quit()
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM quote_latest')
    print(f'fugle.db quote_latest: {cur.fetchone()[0]} 檔')
    conn.close()

if __name__ == '__main__':
    main()
