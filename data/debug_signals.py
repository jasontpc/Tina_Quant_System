import sqlite3, sys
import numpy as np
import pandas as pd
from pathlib import Path

DB_PATH = Path('data/yfinance.db')

def calc_rsi(closes: np.ndarray, period: int = 14) -> np.ndarray:
    if len(closes) < period + 1:
        return np.full_like(closes, 50.0)
    deltas = np.diff(closes, prepend=closes[0])
    gains  = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_g  = pd.Series(gains).rolling(period).mean().values
    avg_l  = pd.Series(losses).rolling(period).mean().values
    rs     = avg_g / np.where(avg_l == 0, 1e-10, avg_l)
    return 100 - (100 / (1 + rs))

def calc_atr(highs, lows, closes, period=14):
    trs = np.zeros(len(highs))
    trs[1:] = np.maximum(highs[1:] - lows[1:], np.maximum(np.abs(highs[1:] - closes[:-1]), np.abs(lows[1:] - closes[:-1])))
    return pd.Series(trs).rolling(period).mean().fillna(0).values

def calc_ma(closes, n):
    return pd.Series(closes).rolling(n).mean().fillna(method='bfill').values

conn = sqlite3.connect(str(DB_PATH))
df = pd.read_sql('''
    SELECT date, open, high, low, close, volume,
           change_pct, sma_20, sma_60, sma_120,
           rsi_14, atr_14, macd, macd_sig, macd_hist,
           bb_upper, bb_middle, bb_lower, vol_ratio
    FROM daily_ohlcv
    WHERE symbol='2330.TW' AND date >= '2024-01-01' AND date <= '2026-05-08'
    ORDER BY date
''', conn, parse_dates=['date'])
conn.close()

print(f'Loaded {len(df)} rows')
df = df[df['close'] > 0].copy()
df['rsi_14'] = df['rsi_14'].fillna(50)
df['atr_14'] = df['atr_14'].fillna(df['close'] * 0.02)
df['sma_20'] = df['sma_20'].fillna(df['close'])
df['sma_60'] = df['sma_60'].fillna(df['close'])

closes = df['close'].values
highs  = df['high'].values
lows   = df['low'].values
rsi    = df['rsi_14'].values
atr    = df['atr_14'].values
sma20  = df['sma_20'].values
sma60  = df['sma_60'].values

ma20 = calc_ma(closes, 20)
ma60 = calc_ma(closes, 60)
atr14 = calc_atr(highs, lows, closes, 14)

print('First 10 rows (bar, date, close, rsi, ma20, ma60, ma_bull, atr_pct):')
for i in range(10, 60):
    bull = ma20[i] > ma60[i]
    print(f'  bar={i} date={df["date"].iloc[i].date()} close={closes[i]:.2f} rsi={rsi[i]:.1f} ma20={ma20[i]:.2f} ma60={ma60[i]:.2f} bull={bull} atr%={atr14[i]/closes[i]*100:.2f}%')

# Check how many bars meet entry criteria
entries = []
for i in range(50, len(df)):
    if rsi[i] >= 30 and rsi[i] < 55 and ma20[i] > ma60[i] and atr14[i] / closes[i] >= 0.005:
        entries.append(i)

print(f'\nTotal entries found: {len(entries)}')
if entries:
    print(f'First 5 entry bars: {entries[:5]}')
    print(f'First entry date: {df["date"].iloc[entries[0]].date()}, close={closes[entries[0]]:.2f}')