"""yfinance DB Loader - Fast batch loader for remaining 17 symbols"""
import yfinance as yf
import sqlite3
from datetime import datetime
import pandas as pd

WORKSPACE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System'
DB_PATH = f'{WORKSPACE}\\data\\yfinance.db'
conn = sqlite3.connect(DB_PATH)
conn.execute('PRAGMA journal_mode=WAL')
conn.execute('PRAGMA foreign_keys = ON')

UNIVERSE = {
    'core': ['2330.TW', '2382.TW', '00713.TW', '0050.TW'],
    'tw_etf': ['0056.TW', '00646.TW', '00662.TW', '00757.TW', '00927.TW'],
    'us_etf': ['SPY', 'QQQ', 'SOXL', 'TQQQ', 'SPXL', 'UPRO'],
    'index': ['^TWII', '^SPX', '^NDX'],
}

all_syms = [s for group in UNIVERSE.values() for s in group]

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


def fetch_and_save(symbol):
    try:
        tk = yf.Ticker(symbol)
        hist = tk.history(period='max')
        if hist.empty:
            print(f'  EMPTY: {symbol}')
            return 0

        df = hist.copy()
        df = compute_indicators(df)
        df.index = df.index.strftime('%Y-%m-%d')

        c = conn.cursor()
        saved = 0
        for idx, row in df.iterrows():
            try:
                c.execute('''
                    INSERT OR REPLACE INTO daily_ohlcv
                    (symbol, date, open, high, low, close, volume, change_pct,
                     sma_20, sma_60, sma_120, rsi_14, atr_14, macd, macd_sig, macd_hist,
                     bb_upper, bb_middle, bb_lower, vol_ratio)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    symbol, idx,
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
                saved += 1
            except Exception as e:
                pass
        conn.commit()
        return saved
    except Exception as e:
        print(f'  ERROR {symbol}: {e}')
        return 0


# Check which need loading
c = conn.cursor()
c.execute('SELECT DISTINCT symbol FROM daily_ohlcv')
existing = {r[0] for r in c.fetchall()}
need = [s for s in all_syms if s not in existing]
print(f'Loading {len(need)} symbols: {need}')

for i, sym in enumerate(need):
    print(f'[{i+1}/{len(need)}] {sym}...', end=' ', flush=True)
    saved = fetch_and_save(sym)
    print(f'{saved} rows')

# Summary
c.execute('SELECT COUNT(*) FROM daily_ohlcv')
print(f'\nTotal rows in DB: {c.fetchone()[0]:,}')
c.execute('SELECT DISTINCT symbol FROM daily_ohlcv')
syms = [r[0] for r in c.fetchall()]
print(f'Symbols: {len(syms)} - {syms}')
conn.close()
print('DONE')
