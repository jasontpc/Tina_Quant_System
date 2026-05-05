"""Daily DB Update Script - yfinance + TWSE 收盤後增量更新
======================================================
用法：
  python scripts/daily_db_update.py          # 全量更新（收盤後）
  python scripts/daily_db_update.py --quick  # 快速更新（當日新資料）
"""

import os
import sys
import json
import sqlite3
from datetime import datetime, date
import argparse

WORKSPACE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System'
DB_YF = os.path.join(WORKSPACE, 'data', 'yfinance.db')
DB_TWSE = os.path.join(WORKSPACE, 'data', 'twse_data.db')

UNIVERSE = {
    'core': ['2330.TW', '2382.TW', '00713.TW', '0050.TW'],
    'tw_etf': ['0056.TW', '00646.TW', '00662.TW', '00757.TW', '00927.TW'],
    'us_etf': ['SPY', 'QQQ', 'SOXL', 'TQQQ', 'SPXL', 'UPRO'],
    'index': ['^TWII', '^SPX', '^NDX'],
}
ALL_SYMBOLS = [s for group in UNIVERSE.values() for s in group]


def get_yf_conn():
    conn = sqlite3.connect(DB_YF)
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def compute_indicators(df):
    close = df['Close']
    df['sma_20'] = close.rolling(20).mean()
    df['sma_60'] = close.rolling(60).mean()
    df['sma_120'] = close.rolling(120).mean()
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, float('inf'))
    df['rsi_14'] = 100 - (100 / (1 + rs))
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    tr = high_low.combine(high_close, max).combine(low_close, max)
    df['atr_14'] = tr.rolling(14).mean()
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    df['macd'] = ema12 - ema26
    df['macd_sig'] = df['macd'].ewm(span=9).mean()
    df['macd_hist'] = df['macd'] - df['macd_sig']
    bb_middle = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    df['bb_upper'] = bb_middle + (bb_std * 2)
    df['bb_middle'] = bb_middle
    df['bb_lower'] = bb_middle - (bb_std * 2)
    df['vol_sma20'] = df['Volume'].rolling(20).mean()
    df['vol_ratio'] = df['Volume'] / df['vol_sma20']
    df['change_pct'] = close.pct_change() * 100
    return df


def update_yfinance_db(conn, quick=True):
    """更新 yfinance.db"""
    import yfinance as yf
    import pandas as pd

    c = conn.cursor()
    period = '3mo' if not quick else '5d'
    updated = 0
    errors = 0

    for sym in ALL_SYMBOLS:
        try:
            tk = yf.Ticker(sym)
            hist = tk.history(period=period, auto_adjust=True)
            if hist.empty:
                continue

            df = hist.copy()
            df = compute_indicators(df)
            df.index = df.index.strftime('%Y-%m-%d')

            for idx, row in df.iterrows():
                try:
                    c.execute('''
                        INSERT OR REPLACE INTO daily_ohlcv
                        (symbol, date, open, high, low, close, volume, change_pct,
                         sma_20, sma_60, sma_120, rsi_14, atr_14,
                         macd, macd_sig, macd_hist,
                         bb_upper, bb_middle, bb_lower, vol_ratio)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        sym, idx,
                        row['Open'], row['High'], row['Low'], row['Close'], int(row['Volume']),
                        round(float(row['change_pct']), 4) if pd.notna(row['change_pct']) else None,
                        round(float(row['sma_20']), 4) if pd.notna(row['sma_20']) else None,
                        round(float(row['sma_60']), 4) if pd.notna(row['sma_60']) else None,
                        round(float(row['sma_120']), 4) if pd.notna(row['sma_120']) else None,
                        round(float(row['rsi_14']), 4) if pd.notna(row['rsi_14']) else None,
                        round(float(row['atr_14']), 4) if pd.notna(row['atr_14']) else None,
                        round(float(row['macd']), 4) if pd.notna(row['macd']) else None,
                        round(float(row['macd_sig']), 4) if pd.notna(row['macd_sig']) else None,
                        round(float(row['macd_hist']), 4) if pd.notna(row['macd_hist']) else None,
                        round(float(row['bb_upper']), 4) if pd.notna(row['bb_upper']) else None,
                        round(float(row['bb_middle']), 4) if pd.notna(row['bb_middle']) else None,
                        round(float(row['bb_lower']), 4) if pd.notna(row['bb_lower']) else None,
                        round(float(row['vol_ratio']), 4) if pd.notna(row['vol_ratio']) else None,
                    ))
                    updated += 1
                except Exception:
                    pass
            conn.commit()
        except Exception as e:
            errors += 1

    c.execute('SELECT COUNT(*) FROM daily_ohlcv')
    total = c.fetchone()[0]
    c.execute('SELECT DISTINCT symbol FROM daily_ohlcv')
    syms = len(c.fetchall())

    return {'updated_rows': updated, 'errors': errors, 'total_rows': total, 'total_symbols': syms}


def update_twse_db(conn):
    """更新 TWSE data.db"""
    import requests

    c = conn.cursor()
    updated = 0

    # MI_5MINS
    try:
        r = requests.get(
            'https://www.twse.com.tw/exchangeReport/MI_5MINS?response=json',
            timeout=10, headers={'User-Agent': 'Mozilla/5.0'}
        )
        if r.status_code == 200:
            data = r.json()
            if data.get('stat') == 'OK':
                tradedate = data.get('date', '')
                rows = data.get('data', [])

                for row in rows:
                    if len(row) < 8:
                        continue
                    try:
                        c.execute('''
                            INSERT OR REPLACE INTO twse_mi_5mins
                            (tradedate, traded_time, bid_count_acc, bid_vol_acc,
                             ask_count_acc, ask_vol_acc, trade_count, trade_vol, trade_value)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            tradedate, row[0],
                            int(row[1].replace(',', '')),
                            int(row[2].replace(',', '')),
                            int(row[3].replace(',', '')),
                            int(row[4].replace(',', '')),
                            int(row[5].replace(',', '')),
                            int(row[6].replace(',', '')),
                            int(row[7].replace(',', '')),
                        ))
                        updated += 1
                    except Exception:
                        pass
                conn.commit()
                print(f'  MI_5MINS: {len(rows)} rows for {tradedate}')
    except Exception as e:
        print(f'  MI_5MINS error: {e}')

    # MI_INDEX
    try:
        r = requests.get(
            'https://www.twse.com.tw/exchangeReport/MI_INDEX?response=json&index=IX0001',
            timeout=10, headers={'User-Agent': 'Mozilla/5.0'}
        )
        if r.status_code == 200:
            data = r.json()
            if data.get('stat') == 'OK':
                tradedate = data.get('date', '')
                tables = data.get('tables', [])
                for t in tables:
                    title = t.get('title', '')
                    if title:
                        c.execute('''
                            INSERT OR REPLACE INTO twse_mi_index (tradedate, title, data)
                            VALUES (?, ?, ?)
                        ''', (tradedate, title, json.dumps(t.get('data', []))))
                conn.commit()
                print(f'  MI_INDEX: {len(tables)} tables for {tradedate}')
    except Exception as e:
        print(f'  MI_INDEX error: {e}')

    return updated


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--quick', action='store_true', help='Quick update (5d only)')
    args = parser.parse_args()

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'\n[Daily DB Update] {now}')
    print('=' * 60)

    # yfinance update
    print('\n[1] yfinance.db update...')
    conn_yf = get_yf_conn()
    result = update_yfinance_db(conn_yf, quick=args.quick)
    print(f'  Rows updated: {result["updated_rows"]}')
    print(f'  DB total: {result["total_rows"]:,} rows / {result["total_symbols"]} symbols')
    if result['errors']:
        print(f'  Errors: {result["errors"]}')
    conn_yf.close()

    # TWSE update
    print('\n[2] TWSE data.db update...')
    conn_twse = sqlite3.connect(DB_TWSE)
    conn_twse.execute('PRAGMA journal_mode=WAL')
    twse_updated = update_twse_db(conn_twse)
    print(f'  TWSE rows updated: {twse_updated}')
    conn_twse.close()

    print(f'\n[DONE] {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')


if __name__ == '__main__':
    run()
