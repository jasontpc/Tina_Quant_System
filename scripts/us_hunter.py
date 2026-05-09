import yfinance as yf

print('='*75)
print('US 主動獵人模式 | 2026-05-08 21:53')
print('='*75)
print()

# 美股熱門掃描清單
tickers = ['NVDA', 'AMD', 'AVGO', 'TSLA', 'META', 'MSFT', 'AAPL', 'AMZN', 'GOOGL', 'COIN', 'APP', 'ARM', 'PLTR']

results = []

for sym in tickers:
    try:
        t = yf.Ticker(sym)
        info = t.info
        
        curr = info.get('currentPrice', 0)
        chg_pct = info.get('regularMarketChangePercent', 0)
        high52 = info.get('fiftyTwoWeekHigh', 0)
        low52 = info.get('fiftyTwoWeekLow', 0)
        pe = info.get('trailingPE', 0)
        mktcap = info.get('marketCap', 0)
        rec = info.get('recommendationKey', 'N/A')
        
        if curr and high52:
            dist_from_high = (curr - high52) / high52 * 100
            
            results.append({
                'sym': sym,
                'price': curr,
                'chg': chg_pct,
                'dist_high': dist_from_high,
                'pe': pe,
                'rec': rec,
                'cap': mktcap
            })
    except Exception as e:
        print(f'{sym}: error - {e}')

# 排序：今日漲幅
results.sort(key=lambda x: x['chg'], reverse=True)

print(f'{"標的":<6} {"現價":>8} {"今日":>7} {"距高點":>7} {"PE":>6} {"建議":<12} {"市值"}')
print('-'*75)

for r in results:
    price_str = '${:.2f}'.format(r['price'])
    chg_str = '{:+.2%}'.format(r['chg'])
    dist_str = '{:+.1f}%'.format(r['dist_high'])
    pe_str = '{:.1f}'.format(r['pe']) if r['pe'] else 'N/A'
    rec_str = r['rec'][:12]
    cap_str = '${:.0f}B'.format(r['cap']/1e9) if r['cap'] else 'N/A'
    
    # 標記警示
    flag = ''
    if r['chg'] > 3:
        flag = ' [領漲]'
    elif r['chg'] < -3:
        flag = ' [領跌]'
    elif r['dist_high'] > -10:
        flag = ' [near high]'
    elif r['dist_high'] < -40:
        flag = ' [deep cut]'
    
    print(f'{r["sym"]:<6} {price_str:>8} {chg_str:>7} {dist_str:>7} {pe_str:>6} {rec_str:<12} {cap_str}{flag}')

print()
print('=== 獵人篩選條件 ===')
print('1. 今日漲幅 > 3% [領漲]')
print('2. 距離高點 < -10% [反彈潛力]')
print('3. PE < 50 [合理估值]')
print('4. Recommendation: buy/strong_buy')
print()
print('=== 符合條件（滿足2項以上）===')

for r in results:
    cond1 = r['chg'] > 3
    cond2 = r['dist_high'] < -10
    cond3 = r['pe'] and r['pe'] < 50
    cond4 = r['rec'] in ['buy', 'strong_buy', 'outperform']
    
    matches = sum([cond1, cond2, cond3, cond4])
    if matches >= 2:
        badges = []
        if cond1: badges.append('領漲')
        if cond2: badges.append('深跌')
        if cond3: badges.append('低PE')
        if cond4: badges.append('買進')
        print(f'  {r["sym"]}: {" | ".join(badges)}')

print()
print('=== Jo 持倉 ===')
jo_holdings = ['APP', 'AMAT', 'META', 'MSFT']
for sym in jo_holdings:
    for r in results:
        if r['sym'] == sym:
            chg_str = '{:+.2%}'.format(r['chg'])
            print(f'  {sym}: ${r["price"]:.2f} ({chg_str})')
            break