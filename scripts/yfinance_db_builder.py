"""yfinance Unified DB Builder v2
==================================
建立單一本地 SQLite 資料庫，涵蓋 Jo 的完整投資宇宙

Architecture:
  - data/yfinance.db: 單一資料庫
    - symbols: 標的元數據
    - daily_ohlcv: 日K + 技術指標
    - fetch_log: 抓取歷史
"""

import os
import json
import sqlite3
from datetime import datetime, date, timedelta
import subprocess

WORKSPACE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System'
DB_PATH = os.path.join(WORKSPACE, 'data', 'yfinance.db')
LOG_DIR = os.path.join(WORKSPACE, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# Jo 的投資宇宙（按優先級）
UNIVERSE = {
    # 核心持倉
    'core': [
        '2330.TW',  # 台積電
        '2382.TW',  # 廣達
        '00713.TW', # 元大高息低波
        '0050.TW',  # 元大台灣50
    ],
    # TW ETFs
    'tw_etf': [
        '0056.TW',  # 元大高股息
        '00646.TW', # 富邦S&P500
        '00662.TW', # 富邦NASDAQ100
        '00757.TW', # 統一大FANG+
        '00927.TW', # 統一手創未來
    ],
    # US ETFs
    'us_etf': [
        'SPY',      # S&P 500
        'QQQ',      # NASDAQ 100
        'SOXL',     # 3x 半導體
        'TQQQ',     # 3x QQQ
        'SPXL',     # 3x S&P500
        'UPRO',     # 3x S&P500
    ],
    # Indices
    'index': [
        '^TWII',    # 台灣加權
        '^SPX',     # S&P 500
        '^NDX',     # NASDAQ 100
    ],
}

# 技術指標計算
def compute_indicators(df):
    """計算技術指標"""
    close = df['Close']

    # SMA
    df['sma_20'] = close.rolling(20).mean()
    df['sma_60'] = close.rolling(60).mean()
    df['sma_120'] = close.rolling(120).mean()

    # RSI
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, float('inf'))
    df['rsi_14'] = 100 - (100 / (1 + rs))

    # ATR
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    tr = high_low.clip(lower=high_close.clip(lower=low_close))
    df['atr_14'] = tr.rolling(14).mean()

    # MACD
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    df['macd'] = ema12 - ema26
    df['macd_sig'] = df['macd'].ewm(span=9).mean()
    df['macd_hist'] = df['macd'] - df['macd_sig']

    # Bollinger Bands
    bb_middle = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    df['bb_upper'] = bb_middle + (bb_std * 2)
    df['bb_middle'] = bb_middle
    df['bb_lower'] = bb_middle - (bb_std * 2)

    # Volume ratio
    df['vol_sma20'] = df['Volume'].rolling(20).mean()
    df['vol_ratio'] = df['Volume'] / df['vol_sma20']

    # Change %
    df['change_pct'] = close.pct_change() * 100

    return df


def get_db_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db(conn):
    c = conn.cursor()

    # Symbols metadata
    c.execute('''
        CREATE TABLE IF NOT EXISTS symbols (
            symbol TEXT PRIMARY KEY,
            name TEXT,
            exchange TEXT,
            category TEXT,
            universe_group TEXT,
            last_updated TEXT,
            notes TEXT
        )
    ''')

    # Daily OHLCV with indicators
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_ohlcv (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL, high REAL, low REAL, close REAL,
            volume INTEGER,
            change_pct REAL,
            sma_20 REAL, sma_60 REAL, sma_120 REAL,
            rsi_14 REAL,
            atr_14 REAL,
            macd REAL, macd_sig REAL, macd_hist REAL,
            bb_upper REAL, bb_middle REAL, bb_lower REAL,
            vol_ratio REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, date)
        )
    ''')

    # Fetch log
    c.execute('''
        CREATE TABLE IF NOT EXISTS fetch_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            symbol TEXT,
            status TEXT,
            rows_fetched INTEGER,
            rows_saved INTEGER,
            error TEXT
        )
    ''')

    # Index: symbol + date
    c.execute('CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_date ON daily_ohlcv(symbol, date)')

    conn.commit()


def upsert_symbols(conn, symbols_list, group):
    c = conn.cursor()
    for sym in symbols_list:
        c.execute('''
            INSERT INTO symbols (symbol, universe_group, last_updated)
            VALUES (?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                universe_group = excluded.universe_group,
                last_updated = excluded.last_updated
        ''', (sym, group, datetime.now().isoformat()))
    conn.commit()


def fetch_and_save(conn, symbol, period='max', chunk_days=1000):
    """抓取並寫入一檔標的"""
    import yfinance as yf

    c = conn.cursor()

    try:
        tk = yf.Ticker(symbol)

        # 取得歷史資料
        hist = tk.history(period=period, auto_adjust=True)
        if hist.empty:
            log_fetch(conn, symbol, 'EMPTY', 0, 0, 'No data')
            return 0

        # 計算技術指標
        df = hist.copy()
        df = compute_indicators(df)
        df.index = df.index.strftime('%Y-%m-%d')

        rows_saved = 0
        for idx, row in df.iterrows():
            try:
                c.execute('''
                    INSERT OR REPLACE INTO daily_ohlcv
                    (symbol, date, open, high, low, close, volume,
                     change_pct, sma_20, sma_60, sma_120,
                     rsi_14, atr_14,
                     macd, macd_sig, macd_hist,
                     bb_upper, bb_middle, bb_lower,
                     vol_ratio)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    symbol, idx,
                    row['Open'], row['High'], row['Low'], row['Close'], int(row['Volume']),
                    round(row.get('change_pct', 0), 4),
                    round(row.get('sma_20', 0), 4) if pd.notna(row.get('sma_20')) else None,
                    round(row.get('sma_60', 0), 4) if pd.notna(row.get('sma_60')) else None,
                    round(row.get('sma_120', 0), 4) if pd.notna(row.get('sma_120')) else None,
                    round(row.get('rsi_14', 0), 4) if pd.notna(row.get('rsi_14')) else None,
                    round(row.get('atr_14', 0), 4) if pd.notna(row.get('atr_14')) else None,
                    round(row.get('macd', 0), 4) if pd.notna(row.get('macd')) else None,
                    round(row.get('macd_sig', 0), 4) if pd.notna(row.get('macd_sig')) else None,
                    round(row.get('macd_hist', 0), 4) if pd.notna(row.get('macd_hist')) else None,
                    round(row.get('bb_upper', 0), 4) if pd.notna(row.get('bb_upper')) else None,
                    round(row.get('bb_middle', 0), 4) if pd.notna(row.get('bb_middle')) else None,
                    round(row.get('bb_lower', 0), 4) if pd.notna(row.get('bb_lower')) else None,
                    round(row.get('vol_ratio', 0), 4) if pd.notna(row.get('vol_ratio')) else None,
                ))
                rows_saved += 1
            except Exception as e:
                pass

        conn.commit()

        # Update symbol last_updated
        c.execute('UPDATE symbols SET last_updated=? WHERE symbol=?',
                  (datetime.now().isoformat(), symbol))

        log_fetch(conn, symbol, 'OK', len(hist), rows_saved, '')
        return rows_saved

    except Exception as e:
        log_fetch(conn, symbol, 'ERROR', 0, 0, str(e)[:200])
        return 0


def log_fetch(conn, symbol, status, rows_fetched, rows_saved, error):
    c = conn.cursor()
    c.execute('''
        INSERT INTO fetch_log (timestamp, symbol, status, rows_fetched, rows_saved, error)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (datetime.now().isoformat(), symbol, status, rows_fetched, rows_saved, error))
    conn.commit()


def get_symbols_to_update(conn, groups=None, min_interval_hours=24):
    """取得需要更新的標的"""
    c = conn.cursor()
    query = 'SELECT symbol FROM symbols'
    if groups:
        placeholders = ','.join(['?' for _ in groups])
        query += f' WHERE universe_group IN ({placeholders})'

    c.execute(query, groups if groups else [])
    results = []

    for row in c.fetchall():
        sym = row[0]
        c.execute('SELECT MAX(date) FROM daily_ohlcv WHERE symbol=?', (sym,))
        last_date_row = c.fetchone()[0]
        if not last_date_row:
            results.append(sym)
            continue
        last_date = datetime.strptime(last_date_row, '%Y-%m-%d')
        hours_since = (datetime.now() - last_date).total_seconds() / 3600
        if hours_since >= min_interval_hours:
            results.append(sym)

    return results


def run():
    import pandas as pd
    import yfinance as yf

    print('[yfinance Unified DB Builder v2]')
    print('=' * 60)

    conn = get_db_conn()
    init_db(conn)

    # Register all symbols
    all_symbols = []
    for group, syms in UNIVERSE.items():
        upsert_symbols(conn, syms, group)
        all_symbols.extend(syms)

    print(f'\n[*] Universe: {len(all_symbols)} symbols')
    for group, syms in UNIVERSE.items():
        print(f'    {group}: {len(syms)} symbols - {syms}')

    # Check what needs update
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM daily_ohlcv')
    current_rows = c.fetchone()[0]
    print(f'\n[*] Current DB: {current_rows:,} rows')

    # Check which symbols have data
    c.execute('SELECT DISTINCT symbol FROM daily_ohlcv')
    existing = [r[0] for r in c.fetchall()]
    print(f'[*] Symbols with data: {len(existing)}')

    need_update = [s for s in all_symbols if s not in existing]

    if need_update:
        print(f'\n[*] Fetching {len(need_update)} new symbols...')
        for i, sym in enumerate(need_update):
            print(f'  [{i+1}/{len(need_update)}] {sym}...', end=' ', flush=True)
            saved = fetch_and_save(conn, sym, period='max')
            print(f'saved={saved}')
    else:
        print('\n[*] All symbols up to date. Checking for daily update...')
        # Quick update - only last 5 days
        for sym in all_symbols:
            tk = yf.Ticker(sym)
            hist = tk.history(period='5d')
            if not hist.empty:
                df = hist.copy()
                df = compute_indicators(df)
                df.index = df.index.strftime('%Y-%m-%d')
                for idx, row in df.iterrows():
                    try:
                        c.execute('''
                            INSERT OR REPLACE INTO daily_ohlcv
                            (symbol, date, open, high, low, close, volume,
                             change_pct, sma_20, sma_60, sma_120,
                             rsi_14, atr_14,
                             macd, macd_sig, macd_hist,
                             bb_upper, bb_middle, bb_lower, vol_ratio)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            sym, idx,
                            row['Open'], row['High'], row['Low'], row['Close'], int(row['Volume']),
                            round(row.get('change_pct', 0), 4),
                            round(row.get('sma_20', 0), 4) if pd.notna(row.get('sma_20')) else None,
                            round(row.get('sma_60', 0), 4) if pd.notna(row.get('sma_60')) else None,
                            round(row.get('sma_120', 0), 4) if pd.notna(row.get('sma_120')) else None,
                            round(row.get('rsi_14', 0), 4) if pd.notna(row.get('rsi_14')) else None,
                            round(row.get('atr_14', 0), 4) if pd.notna(row.get('atr_14')) else None,
                            round(row.get('macd', 0), 4) if pd.notna(row.get('macd')) else None,
                            round(row.get('macd_sig', 0), 4) if pd.notna(row.get('macd_sig')) else None,
                            round(row.get('macd_hist', 0), 4) if pd.notna(row.get('macd_hist')) else None,
                            round(row.get('bb_upper', 0), 4) if pd.notna(row.get('bb_upper')) else None,
                            round(row.get('bb_middle', 0), 4) if pd.notna(row.get('bb_middle')) else None,
                            round(row.get('bb_lower', 0), 4) if pd.notna(row.get('bb_lower')) else None,
                            round(row.get('vol_ratio', 0), 4) if pd.notna(row.get('vol_ratio')) else None,
                        ))
                    except Exception:
                        pass
                conn.commit()
        print('  [OK] Daily update complete')

    # Summary
    c.execute('SELECT COUNT(*) FROM daily_ohlcv')
    total = c.fetchone()[0]
    c.execute('SELECT DISTINCT symbol FROM daily_ohlcv')
    syms_with_data = len(c.fetchall())
    print(f'\n[*] Final DB: {total:,} rows for {syms_with_data} symbols')
    print(f'[*] DB: {DB_PATH}')

    conn.close()
    print('[DONE]')


if __name__ == '__main__':
    run()
