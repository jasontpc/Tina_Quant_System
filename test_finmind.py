import requests
import json

TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjJ9.1LHB4yKHeZFoXStyjK2W9F6X3nZLMA1IfPWpDVlv6K0"
BASE = "https://api.finmindtrade.com/api/v4/data"

test_stocks = ["2330", "2884", "1101", "2311", "2303"]
for stock_id in test_stocks:
    params = {
        "dataset": "TaiwanStockPrice",
        "data_id": stock_id,
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "token": TOKEN,
    }
    try:
        r = requests.get(BASE, params=params, timeout=10)
        data = r.json()
        print(f"{stock_id}: raw response keys={list(data.keys())}, success={data.get('success')}, msg={data.get('msg')}")
        if 'data' in data:
            print(f"  -> {len(data['data'])} rows")
    except Exception as e:
        print(f"{stock_id}: ERROR {e}")