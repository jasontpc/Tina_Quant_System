import requests
import sqlite3
from datetime import datetime, date

DB_PATH = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\tw_margin.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
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

def fetch_twse_margin(date_str):
    """從 TWSE OpenAPI 取得單日融資融券資料"""
    url = f'https://openapi.twse.com.tw/v1/BFIAUU_d/{date_str}'
    
    try:
        resp = requests.get(url, timeout=15)
        data = resp.json()
        
        if 'data' in data:
            return data['data']
        elif resp.text and resp.text.startswith('{'):
            # Might be an error object
            return None
        else:
            # CSV format
            return resp.text
    except Exception as e:
        print(f'Error: {e}')
        return None

def parse_twse_csv(data):
    """解析 TWSE CSV 資料"""
    records = []
    
    lines = data.strip().split('\n')
    if len(lines) < 2:
        return records
    
    # Skip header
    for line in lines[1:]:
        parts = line.split(',')
        if len(parts) < 10:
            continue
        
        try:
            stock_id = parts[0].strip()
            date_str = parts[1].strip()
            margin_balance = int(parts[2].strip()) if parts[2].strip() else 0
            short_balance = int(parts[8].strip()) if parts[8].strip() else 0
            
            records.append({
                'stock_id': stock_id,
                'date': date_str,
                'margin_balance': margin_balance,
                'short_balance': short_balance
            })
        except:
            continue
    
    return records

def parse_twse_json(data):
    """解析 TWSE JSON 資料"""
    records = []
    
    for item in data:
        try:
            stock_id = str(item.get('stock_id', item.get('Code', '')))
            date_str = item.get('date', '')
            
            if not date_str:
                # Try to extract date from response
                date_str = item.get('Report_Date', item.get('date', ''))
            
            # Find margin balance field
            margin_balance = 0
            short_balance = 0
            
            for key, val in item.items():
                if 'MarginBalance' in key or 'margin_balance' in key:
                    margin_balance = int(val) if val else 0
                if 'ShortBalance' in key or 'short_balance' in key:
                    short_balance = int(val) if val else 0
            
            if stock_id and date_str:
                records.append({
                    'stock_id': stock_id,
                    'date': date_str,
                    'margin_balance': margin_balance,
                    'short_balance': short_balance
                })
        except:
            continue
    
    return records

def save_records(records):
    """儲存記錄"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    count = 0
    for r in records:
        try:
            c.execute('''
                INSERT OR REPLACE INTO margin_summary 
                (stock_id, date, margin_balance, short_balance)
                VALUES (?, ?, ?, ?)
            ''', (r['stock_id'], r['date'], r['margin_balance'], r['short_balance']))
            count += 1
        except:
            pass
    
    conn.commit()
    conn.close()
    
    return count

# Initialize
init_db()

print('TWSE Margin Data Fetcher')
print('='*50)

# Fetch recent dates
dates = [
    '20260502',
    '20260430',
    '20260429',
    '20260428',
    '20260425',
]

all_records = []

for d in dates:
    print(f'Fetching {d}...')
    
    # TWSE format: YYYYMMDD
    result = fetch_twse_margin(d)
    
    if result:
        if isinstance(result, str):
            # CSV format
            records = parse_twse_csv(result)
            print(f'  Parsed {len(records)} CSV records')
        elif isinstance(result, list):
            # JSON format
            records = parse_twse_json(result)
            print(f'  Parsed {len(records)} JSON records')
        else:
            records = []
            print(f'  Unknown format')
        
        if records:
            count = save_records(records)
            all_records.extend(records)
            print(f'  Saved {count} records')
    else:
        print(f'  No data')

print()
print(f'Total records fetched: {len(all_records)}')

# Show summary
if all_records:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('SELECT COUNT(DISTINCT stock_id) as cnt, COUNT(*) as total, MAX(date) as latest FROM margin_summary')
    row = c.fetchone()
    print(f'Database: {row[0]} stocks, {row[1]} records, latest {row[2]}')
    
    # Show top margin balance stocks
    c.execute('''
        SELECT stock_id, margin_balance, short_balance, date
        FROM margin_summary
        WHERE date = (SELECT MAX(date) FROM margin_summary)
        ORDER BY margin_balance DESC
        LIMIT 10
    ''')
    
    top = c.fetchall()
    
    if top:
        print()
        print('Top 10 Margin Balance Stocks:')
        print('Stock   | Margin     | Short      | Date')
        print('-'*50)
        for r in top:
            print(f'{r[0]:<8} {r[1]:>10,}  {r[2]:>10,}  {r[3]}')
    
    conn.close()