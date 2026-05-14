# -*- coding: utf-8 -*-
import sys, requests
sys.stdout.reconfigure(encoding='utf-8')
token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjJ9.1LHB4yKHeZFoXStyjK2W9F6X3nZLMA1IfPWpDVlv6K0'

r = requests.get('https://api.finmindtrade.com/api/v4/data', params={
    'dataset': 'TaiwanIndicesDaily',
    'data_id': 'TAIEX',
    'start_date': '2026-04-25',
    'end_date': '2026-04-28',
    'token': token
}, timeout=10)
if r.status_code == 200:
    d = r.json()
    if d.get('status') == 200:
        for row in d['data']['data']:
            print(f"TWII {row.get('date')}: close={row.get('close')}")
    else:
        print('TWII status:', d.get('status'))
else:
    print('HTTP:', r.status_code)

