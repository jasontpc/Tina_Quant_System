# -*- coding: utf-8 -*-
import sys, sqlite3, requests
sys.stdout.reconfigure(encoding='utf-8')

db = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\vogel.db'
conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute('SELECT name FROM sqlite_master WHERE type="table"')
print('Tables:', [r[0] for r in cur.fetchall()])
conn.close()

# Try vogel_indicators.db
db2 = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\vogel_indicators.db'
try:
    conn2 = sqlite3.connect(db2)
    cur2 = conn2.cursor()
    cur2.execute('SELECT name FROM sqlite_master WHERE type="table"')
    print('vogel_indicators tables:', [r[0] for r in cur2.fetchall()])
    conn2.close()
except Exception as e:
    print('vogel_indicators error:', e)

# Try to get TX data from FinMind directly
try:
    token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSJ9.oCdQO1qNRUCYxHZSVuRQCqlF7X2DbQ77wury5ARCKzM'
    r = requests.get('https://api.finmindtrade.com/api/v4/data', params={
        'dataset': 'TaiwanFuturesDaily',
        'data_id': 'TX',
        'start_date': '2026-04-27',
        'end_date': '2026-04-28',
        'token': token
    }, timeout=10)
    if r.status_code == 200:
        data = r.json()
        if data.get('status') == 200:
            rows = data['data']['data']
            print('\n=== TX?Ÿè²¨ ===')
            for d in rows:
                print(f"  {d.get('date')}: close={d.get('close')}")
except Exception as e:
    print('TX FinMind error:', e)
