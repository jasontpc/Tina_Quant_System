# -*- coding: utf-8 -*-
"""
ETF 台股歷史交易資料庫建置腳本
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3, json, os, time
from datetime import datetime, timedelta
import numpy as np
import yfinance as yf

DATA_DIR = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data"
ETF_DB = os.path.join(DATA_DIR, "etf_history.db")
ETF_LIST = [
    ("0050", "元大台灣50"),
    ("0056", "元大高股息"),
    ("00646", "富邦S&P500"),
    ("00662", "富邦NASDAQ100"),
    ("00757", "統一大FANG+"),
    ("00713", "元大高息低波"),
    ("00927", "統一手創未來"),
    ("00881", "國泰5G"),
    ("00893", "國泰費城半導體"),
    ("00788", "期元大S&P500"),
    ("00690", "兆豐藍籌30"),
    ("00731", "復華股利精選"),
    ("0057", "元大摩臺"),
]

RSI_ZONES = {"OVERBOUGHT": 70, "NEUTRAL_HIGH": 60, "NEUTRAL_LOW": 40, "OVERSOLD": 30}

def calc_rsi(closes, period=14):
    closes = np.array(closes, dtype=float)
    n = len(closes)
    if n < period + 1: return np.full(n, np.nan)
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.convolve(gains, np.ones(period)/period, mode='valid')
    avg_loss = np.convolve(losses, np.ones(period)/period, mode='valid')
    rs = avg_gain / (avg_loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    return np.concatenate([np.full(period, np.nan), rsi])

def calc_sma(data, period):
    data = np.array(data, dtype=float)
    n = len(data)
    result = np.full(n, np.nan)
    for i in range(period - 1, n):
        result[i] = np.mean(data[i - period + 1:i + 1])
    return result

def calc_ema(data, period):
    data = np.array(data, dtype=float)
    n = len(data)
    result = np.full(n, np.nan)
    ema = data[0]
    mult = 2.0 / (period + 1)
    for i in range(n):
        if np.isnan(data[i]): continue
        ema = (data[i] - ema) * mult + ema
        result[i] = ema
    return result

def calc_kd(highs, lows, closes, n=9):
    highs = np.array(highs, dtype=float)
    lows = np.array(lows, dtype=float)
    closes = np.array(closes, dtype=float)
    k_val = np.full(len(closes), 50.0)
    d_val = np.full(len(closes), 50.0)
    for i in range(n, len(closes)):
        low_n = np.min(lows[i-n+1:i+1])
        high_n = np.max(highs[i-n+1:i+1])
        rsv = 100 * (closes[i] - low_n) / (high_n - low_n + 1e-10)
        k_val[i] = 2/3 * k_val[i-1] + 1/3 * rsv
        d_val[i] = 2/3 * d_val[i-1] + 1/3 * k_val[i]
    return k_val, d_val

def calc_atr(highs, lows, closes, period=14):
    n = len(highs)
    tr_list = []
    for i in range(n):
        if i == 0:
            tr_list.append(float(highs[i]) - float(lows[i]))
        else:
            hl = float(highs[i]) - float(lows[i])
            hc = abs(float(highs[i]) - float(closes[i-1]))
            lc = abs(float(lows[i]) - float(closes[i-1]))
            tr_list.append(max(hl, hc, lc))
    atr = np.full(n, np.nan)
    if n >= period:
        atr[period-1] = np.mean(tr_list[:period])
        for i in range(period, n):
            atr[i] = (atr[i-1] * (period - 1) + tr_list[i]) / period
    return atr

def get_zone(rsi):
    if rsi is None or np.isnan(rsi): return "UNKNOWN"
    if rsi >= RSI_ZONES["OVERBOUGHT"]: return "OVERBOUGHT"
    if rsi <= RSI_ZONES["OVERSOLD"]: return "OVERSOLD"
    if rsi >= RSI_ZONES["NEUTRAL_HIGH"]: return "NEUTRAL_HIGH"
    if rsi <= RSI_ZONES["NEUTRAL_LOW"]: return "NEUTRAL_LOW"
    return "NEUTRAL"

def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(ETF_DB)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS etf_list (
            symbol TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_ohlcv (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL, high REAL, low REAL, close REAL,
            volume INTEGER, change REAL, change_pct REAL,
            rsi_14 REAL, sma_20 REAL, sma_60 REAL,
            ema_12 REAL, ema_26 REAL,
            macd REAL, macd_signal REAL, macd_hist REAL,
            k REAL, d REAL,
            atr REAL, zone TEXT,
            UNIQUE(symbol, date)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL, date TEXT NOT NULL,
            rsi_value REAL, zone TEXT, signal_type TEXT,
            price REAL, verified INTEGER DEFAULT 0,
            outcome TEXT, exit_date TEXT, exit_price REAL,
            return_pct REAL, hold_days INTEGER,
            UNIQUE(symbol, date, signal_type)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS dca_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL, date TEXT NOT NULL,
            price REAL, shares INTEGER, amount REAL,
            UNIQUE(symbol, date)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS db_version (
            id INTEGER PRIMARY KEY,
            version TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("INSERT OR IGNORE INTO db_version (id, version) VALUES (1, 'v1.0 ETF Historical DB')")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_etf_symbol ON daily_ohlcv(symbol)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_etf_date ON daily_ohlcv(date)")
    conn.commit()
    return conn

def fetch_and_store(conn, symbol, name, years=3):
    try:
        ticker = yf.Ticker(f"{symbol}.TW")
        hist = ticker.history(period=f"{years}y")
        if hist.empty or len(hist) < 60:
            return 0, 0

        opens   = list(hist["Open"].values)
        highs   = list(hist["High"].values)
        lows    = list(hist["Low"].values)
        closes  = list(hist["Close"].values)
        volumes = list(hist["Volume"].values)
        dates   = [d.strftime("%Y-%m-%d") for d in hist.index]
        n = len(closes)

        rsi_14  = list(calc_rsi(closes, 14))
        sma_20  = list(calc_sma(closes, 20))
        sma_60  = list(calc_sma(closes, 60))
        ema_12  = list(calc_ema(closes, 12))
        ema_26  = list(calc_ema(closes, 26))
        k_arr, d_arr = calc_kd(highs, lows, closes, 9)
        k_arr = list(k_arr); d_arr = list(d_arr)
        atr_arr = list(calc_atr(highs, lows, closes, 14))

        # MACD
        ema_fast = calc_ema(closes, 12)
        ema_slow = calc_ema(closes, 26)
        macd_vals = list(ema_fast - ema_slow)
        macd_sig  = list(calc_ema(macd_vals, 9))
        macd_hist = list(np.array(macd_vals) - np.array(macd_sig))

        cur = conn.cursor()
        inserted = 0
        signals = 0
        prev_zone = None

        for i in range(n):
            c = float(closes[i])
            if np.isnan(c): continue
            chg = float(closes[i] - closes[i-1]) if i > 0 else 0.0
            chg_pct = (chg / float(closes[i-1]) * 100) if i > 0 and closes[i-1] != 0 else 0.0
            rsi14_val = float(rsi_14[i]) if not np.isnan(rsi_14[i]) else None
            zone = get_zone(rsi14_val)

            def v(x):
                return round(float(x), 4) if x is not None and not np.isnan(x) else None

            cur.execute("""
                INSERT OR REPLACE INTO daily_ohlcv
                (symbol, date, open, high, low, close, volume, change, change_pct,
                 rsi_14, sma_20, sma_60, ema_12, ema_26,
                 macd, macd_signal, macd_hist, k, d, atr, zone)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (symbol, dates[i],
                  v(opens[i]), v(highs[i]), v(lows[i]), c,
                  int(volumes[i]), round(chg, 2), round(chg_pct, 2),
                  v(rsi_14[i]), v(sma_20[i]), v(sma_60[i]),
                  v(ema_12[i]), v(ema_26[i]),
                  v(macd_vals[i]), v(macd_sig[i]), v(macd_hist[i]),
                  v(k_arr[i]), v(d_arr[i]), v(atr_arr[i]), zone))
            inserted += 1

            if not np.isnan(rsi_14[i]) and prev_zone is not None:
                if prev_zone == "OVERSOLD" and zone in ("NEUTRAL_LOW", "NEUTRAL", "NEUTRAL_HIGH"):
                    cur.execute("""
                        INSERT OR IGNORE INTO signals
                        (symbol, date, rsi_value, zone, signal_type, price, verified)
                        VALUES (?, ?, ?, ?, 'ENTRY_OVERSOLD', ?, 0)
                    """, (symbol, dates[i], round(float(rsi_14[i]), 2), zone, c))
                    signals += 1
            prev_zone = zone

        conn.commit()
        return inserted, signals

    except Exception as e:
        print(f"[ERR] {symbol} {name}: {e}")
        return 0, 0

def print_stats(conn):
    cur = conn.cursor()
    print('\n=== ETF Historical DB Stats ===')
    cur.execute('SELECT COUNT(DISTINCT symbol) FROM daily_ohlcv')
    print(f'ETFs: {cur.fetchone()[0]}')
    cur.execute('SELECT COUNT(*) FROM daily_ohlcv')
    print(f'OHLCV rows: {cur.fetchone()[0]}')
    cur.execute('SELECT COUNT(*) FROM signals')
    print(f'Signals: {cur.fetchone()[0]}')
    cur.execute('SELECT MIN(date), MAX(date) FROM daily_ohlcv')
    row = cur.fetchone()
    print(f'Date range: {row[0]} ~ {row[1]}')
    cur.execute('SELECT zone, COUNT(*) FROM daily_ohlcv GROUP BY zone ORDER BY COUNT(*) DESC')
    print('\nRSI Zone:')
    for row in cur.fetchall():
        print(f'  {row[0]}: {row[1]}')
    cur.execute('SELECT symbol, COUNT(*) FROM daily_ohlcv GROUP BY symbol ORDER BY COUNT(*) DESC')
    print('\nBy ETF:')
    for row in cur.fetchall():
        print(f'  {row[0]}: {row[1]} days')
    conn.close()
    import os
    size = os.path.getsize(ETF_DB)
    print(f'\nDB size: {size:,} bytes ({size/1024/1024:.1f} MB)')

def main():
    print('=== ETF Historical Trade DB Builder ===')
    print(f'Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    conn = init_db()

    cur = conn.cursor()
    for sym, name in ETF_LIST:
        cur.execute("INSERT OR IGNORE INTO etf_list (symbol, name) VALUES (?, ?)", (sym, name))
    conn.commit()

    total_ohlcv = 0
    total_signals = 0

    for i, (sym, name) in enumerate(ETF_LIST):
        ins, sig = fetch_and_store(conn, sym, name, years=3)
        total_ohlcv += ins
        total_signals += sig
        if ins > 0:
            print(f'  [{i+1}/{len(ETF_LIST)}] {sym} {name}: {ins} rows, {sig} signals')
        else:
            print(f'  [{i+1}/{len(ETF_LIST)}] {sym} {name}: FAILED')
        time.sleep(0.3)

    print(f'\nTotal: {total_ohlcv} OHLCV rows, {total_signals} signals')
    print_stats(conn)
    print(f'\nDB path: {ETF_DB}')
    print('=== Done ===')

if __name__ == '__main__':
    main()
