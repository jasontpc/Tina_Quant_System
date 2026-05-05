# -*- coding: utf-8 -*-
"""
元大正二 (00631L) 專屬資料庫
Leveraged ETF 歷史數據 + 每日交易追蹤
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import sqlite3
import yfinance as yf
import pandas as pd
from datetime import datetime
import os

DB = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\yuan_zheng2.db'
SYMBOL = '00631L.TW'
NAME = '元大正二'

def init_db():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS daily_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            rsi_14 REAL,
            rsi_30 REAL,
            ma5 REAL,
            ma10 REAL,
            ma20 REAL,
            ma60 REAL,
            bias5 REAL,
            bias10 REAL,
            bias20 REAL,
            bias60 REAL,
            mom1d REAL,
            mom5d REAL,
            mom10d REAL,
            mom20d REAL,
            atr14 REAL,
            updated_at TEXT
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS trading_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            signal TEXT,
            price REAL,
            rsi_14 REAL,
            bias20 REAL,
            notes TEXT,
            created_at TEXT
        )
    ''')
    
    conn.commit()
    return conn

def fetch_history(conn):
    """抓取 2 年歷史數據寫入DB"""
    cur = conn.cursor()
    
    print(f'抓取 {NAME} ({SYMBOL}) 歷史數據...')
    t = yf.Ticker(SYMBOL)
    h = t.history(period='2y')
    
    if h.empty:
        print('No data found!')
        return
    
    c = h['Close']
    
    print(f'資料點: {len(h)}筆')
    
    for i in range(len(h)):
        date = h.index[i].strftime('%Y-%m-%d')
        close = float(h['Close'].iloc[i])
        open_ = float(h['Open'].iloc[i])
        high = float(h['High'].iloc[i])
        low = float(h['Low'].iloc[i])
        vol = int(h['Volume'].iloc[i])
        
        # Calculate all indicators up to this point
        hist = c.iloc[:i+1]
        
        rsi14 = None
        rsi30 = None
        if len(hist) >= 14:
            delta = hist.diff()
            gain = delta.where(delta > 0, 0).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
            loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
            rs = gain / loss
            rsi14 = float((100 - (100 / (1 + rs)).iloc[-1]))
        
        if len(hist) >= 30:
            delta = hist.diff()
            gain = delta.where(delta > 0, 0).ewm(alpha=1/30, min_periods=30, adjust=False).mean()
            loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/30, min_periods=30, adjust=False).mean()
            rs = gain / loss
            rsi30 = float((100 - (100 / (1 + rs)).iloc[-1]))
        
        ma5 = float(hist.rolling(5).mean().iloc[-1]) if len(hist) >= 5 else None
        ma10 = float(hist.rolling(10).mean().iloc[-1]) if len(hist) >= 10 else None
        ma20 = float(hist.rolling(20).mean().iloc[-1]) if len(hist) >= 20 else None
        ma60 = float(hist.rolling(60).mean().iloc[-1]) if len(hist) >= 60 else None
        
        bias5 = (close / ma5 - 1) * 100 if ma5 else None
        bias10 = (close / ma10 - 1) * 100 if ma10 else None
        bias20 = (close / ma20 - 1) * 100 if ma20 else None
        bias60 = (close / ma60 - 1) * 100 if ma60 else None
        
        mom1d = float((c.iloc[i] / c.iloc[i-1] - 1) * 100) if i >= 1 else None
        mom5d = float((c.iloc[i] / c.iloc[i-6] - 1) * 100) if i >= 6 else None
        mom10d = float((c.iloc[i] / c.iloc[i-11] - 1) * 100) if i >= 11 else None
        mom20d = float((c.iloc[i] / c.iloc[i-21] - 1) * 100) if i >= 21 else None
        
        atr = None
        if i >= 13:
            tr_data = pd.concat([
                h['High'].iloc[i-13:i+1] - h['Low'].iloc[i-13:i+1],
                (h['High'].iloc[i-13:i+1] - h['Close'].iloc[i-14:i]).abs(),
                (h['Low'].iloc[i-13:i+1] - h['Close'].iloc[i-14:i]).abs()
            ], axis=1).max(axis=1)
            atr = float(tr_data.mean())
        
        cur.execute('''
            INSERT OR REPLACE INTO daily_data 
            (date, open, high, low, close, volume, rsi_14, rsi_30,
             ma5, ma10, ma20, ma60, bias5, bias10, bias20, bias60,
             mom1d, mom5d, mom10d, mom20d, atr14, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (date, open_, high, low, close, vol, rsi14, rsi30,
              ma5, ma10, ma20, ma60, bias5, bias10, bias20, bias60,
              mom1d, mom5d, mom10d, mom20d, atr, datetime.now().strftime('%Y-%m-%d %H:%M')))
    
    conn.commit()
    print(f'已寫入 {len(h)} 筆歷史數據')

def analyze_today(conn):
    """分析今日數據並給出信號"""
    cur = conn.cursor()
    
    cur.execute('SELECT * FROM daily_data ORDER BY date DESC LIMIT 1')
    row = cur.fetchone()
    
    if not row:
        return None
    
    cols = [desc[0] for desc in cur.description]
    data = dict(zip(cols, row))
    
    date = data['date']
    price = data['close']
    rsi = data['rsi_14']
    bias20 = data['bias20']
    bias60 = data['bias60']
    mom5d = data['mom5d']
    mom20d = data['mom20d']
    
    # Signal logic
    if rsi and rsi < 35: sig = 'STRONG_BUY'
    elif rsi and rsi < 45: sig = 'BUY'
    elif rsi and rsi < 60: sig = 'HOLD'
    else: sig = 'WAIT'
    
    # Check for key levels
    notes = []
    if bias20 and bias20 < -5: notes.append('BIAS20 低估')
    if bias20 and bias20 > 10: notes.append('BIAS20 偏高')
    if rsi and rsi > 75: notes.append('RSI 過熱')
    if mom5d and mom5d < -5: notes.append('5日回調')
    
    return {
        'date': date,
        'price': price,
        'rsi': rsi,
        'bias20': bias20,
        'bias60': bias60,
        'mom5d': mom5d,
        'mom20d': mom20d,
        'signal': sig,
        'notes': ', '.join(notes) if notes else '正常'
    }

def print_summary(conn):
    """打印今日分析摘要"""
    cur = conn.cursor()
    
    cur.execute('SELECT COUNT(*) FROM daily_data')
    count = cur.fetchone()[0]
    
    cur.execute('SELECT date, close, rsi_14, bias20, bias60, mom5d, mom20d FROM daily_data ORDER BY date DESC LIMIT 5')
    recent = cur.fetchall()
    
    cur.execute('SELECT MAX(close) FROM daily_data WHERE date LIKE "2025%"')
    high_2025 = cur.fetchone()[0]
    cur.execute('SELECT MIN(close) FROM daily_data WHERE date LIKE "2025%"')
    low_2025 = cur.fetchone()[0]
    
    print()
    print('=' * 60)
    print(f'{NAME} ({SYMBOL}) 每日分析報告')
    print(f'資料庫: {count} 筆')
    print('=' * 60)
    print()
    
    print('【近期數據】')
    print('日期        價格      RSI    BIAS20  BIAS60  5D動能  20D動能')
    print('-' * 60)
    for r in recent:
        d, p, rsi, b20, b60, m5, m20 = r
        print(f'{d}  {p:>9.2f}  {rsi:>5.1f}  {b20:>+6.1f}% {b60:>+6.1f}% {m5:>+6.1f}% {m20:>+6.1f}%')
    
    print()
    print('【2025 年高低點】')
    print(f'全年最高: {high_2025:.2f}')
    print(f'全年最低: {low_2025:.2f}')
    
    today = analyze_today(conn)
    if today:
        print()
        print('【今日信號】')
        sig_icon = {'STRONG_BUY': '🟢', 'BUY': '🟢', 'HOLD': '🟡', 'WAIT': '🔴'}[today['signal']]
        print(f'日期: {today["date"]}')
        print(f'價格: ${today["price"]:.2f}')
        print(f'RSI(14): {today["rsi"]:.1f}' if today['rsi'] else 'RSI: N/A')
        print(f'BIAS20: {today["bias20"]:+.1f}%' if today['bias20'] else 'BIAS20: N/A')
        print(f'BIAS60: {today["bias60"]:+.1f}%' if today['bias60'] else 'BIAS60: N/A')
        print(f'5D動能: {today["mom5d"]:+.1f}%' if today['mom5d'] else '5D: N/A')
        print(f'20D動能: {today["mom20d"]:+.1f}%' if today['mom20d'] else '20D: N/A')
        print(f'信號: {sig_icon} {today["signal"]}')
        print(f'備註: {today["notes"]}')
    
    print()
    print('=' * 60)

def log_trade(conn, signal, price, rsi, bias20, notes=''):
    """記錄交易信號"""
    cur = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')
    cur.execute('''
        INSERT INTO trading_log (date, signal, price, rsi_14, bias20, notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (today, signal, price, rsi, bias20, notes, datetime.now().strftime('%Y-%m-%d %H:%M')))
    conn.commit()

def main():
    conn = init_db()
    
    print()
    print('=' * 60)
    print(f'{NAME} ({SYMBOL}) 資料庫建立')
    print(f'Time: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print('=' * 60)
    
    # Fetch and store history
    fetch_history(conn)
    
    # Print summary
    print_summary(conn)
    
    conn.close()
    print(f'\n資料庫已建立: {DB}')

if __name__ == '__main__':
    main()