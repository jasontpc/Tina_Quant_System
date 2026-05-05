import yfinance as yf
import json

def calc_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def analyze_stock(ticker, name, market='US'):
    try:
        if market == 'TW':
            tk = yf.Ticker(ticker + '.TW')
            suffix = '.TW'
        else:
            tk = yf.Ticker(ticker)
            suffix = ''
        
        h = tk.history(period='3mo')
        info = tk.info
        
        if len(h) < 30:
            return None
        
        price = float(h['Close'].iloc[-1])
        rsi = calc_rsi(h['Close'], 14).iloc[-1]
        ma20 = h['Close'].rolling(20).mean().iloc[-1]
        ma60 = h['Close'].rolling(60).mean().iloc[-1] if len(h) >= 60 else ma20
        bias20 = (price / ma20 - 1) * 100
        ret_1m = (price / float(h['Close'].iloc[-20]) - 1) * 100 if len(h) >= 20 else 0
        ret_3m = (price / float(h['Close'].iloc[0]) - 1) * 100
        
        vol = h['Volume'].iloc[-1]
        vol_avg = h['Volume'].rolling(20).mean().iloc[-1]
        vol_ratio = vol / vol_avg if vol_avg > 0 else 0
        
        pe = info.get('trailingPE', 0) or 0
        roe = info.get('returnOnEquity', 0) or 0
        rev_growth = info.get('revenueGrowth', 0) or 0
        div = info.get('dividendYield', 0) or 0
        mktcap = info.get('marketCap', 0) / 1e9
        
        # Entry conditions check
        if price > ma20 and ma20 > ma60:
            ma_status = '多頭排列'
        elif price > ma20:
            ma_status = 'MA20上方'
        else:
            ma_status = '偏弱'
        
        # Score
        score = 0
        tech_score = 0
        if 35 <= rsi <= 65: tech_score = 2
        elif 30 <= rsi <= 70: tech_score = 1
        if bias20 <= 8: tech_score += 1
        if price > ma20: tech_score += 1
        
        fund_score = 0
        if rev_growth > 0.1: fund_score = 2
        elif rev_growth > 0: fund_score = 1
        if pe > 0 and pe < 30: fund_score += 1
        if roe > 0.1: fund_score += 1
        
        rec = info.get('recommendationKey', 'none')
        inst_score = 2 if rec in ['strong_buy', 'buy', 'outperform'] else (1 if rec in ['hold', 'neutral'] else 0)
        
        total = tech_score + fund_score + inst_score
        
        return {
            'ticker': ticker,
            'name': name,
            'market': market,
            'price': price,
            'rsi': rsi,
            'bias20': bias20,
            'ma_status': ma_status,
            'ret_1m': ret_1m,
            'ret_3m': ret_3m,
            'vol_ratio': vol_ratio,
            'pe': pe,
            'roe': roe * 100 if roe else 0,
            'rev_growth': rev_growth * 100 if rev_growth else 0,
            'div': div * 100 if div else 0,
            'mktcap': mktcap,
            'rec': rec,
            'tech_score': tech_score,
            'fund_score': fund_score,
            'inst_score': inst_score,
            'total': total
        }
    except Exception as e:
        return {'ticker': ticker, 'name': name, 'error': str(e)}

stocks = [
    ('2855', '統一證', 'TW'),
    ('2891', 'CTBC金控', 'TW'),
    ('DLO', 'Deloitte', 'US'),
    ('2884', '玉山金控', 'TW'),
    ('2883', '中信金控', 'TW'),
    ('GEN', 'Gen', 'US'),
    ('RKLB', 'RocketLab', 'US'),
    ('2886', '兆豐金控', 'TW'),
    ('DXCM', 'DexCom', 'US'),
    ('2881', '富邦金控', 'TW')
]

print('=' * 80)
print('TOP 10 百元內健康個股逐項分析')
print('=' * 80)

results = []
for ticker, name, market in stocks:
    r = analyze_stock(ticker, name, market)
    if r:
        results.append(r)
        print(f"\n{'='*60}")
        print(f"#{len(results)}. {ticker} {name} ({market})")
        print(f"{'='*60}")
        print(f"價格: ${r['price']:.2f}" if market == 'US' else f"價格: TWD {r['price']:.2f}")
        print(f"RSI(14): {r['rsi']:.1f}")
        print(f"MA20: ${r['bias20']:+.2f}% Bias20")
        print(f"均線: {r['ma_status']}")
        print(f"1M動能: {r['ret_1m']:+.2f}%")
        print(f"3M動能: {r['ret_3m']:+.2f}%")
        print(f"成交量比: {r['vol_ratio']:.2f}x")
        print()
        print(f"PE: {r['pe']:.1f}")
        print(f"ROE: {r['roe']:.2f}%")
        print(f"營收成長: {r['rev_growth']:.1f}%")
        print(f"殖利率: {r['div']:.2f}%")
        print(f"市值: ${r['mktcap']:.1f}B" if market == 'US' else f"市值: ${r['mktcap']:.0f}B")
        print(f"法人評級: {r['rec']}")
        print()
        print(f"技術面分數: {r['tech_score']}/5 | 基本面分數: {r['fund_score']}/5 | 資金面分數: {r['inst_score']}/2")
        print(f"總分: {r['total']}/12")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
results.sort(key=lambda x: -x['total'])
for i, r in enumerate(results):
    market = 'TW' if r['market'] == 'TW' else 'US'
    print(f"{i+1}. {r['ticker']} {r['name']} ({market}): RSI={r['rsi']:.1f}, 營收={r['rev_growth']:.1f}%, 總分={r['total']}/12")