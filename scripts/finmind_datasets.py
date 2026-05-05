import requests
import json

base = 'https://api.finmindtrade.com/api/v4/data'
token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSJ9.oCdQO1qNRUCYxHZSVuRQCqlF7X2DbQ77wury5ARCKzM'

# Trigger a 422 to get the full enum list
r = requests.get(base, params={'dataset': 'INVALID', 'token': token}, timeout=10)
if r.status_code == 422:
    detail = r.json().get('detail', [])
    for d in detail:
        msg = d.get('msg', '')
        if 'should be' in msg:
            print(msg)
