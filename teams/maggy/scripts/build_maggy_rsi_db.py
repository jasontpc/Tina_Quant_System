# -*- coding: utf-8 -*-
"""Build Maggy US Stock RSI Database"""
import sys, yfinance, sqlite3, json
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
DB = f'{DATA_DIR}\\maggy_rsi.db'

# Extended watchlist
STOCKS = {
    # ETFs
    'SPY': 'S&P 500 ETF', 'QQQ': 'NASDAQ ETF', 'SSO': 'S&P 500 2x',
    'QLD': 'NASDAQ 2x', 'TQQQ': 'NASDAQ 3x', 'SPXL': 'S&P 500 3x',
    'FANG': 'FANG+ ETF', 'ARKK': 'ARK Innovation', 'XLK': 'Tech Sector',
    'XLE': 'Energy', 'XLV': 'Healthcare', 'VGT': 'Info Tech',
    # Tech
    'NVDA': 'Nvidia', 'AAPL': 'Apple', 'MSFT': 'Microsoft', 'GOOGL': 'Google',
    'AMZN': 'Amazon', 'META': 'Meta', 'TSLA': 'Tesla', 'AMD': 'AMD',
    'INTC': 'Intel', 'NFLX': 'Netflix', 'DIS': 'Disney', 'COIN': 'Coinbase',
    'UBER': 'Uber', 'ABNB': 'Airbnb',
    # FinTech/Semis
    'V': 'Visa', 'MA': 'Mastercard', 'PYPL': 'PayPal', 'SQ': 'Block',
    'ASML': 'ASML', 'TSM': 'Taiwan Semi', 'MU': 'Micron', 'AMAT': 'Applied Materials',
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

def calc_rsi_multi(closes):
    rsi7 = calc_rsi(closes, 7)
    rsi14 = calc_rsi(closes, 14)
    rsi28 = calc_rsi(closes, 28)
    return rsi7, rsi14, rsi28

def detect_zone(rsi14):
    if rsi14 < 30:
        return 'OVERSOLD'
    elif rsi14 > 70:
        return 'OVERBOUGHT'
    else:
        return 'NEUTRAL'

def build_rsi_db():
    print('=== 建立 Maggy 美股 RSI 資料庫 ===\n')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
    
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    cur.execute('''CREATE TABLE IF NOT EXISTS rsi_signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT, date TEXT,
        close REAL, rsi_7 REAL, rsi_14 REAL, rsi_28 REAL,
        signal TEXT, zone TEXT,
        ma20_dev REAL, atr_14 REAL,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(symbol, date)
    )''')
    
    cur.execute('''CREATE TABLE IF NOT EXISTS rsi_summary (
        symbol TEXT PRIMARY KEY,
        name TEXT,
        current_rsi REAL, current_price REAL,
        zone TEXT,
        high_52w REAL, low_52w REAL,
        avg_rsi REAL, rsi_trades INTEGER,
        last_updated TEXT
    )''')
    
    conn.commit()
    
    total = len(STOCKS)
    total_records = 0
    
    for i, (sym, name) in enumerate(STOCKS.items(), 1):
        print(f'[{i}/{total}] {sym} {name}...', end=' ')
        
        try:
            t = yfinance.Ticker(sym)
            hist = t.history(period='2y')
            
            if len(hist) < 100:
                print(f'不足 {len(hist)}筆')
                continue
            
            closes = hist['Close'].tolist()
            highs = hist['High'].tolist()
            lows = hist['Low'].tolist()
            dates = hist.index.strftime('%Y-%m-%d').tolist()
            
            records = 0
            latest_data = {}
            
            for j in range(60, len(closes)):
                date = dates[j]
                close = closes[j]
                
                rsi7, rsi14, rsi28 = calc_rsi_multi(closes[:j+1])
                
                # ATR
                trs = []
                for k in range(1, 15):
                    tr = max(closes[j-k] - lows[j-k], abs(closes[j-k] - closes[j-k-1]))
                    trs.append(tr)
                atr = sum(trs) / 14
                
                # MA20 deviation
                sma20 = sum(closes[j-19:j+1]) / 20 if j >= 19 else closes[0]
                ma20_dev = ((close - sma20) / sma20 * 100)
                
                zone = detect_zone(rsi14)
                
                cur.execute('''INSERT OR REPLACE INTO rsi_signals 
                    (symbol, date, close, rsi_7, rsi_14, rsi_28, signal, zone, ma20_dev, atr_14)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (sym, date, close, rsi7, rsi14, rsi28, zone, zone, ma20_dev, atr))
                
                records += 1
                latest_data = {'date': date, 'close': close, 'rsi14': rsi14, 'zone': zone}
            
            if records > 0:
                conn.commit()
                
                high_52w = max(closes[-252:]) if len(closes) >= 252 else max(closes)
                low_52w = min(closes[-252:]) if len(closes) >= 252 else min(closes)
                
                rsi_values = [calc_rsi(closes[:j+1], 14) for j in range(60, len(closes))]
                avg_rsi = sum(rsi_values) / len(rsi_values)
                
                trades = sum(1 for i in range(1, len(rsi_values)) if len(rsi_values) > 1 and 
                    (rsi_values[i-1] < 50 <= rsi_values[i]) or (rsi_values[i-1] > 50 >= rsi_values[i]))
                
                cur.execute('''INSERT OR REPLACE INTO rsi_summary 
                    (symbol, name, current_rsi, current_price, zone, high_52w, low_52w, avg_rsi, rsi_trades, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (sym, name, latest_data['rsi14'], latest_data['close'], latest_data['zone'], 
                     high_52w, low_52w, avg_rsi, trades, latest_data['date']))
                
                conn.commit()
                print(f'{records}筆 RSI={latest_data["rsi14"]:.1f} {latest_data["zone"]}')
            
        except Exception as e:
            print(f'error: {e}')
    
    print(f'\n=== RSI 資料庫建立完成 ===')
    cur.execute('SELECT COUNT(*) FROM rsi_signals')
    total = cur.fetchone()[0]
    cur.execute('SELECT COUNT(DISTINCT symbol) FROM rsi_signals')
    syms = cur.fetchone()[0]
    
    print(f'總筆數: {total}')
    print(f'股票數: {syms}')
    
    print('\n=== 當前 RSI 摘要 ===')
    print(f'{"代號":<6} {"名稱":<14} {"現價":>8} {"RSI14":>7} {"區間"}')
    print('-' * 50)
    
    cur.execute('SELECT symbol, name, current_price, current_rsi, zone FROM rsi_summary ORDER BY current_rsi ASC')
    for r in cur.fetchall():
        sym, name, price, rsi, zone = r
        zone_icon = '🟢' if zone == 'OVERSOLD' else ('🔴' if zone == 'OVERBOUGHT' else '⚪')
        print(f'{sym:<6} {name:<14} {price:>8.0f} {rsi:>7.1f} {zone_icon} {zone}')
    
    conn.close()

if __name__ == '__main__':
    build_rsi_db()