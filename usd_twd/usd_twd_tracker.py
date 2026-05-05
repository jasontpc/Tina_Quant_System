"""
USD/TWD 美元兌台幣 價格追蹤資料庫
USD/TWD Exchange Rate Tracker
"""

import sqlite3
import json
import yfinance as yf
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

DATA_DIR = Path(__file__).parent
DB_FILE = DATA_DIR / 'usd_twd.db'

def init_db():
    """初始化資料庫"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    
    cur.execute('''
    CREATE TABLE IF NOT EXISTS daily_rates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        symbol TEXT,
        price REAL,
        change_pct REAL,
        trend TEXT
    )
    ''')
    
    cur.execute('''
    CREATE TABLE IF NOT EXISTS rate_signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        signal TEXT,
        level TEXT,
        price REAL,
        threshold TEXT,
        interpretation TEXT,
        action TEXT
    )
    ''')
    
    cur.execute('''
    CREATE TABLE IF NOT EXISTS monthly_avg (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        month TEXT,
        avg_rate REAL,
        trend TEXT,
        YoY_change REAL
    )
    ''')
    
    conn.commit()
    conn.close()
    return DB_FILE

def fetch_current_rate():
    """抓取即期匯率"""
    try:
        t = yf.Ticker('USDTWD=X')
        hist = t.history(period='5d')
        
        if len(hist) >= 2:
            curr = float(hist['Close'].iloc[-1])
            prev = float(hist['Close'].iloc[-2])
            chg = (curr - prev) / prev * 100 if prev > 0 else 0
            
            return {
                'symbol': 'USDTWD',
                'price': curr,
                'prev': prev,
                'change_pct': chg
            }
    except Exception as e:
        print(f"Error: {e}")
        return None

def fetch_historical_rates():
    """抓取歷史匯率"""
    try:
        t = yf.Ticker('USDTWD=X')
        hist = t.history(period='3mo')
        
        results = []
        for i, (date, row) in enumerate(hist.iterrows()):
            results.append({
                'date': date.isoformat(),
                'price': float(row['Close']),
                'volume': float(row['Volume']) if 'Volume' in row else 0
            })
        return results
    except Exception as e:
        print(f"Error: {e}")
        return []

def analyze_rate_level(price):
    """分析匯率區間"""
    # 根據歷史數據分類
    if price > 33:
        level = 'HIGH'
        signal = 'TWD_WEAK'
    elif price > 31:
        level = 'MEDIUM'
        signal = 'NEUTRAL'
    else:
        level = 'LOW'
        signal = 'TWD_STRONG'
    
    return level, signal

def generate_signals(price, change_pct, hist_data):
    """產生交易信號"""
    signals = []
    timestamp = datetime.now().isoformat()
    
    # 短期信號
    if change_pct > 1:
        signals.append({
            'signal': 'USD_STRONG',
            'level': 'SHORT',
            'price': price,
            'threshold': '>1%',
            'interpretation': 'USD 快速升值',
            'action': '換匯觀望'
        })
    elif change_pct < -1:
        signals.append({
            'signal': 'TWD_STRONG',
            'level': 'SHORT',
            'price': price,
            'threshold': '<-1%',
            'interpretation': 'TWD 升值趨勢',
            'action': '分批換USD'
        })
    
    # 技術分析
    if len(hist_data) >= 20:
        ma20 = sum([d['price'] for d in hist_data[-20:]]) / 20
        if price > ma20:
            trend = 'UPTREND'
            action = 'USD 強勢'
        else:
            trend = 'DOWNTREND'
            action = 'TWD 回升'
        
        signals.append({
            'signal': trend,
            'level': 'TECHNICAL',
            'price': price,
            'ma20': ma20,
            'threshold': 'MA20',
            'interpretation': f'Price {"above" if price > ma20 else "below"} MA20',
            'action': action
        })
    
    return signals

def save_data(rate_data, hist_data, signals):
    """儲存數據"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    timestamp = datetime.now().isoformat()
    
    # Save current rate
    if rate_data:
        try:
            cur.execute('''
                INSERT INTO daily_rates (timestamp, symbol, price, change_pct, trend)
                VALUES (?, ?, ?, ?, ?)
            ''', (timestamp, 'USDTWD', rate_data['price'], rate_data['change_pct'], 
                  'UP' if rate_data['change_pct'] > 0 else 'DOWN'))
        except:
            pass
    
    # Save signals
    for s in signals:
        try:
            cur.execute('''
                INSERT INTO rate_signals 
                (timestamp, signal, level, price, threshold, interpretation, action)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (timestamp, s['signal'], s['level'], s['price'], 
                  s.get('threshold', ''), s['interpretation'], s['action']))
        except:
            pass
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    print("=" * 60)
    print("  USD/TWD 美元兌台幣 價格追蹤")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Init
    print("\n[1] Initializing database...")
    init_db()
    print(f"  OK: {DB_FILE}")
    
    # Fetch current rate
    print("\n[2] Fetching current USD/TWD rate...")
    rate = fetch_current_rate()
    if rate:
        print(f"  USD/TWD: {rate['price']:.4f}")
        print(f"  Change: {rate['change_pct']:+.4f}%")
    else:
        print("  Failed to fetch rate")
    
    # Fetch historical
    print("\n[3] Fetching historical rates...")
    hist = fetch_historical_rates()
    print(f"  Got {len(hist)} historical data points")
    
    # Analyze
    if rate:
        level, signal = analyze_rate_level(rate['price'])
        print(f"\n[4] Rate Analysis:")
        print(f"  Level: {level}")
        print(f"  Signal: {signal}")
    
    # Generate signals
    print("\n[5] Signals:")
    signals = generate_signals(rate['price'] if rate else 0, 
                              rate['change_pct'] if rate else 0, 
                              hist)
    for s in signals:
        print(f"  {s['signal']}: {s['interpretation']} → {s['action']}")
    
    # Save
    print("\n[6] Saving data...")
    save_data(rate, hist, signals)
    print("  OK")
    
    print("\n" + "=" * 60)
