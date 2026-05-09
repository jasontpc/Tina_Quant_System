import sqlite3
import numpy as np
import pandas as pd
from pathlib import Path

DB_PATH = Path('data/yfinance.db')

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

# Use df['sma_20'] and df['sma_60'] directly for entry check
in_pos    = False
entry_p   = 0.0
entry_idx = 0
atr_x     = 1.5
SL_PCT    = 0.08

entry_count = 0
exit_count  = 0

for i in range(50, len(df)):
    price = closes[i]
    date  = df['date'].iloc[i]

    if not in_pos:
        # Entry check using df['sma_20'] and df['sma_60']
        can_entry = True
        if rsi[i] >= 55 or rsi[i] < 30:
            can_entry = False
        if not (sma20[i] > sma60[i]):
            can_entry = False
        if atr[i] / price < 0.005:
            can_entry = False

        if can_entry:
            print(f'ENTRY bar={i} date={date.date()} price={price:.2f} rsi={rsi[i]:.1f} ma20={sma20[i]:.2f} ma60={sma60[i]:.2f}')
            in_pos    = True
            entry_p   = price
            entry_idx = i
            entry_count += 1
    else:
        # Exit check
        should_exit = False
        ret = (price / entry_p - 1) * 100

        if price <= entry_p * (1 - SL_PCT):
            should_exit = True
            print(f'EXIT bar={i} date={date.date()} price={price:.2f} ret={ret:.1f}% reason=SL')
        elif price <= entry_p - atr[i] * atr_x:
            should_exit = True
            print(f'EXIT bar={i} date={date.date()} price={price:.2f} ret={ret:.1f}% reason=SL_ATR')
        elif i - entry_idx >= 7:
            should_exit = True
            print(f'EXIT bar={i} date={date.date()} price={price:.2f} ret={ret:.1f}% reason=MAX_HOLD')
        else:
            pass  # still in position

        if should_exit:
            in_pos = False
            exit_count += 1

print(f'\nTotal entries: {entry_count}, Total exits: {exit_count}')