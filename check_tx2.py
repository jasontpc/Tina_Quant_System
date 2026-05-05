# -*- coding: utf-8 -*-
import sys, sqlite3, requests
sys.stdout.reconfigure(encoding='utf-8')

# Check vogel_indicators.db daily table
db = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\vogel_indicators.db'
conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute('PRAGMA table_info(daily)')
cols = [r[1] for r in cur.fetchall()]
print('daily cols:', cols)
cur.execute('SELECT date, close, bb_upper, bb_middle, bb_lower, rsi, atr FROM daily ORDER BY date DESC LIMIT 5')
print('\nTX daily:')
for r in cur.fetchall():
    print(f'  {r}')

# Check TWII via FinMind
try:
    token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSJ9.oCdQO1qNRUCYxHZSVuRQCqlF7X2DbQ77wury5ARCKzM'
    r = requests.get('https://api.finmindtrade.com/api/v4/data', params={
        'dataset': 'TaiwanIndicesDaily',
        'data_id': 'TAIEX',
        'start_date': '2026-04-25',
        'end_date': '2026-04-28',
        'token': token
    }, timeout=10)
    if r.status_code == 200:
        data = r.json()
        if data.get('status') == 200:
            rows = data['data']['data']
            print('\n=== TWII ===')
            for d in rows:
                print(f"  {d.get('date')}: close={d.get('close')}")
        else:
            print(f'TWII status: {data.get("status")} - {data}')
    else:
        print(f'TWII HTTP: {r.status_code}')
except Exception as e:
    print('TWII error:', e)

conn.close()
