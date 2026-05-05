# -*- coding: utf-8 -*-
"""Vogel 台指期自主學習系統 v4
===================================
使用 yfinance 取得 TX 期貨數據（舊 FinMind 失效）
"""
import sqlite3
import yfinance as yf
import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
DATA_DIR = WORKSPACE / "data"
DB = DATA_DIR / "vogel_tx.db"

def calc_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(com=period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(com=period, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calc_atr(hist, period=14):
    high = hist['High']
    low = hist['Low']
    close = hist['Close']
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = tr1.combine(tr2, max).combine(tr3, max)
    return tr.ewm(com=period, adjust=False).mean()

def calc_bb(hist, period=20):
    mid = hist['Close'].ewm(com=period, adjust=False).mean()
    std = hist['Close'].std()
    upper = mid + 2 * std
    lower = mid - 2 * std
    return upper, mid, lower

def build_vogel_db():
    """建立 Vogel TX 期貨資料庫"""
    print('[Vogel v4] 自主學習系統啟動')
    print('Fetching TX futures data from yfinance...')

    # TXF 台指期 (TWSE)
    try:
        ticker = yf.Ticker("TXF.TW")
        hist = ticker.history(period="2y")
        if len(hist) < 60:
            print('TXF.TW insufficient data, trying ^TWII')
            ticker = yf.Ticker("^TWII")
            hist = ticker.history(period="2y")
    except Exception as e:
        print(f'TXF error: {e}, using ^TWII')
        ticker = yf.Ticker("^TWII")
        hist = ticker.history(period="2y")

    print(f'Got {len(hist)} rows, date range: {hist.index[0].date()} to {hist.index[-1].date()}')

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS tx_daily (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            open REAL, high REAL, low REAL, close REAL, volume INTEGER,
            rsi_14 REAL, atr_14 REAL,
            bb_upper REAL, bb_mid REAL, bb_lower REAL,
            macd_line REAL, macd_signal REAL, macd_hist REAL,
            sma20 REAL, sma60 REAL, trend TEXT,
            UNIQUE(date)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, signal_type TEXT, price REAL,
            rsi REAL, reason TEXT, result TEXT,
            entry_price REAL, exit_price REAL, pnl_pct REAL
        )
    ''')

    c.execute('DELETE FROM tx_daily')
    conn.commit()

    close = hist['Close']
    rsi_vals = calc_rsi(close)
    atr_vals = calc_atr(hist)
    bb_upper, bb_mid, bb_lower = calc_bb(hist)

    # MACD (12, 26, 9)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    macd_signal = macd_line.ewm(span=9, adjust=False).mean()
    macd_hist = macd_line - macd_signal

    # SMA
    sma20 = close.ewm(span=20, adjust=False).mean()
    sma60 = close.ewm(span=60, adjust=False).mean()

    rows = 0
    for i in range(60, len(hist)):
        dt = hist.index[i].strftime('%Y-%m-%d')
        row = hist.iloc[i]
        c.execute('''
            INSERT OR IGNORE INTO tx_daily
            (date, open, high, low, close, volume,
             rsi_14, atr_14, bb_upper, bb_mid, bb_lower,
             macd_line, macd_signal, macd_hist,
             sma20, sma60, trend)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            dt, float(row['Open']), float(row['High']), float(row['Low']),
            float(row['Close']), int(row['Volume']),
            round(float(rsi_vals.iloc[i]), 2),
            round(float(atr_vals.iloc[i]), 2),
            round(float(bb_upper.iloc[i]), 2),
            round(float(bb_mid.iloc[i]), 2),
            round(float(bb_lower.iloc[i]), 2),
            round(float(macd_line.iloc[i]), 2),
            round(float(macd_signal.iloc[i]), 2),
            round(float(macd_hist.iloc[i]), 2),
            round(float(sma20.iloc[i]), 2),
            round(float(sma60.iloc[i]), 2),
            'BULL' if sma60.iloc[i] > sma60.iloc[i-1] else 'BEAR'
        ))
        rows += 1

    conn.commit()

    # Latest signal
    c.execute('SELECT date, close, rsi_14, atr_14, bb_upper, bb_mid, bb_lower FROM tx_daily ORDER BY date DESC LIMIT 1')
    latest = c.fetchone()
    if latest:
        print(f'Latest: {latest[0]} Close={latest[1]:.0f} RSI={latest[2]:.1f} ATR={latest[3]:.0f}')
        print(f'BB Upper={latest[4]:.0f} Mid={latest[5]:.0f} Lower={latest[6]:.0f}')

    conn.close()
    print(f'Vogel DB built: {rows} new rows')


if __name__ == '__main__':
    build_vogel_db()
