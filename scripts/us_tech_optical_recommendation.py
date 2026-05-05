import sqlite3
from pathlib import Path
from datetime import datetime

DB = Path('data/yfinance.db')

conn = sqlite3.connect(str(DB))
c = conn.cursor()
c.execute("""
    SELECT symbol, date, close, rsi_14, macd_hist, sma_20, sma_60, volume
    FROM daily_ohlcv
    WHERE symbol NOT LIKE '%.TW' AND symbol NOT LIKE '%.TWO'
    ORDER BY symbol, date DESC
""")
rows = c.fetchall()
conn.close()

symbols = {}
for r in rows:
    sym = r[0]
    if sym not in symbols:
        symbols[sym] = r

# Keywords for US tech + optical/comm
OPTICAL_TECH = ['AAOI', 'LRCX', 'AMAT', 'MU', 'INTC', 'AMD', 'NVDA', 'AVGO', 'MRVL', 'AVGO',
                'COHR', 'IPG', 'LITE', 'OCLR', 'PLAB', 'FORM', 'ACLS', 'EMES']
CLOUD_INTERNET = ['PLTR', 'SNOW', 'NET', 'AKAM', 'FSLR', 'ENPH', 'SPWR', 'RUN']
AI_HPC = ['MSFT', 'CRM', 'ADBE', 'NVDA', 'AMD', 'INTC', 'MU', 'AVGO', 'MRVL']

results = []
for sym, r in symbols.items():
    price = r[2]
    rsi = r[3] or 50
    macd = r[4] or 0
    sma20 = r[5] or price
    sma60 = r[6] or price

    if not price or price <= 0 or price > 10000:
        continue

    score = 0
    tags = []

    if 25 <= rsi <= 40:
        score += 35; tags.append('RSI_Entry')
    elif 40 < rsi <= 55:
        score += 20; tags.append('RSI_Low')
    elif 55 < rsi <= 65:
        score += 5; tags.append('RSI_Neutral')
    else:
        continue

    if macd > 0:
        score += 25; tags.append('MACD_Bull')
    elif macd > -0.3:
        score += 10; tags.append('MACD_NearZero')

    if sma20 > sma60:
        score += 15; tags.append('MA_Bull')

    # Optical/Telecom exposure
    if sym in OPTICAL_TECH:
        score += 10; tags.append('OPTICAL_TECH')
    elif sym in CLOUD_INTERNET:
        score += 5; tags.append('CLOUD_NET')
    elif sym in AI_HPC:
        score += 5; tags.append('AI_HPC')

    if score >= 45:
        results.append({
            'symbol': sym,
            'price': price,
            'rsi': round(rsi, 1),
            'macd': round(macd, 4),
            'sma20': round(sma20, 2),
            'sma60': round(sma60, 2),
            'score': score,
            'tags': tags,
            'ma_bull': sma20 > sma60,
            'category': 'OPTICAL' if sym in OPTICAL_TECH else ('CLOUD' if sym in CLOUD_INTERNET else 'AI_HPC')
        })

results.sort(key=lambda x: x['score'], reverse=True)

print('='*65)
print('  Tina US Tech + Optical/Comm Recommendations')
print('  ' + datetime.now().strftime('%Y-%m-%d'))
print('='*65)
print()

# Optical/Comm section
optical = [r for r in results if r['category'] == 'OPTICAL']
cloud = [r for r in results if r['category'] == 'CLOUD']
ai_hpc = [r for r in results if r['category'] == 'AI_HPC']

print('[OPTICAL/TELCOM TECH]')
if optical:
    print('%-10s %9s %5s %8s %5s %s' % ('Symbol', 'Price', 'RSI', 'MACD', 'Score', 'Tags'))
    print('-'*65)
    for r in optical:
        rsi_flag = 'G' if r['rsi'] < 40 else 'Y'
        macd_flag = 'Up' if r['macd'] > 0 else 'Dn'
        print('%s %10.2f %s(%.1f) %s(%.3f) %d %s' % (
            r['symbol'], r['price'], rsi_flag, r['rsi'],
            macd_flag, r['macd'], r['score'], ', '.join(r['tags'])))
else:
    print('  No optical/comm in acceptable range')

print()
print('[CLOUD/INTERNET INFRA]')
if cloud:
    print('%-10s %9s %5s %8s %5s %s' % ('Symbol', 'Price', 'RSI', 'MACD', 'Score', 'Tags'))
    print('-'*65)
    for r in cloud[:8]:
        rsi_flag = 'G' if r['rsi'] < 40 else 'Y'
        macd_flag = 'Up' if r['macd'] > 0 else 'Dn'
        print('%s %10.2f %s(%.1f) %s(%.3f) %d %s' % (
            r['symbol'], r['price'], rsi_flag, r['rsi'],
            macd_flag, r['macd'], r['score'], ', '.join(r['tags'])))
else:
    print('  None in acceptable range')

print()
print('[AI/HPC CHIPS]')
if ai_hpc:
    print('%-10s %9s %5s %8s %5s %s' % ('Symbol', 'Price', 'RSI', 'MACD', 'Score', 'Tags'))
    print('-'*65)
    for r in ai_hpc[:8]:
        rsi_flag = 'G' if r['rsi'] < 40 else 'Y'
        macd_flag = 'Up' if r['macd'] > 0 else 'Dn'
        print('%s %10.2f %s(%.1f) %s(%.3f) %d %s' % (
            r['symbol'], r['price'], rsi_flag, r['rsi'],
            macd_flag, r['macd'], r['score'], ', '.join(r['tags'])))
else:
    print('  None in acceptable range')

print()
print('='*65)
print('[Summary]')
buys = [r for r in results if r['score'] >= 60]
watches = [r for r in results if 45 <= r['score'] < 60]
if buys:
    print('BUY: %s' % ', '.join(r['symbol'] for r in buys))
if watches:
    print('WATCH: %s' % ', '.join(r['symbol'] for r in watches[:8]))