import yfinance as yf
import sqlite3
import os
from datetime import datetime

data_dir = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
db_path = os.path.join(data_dir, 'tw_history.db')

stocks = [
    '2330', '2382', '2454', '2317', '3034', '3665', '4961',
    '2881', '2884', '2891', '2883', '2886', '2855',
    '3231', '3017', '2345', '3717', '2458', '2303'
]

print('=== yfinance TWSE 本地資料庫更新 ===')
print(f'Target: {db_path}')
print(f'Stocks: {len(stocks)} 檔')
print()

conn = sqlite3.connect(db_path)
c = conn.cursor()

# Check/create table
c.execute('''CREATE TABLE IF NOT EXISTS tw_history (
    stock TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL,
    volume INTEGER, rsi14 REAL, ma20 REAL, ma60 REAL, bias REAL,
    pe REAL, mktcap REAL, updated_at TEXT,
    PRIMARY KEY (stock, date))''')
conn.commit()

# Get existing count
c.execute('SELECT COUNT(*) FROM tw_history')
old_count = c.fetchone()[0]

for ticker in stocks:
    try:
        tk = yf.Ticker(ticker + '.TW')
        h = tk.history(period='6mo')
        info = tk.info
        
        if len(h) < 30:
            print(f'{ticker}: 無法取得資料')
            continue
        
        price = float(h['Close'].iloc[-1])
        
        # RSI
        delta = h['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = float((100 - (100 / (1 + rs))).iloc[-1])
        
        ma20 = float(h['Close'].rolling(20).mean().iloc[-1])
        ma60 = float(h['Close'].rolling(60).mean().iloc[-1]) if len(h) >= 60 else ma20
        bias = (price / ma20 - 1) * 100
        
        vol = int(h['Volume'].iloc[-1])
        vol20 = float(h['Volume'].rolling(20).mean().iloc[-1])
        
        pe = info.get('trailingPE', 0) or 0
        mktcap = info.get('marketCap', 0) / 1e9
        
        date_str = datetime.now().strftime('%Y-%m-%d')
        time_str = datetime.now().strftime('%H:%M:%S')
        
        c.execute('''INSERT OR REPLACE INTO tw_history 
            (stock, date, open, high, low, close, volume, rsi14, ma20, ma60, bias, pe, mktcap, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (ticker, date_str, float(h['Open'].iloc[-1]), float(h['High'].iloc[-1]),
             float(h['Low'].iloc[-1]), price, vol, rsi, ma20, ma60, bias, float(pe), float(mktcap), time_str))
        
        print(f'{ticker}: ${price:.2f} RSI={rsi:.1f} BIAS={bias:+.1f}%')
        
    except Exception as e:
        print(f'{ticker}: Error - {str(e)[:50]}')

conn.commit()

c.execute('SELECT COUNT(*) FROM tw_history')
new_count = c.fetchone()[0]
conn.close()

print()
print('=== 更新完成 ===')
print(f'更新前: {old_count} rows')
print(f'更新後: {new_count} rows')
print(f'新增: {new_count - old_count} rows')