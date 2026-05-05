import yfinance as yf, pandas as pd, sys, requests
sys.stdout.reconfigure(encoding='utf-8')

TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSJ9.oCdQO1qNRUCYxHZSVuRQCqlF7X2DbQ77wury5ARCKzM'
BASE = 'https://api.finmindtrade.com/api/v4/data'

TW_CPO = [
    ('2330','台積電'),('2303','聯電'),('3081','聯亞'),('2455','全新'),('3105','穩懋'),
    ('3163','波若威'),('6442','光聖'),('3363','上詮'),
    ('4979','華星光'),('4908','前鼎'),('4977','眾達-KY'),('2489','瑞軒'),
    ('6223','旺矽'),('6515','穎崴'),('2360','致茂'),('2499','京元電'),('6830','沅銓'),('6706','惠特'),
    ('2345','智邦'),('3665','贸聯-KY'),('6715','嘉基'),('3533','嘉澤'),
    ('6451','訊芯-KY'),('3711','日月光'),('3450','聯鈞'),('3265','台星科'),
]
US_CPO = [('AVGO','博通'),('NVDA','英偉達'),('MRVL','邁威爾'),('COHR','Coherent'),('LITE','Lumentum'),('CSCO','思科'),('META','Meta'),('MSFT','微軟'),('GOOGL','谷歌')]

def compute_indicators(prices, high_v=None, low_v=None):
    close = pd.Series(prices)
    rsi_s = 100-(100/(1+(close.diff().clip(lower=0).ewm(com=13,adjust=False).mean()/(-close.diff().clip(upper=0)).ewm(com=13,adjust=False).mean())))
    rsi_v = float(rsi_s.iloc[-1])
    ema12 = close.ewm(span=12,adjust=False).mean()
    ema26 = close.ewm(span=26,adjust=False).mean()
    macd_l = ema12-ema26
    macd_s = macd_l.ewm(span=9,adjust=False).mean()
    macd_v = float((macd_l-macd_s).iloc[-1])
    if high_v and low_v:
        tr = pd.Series([max(high_v[i]-low_v[i], abs(high_v[i]-prices[i-1]) if i>0 else 0, abs(low_v[i]-prices[i-1]) if i>0 else 0) for i in range(len(prices))]).ewm(com=14,adjust=False).mean()
        atr = float(tr.iloc[-1])
    else:
        atr = 0
    price = prices[-1]
    return price, rsi_v, macd_v, atr, max(high_v) if high_v else 0, min(low_v) if low_v else 0

print('='*70)
print('  CPO 產業鏈 35 檔完整分析（台股+美股）')
print('='*70)

# TW
print()
print('[台股 CPO - 26 檔]')
print('%-8s %-8s %7s %5s %7s %5s %+7s' % ('Symbol','Name','Price','RSI','MACD','ATR%','Dist'))
print('-'*70)
candidates = []
for sid, name in TW_CPO:
    params = {'dataset':'TaiwanStockPrice','data_id':sid,'start_date':'2026-04-01','end_date':'2026-05-03','token':TOKEN}
    try:
        r = requests.get(BASE, params=params, timeout=10)
        d = r.json()
        if d.get('status') != 200 or not d.get('data'): continue
        rows = d['data']
        prices = [float(x['close']) for x in rows]
        high_v = [float(x['max']) for x in rows]
        low_v = [float(x['min']) for x in rows]
        price, rsi_v, macd_v, atr, high52, low52 = compute_indicators(prices, high_v, low_v)
        rsi_t = '🟢' if 40<=rsi_v<=50 else ('🔵' if rsi_v<60 else '🔴')
        macd_t = '🟢' if macd_v>0 else '🔴'
        score = (30 if 35<=rsi_v<=50 else 15 if rsi_v<40 else 0) + (25 if macd_v>0 else 0)
        dist = (price-high52)/high52*100
        print(f'{sid}.TW {name:6s} ${price:8.0f} {rsi_v:5.1f}{rsi_t} {macd_v:+7.2f}{macd_t} {atr/price*100:5.1f}% {dist:+6.1f}%')
        if score >= 30:
            candidates.append((score, sid+'.TW', name, price, rsi_v, macd_v, dist))
    except: pass

# US
print()
print('[美股 CPO - 9 檔]')
print('%-8s %-8s %7s %5s %7s %5s %+7s' % ('Symbol','Name','Price','RSI','MACD','ATR%','Dist'))
print('-'*70)
for sym, name in US_CPO:
    try:
        tk = yf.Ticker(sym)
        h = tk.history(period='3mo')
        if len(h) < 20: continue
        closes = h['Close'].tolist()
        highs = h['High'].tolist()
        lows = h['Low'].tolist()
        price, rsi_v, macd_v, atr, high52, low52 = compute_indicators(closes, highs, lows)
        rsi_t = '🟢' if 40<=rsi_v<=50 else ('🔵' if rsi_v<60 else '🔴')
        macd_t = '🟢' if macd_v>0 else '🔴'
        score = (30 if 35<=rsi_v<=50 else 15 if rsi_v<40 else 0) + (25 if macd_v>0 else 0)
        dist = (price-high52)/high52*100
        print(f'{sym:8s} {name:8s} ${price:8.2f} {rsi_v:5.1f}{rsi_t} {macd_v:+7.2f}{macd_t} {atr/price*100:5.1f}% {dist:+6.1f}%')
        if score >= 30:
            candidates.append((score, sym, name, price, rsi_v, macd_v, dist))
    except: pass

print()
print('='*70)
print('  Score >= 30 候選（進場區 + 多頭）')
print('='*70)
candidates.sort(key=lambda x: -x[0])
for score, sym, name, price, rsi_v, macd_v, dist in candidates:
    rsi_t = '🟢' if 40<=rsi_v<=50 else ('🔵' if rsi_v<60 else '🔴')
    macd_t = '🟢' if macd_v>0 else '🔴'
    print(f'  Score={score} {sym} {name} ${price:.2f} RSI={rsi_v:.1f}{rsi_t} MACD={macd_v:+.2f}{macd_t}')