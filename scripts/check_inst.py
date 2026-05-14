import urllib.request, json

token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjJ9.1LHB4yKHeZFoXStyjK2W9F6X3nZLMA1IfPWpDVlv6K0'
codes = ['2330', '2376', '3034', '2303', '2379', '2317']

for code in codes:
    url = f'https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockInstitutionalInvestorsBuySell&data_id={code}&start_date=2026-05-10&end_date=2026-05-14&token={token}'
    try:
        with urllib.request.urlopen(url, timeout=8) as resp:
            data = json.loads(resp.read())
            rows = data.get('data', [])
            if not rows:
                print(f'{code}: NO DATA')
                continue
            
            # Get all latest by name
            latest_date = max(r['date'] for r in rows)
            day_rows = [r for r in rows if r['date'] == latest_date]
            
            result = {}
            for r in day_rows:
                name = r.get('name', '?')
                net = r.get('buy', 0) - r.get('sell', 0)
                result[name] = net
            
            foreign = result.get('Foreign_Investor', 0)
            trust = result.get('Investment_Trust', 0)
            dealer = result.get('Foreign_Dealer_Self', 0) + result.get('Dealer_Self', 0)
            
            print(f'{code}: F={foreign:+d} T={trust:+d} D={dealer:+d} | {latest_date}')
            
    except Exception as e:
        print(f'{code}: ERROR {e}')