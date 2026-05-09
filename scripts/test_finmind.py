import requests
import json

TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjJ9.1LHB4yKHeZFoXStyjK2W9F6X3nZLMA1IfPWpDVlv6K0"
BASE_URL = "https://api.finmindtrade.com/api/v4/data"

# Test margin data
payload = {
    "dataset": "TaiwanStockMarginBuySell",
    "data_id": "2330",
    "start_date": "2026-05-01",
    "end_date": "2026-05-08",
    "token": TOKEN
}

print("Testing FinMind API...")
print(f"Token: {TOKEN[:50]}...")
print()

try:
    resp = requests.post(BASE_URL, json=payload, timeout=15)
    print(f"Status: {resp.status_code}")
    data = resp.json()
    
    if "data" in data:
        print(f"Data rows: {len(data['data'])}")
        if data['data']:
            for row in data['data'][:3]:
                print(row)
    else:
        print(f"Response: {data}")
except Exception as e:
    print(f"Error: {e}")