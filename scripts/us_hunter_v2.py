import yfinance as yf

print('='*80)
print('US 主動獵人模式 v2.0 | 2026-05-08 22:06')
print('='*80)
print()

# Jo's portfolio + scan candidates
tickers = ['NVDA', 'AMD', 'AVGO', 'TSLA', 'META', 'MSFT', 'AAPL', 'AMZN', 
           'GOOGL', 'COIN', 'APP', 'ARM', 'PLTR', 'CRWD', 'SNOW', 'DDOG']

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
        eps = info.get('trailingEps', 0)
        mktcap = info.get('marketCap', 0)
        rec = info.get('recommendationKey', 'N/A')
        target = info.get('targetMeanPrice', 0)
        rec_count = info.get('numberOfAnalystOpinions', 0) or 0
        
        if not curr or not high52:
            continue
        
        dist_high = (curr - high52) / high52 * 100
        dist_low = (curr - low52) / low52 * 100
        
        # Calculate RSI (14-day from history)
        try:
            hist = t.history(period='1mo')
            if len(hist) >= 14:
                delta = hist['Close'].diff()
                gain = delta.where(delta > 0, 0).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs)).iloc[-1]
            else:
                rsi = 50
        except:
            rsi = 50
        
        # Score calculation
        score = 0
        reasons = []
        
        # RSI gate
        if 40 <= rsi <= 70:
            score += 25
            reasons.append('RSI健康' + str(int(rsi)))
        elif rsi < 40:
            score += 15
            reasons.append('RSI超賣' + str(int(rsi)))
        elif rsi > 90:
            score -= 30
            reasons.append('RSI過熱' + str(int(rsi)))
        else:
            score += 5
            reasons.append('RSI中性' + str(int(rsi)))
        
        # Distance from 52W high
        if -40 <= dist_high <= -10:
            score += 20
            reasons.append('回調' + str(int(dist_high)) + '%')
        elif dist_high < -40:
            score += 15
            reasons.append('超跌' + str(int(dist_high)) + '%')
        elif dist_high > -10:
            score += 5
            reasons.append('接近高點' + str(int(dist_high)) + '%')
        
        # PE valuation
        if pe and pe < 40:
            score += 15
            reasons.append('PE低' + str(int(pe)))
        elif pe and pe < 60:
            score += 10
            reasons.append('PE中' + str(int(pe)))
        elif pe and pe > 100:
            score -= 20
            reasons.append('PE過高' + str(int(pe)))
        
        # Analyst rating
        if rec in ['strong_buy', 'outperform']:
            score += 10
            reasons.append('分析師買進')
        elif rec == 'buy':
            score += 5
            reasons.append('分析師持有')
        
        # Target price upside
        if target and curr:
            upside = (target - curr) / curr * 100
            if upside > 25:
                score += 15
                reasons.append('目標+' + str(int(upside)) + '%')
            elif upside > 15:
                score += 10
                reasons.append('目標+' + str(int(upside)) + '%')
            elif upside < 5:
                score -= 10
                reasons.append('目標+' + str(int(upside)) + '%')
        
        # Volume confirmation
        try:
            hist5d = t.history(period='5d')
            if len(hist5d) >= 5:
                avg_vol = hist5d['Volume'].mean()
                today_vol = hist5d['Volume'].iloc[-1]
                if today_vol > avg_vol * 1.5:
                    score += 10
                    reasons.append('放量')
        except:
            pass
        
        results.append({
            'sym': sym,
            'price': curr,
            'chg': chg_pct,
            'rsi': rsi,
            'dist_high': dist_high,
            'pe': pe,
            'target_up': (target - curr) / curr * 100 if target and curr else 0,
            'rec': rec,
            'cap': mktcap,
            'score': score,
            'reasons': reasons
        })
        
    except Exception as e:
        print('Error ' + sym + ': ' + str(e))

# Sort by score descending
results.sort(key=lambda x: x['score'], reverse=True)

# Print header
print('{:6} {:>8} {:>6} {:>5} {:>6} {:>5} {:>6} {:>5} {}'.format(
    '標的', '現價', '今日', 'RSI', '距高', 'PE', '目標', '評分', '原因'))
print('-'*80)

for r in results:
    price_str = '${:.2f}'.format(r['price'])
    chg_str = '{:+.1f}%'.format(r['chg'])
    rsi_str = '{:.0f}'.format(r['rsi']) if r['rsi'] else 'N/A'
    dist_str = '{:+.0f}%'.format(r['dist_high'])
    pe_str = '{:.0f}'.format(r['pe']) if r['pe'] else 'N/A'
    target_str = '{:+.0f}%'.format(r['target_up']) if r['target_up'] else 'N/A'
    score_str = '{:.0f}'.format(r['score'])
    reasons_str = ' | '.join(r['reasons'][:3]) if r['reasons'] else ''
    
    print('{:<6} {:>8} {:>6} {:>5} {:>6} {:>5} {:>6} {:>5} {}'.format(
        r['sym'], price_str, chg_str, rsi_str, dist_str, pe_str, target_str, score_str, reasons_str))

print()
print('='*80)
print('篩選：RSI 40-70(健康) + 回調-40%~-10% + PE<60 + 分析師買進 + 目標+15%')
print('評分70+ = APPROVE | 50-69 = CAUTION | <50 = REJECT')
print('='*80)
print()

# Show top picks
print('=== 獵人精選（評分>=60）===')
for r in results:
    if r['score'] >= 60:
        verdict = 'APPROVE' if r['score'] >= 70 else 'CAUTION'
        reasons_line = ' | '.join(r['reasons'][:4])
        print(verdict + ' ' + r['sym'] + ': ' + str(r['score']) + '分 | ' + reasons_line)

print()
print('=== Jo 持倉評估 ===')
jo_holdings = ['APP', 'AMAT', 'META', 'MSFT']
for sym in jo_holdings:
    for r in results:
        if r['sym'] == sym:
            status = 'OK' if r['rsi'] < 70 and r['dist_high'] > -40 else 'WATCH'
            print(sym + ': $' + '{:.2f}'.format(r['price']) + ' (' + '{:+.1f}%'.format(r['chg']) + ') | RSI=' + '{:.0f}'.format(r['rsi']) + ' | 距高' + '{:+.0f}%'.format(r['dist_high']) + ' | ' + status)
            break

print()
print('=== 禁止進場 ===')
for r in results:
    if r['rsi'] > 90 or r['score'] < 0:
        print('REJECT ' + r['sym'] + ': RSI=' + '{:.0f}'.format(r['rsi']) + ' score=' + str(r['score']))