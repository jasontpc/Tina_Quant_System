# -*- coding: utf-8 -*-
"""Build Maggy US Stock Historical Database"""
import sys, yfinance, sqlite3, time
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
DB = f'{DATA_DIR}\\maggy.db'

# Key US stocks/ETFs
STOCKS = {
    # ETFs
    'SPY': 'S&P 500 ETF',
    'QQQ': 'NASDAQ ETF',
    'SSO': 'S&P 500 2x',
    'QLD': 'NASDAQ 2x',
    'TQQQ': 'NASDAQ 3x',
    'SPXL': 'S&P 500 3x',
    'FANG': 'FANG+ ETF',
    'ARKK': 'ARK Innovation',
    # Mega Tech
    'NVDA': 'Nvidia',
    'AAPL': 'Apple',
    'MSFT': 'Microsoft',
    'GOOGL': 'Google',
    'AMZN': 'Amazon',
    'META': 'Meta',
    'TSLA': 'Tesla',
}

def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50
    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(diff if diff > 0 else 0)
        losses.append(abs(diff) if diff < 0 else 0)
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    rs = avg_gain / avg_loss if avg_loss > 0 else 100
    return 100 - (100 / (1 + rs))

def calc_sma(values, period):
    if len(values) < period:
        return None
    return sum(values[-period:]) / period

def calc_bb(closes, period=20):
    if len(closes) < period:
        return None, None, None
    sma = sum(closes[-period:]) / period
    std = (sum([(x - sma)**2 for x in closes[-period:]]) / period) ** 0.5
    upper = sma + 2 * std
    lower = sma - 2 * std
    return upper, sma, lower

def calc_atr(highs, lows, closes, period=14):
    if len(highs) < period + 1:
        return 20
    trs = []
    for i in range(1, period + 1):
        tr = max(highs[-i] - lows[-i], abs(highs[-i] - closes[-i-1]), abs(lows[-i] - closes[-i-1]))
        trs.append(tr)
    return sum(trs) / period

def main():
    print('=== 建立 Maggy 美股歷史資料庫 ===\n')
    
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    # Create table
    cur.execute('''CREATE TABLE IF NOT EXISTS daily (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL, volume INTEGER,
        sma_20 REAL, sma_60 REAL,
        bb_upper REAL, bb_middle REAL, bb_lower REAL,
        rsi_14 REAL, atr_14 REAL,
        UNIQUE(symbol, date)
    )''')
    
    conn.commit()
    
    total = len(STOCKS)
    for i, (sym, name) in enumerate(STOCKS.items(), 1):
        print(f'[{i}/{total}] {sym} {name}...', end=' ')
        
        try:
            t = yfinance.Ticker(sym)
            hist = t.history(period='2y')
            
            if len(hist) < 60:
                print(f'不足 {len(hist)}筆')
                continue
            
            dates = hist.index.strftime('%Y-%m-%d').tolist()
            opens = hist['Open'].tolist()
            highs = hist['High'].tolist()
            lows = hist['Low'].tolist()
            closes = hist['Close'].tolist()
            volumes = hist['Volume'].tolist()
            
            count = 0
            for j in range(60, len(closes)):
                date = dates[j]
                close = closes[j]
                
                sma20 = calc_sma(closes[:j+1], 20)
                sma60 = calc_sma(closes[:j+1], 60)
                bb_upper, bb_middle, bb_lower = calc_bb(closes[:j+1], 20)
                rsi = calc_rsi(closes[:j+1], 14)
                atr = calc_atr(highs[:j+1], lows[:j+1], closes[:j+1], 14)
                
                cur.execute('''INSERT OR REPLACE INTO daily 
                    (symbol, date, open, high, low, close, volume, sma_20, sma_60, bb_upper, bb_middle, bb_lower, rsi_14, atr_14)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (sym, date, opens[j], highs[j], lows[j], close, volumes[j], sma20, sma60, bb_upper, bb_middle, bb_lower, rsi, atr))
                count += 1
            
            conn.commit()
            print(f'{count}筆')
            time.sleep(0.3)  # Rate limit
            
        except Exception as e:
            print(f'error: {e}')
    
    # Stats
    cur.execute('SELECT COUNT(*) FROM daily')
    total_records = cur.fetchone()[0]
    cur.execute('SELECT COUNT(DISTINCT symbol) FROM daily')
    total_symbols = cur.fetchone()[0]
    cur.execute('SELECT MAX(date) FROM daily')
    latest = cur.fetchone()[0]
    
    print(f'\n=== 資料庫建立完成 ===')
    print(f'股票數: {total_symbols}')
    print(f'總筆數: {total_records}')
    print(f'最新日期: {latest}')
    
    conn.close()

if __name__ == '__main__':
    main()