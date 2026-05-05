import requests
from datetime import datetime, date, timedelta
import sys
sys.path.insert(0, r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
from scripts.tw_margin_db import fetch_margin_data_twse, parse_twse_margin_data, save_margin_data

print('Fetching TW Margin Data from TWSE...')
print('='*50)

# Fetch for major stocks
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
    
    data = fetch_margin_data_twse(stock_id, start_date, end_date)
    
    if data and len(data) > 0:
        records = parse_twse_margin_data(data)
        if records:
            save_margin_data(stock_id, records)
            total_records += len(records)
            print(f'  Saved {len(records)} records')
        else:
            print(f'  No valid records')
    else:
        print(f'  No data received')

print()
print(f'Total records saved: {total_records}')

# Show summary
if total_records > 0:
    print()
    print('Checking saved data...')
    
    import sqlite3
    db_path = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\tw_margin.db'
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    c.execute('SELECT stock_id, COUNT(*) as cnt, MAX(date) as latest FROM margin_summary GROUP BY stock_id')
    rows = c.fetchall()
    
    print()
    print('Stock | Records | Latest Date')
    print('-'*35)
    for row in rows:
        print(f'{row[0]:<8} {row[1]:>6}    {row[2]}')
    
    conn.close()