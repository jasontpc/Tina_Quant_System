# -*- coding: utf-8 -*-
"""
Taiwan Stock Historical Trade Database Builder v3
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
import json
import os
import time
from datetime import datetime, timedelta
import numpy as np
import yfinance as yf

DATA_DIR = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data"
DB_PATH = os.path.join(DATA_DIR, "tw_history.db")
STOCK_FILE = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\nana\stock_names.json"
RSI_ZONES = {"OVERBOUGHT": 70, "NEUTRAL_HIGH": 60, "NEUTRAL_LOW": 40, "OVERSOLD": 30}

def calc_rsi(closes, period=14):
    closes = np.array(closes, dtype=float)
    n = len(closes)
    if n < period + 1:
        return np.full(n, np.nan)
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
    multiplier = 2.0 / (period + 1)
    for i in range(n):
        if np.isnan(data[i]):
            continue
        ema = (data[i] - ema) * multiplier + ema
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

def calc_macd(closes, fast=12, slow=26, signal=9):
    ema_fast = calc_ema(closes, fast)
    ema_slow = calc_ema(closes, slow)
    macd = ema_fast - ema_slow
    sig = calc_ema(macd, signal)
    hist = macd - sig
    return macd, sig, hist

def calc_bb(closes, period=20, mult=2.0):
    closes = np.array(closes, dtype=float)
    n = len(closes)
    mid = calc_sma(closes, period)
    upper = np.full(n, np.nan)
    lower = np.full(n, np.nan)
    for i in range(period - 1, n):
        std = np.std(closes[i-period+1:i+1])
        upper[i] = mid[i] + mult * std
        lower[i] = mid[i] - mult * std
    return upper, mid, lower

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

def get_rsi_zone(rsi):
    if rsi is None or np.isnan(rsi):
        return "UNKNOWN"
    if rsi >= RSI_ZONES["OVERBOUGHT"]:
        return "OVERBOUGHT"
    if rsi <= RSI_ZONES["OVERSOLD"]:
        return "OVERSOLD"
    if rsi >= RSI_ZONES["NEUTRAL_HIGH"]:
        return "NEUTRAL_HIGH"
    if rsi <= RSI_ZONES["NEUTRAL_LOW"]:
        return "NEUTRAL_LOW"
    return "NEUTRAL"

def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stocks (
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
            rsi_5 REAL, rsi_14 REAL, rsi_20 REAL,
            sma_5 REAL, sma_10 REAL, sma_20 REAL, sma_60 REAL,
            ema_12 REAL, ema_26 REAL,
            macd REAL, macd_signal REAL, macd_hist REAL,
            k REAL, d REAL,
            bb_upper REAL, bb_mid REAL, bb_lower REAL,
            atr REAL, zone TEXT,
            UNIQUE(symbol, date)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS rsi_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL, date TEXT NOT NULL,
            rsi_value REAL, zone TEXT, signal_type TEXT,
            price REAL, expected_return REAL,
            verified INTEGER DEFAULT 0,
            outcome TEXT,
            exit_date TEXT, exit_price REAL,
            return_pct REAL, hold_days INTEGER,
            UNIQUE(symbol, date, signal_type)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS market_index (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL, date TEXT NOT NULL,
            close REAL, rsi_14 REAL, zone TEXT, volume INTEGER,
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
    cur.execute("INSERT OR IGNORE INTO db_version (id, version) VALUES (1, 'v1.1 Taiwan Historical DB')")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol ON daily_ohlcv(symbol)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ohlcv_date ON daily_ohlcv(date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_signals_symbol ON rsi_signals(symbol)")
    conn.commit()
    return conn

def get_stock_list():
    with open(STOCK_FILE, encoding='utf-8') as f:
        stocks = json.load(f)
    exclude = {'2888', '5882', '3008', '2330'}
    return [(k, v) for k, v in stocks.items() if k not in exclude]

def fetch_and_store_daily(conn, symbol, name, years=2):
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

        rsi_5  = list(calc_rsi(closes, 5))
        rsi_14 = list(calc_rsi(closes, 14))
        rsi_20 = list(calc_rsi(closes, 20))
        sma_5  = list(calc_sma(closes, 5))
        sma_10 = list(calc_sma(closes, 10))
        sma_20 = list(calc_sma(closes, 20))
        sma_60 = list(calc_sma(closes, 60))
        ema_12 = list(calc_ema(closes, 12))
        ema_26 = list(calc_ema(closes, 26))
        macd, macd_sig, macd_hist = calc_macd(closes, 12, 26, 9)
        macd = list(macd); macd_sig = list(macd_sig); macd_hist = list(macd_hist)
        k_arr, d_arr = calc_kd(highs, lows, closes, 9)
        k_arr = list(k_arr); d_arr = list(d_arr)
        bb_u, bb_m, bb_l = calc_bb(closes, 20, 2.0)
        bb_u = list(bb_u); bb_m = list(bb_m); bb_l = list(bb_l)
        atr_arr = list(calc_atr(highs, lows, closes, 14))

        cur = conn.cursor()
        inserted = 0
        signals = 0
        prev_zone = None

        for i in range(n):
            c = float(closes[i])
            if np.isnan(c):
                continue
            chg = float(closes[i] - closes[i-1]) if i > 0 else 0.0
            chg_pct = (chg / float(closes[i-1]) * 100) if i > 0 and closes[i-1] != 0 else 0.0
            rsi14_val = float(rsi_14[i]) if not np.isnan(rsi_14[i]) else None
            zone = get_rsi_zone(rsi14_val)

            def val(x):
                return round(float(x), 4) if x is not None and not np.isnan(x) else None

            cur.execute("""
                INSERT OR REPLACE INTO daily_ohlcv
                (symbol, date, open, high, low, close, volume, change, change_pct,
                 rsi_5, rsi_14, rsi_20, sma_5, sma_10, sma_20, sma_60,
                 ema_12, ema_26, macd, macd_signal, macd_hist, k, d,
                 bb_upper, bb_mid, bb_lower, atr, zone)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (symbol, dates[i],
                  val(opens[i]), val(highs[i]), val(lows[i]), c,
                  int(volumes[i]), round(chg, 2), round(chg_pct, 2),
                  val(rsi_5[i]), val(rsi_14[i]), val(rsi_20[i]),
                  val(sma_5[i]), val(sma_10[i]), val(sma_20[i]), val(sma_60[i]),
                  val(ema_12[i]), val(ema_26[i]),
                  val(macd[i]), val(macd_sig[i]), val(macd_hist[i]),
                  val(k_arr[i]), val(d_arr[i]),
                  val(bb_u[i]), val(bb_m[i]), val(bb_l[i]),
                  val(atr_arr[i]), zone))
            inserted += 1

            if not np.isnan(rsi_14[i]) and prev_zone is not None:
                if prev_zone == "OVERSOLD" and zone in ("NEUTRAL_LOW", "NEUTRAL", "NEUTRAL_HIGH"):
                    cur.execute("""
                        INSERT OR IGNORE INTO rsi_signals
                        (symbol, date, rsi_value, zone, signal_type, price, expected_return)
                        VALUES (?, ?, ?, ?, 'ENTRY_OVERSOLD', ?, 1)
                    """, (symbol, dates[i], round(float(rsi_14[i]), 2), zone, c))
                    signals += 1
                elif prev_zone == "OVERBOUGHT" and zone in ("NEUTRAL", "NEUTRAL_HIGH", "NEUTRAL_LOW"):
                    cur.execute("""
                        INSERT OR IGNORE INTO rsi_signals
                        (symbol, date, rsi_value, zone, signal_type, price, expected_return)
                        VALUES (?, ?, ?, ?, 'EXIT_OVERBOUGHT', ?, -1)
                    """, (symbol, dates[i], round(float(rsi_14[i]), 2), zone, c))
                    signals += 1
            prev_zone = zone

        conn.commit()
        return inserted, signals

    except Exception as e:
        print(f"[ERR] {symbol} {name}: {e}")
        return 0, 0

def fetch_market_index(conn):
    try:
        ticker = yf.Ticker("^TWII")
        hist = ticker.history(period="2y")
        if hist.empty:
            return
        closes = list(hist["Close"].values)
        volumes = list(hist["Volume"].values)
        dates = [d.strftime("%Y-%m-%d") for d in hist.index]
        rsi_14 = list(calc_rsi(closes, 14))
        cur = conn.cursor()
        for i, d in enumerate(dates):
            rsi_val = float(rsi_14[i]) if not np.isnan(rsi_14[i]) else None
            cur.execute("""
                INSERT OR IGNORE INTO market_index (symbol, date, close, rsi_14, zone, volume)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ("TWII", d, round(float(closes[i]), 2), rsi_val, get_rsi_zone(rsi_val), int(volumes[i])))
        conn.commit()
        print("[OK] TWII market index stored")
    except Exception as e:
        print(f"[ERR] market TWII: {e}")

def verify_rsi_signals(conn, holding_days=5):
    cur = conn.cursor()
    cur.execute("""
        SELECT id, symbol, date, price, signal_type
        FROM rsi_signals
        WHERE verified = 0 AND signal_type = 'ENTRY_OVERSOLD'
        ORDER BY date DESC LIMIT 500
    """)
    pending = cur.fetchall()
    verified = 0

    for sig_id, sym, entry_date, entry_price, sig_type in pending:
        cur.execute("""
            SELECT close FROM daily_ohlcv
            WHERE symbol = ? AND date > ? AND date <= ?
            ORDER BY date LIMIT ?
        """, (sym, entry_date,
              (datetime.strptime(entry_date, "%Y-%m-%d") + timedelta(days=holding_days + 2)).strftime("%Y-%m-%d"),
              holding_days))
        rows = cur.fetchall()
        if len(rows) >= holding_days:
            exit_price = rows[holding_days - 1][0]
            ret_pct = ((exit_price - entry_price) / entry_price) * 100 if entry_price else 0
            outcome = "WIN" if ret_pct > 0 else "LOSS"
            exit_date = (datetime.strptime(entry_date, "%Y-%m-%d") + timedelta(days=holding_days)).strftime("%Y-%m-%d")
            cur.execute("""
                UPDATE rsi_signals
                SET verified = 1, outcome = ?, exit_date = ?, exit_price = ?,
                    return_pct = ?, hold_days = ?
                WHERE id = ?
            """, (outcome, exit_date, exit_price, round(ret_pct, 2), holding_days, sig_id))
            verified += 1

    conn.commit()
    return verified

def print_stats(conn):
    cur = conn.cursor()
    print('\n=== Taiwan Historical DB Stats ===')
    cur.execute('SELECT COUNT(DISTINCT symbol) FROM daily_ohlcv')
    print(f'Stocks: {cur.fetchone()[0]}')
    cur.execute('SELECT COUNT(*) FROM daily_ohlcv')
    print(f'OHLCV rows: {cur.fetchone()[0]}')
    cur.execute('SELECT COUNT(*) FROM rsi_signals')
    print(f'RSI signals: {cur.fetchone()[0]}')
    cur.execute('SELECT COUNT(*) FROM rsi_signals WHERE verified = 1')
    print(f'Verified: {cur.fetchone()[0]}')
    cur.execute('''
        SELECT outcome, COUNT(*), AVG(return_pct)
        FROM rsi_signals WHERE verified = 1 AND outcome IN ("WIN", "LOSS")
        GROUP BY outcome
    ''')
    print('\nVerified results:')
    for row in cur.fetchall():
        print(f'  {row[0]}: {row[1]} rows, Avg={row[2]:+.2f}%')
    cur.execute('SELECT zone, COUNT(*) FROM daily_ohlcv GROUP BY zone')
    print('\nRSI Zone distribution:')
    for row in cur.fetchall():
        print(f'  {row[0]}: {row[1]}')
    import os
    size = os.path.getsize(DB_PATH)
    print(f'\nDB size: {size:,} bytes ({size/1024/1024:.1f} MB)')
    conn.close()

def main():
    print('=== Taiwan Historical Trade DB v3 ===')
    print(f'Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    conn = init_db()
    stocks = get_stock_list()
    print(f'Stock list: {len(stocks)} stocks')

    cur = conn.cursor()
    for sym, name in stocks:
        try:
            cur.execute("INSERT OR IGNORE INTO stocks (symbol, name) VALUES (?, ?)", (sym, name))
        except:
            pass
    conn.commit()
    cur.execute('SELECT COUNT(*) FROM stocks')
    print(f'Stocks loaded: {cur.fetchone()[0]}')

    total_ohlcv = 0
    total_signals = 0

    # 剩餘28檔
    batch = stocks[30:]

    for i, (sym, name) in enumerate(batch):
        ins, sig = fetch_and_store_daily(conn, sym, name, years=2)
        total_ohlcv += ins
        total_signals += sig
        if ins > 0:
            print(f'  [{i+1}/{len(batch)}] {sym} {name}: {ins} rows, {sig} signals')
        else:
            print(f'  [{i+1}/{len(batch)}] {sym} {name}: FAILED')
        time.sleep(0.2)

    print(f'\nTotal: {total_ohlcv} OHLCV rows, {total_signals} RSI signals')

    fetch_market_index(conn)

    verified = verify_rsi_signals(conn, holding_days=5)
    print(f'Verified {verified} RSI signals')

    print_stats(conn)
    print(f'\nDB path: {DB_PATH}')
    print('=== Done ===')

if __name__ == '__main__':
    main()
