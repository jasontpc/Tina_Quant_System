import requests

token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjF9.ivums9mfJUrM2MYazJiOEg49RiYLOJMZtejqX79YWS8'
base = 'https://api.finmindtrade.com/api/v4/data'

print('='*60)
print('INSTITUTIONAL FLOW - 法人資金流向')
print('='*60)

stocks = [
    ('2330', '台積電'),
    ('2382', '廣達'),
    ('2317', '鴻海'),
    ('3231', '緯創'),
    ('2881', '富邦金'),
    ('2883', '凱基金'),
]

for stock_id, name in stocks:
    params = {
        'dataset': 'TaiwanStockInstitutionalInvestorsBuySell',
        'data_id': stock_id,
        'start_date': '2026-04-25',
        'end_date': '2026-05-02',
        'token': token
    }
    
    try:
        resp = requests.get(base, params=params, timeout=10)
        data = resp.json()
        
        if 'data' not in data or len(data['data']) == 0:
            print(f'{name} ({stock_id}): No data')
            continue
        
        records = data['data']
        records.sort(key=lambda x: x['date'])
        
        # 依 name 分組
        by_name = {}
        for r in records:
            n = r.get('name', 'Unknown')
            if n not in by_name:
                by_name[n] = {'buy': 0, 'sell': 0}
            by_name[n]['buy'] += int(r.get('buy', 0) or 0)
            by_name[n]['sell'] += int(r.get('sell', 0) or 0)
        
        # 近5日
        recent = [r for r in records if r['date'] >= '2026-04-25']
        
        # 找出主要法人
        foreign_buy = foreign_sell = 0
        trust_buy = trust_sell = 0
        dealer_buy = dealer_sell = 0
        
        for r in recent:
            n = r.get('name', '')
            if 'Foreign' in n:
                foreign_buy += int(r.get('buy', 0) or 0)
                foreign_sell += int(r.get('sell', 0) or 0)
            elif 'Investment' in n or 'Trust' in n:
                trust_buy += int(r.get('buy', 0) or 0)
                trust_sell += int(r.get('sell', 0) or 0)
            elif 'Dealer' in n or 'Self' in n:
                dealer_buy += int(r.get('buy', 0) or 0)
                dealer_sell += int(r.get('sell', 0) or 0)
        
        total_foreign = foreign_buy - foreign_sell
        total_trust = trust_buy - trust_sell
        total_dealer = dealer_buy - dealer_sell
        
        print(f'\n{name} ({stock_id})')
        print(f'  外資: {total_foreign:+,} 張 ({">>>" if total_foreign > 0 else "<<<" if total_foreign < 0 else "---"})')
        print(f'  投信: {total_trust:+,} 張 ({">>>" if total_trust > 0 else "<<<" if total_trust < 0 else "---"})')
        print(f'  自營: {total_dealer:+,} 張 ({">>>" if total_dealer > 0 else "<<<" if total_dealer < 0 else "---"})')
        
        total = total_foreign + total_trust + total_dealer
        sentiment = 'BUY' if total > 0 else 'SELL' if total < 0 else 'NEUTRAL'
        print(f'  合計: {total:+,} 張 [{sentiment}]')
        
    except Exception as e:
        print(f'{name} ({stock_id}): Error - {e}')

print()
print('='*60)
print('Market Status: TW RSI 79.9 - OVERHEATED')
print('All systems on standby')
print('Wait for pullback before entry')