# -*- coding: utf-8 -*-
"""Build Comprehensive Maggy US Stock DB - Extended Watchlist"""
import sys, yfinance, sqlite3, time
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
DB = f'{DATA_DIR}\\maggy.db'

# Extended watchlist - 35 stocks
STOCKS = {
    # ETFs
    'SPY': 'S&P 500 ETF',
    'QQQ': 'NASDAQ ETF',
    'SSO': 'S&P 500 2x Lever',
    'QLD': 'NASDAQ 2x Lever',
    'TQQQ': 'NASDAQ 3x Lever',
    'SPXL': 'S&P 500 3x Lever',
    'FANG': 'FANG+ ETF',
    'ARKK': 'ARK Innovation',
    'XLK': 'Tech Sector ETF',
    'XLE': 'Energy Sector ETF',
    'XLV': 'Health Care ETF',
    'VGT': 'Info Tech ETF',
    # Mega Tech
    'NVDA': 'Nvidia',
    'AAPL': 'Apple',
    'MSFT': 'Microsoft',
    'GOOGL': 'Google',
    'AMZN': 'Amazon',
    'META': 'Meta',
    'TSLA': 'Tesla',
    'AMD': 'AMD',
    'INTC': 'Intel',
    'NFLX': 'Netflix',
    'DIS': 'Disney',
    'COIN': 'Coinbase',
    'UBER': 'Uber',
    'ABNB': 'Airbnb',
    # FinTech
    'SQ': 'Block/Square',
    'PYPL': 'PayPal',
    # Semis
    'ASML': 'ASML',
    'TSM': 'Taiwan Semi',
    'MU': 'Micron',
    'AMAT': 'Applied Materials',
    # Others
    'V': 'Visa',
    'MA': 'Mastercard',
    'JPM': 'JPMorgan',
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
    return sma + 2 * std, sma, sma - 2 * std

def calc_atr(highs, lows, closes, period=14):
    if len(highs) < period + 1:
        return 20
    trs = []
    for i in range(1, period + 1):
        tr = max(highs[-i] - lows[-i], abs(highs[-i] - closes[-i-1]), abs(lows[-i] - closes[-i-1]))
        trs.append(tr)
    return sum(trs) / period

def calc_macd(closes, fast=12, slow=26, signal=9):
    if len(closes) < slow + 1:
        return None, None, None
    
    ema_fast = closes[-fast]
    ema_slow = closes[-slow]
    
    # Simplified MACD
    macd_line = ema_fast - ema_slow
    signal_line = macd_line * 0.9  # simplified
    macd_hist = macd_line - signal_line
    
    return macd_line, signal_line, macd_hist

def main():
    print('=== 建立 Maggy 美股完整資料庫 ===\n')
    
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    # Check existing
    cur.execute('SELECT COUNT(DISTINCT symbol) FROM daily')
    existing = cur.fetchone()[0]
    print(f'現有股票: {existing}檔')
    
    # Create table if not exists
    cur.execute('''CREATE TABLE IF NOT EXISTS daily (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT, date TEXT UNIQUE,
        open REAL, high REAL, low REAL, close REAL, volume INTEGER,
        sma_20 REAL, sma_60 REAL,
        bb_upper REAL, bb_middle REAL, bb_lower REAL,
        rsi_14 REAL, atr_14 REAL,
        macd_line REAL, macd_signal REAL, macd_hist REAL,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    
    total = len(STOCKS)
    new_count = 0
    
    for i, (sym, name) in enumerate(STOCKS.items(), 1):
        # Check if already exists
        cur.execute('SELECT COUNT(*) FROM daily WHERE symbol=?', (sym,))
        existing_count = cur.fetchone()[0]
        
        if existing_count > 400:
            print(f'[{i}/{total}] {sym} 已存在 ({existing_count}筆)，跳過')
            continue
        
        print(f'[{i}/{total}] {sym} {name}...', end=' ')
        
        try:
            t = yfinance.Ticker(sym)
            hist = t.history(period='3y')  # 3 years for better backtest
            
            if len(hist) < 100:
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
                
                sma20 = calc_sma(closes[:j+1], 20)
                sma60 = calc_sma(closes[:j+1], 60)
                bb_u, bb_m, bb_l = calc_bb(closes[:j+1], 20)
                rsi = calc_rsi(closes[:j+1], 14)
                atr = calc_atr(highs[:j+1], lows[:j+1], closes[:j+1], 14)
                macd_line, macd_signal, macd_hist = calc_macd(closes[:j+1], 12, 26, 9)
                
                cur.execute('''INSERT OR REPLACE INTO daily 
                    (symbol, date, open, high, low, close, volume, sma_20, sma_60, bb_upper, bb_middle, bb_lower, rsi_14, atr_14, macd_line, macd_signal, macd_hist)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (sym, date, opens[j], highs[j], lows[j], closes[j], volumes[j], sma20, sma60, bb_u, bb_m, bb_l, rsi, atr, macd_line, macd_signal, macd_hist))
                count += 1
            
            conn.commit()
            new_count += count
            print(f'{count}筆')
            time.sleep(0.2)
            
        except Exception as e:
            print(f'error: {e}')
    
    # Final stats
    cur.execute('SELECT COUNT(*) FROM daily')
    total_records = cur.fetchone()[0]
    cur.execute('SELECT COUNT(DISTINCT symbol) FROM daily')
    total_symbols = cur.fetchone()[0]
    cur.execute('SELECT MAX(date) FROM daily')
    latest = cur.fetchone()[0]
    cur.execute('SELECT MIN(date) FROM daily')
    earliest = cur.fetchone()[0]
    
    print(f'\n=== 資料庫更新完成 ===')
    print(f'股票數: {total_symbols}')
    print(f'總筆數: {total_records} (新增 +{new_count})')
    print(f'時間範圍: {earliest} ~ {latest}')
    
    conn.close()

if __name__ == '__main__':
    main()