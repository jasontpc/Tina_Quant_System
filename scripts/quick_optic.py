import requests, sqlite3, pandas as pd, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

DB = Path('data/yfinance.db')
TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSJ9.oCdQO1qNRUCYxHZSVuRQCqlF7X2DbQ77wury5ARCKzM'
BASE = 'https://api.finmindtrade.com/api/v4/data'

SYMS = [('3081','聯亞'), ('6442','光聖'), ('4979','華星光'), ('4971','IET-KY')]

for sid, name in SYMS:
    params = {'dataset':'TaiwanStockPrice','data_id':sid,'start_date':'2026-01-01','end_date':'2026-05-03','token':TOKEN}
    try:
        r = requests.get(BASE, params=params, timeout=15)
        d = r.json()
        if d.get('status') != 200 or not d.get('data'):
            print(f'{sid} no data'); continue
        rows = d['data']
        prices = [float(x['close']) for x in rows]
        dates = [x['date'] for x in rows]
        volumes = [int(x['Trading_Volume']) for x in rows]
        high_v = [float(x['max']) for x in rows]
        low_v = [float(x['min']) for x in rows]

        close = pd.Series(prices)
        delta = close.diff()
        gain = delta.clip(lower=0).ewm(com=13, adjust=False).mean()
        loss = (-delta.clip(upper=0)).ewm(com=13, adjust=False).mean()
        rsi_v = float(100-(100/(1+gain/loss)).iloc[-1])
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd_l = ema12-ema26
        macd_s = macd_l.ewm(span=9, adjust=False).mean()
        macd_v = float((macd_l-macd_s).iloc[-1])

        tr_list = []
        for i in range(len(prices)):
            h = high_v[i]; l = low_v[i]; c = prices[i]
            prev_c = prices[i-1] if i > 0 else c
            tr_list.append(max(h-l, abs(h-prev_c), abs(l-prev_c)))
        tr_s = pd.Series(tr_list).ewm(com=14, adjust=False).mean()
        atr = float(tr_s.iloc[-1])
        price = prices[-1]
        sma20_series = close.ewm(span=20, adjust=False).mean()
        s20 = float(sma20_series.iloc[-1])

        rsi_tag = '🟢進場區' if 40<=rsi_v<=50 else ('🔵偏多' if rsi_v<60 else '🔴過熱')
        macd_tag = '🟢多頭' if macd_v>0 else '🔴空頭'
        arrow = '▲' if price>s20 else '▼'

        high52 = max(high_v)
        low52 = min(low_v)

        print('='*60)
        print(f'  {sid}.TW {name}')
        print('='*60)
        print(f'  現價:   ${price:.2f}')
        print(f'  RSI:    {rsi_v:.1f}  {rsi_tag}')
        print(f'  MACD:   {macd_v:+.2f}  {macd_tag}')
        print(f'  SMA20:  ${s20:.2f}  price {arrow}')
        print(f'  ATR:    ${atr:.2f} ({atr/price*100:.1f}%)')
        print(f'  52w高:  ${high52:.2f} ({((price-high52)/high52)*100:+.1f}%)')
        print(f'  52w低:  ${low52:.2f} ({((price-low52)/low52)*100:+.1f}%)')
        print()
    except Exception as e:
        print(f'{sid} ERR {e}')