import yfinance as yf

def calc_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

stocks = [
    ('D', 'Dominion Energy'), ('BMY', 'Bristol-Myers'), ('SO', 'Southern'),
    ('DXCM', 'DexCom'), ('COIN', 'Coinbase'), ('NET', 'Cloudflare'),
    ('RIVN', 'Rivian'), ('SOFI', 'SoFi'), ('SMCI', 'Super Micro'),
    ('PATH', 'UiPath'), ('GTLB', 'GitLab'), ('U', 'Unity'),
    ('BILL', 'Bill'), ('ESTC', 'Elastic'), ('GEN', 'Gen'),
    ('HOOD', 'Robinhood'), ('RKLB', 'RocketLab'), ('GDDY', 'GoDaddy'),
    ('NDAQ', 'Nasdaq'), ('FAST', 'Fastenal'), ('DLO', 'Deloitte'),
    ('SMCI', 'Super Micro'), ('SOFI', 'SoFi')
]

print("=== US Stocks Full System Health Check ===")
print(f"{'Ticker':<6} {'Name':<12} {'Price':>8} {'RSI':>5} {'Bias20':>8} {'Rev%':>7} {'PE':>5} {'Rec':>8} {'Score':>5} {'Status'}")
print("-" * 85)

results = []
for ticker, name in stocks:
    try:
        tk = yf.Ticker(ticker)
        h = tk.history(period='3mo')
        info = tk.info
        
        if len(h) >= 30:
            price = float(h['Close'].iloc[-1])
            rsi = calc_rsi(h['Close'], 14).iloc[-1]
            ma20 = h['Close'].rolling(20).mean().iloc[-1]
            ma60 = h['Close'].rolling(60).mean().iloc[-1] if len(h) >= 60 else ma20
            bias20 = (price / ma20 - 1) * 100
            
            rev_growth = info.get('revenueGrowth', 0) or 0
            pe = info.get('trailingPE', 0) or 0
            roe = info.get('returnOnEquity', 0) or 0
            rec = info.get('recommendationKey', 'none')
            
            # Score
            score = 0
            
            # Technical
            if 35 <= rsi <= 65:
                score += 2
            elif 30 <= rsi <= 70:
                score += 1
            
            # Fundamental
            if rev_growth > 0.1 and pe > 0 and pe < 35 and roe > 0.1:
                score += 2
            elif rev_growth > 0:
                score += 1
            
            # Institutional
            if rec in ['strong_buy', 'buy', 'outperform']:
                score += 2
            elif rec in ['market_perform', 'neutral']:
                score += 1
            
            # MA healthy
            if price > ma20 and ma20 > ma60:
                score += 1
            elif price > ma20:
                score += 0.5
            
            if score >= 6:
                status = "FULLY HEALTHY"
            elif score >= 4:
                status = "HEALTHY"
            elif score >= 3:
                status = "WATCH"
            else:
                status = "RISKY"
                
            results.append((ticker, name, price, rsi, bias20, rev_growth*100, pe, rec, score, status))
    except Exception as e:
        pass

results.sort(key=lambda x: -x[8])
for ticker, name, price, rsi, bias, rev, pe, rec, score, status in results:
    print(f"{ticker:<6} {name:<12} ${price:>7.2f} {rsi:>5.1f} {bias:>+7.1f}% {rev:>6.1f}% {pe:>5.1f} {rec:>8} {score:>5.1f} {status}")

print()
print("=== HEALTHY LIST (Score >= 6) ===")
healthy = [r for r in results if r[8] >= 6]
for r in healthy:
    print(f"{r[0]} {r[1]}: Price=${r[2]:.2f}, RSI={r[3]:.1f}, Rev={r[5]:.1f}%, PE={r[6]:.1f}, Rec={r[7]}, Score={r[8]:.1f}")