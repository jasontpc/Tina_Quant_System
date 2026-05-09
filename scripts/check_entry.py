import sqlite3
db = '../data/yfinance.db'
conn = sqlite3.connect(db)
c = conn.cursor()
syms = ['META','NVDA','AMD','AVGO','PLTR','AAPL','TSM','LITE','SEDG','NUGT','COHR',
        'WDC','SMCI','DELL','2330.TW','0050.TW','6223.TW','3363.TW','6442.TW',
        '2360.TW','4979.TW','3163.TW','2376.TW','2357.TW','5289.TW','3260.TW']
cutoff = '2026-05-08'
print('SYMBOL           DATE        CLOSE      RSI    MA20    MA60  TREND  ZONE')
print('-'*88)
for s in syms:
    c.execute('SELECT date,close,rsi_14,sma_20,sma_60 FROM daily_ohlcv WHERE symbol=? AND date<=? ORDER BY date DESC LIMIT 1', (s, cutoff))
    row = c.fetchone()
    if row and row[2] and row[3] and row[4]:
        d,cl,r,m20,m60 = row
        trend = 'BULL' if m20>m60*1.02 else 'bull' if m20>m60 else 'BEAR'
        zone = 'OK' if m20>m60 and r<70 else 'RSI_H' if r>=70 else 'BEAR'
        print(f'{s:<15} {d[:10]} {cl:>9.2f} {r:>6.1f} {m20:>8.2f} {m60:>8.2f}  {trend}  {zone}')
conn.close()