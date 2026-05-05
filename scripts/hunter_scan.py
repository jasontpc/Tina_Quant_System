import sqlite3
from pathlib import Path
from datetime import datetime
import pandas as pd
import yfinance as yf

DB = Path('data/yfinance.db')

# Core scan: growth candidates from local DB
symbols = [
    'NVDA', 'AMD', 'AVGO', 'MRVL', 'LRCX', 'AMAT',
    'META', 'AMZN', 'GOOGL', 'TSLA', 'SNOW', 'PLTR',
    'MSFT', 'CRM', 'ADBE', 'ORCL', 'CSCO', 'INTC',
    '2330.TW', '2454.TW', '2382.TW', '2317.TW', '3034.TW',
    '3665.TW', '4961.TW', '3231.TW', '3711.TW', '2467.TW',
    '5269.TW', '2359.TW', '2408.TW', '2344.TW', '2464.TW',
    '3324.TWO', '3037.TW', '1590.TW', '2201.TW', '2207.TW',
    '2881.TW', '2882.TW', '2883.TW', '2884.TW', '2885.TW',
    '2891.TW', '2892.TW', '1519.TW', '2634.TW', '2313.TW',
]

BLACKLIST = {'YANG', 'SOXS', 'NUGT', 'SOXL', 'TNA', 'JDST', 'KOLD', 'SPXL', 'UPRO', 'TQQQ'}

def verify_rsi_yf(sym):
    """Verify RSI against Yahoo Finance API"""
    try:
        tk = yf.Ticker(sym)
        h = tk.history(period='1mo')
        if len(h) < 15:
            return None, None
        closes = h['Close'].tolist()
        s = pd.Series(closes)
        delta = s.diff()
        gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        rsi = float((100 - (100 / (1 + rs))).iloc[-1])
        yf_price = closes[-1]
        return rsi, yf_price
    except:
        return None, None

print('Tina Active Hunter Mode - Growth Stock Scan (Local DB + YF Verification)')
print(datetime.now().strftime('%Y-%m-%d %H:%M'))
print('='*90)
print('%-12s %9s %6s %6s %6s %6s %6s %-8s' % ('Symbol', 'Price', 'DB_RSI', 'YF_RSI', 'DIFF', 'ATR%', 'Score', 'Signal'))
print('-'*90)

results = []
conn = sqlite3.connect(str(DB))

for sym in symbols:
    if sym in BLACKLIST:
        continue
    
    try:
        c = conn.cursor()
        c.execute("""
            SELECT date, close, open, high, low, volume, rsi_14, macd_hist, sma_20, sma_60
            FROM daily_ohlcv 
            WHERE symbol=? 
            ORDER BY date DESC LIMIT 30
        """, (sym,))
        rows = c.fetchall()
        
        if len(rows) < 20:
            continue
        
        latest = rows[0]
        price = latest[1]
        prev_close = rows[1][1] if len(rows) > 1 else price
        change_1d = (price - prev_close) / prev_close * 100
        
        # ATR
        trs = []
        for i in range(1, min(15, len(rows))):
            high = rows[i][3]
            low = rows[i][4]
            prev_close_row = rows[i-1][1] if i > 0 else rows[i][1]
            tr = max(high - low, abs(high - prev_close_row), abs(low - prev_close_row))
            trs.append(tr)
        atr = sum(trs) / len(trs) if trs else 0
        atr_pct = atr / price * 100 if price else 0
        
        # DB indicators
        rsi_db = latest[6] or 50
        macd_hist = latest[7] or 0
        sma20 = latest[8] or price
        sma60 = latest[9] or price
        
        # Verify with Yahoo Finance
        rsi_yf, yf_price = verify_rsi_yf(sym)
        
        if rsi_yf:
            rsi_diff = abs(rsi_db - rsi_yf)
        else:
            rsi_diff = None
        
        # Score
        score = 0
        if 30 <= rsi_db <= 70: score += 30
        elif rsi_db < 30: score += 50
        if macd_hist > 0: score += 25
        if atr_pct > 3: score += 20
        elif atr_pct > 1.5: score += 10
        if price < 100: score += 10
        
        signal = 'BUY' if score >= 60 else ('WATCH' if score >= 40 else 'HOLD')
        results.append((sym, price, rsi_db, rsi_yf, rsi_diff, macd_hist, atr_pct, score, change_1d, signal))
        
    except Exception as e:
        pass

conn.close()

results.sort(key=lambda x: x[7], reverse=True)
for r in results:
    sym, price, rsi_db, rsi_yf, rsi_diff, macd, atr_pct, score, change_1d, signal = r
    
    # Format diff
    if rsi_diff is not None:
        diff_str = '%+.1f' % (rsi_db - rsi_yf)
        if abs(rsi_db - rsi_yf) > 10:
            diff_str += ' [!]'
        elif abs(rsi_db - rsi_yf) > 5:
            diff_str += ' [w]'
    else:
        diff_str = 'N/A'
    
    sig = r[9]
    print('%-12s $%9.2f %5.1f %6.1f %6s %5.1f%% %5d %6.1f%% %s' % (
        sym, price, rsi_db, rsi_yf or 0, diff_str, atr_pct, score, change_1d, sig))

buys = [r for r in results if r[9] == 'BUY']
watches = [r for r in results if r[9] == 'WATCH']
print()
print('SUMMARY: BUY=%d WATCH=%d' % (len(buys), len(watches)))
if buys:
    print('BUY: %s' % ', '.join(r[0] for r in buys))
if watches:
    print('WATCH: %s' % ', '.join(r[0] for r in watches))
print()
print('[!] = Diff >10, [w] = Diff >5, verification recommended')