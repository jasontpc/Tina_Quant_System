# TW Financial Stocks Tracker v2
# Tracks: 2881, 2884, 2891, 2883, 2886
# Uses FinMind API to get RSI and price signals

import requests
import sqlite3
from datetime import datetime, timedelta

TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSJ9.oCdQO1qNRUCYxHZSVuRQCqlF7X2DbQ77wury5ARCKzM'
BASE_URL = 'https://api.finmindtrade.com/api/v4/data'

STOCKS = ['2881', '2884', '2891', '2883', '2886']

def fetch_price_and_rsi(symbol, days=60):
    """Get price history and compute RSI for a TW stock"""
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    try:
        resp = requests.get(BASE_URL, params={
            'token': TOKEN,
            'dataset': 'TaiwanStockPrice',
            'data_id': symbol,
            'start_date': start_date,
            'end_date': end_date,
        }, timeout=15)
        data = resp.json()
        if not data.get('success') or not data.get('data'):
            return None, None
        
        prices = [float(d['close']) for d in data['data']]
        if len(prices) < 15:
            return None, None
        
        # Compute RSI(14)
        gains = []
        losses = []
        for i in range(1, len(prices)):
            diff = prices[i] - prices[i-1]
            if diff > 0:
                gains.append(diff)
            else:
                losses.append(abs(diff))
        
        # Use last 14 periods for RSI
        recent_gains = gains[-14:]
        recent_losses = losses[-14:]
        
        avg_gain = sum(recent_gains) / 14
        avg_loss = sum(recent_losses) / 14
        rs = avg_gain / avg_loss if avg_loss > 0 else 999
        rsi = 100 - (100 / (1 + rs))
        
        latest_price = prices[-1]
        return latest_price, rsi
    except Exception as e:
        print(f'Fetch error {symbol}: {e}')
        return None, None

db = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\stock_tracking.db'
conn = sqlite3.connect(db)
c = conn.cursor()

print('=== TW Financial Stocks Tracker ===')
for stock in STOCKS:
    price, rsi = fetch_price_and_rsi(stock)
    now = datetime.now().strftime('%Y-%m-%d')
    if rsi:
        c.execute('''INSERT OR REPLACE INTO entry_signals 
            (date, stock_code, signal_type, price, rsi, reason, score) 
            VALUES (?,?,?,?,?,?,?)''',
            (now, stock, 'ENTRY_WATCH', price, round(rsi,1), f'金融股追蹤 RSI={rsi:.1f}', 0.0))
        print(f'{stock}: price={price:.2f} RSI={rsi:.1f}')
    else:
        print(f'{stock}: No data')

conn.commit()
conn.close()
print('Done!')