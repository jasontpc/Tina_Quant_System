import sqlite3
from pathlib import Path
from datetime import datetime

ETF_DB = Path('data/etf.db')
YFIN_DB = Path('data/yfinance.db')

# Get TW ETF data
conn = sqlite3.connect(str(ETF_DB))
c = conn.cursor()
c.execute("SELECT symbol, date, close, volume FROM etf_daily WHERE date >= '2026-04-01' ORDER BY symbol, date DESC")
etf_rows = c.fetchall()
conn.close()

# Get latest for each TW ETF
etf_latest = {}
for r in etf_rows:
    sym = r[0]
    if sym not in etf_latest:
        etf_latest[sym] = r

# Get US ETF data from yfinance
conn = sqlite3.connect(str(YFIN_DB))
c = conn.cursor()
c.execute("""
    SELECT symbol, date, close, rsi_14, macd_hist, sma_20, sma_60
    FROM daily_ohlcv
    WHERE symbol IN ('VTI', 'IWM', 'QQQ', 'SPY', 'DIA', 'VEA', 'VWO', 'BND', 'TLT', 'GLD', 'SLV')
    ORDER BY symbol, date DESC
""")
us_rows = c.fetchall()
conn.close()

us_latest = {}
for r in us_rows:
    sym = r[0]
    if sym not in us_latest:
        us_latest[sym] = r

print('='*65)
print('  Tina TW + US ETF Recommendations')
print('  ' + datetime.now().strftime('%Y-%m-%d'))
print('='*65)
print()

# TW ETF analysis
tw_etfs = [
    ('0050.TW', '元大台灣50'),
    ('0056.TW', '元大高股息'),
    ('00646.TW', '富邦S&P500'),
    ('00662.TW', '富邦NASDAQ100'),
    ('00713.TW', '元大高息低波'),
    ('00757.TW', '統一大FANG+'),
    ('00927.TW', '統一手創未來'),
    ('00981.TW', '國泰5G+'),
    ('00952.TW', '凱基台灣AI50'),
]

print('[Taiwan ETFs]')
print('%-12s %-20s %8s' % ('代號', '名稱', '價格'))
print('-'*50)
for sym, name in tw_etfs:
    if sym in etf_latest:
        r = etf_latest[sym]
        price = r[2]
        print('%s %-20s %9.2f' % (sym, name, price))
    else:
        print('%s %-20s N/A' % (sym, name))

print()
print('[US ETFs]')
print('%-10s %-18s %8s %5s %8s %5s' % ('代號', '名稱', '價格', 'RSI', 'MACD', 'MA'))
print('-'*65)

us_etf_info = {
    'VTI': 'Vanguard Total Stock',
    'IWM': 'iShares Russell 2000',
    'QQQ': 'Nasdaq 100',
    'SPY': 'S&P 500',
    'DIA': 'Dow Jones',
    'VEA': 'Vanguard Dev Ex-NA',
    'VWO': 'Vanguard Emg Mkts',
    'BND': 'Vanguard Total Bond',
    'TLT': 'iShares 20Y Treasury',
    'GLD': 'SPDR Gold',
    'SLV': 'iShares Silver',
}

us_results = []
for sym, name in us_etf_info.items():
    if sym in us_latest:
        r = us_latest[sym]
        price = r[2]
        rsi = r[3] or 50
        macd = r[4] or 0
        sma20 = r[5] or price
        sma60 = r[6] or price

        score = 0
        tags = []

        if rsi < 40:
            score += 40; tags.append('RSI_OVERSOLD')
        elif rsi < 50:
            score += 25; tags.append('RSI_LOW')
        elif rsi < 60:
            score += 10; tags.append('RSI_NEUTRAL')
        else:
            score += 0; tags.append('RSI_HIGH')

        if macd > 0:
            score += 20; tags.append('MACD_BULL')

        if sma20 > sma60:
            score += 15; tags.append('MA_BULL')

        rsi_flag = 'G' if rsi < 40 else ('Y' if rsi < 55 else 'R')
        macd_flag = 'Up' if macd > 0 else 'Dn'
        ma_flag = 'Bull' if sma20 > sma60 else 'Bear'

        verdict = 'BUY' if score >= 60 else ('WATCH' if score >= 40 else 'HOLD')
        us_results.append((sym, name, price, rsi, macd, rsi_flag, macd_flag, ma_flag, score, verdict, tags))

us_results.sort(key=lambda x: x[8], reverse=True)

for r in us_results:
    sym, name, price, rsi, macd, rsi_flag, macd_flag, ma_flag, score, verdict, tags = r
    print('%s %-20s %9.2f %s(%.1f) %s(%.3f) %s %d %s' % (
        sym, name[:15], price, rsi_flag, rsi, macd_flag, macd, ma_flag, score, verdict))

print()
print('='*65)
print('[Summary]')
buys = [r for r in us_results if r[9] == 'BUY']
watches = [r for r in us_results if r[9] == 'WATCH']
if buys:
    print('BUY: %s' % ', '.join(r[0] for r in buys))
if watches:
    print('WATCH: %s' % ', '.join(r[0] for r in watches))
print()
print('[TW ETF Holdings]')
print('  00713.TW 元大高息低波: $52.85 [持有中]')
print('  2382.TW 廣達: $312.50 [持有中]')