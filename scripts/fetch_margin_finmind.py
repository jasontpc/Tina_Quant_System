import requests
from datetime import datetime, date, timedelta
import sqlite3
import json

token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjF9.ivums9mfJUrM2MYazJiOEg49RiYLOJMZtejqX79YWS8'
base = 'https://api.finmindtrade.com/api/v4/data'

def fetch_margin_finmind(stock_id, start_date, end_date):
    """使用 FinMind API 取得融資融券資料"""
    params = {
        'dataset': 'TaiwanMargin',
        'data_id': stock_id,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'token': token
    }
    
    try:
        resp = requests.get(base, params=params, timeout=15)
        data = resp.json()
        
        if 'data' in data and data['data']:
            return data['data']
        else:
            print(f'  No data from FinMind for {stock_id}')
            return None
    except Exception as e:
        print(f'  Error: {e}')
        return None

def save_margin_records(stock_id, records):
    """儲存到本地資料庫"""
    db_path = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\tw_margin.db'
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    for r in records:
        date_str = r.get('date', '')
        if not date_str:
            continue
        
        margin_buy = r.get('MarginBuy', 0) or 0
        margin_sell = r.get('MarginSell', 0) or 0
        margin_balance = r.get('MarginBalance', 0) or 0
        short_buy = r.get('ShortBuy', 0) or 0
        short_sell = r.get('ShortSell', 0) or 0
        short_balance = r.get('ShortBalance', 0) or 0
        
        c.execute('''
            INSERT OR REPLACE INTO margin_summary 
            (stock_id, date, margin_buy, margin_repay, margin_balance, short_cover, short_sell, short_balance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (stock_id, date_str, margin_buy, margin_sell, margin_balance, short_buy, short_sell, short_balance))
    
    conn.commit()
    conn.close()

def init_db():
    """初始化資料庫"""
    db_path = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\tw_margin.db'
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS margin_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_id TEXT NOT NULL,
            date TEXT NOT NULL,
            margin_buy INTEGER,
            margin_repay INTEGER,
            margin_balance INTEGER,
            short_cover INTEGER,
            short_sell INTEGER,
            short_balance INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(stock_id, date)
        )
    ''')
    
    conn.commit()
    conn.close()

# Init DB first
init_db()

print('Fetching TW Margin Data via FinMind API...')
print('='*50)

stocks = [
    ('2330', '台積電'),
    ('2454', '聯發科'),
    ('2317', '鴻海'),
    ('2382', '廣達'),
    ('2881', '富邦金'),
    ('2883', '凱基金'),
    ('3231', '緯創'),
    ('3034', '緯穎'),
]

end_date = date(2026, 5, 2)
start_date = date(2026, 1, 1)

total_records = 0

for stock_id, name in stocks:
    print(f'Fetching {stock_id} {name}...')
    
    data = fetch_margin_finmind(stock_id, start_date, end_date)
    
    if data:
        print(f'  Received {len(data)} records')
        save_margin_records(stock_id, data)
        total_records += len(data)
    else:
        print(f'  No data')

print()
print(f'Total records saved: {total_records}')

# Show summary
if total_records > 0:
    db_path = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\tw_margin.db'
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    c.execute('SELECT stock_id, COUNT(*) as cnt, MAX(date) as latest FROM margin_summary GROUP BY stock_id')
    rows = c.fetchall()
    
    print()
    print('Stock   | Records | Latest Date')
    print('-'*40)
    for row in rows:
        print(f'{row[0]:<8} {row[1]:>6}    {row[2]}')
    
    # Show sample data for 2330
    c.execute('SELECT * FROM margin_summary WHERE stock_id = "2330" ORDER BY date DESC LIMIT 5')
    sample = c.fetchall()
    
    if sample:
        print()
        print('Sample: 2330 (Recent)')
        for row in sample:
            print(f'  {row[2]}: MarginBuy={row[3]} MarginSell={row[4]} MarginBal={row[5]} ShortBuy={row[6]} ShortSell={row[7]} ShortBal={row[8]}')
    
    conn.close()