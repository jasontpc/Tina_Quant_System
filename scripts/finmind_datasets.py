import requests
import json

base = 'https://api.finmindtrade.com/api/v4/data'
token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjF9.ivums9mfJUrM2MYazJiOEg49RiYLOJMZtejqX79YWS8'

# Trigger a 422 to get the full enum list
r = requests.get(base, params={'dataset': 'INVALID', 'token': token}, timeout=10)
if r.status_code == 422:
    detail = r.json().get('detail', [])
    for d in detail:
        msg = d.get('msg', '')
        if 'should be' in msg:
            print(msg)
