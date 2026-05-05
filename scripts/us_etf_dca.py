import sqlite3
from pathlib import Path

DB = Path('data/yfinance.db')
conn = sqlite3.connect(str(DB))
c = conn.cursor()
c.execute("""
    SELECT symbol, date, close, rsi_14, macd_hist, sma_20, sma_60 
    FROM daily_ohlcv 
    WHERE symbol IN ('VTI','IWM','QQQ','SPY','BND','TLT','GLD','SLV','VOO','VEA','VWO','AGG','SCHZ','TIP')
    ORDER BY symbol, date DESC
""")
rows = c.fetchall()
conn.close()

etfs = {}
for r in rows:
    sym = r[0]
    if sym not in etfs:
        etfs[sym] = r

print('='*65)
print('  Tina US ETF DCA Recommendations')
print('='*65)
print()

# Equity ETFs
equity = ['VTI', 'IWM', 'QQQ', 'SPY', 'VOO']
# Bond ETFs
bonds = ['BND', 'TLT', 'AGG', 'SCHZ', 'TIP']
# Metal ETFs
metals = ['GLD', 'SLV']
# International
intl = ['VEA', 'VWO']

print('[US Equity ETFs]')
for sym in equity:
    if sym not in etfs:
        print('  %s: NO DATA' % sym)
        continue
    r = etfs[sym]
    price = r[2]
    rsi = r[3] or 50
    macd = r[4] or 0
    sma20 = r[5] or price
    sma60 = r[6] or price
    ma_bull = sma20 > sma60 if sma20 and sma60 else False

    if rsi < 30:
        grade = 'EXCELLENT'
    elif rsi < 40:
        grade = 'GOOD'
    elif rsi < 55:
        grade = 'FAIR'
    else:
        grade = 'EXPENSIVE'

    rsi_icon = 'G' if rsi < 40 else ('Y' if rsi < 55 else 'R')
    macd_icon = 'Up' if macd > 0 else 'Dn'
    ma_icon = 'Bull' if ma_bull else 'Bear'
    print('  %s $%.2f | RSI=%s(%.1f) | MACD=%s | MA=%s | DCA=%s' % (
        sym, price, rsi_icon, rsi, macd_icon, ma_icon, grade))

print()
print('[Bond ETFs]')
for sym in bonds:
    if sym not in etfs:
        print('  %s: NO DATA' % sym)
        continue
    r = etfs[sym]
    price = r[2]
    rsi = r[3] or 50
    macd = r[4] or 0

    if rsi < 30:
        grade = 'EXCELLENT'
    elif rsi < 40:
        grade = 'GOOD'
    elif rsi < 55:
        grade = 'FAIR'
    else:
        grade = 'EXPENSIVE'

    rsi_icon = 'G' if rsi < 40 else ('Y' if rsi < 55 else 'R')
    print('  %s $%.2f | RSI=%s(%.1f) | DCA=%s' % (sym, price, rsi_icon, rsi, grade))

print()
print('[Metal ETFs]')
for sym in metals:
    if sym not in etfs:
        print('  %s: NO DATA' % sym)
        continue
    r = etfs[sym]
    price = r[2]
    rsi = r[3] or 50
    macd = r[4] or 0

    if rsi < 30:
        grade = 'EXCELLENT'
    elif rsi < 40:
        grade = 'GOOD'
    elif rsi < 55:
        grade = 'FAIR'
    else:
        grade = 'EXPENSIVE'

    rsi_icon = 'G' if rsi < 40 else ('Y' if rsi < 55 else 'R')
    macd_icon = 'Up' if macd > 0 else 'Dn'
    print('  %s $%.2f | RSI=%s(%.1f) | MACD=%s | DCA=%s' % (sym, price, rsi_icon, rsi, macd_icon, grade))

print()
print('[International]')
for sym in intl:
    if sym not in etfs:
        print('  %s: NO DATA' % sym)
        continue
    r = etfs[sym]
    price = r[2]
    rsi = r[3] or 50
    macd = r[4] or 0

    if rsi < 30:
        grade = 'EXCELLENT'
    elif rsi < 40:
        grade = 'GOOD'
    elif rsi < 55:
        grade = 'FAIR'
    else:
        grade = 'EXPENSIVE'

    rsi_icon = 'G' if rsi < 40 else ('Y' if rsi < 55 else 'R')
    print('  %s $%.2f | RSI=%s(%.1f) | DCA=%s' % (sym, price, rsi_icon, rsi, grade))

print()
print('='*65)
print('DCA Guide:')
print('  GREEN  (RSI < 40): Excellent - Start/Add DCA')
print('  YELLOW (RSI 40-55): Fair - Continue normal DCA')
print('  RED    (RSI > 55): Expensive - Pause DCA')