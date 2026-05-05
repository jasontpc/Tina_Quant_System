import yfinance as yf

stocks = [
    ('D', 'Dominion Energy'),
    ('BMY', 'Bristol-Myers'),
    ('SO', 'Southern Company'),
    ('DXCM', 'DexCom'),
    ('SMCI', 'Super Micro'),
    ('RIVN', 'Rivian'),
    ('SOFI', 'SoFi'),
    ('PATH', 'UiPath'),
    ('GTLB', 'GitLab'),
    ('U', 'Unity Software'),
    ('BILL', 'Bill Holdings'),
    ('ESTC', 'Elastic'),
    ('COIN', 'Coinbase'),
    ('NET', 'Cloudflare')
]

print("=== US Stocks Watchlist (May 1 Close) ===")
print(f"{'Ticker':<8} {'Price':>8} {'Day%':>8} {'RSI':>6} {'Mcap(B)':>10} {'DivYld':>8}")
print("-" * 58)
for ticker, name in stocks:
    try:
        t = yf.Ticker(ticker)
        h = t.history(period='5d')
        if len(h) >= 2:
            curr = float(h['Close'].iloc[-1])
            prev = float(h['Close'].iloc[-2])
            chg = (curr - prev) / prev * 100
            info = t.info
            rsi = info.get('rsi', 50) or 50
            mktcap = info.get('marketCap', 0) / 1e9
            div = info.get('dividendYield', 0) or 0
            print(f"{ticker:<8} ${curr:>7.2f} {chg:>+7.2f}% {rsi:>6.1f} {mktcap:>10.1f} {div*100:>7.2f}%")
    except:
        print(f"{ticker:<8} error")