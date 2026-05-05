import requests, pandas as pd, sys
sys.stdout.reconfigure(encoding='utf-8')
TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSJ9.oCdQO1qNRUCYxHZSVuRQCqlF7X2DbQ77wury5ARCKzM'
BASE = 'https://api.finmindtrade.com/api/v4/data'

SYMS = [('2330','台積電'),('2303','聯電'),('6515','穎崴'),('2360','致茂'),('3533','嘉澤')]

for sid, name in SYMS:
    params = {'dataset':'TaiwanStockPrice','data_id':sid,'start_date':'2026-02-01','end_date':'2026-05-03','token':TOKEN}
    r = requests.get(BASE, params=params, timeout=10)
    d = r.json()
    if d.get('status') != 200: continue
    rows = d['data']
    prices = [float(x['close']) for x in rows]
    opens = [float(x['open']) for x in rows]
    highs = [float(x['max']) for x in rows]
    lows = [float(x['min']) for x in rows]
    vols = [int(x['Trading_Volume']) for x in rows]
    dates = [x['date'] for x in rows]

    close = pd.Series(prices)
    high52 = max(highs)
    low52 = min(lows)
    recent_high = max(prices[-20:])
    recent_low = min(prices[-20:])

    delta = close.diff()
    gain = delta.clip(lower=0).ewm(com=13, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(com=13, adjust=False).mean()
    rsi = 100-(100/(1+gain/loss))
    rsi_v = float(rsi.iloc[-1])

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_l = ema12-ema26
    macd_s = macd_l.ewm(span=9, adjust=False).mean()
    macd_v = float((macd_l-macd_s).iloc[-1])

    tr_list = []
    for i in range(len(prices)):
        h=highs[i]; l=lows[i]; c=prices[i]
        prev_c = prices[i-1] if i>0 else c
        tr_list.append(max(h-l, abs(h-prev_c), abs(l-prev_c)))
    atr = float(pd.Series(tr_list).ewm(com=14, adjust=False).mean().iloc[-1])
    sma20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1])
    sma60 = float(close.ewm(span=60, adjust=False).mean().iloc[-1])

    avg_vol = sum(vols[-20:])/20
    last_vol = vols[-1]
    vol_ratio = last_vol/avg_vol if avg_vol > 0 else 0
    price = prices[-1]

    rsi_tag = 'RSI進場區' if 40<=rsi_v<=50 else ('偏多' if rsi_v<60 else '過熱')
    macd_tag = '多頭' if macd_v>0 else '空頭'
    price_pos = '▲' if price>sma20 else '▼'

    sl = price * 0.92
    tp1 = price * 1.05
    tp2 = price * 1.08
    rrr = (tp1-sl)/(price-sl)

    shares = int(2500000 * 0.02 / (price * 0.08))
    risk = shares * price * 0.08

    print('='*65)
    print(f'  {sid}.TW {name}')
    print('='*65)
    print(f'  現價:        ${price:.2f}')
    print(f'  52w High:    ${high52:.2f}  ({((price-high52)/high52)*100:+.1f}%)')
    print(f'  52w Low:     ${low52:.2f}  ({((price-low52)/low52)*100:+.1f}%)')
    print(f'  20d Range:   ${recent_low:.2f} ~ ${recent_high:.2f}')
    print()
    print(f'  RSI(14):    {rsi_v:.1f}  {rsi_tag}')
    print(f'  MACD hist:  {macd_v:+.2f}  {macd_tag}')
    print(f'  SMA20:      ${sma20:.2f}  {price_pos}')
    print(f'  SMA60:      ${sma60:.2f}')
    print(f'  ATR:        ${atr:.2f} ({atr/price*100:.1f}%)')
    print(f'  量能比:      {vol_ratio:.2f}x')
    print()
    print(f'  進場區間:   ${price:.2f}')
    print(f'  停損:       ${sl:.2f} (-8%)')
    print(f'  第一目標:   ${tp1:.2f} (+5%)')
    print(f'  第二目標:   ${tp2:.2f} (+8%)')
    print(f'  RRR:        {rrr:.1f}')
    print()
    print(f'  建議股數:   {shares} 股')
    print(f'  風險敞口:   ${risk:,.0f}')
    print()