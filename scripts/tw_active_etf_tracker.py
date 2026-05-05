# -*- coding: utf-8 -*-
"""
Taiwan Active ETF Daily Tracker
建立與更新台股主動型ETF資料庫
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import sqlite3
import yfinance as yf
import pandas as pd
from datetime import datetime

DB = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\tw_active_etf.db'

# 主動型ETF追蹤名單（排除已下市/無數據）
ETF_LIST = [
    ('00878.TW', '國泰永續高息', 'ESG高股息'),
    ('00900.TW', '兆豐永續股息', '高股息'),
    ('00882.TW', '中信綠能', '綠能'),
    ('00893.TW', '國泰台灣ESG', 'ESG'),
    ('00902.TW', '中信關鍵半導體', '半導體'),
    ('00896.TW', '兆豐龍頭等權重', '等權重'),
    ('00830.TW', '富邦NASDAQ', '科技'),
    ('00851.TW', '台新永續高峰', '永續'),
    ('00757.TW', '統一奔騰', '科技'),
]

def get_db_table():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS etf_daily (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            name TEXT,
            category TEXT,
            price REAL,
            rsi_14 REAL,
            rsi_30 REAL,
            bias20 REAL,
            bias60 REAL,
            mom1m REAL,
            mom3m REAL,
            mom6m REAL,
            mom1y REAL,
            ma20 REAL,
            ma60 REAL,
            ma120 REAL,
            atr14 REAL,
            vol_ratio REAL,
            updated_at TEXT,
            UNIQUE(symbol, updated_at)
        )
    ''')
    conn.commit()
    return conn

def calc_rsi(prices, period=14):
    if len(prices) < period:
        return None
    delta = pd.Series(prices).diff()
    gain = delta.where(delta > 0, 0).ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = gain / loss
    return (100 - (100 / (1 + rs))).iloc[-1]

def fetch_etf_data(symbol, name, category):
    """Fetch all data for a single ETF"""
    try:
        t = yf.Ticker(symbol)
        h = t.history(period='2y')
        if h.empty or len(h) < 30:
            return None
        
        c = h['Close']
        price = float(c.iloc[-1])
        
        # RSI
        rsi14 = calc_rsi(c.values, 14)
        rsi30 = calc_rsi(c.values, 30)
        
        # MA & BIAS
        ma20 = float(c.rolling(20).mean().iloc[-1]) if len(c) >= 20 else None
        ma60 = float(c.rolling(60).mean().iloc[-1]) if len(c) >= 60 else None
        ma120 = float(c.rolling(120).mean().iloc[-1]) if len(c) >= 120 else None
        bias20 = (price / ma20 - 1) * 100 if ma20 else None
        bias60 = (price / ma60 - 1) * 100 if ma60 else None
        
        # Momentum
        mom1m = float((c.iloc[-1] / c.iloc[-21] - 1) * 100) if len(c) >= 21 else None
        mom3m = float((c.iloc[-1] / c.iloc[-63] - 1) * 100) if len(c) >= 63 else None
        mom6m = float((c.iloc[-1] / c.iloc[-126] - 1) * 100) if len(c) >= 126 else None
        mom1y = float((c.iloc[-1] / c.iloc[-252] - 1) * 100) if len(c) >= 252 else None
        
        # ATR
        high = h['High']
        low = h['Low']
        tr = pd.concat([high - low, (high - c.shift()).abs(), (low - c.shift()).abs()], axis=1).max(axis=1)
        atr14 = float(tr.rolling(14).mean().iloc[-1]) if len(h) >= 14 else None
        
        # Volume
        vol_now = float(h['Volume'].iloc[-1])
        vol_avg = float(h['Volume'].rolling(20).mean().iloc[-1]) if len(h) >= 20 else None
        vol_ratio = vol_now / vol_avg if vol_avg else None
        
        return {
            'symbol': symbol,
            'name': name,
            'category': category,
            'price': price,
            'rsi_14': rsi14,
            'rsi_30': rsi30,
            'bias20': bias20,
            'bias60': bias60,
            'mom1m': mom1m,
            'mom3m': mom3m,
            'mom6m': mom6m,
            'mom1y': mom1y,
            'ma20': ma20,
            'ma60': ma60,
            'ma120': ma120,
            'atr14': atr14,
            'vol_ratio': vol_ratio,
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
        }
    except Exception as e:
        print(f'Error with {symbol}: {e}')
        return None

def main():
    conn = get_db_table()
    cur = conn.cursor()
    
    print('=' * 60)
    print('Taiwan Active ETF Daily Tracker')
    print(f'Time: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print('=' * 60)
    print()
    
    results = []
    for symbol, name, category in ETF_LIST:
        print(f'Fetching {symbol} {name}...', end=' ')
        data = fetch_etf_data(symbol, name, category)
        if data:
            # Insert into DB
            cur.execute('''
                INSERT OR IGNORE INTO etf_daily 
                (symbol, name, category, price, rsi_14, rsi_30, bias20, bias60,
                 mom1m, mom3m, mom6m, mom1y, ma20, ma60, ma120, atr14, vol_ratio, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['symbol'], data['name'], data['category'],
                data['price'], data['rsi_14'], data['rsi_30'], data['bias20'], data['bias60'],
                data['mom1m'], data['mom3m'], data['mom6m'], data['mom1y'],
                data['ma20'], data['ma60'], data['ma120'], data['atr14'], data['vol_ratio'],
                data['updated_at']
            ))
            results.append(data)
            print(f'${data["price"]:.2f} RSI={data["rsi_14"]:.1f}')
        else:
            print('FAILED')
    
    conn.commit()
    
    print()
    print('=' * 60)
    print('SIGNAL SUMMARY')
    print('=' * 60)
    
    results.sort(key=lambda x: x['rsi_14'] if x['rsi_14'] else 999)
    
    for r in results:
        if r['rsi_14'] is None:
            continue
        rsi = r['rsi_14']
        if rsi < 40: sig = 'STRONG_BUY'
        elif rsi < 50: sig = 'BUY'
        elif rsi < 65: sig = 'HOLD'
        else: sig = 'WAIT'
        
        sig_icon = {'STRONG_BUY': '🟢', 'BUY': '🟢', 'HOLD': '🟡', 'WAIT': '🔴'}[sig]
        bias_str = f"{r['bias20']:+.1f}%" if r['bias20'] else 'N/A'
        mom3_str = f"{r['mom3m']:+.1f}%" if r['mom3m'] else 'N/A'
        
        print(f"{sig_icon} {r['name']:<10} ${r['price']:>8.2f} RSI={rsi:>5.1f} BIAS20={bias_str} 3M={mom3_str} {sig}")
    
    buy = [r for r in results if r['rsi_14'] and r['rsi_14'] < 50]
    hold = [r for r in results if r['rsi_14'] and 50 <= r['rsi_14'] < 65]
    wait = [r for r in results if r['rsi_14'] and r['rsi_14'] >= 65]
    
    print()
    print(f'BUY: {len(buy)} | HOLD: {len(hold)} | WAIT: {len(wait)}')
    
    conn.close()
    
    return len(results)

if __name__ == '__main__':
    count = main()
    print(f'\nTotal: {count} ETFs updated')
    sys.exit(0)