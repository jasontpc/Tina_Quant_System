import sys, os, json
import numpy as np
import pandas as pd
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

WORKSPACE = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
DB_PATH   = WORKSPACE / 'data' / 'yfinance.db'
conn = sqlite3.connect(str(DB_PATH))

symbol = '2330.TW'
start  = '2024-01-01'
end    = '2026-05-08'

df = pd.read_sql('''
    SELECT date, open, high, low, close, volume,
           change_pct, sma_20, sma_60, sma_120,
           rsi_14, atr_14, macd, macd_sig, macd_hist,
           bb_upper, bb_middle, bb_lower, vol_ratio
    FROM daily_ohlcv
    WHERE symbol=? AND date >= ? AND date <= ?
    ORDER BY date
''', conn, params=(symbol, start, end), parse_dates=['date'])
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
sma20  = df['sma_20'].values  # stored sma20
sma60  = df['sma_60'].values  # stored sma60

# ATR calculation
def calc_atr(highs, lows, closes, period=14):
    trs = np.zeros(len(highs))
    trs[1:] = np.maximum(highs[1:] - lows[1:], np.maximum(
        np.abs(highs[1:] - closes[:-1]), np.abs(lows[1:] - closes[:-1])))
    return pd.Series(trs).rolling(period).mean().fillna(0).values

atr14 = calc_atr(highs, lows, closes, 14)

# Generate signals
entry_signals = [0] * len(df)
exit_signals  = [0] * len(df)
signal_reasons = [''] * len(df)

SL_PCT = 0.08
ATR_X  = 1.5
MAX_DAYS = 7

in_pos    = False
entry_p   = 0.0
entry_atr = 0.0
entry_idx = 0

for i in range(50, len(df)):
    price = closes[i]
    date  = df['date'].iloc[i]

    if not in_pos:
        if rsi[i] >= 30 and rsi[i] < 55 and sma20[i] > sma60[i] and atr14[i] / price >= 0.005:
            if i % 1 == 0:  # DCA-like entry every bar for swing (not restricted)
                entry_signals[i] = 1
                signal_reasons[i] = f'ENTRY:RSI={rsi[i]:.1f}'
                in_pos = True
                entry_p   = price
                entry_atr = atr14[i]
                entry_idx = i
    else:
        should_exit = False
        exit_reason = ''
        if price <= entry_p * (1 - SL_PCT):
            should_exit = True; exit_reason = 'SL'
        elif price <= entry_p - entry_atr * ATR_X:
            should_exit = True; exit_reason = 'SL_ATR'
        elif i - entry_idx >= MAX_DAYS:
            should_exit = True; exit_reason = 'MAX_HOLD'

        if should_exit:
            exit_signals[i] = 1
            signal_reasons[i] = f'EXIT: {exit_reason}'
            in_pos = False

df['entry_signal'] = entry_signals
df['exit_signal']  = exit_signals
df['signal_reason'] = signal_reasons

# Run backtest
capital    = 1_000_000
position   = 0
shares     = 0
trades     = []

for i, row in df.iterrows():
    price = row['close']
    date  = row['date']
    es    = row['entry_signal']
    xs    = row['exit_signal']

    if es == 1 and position == 0:
        alloc   = capital * 0.10
        shares  = int(alloc / price)
        entry_p = price
        position = 1
        print(f'  BUY  {date.date()} {price:.2f} x{shares} rsi={row["rsi_14"]:.1f} reason={row["signal_reason"]}')

    elif xs == 1 and position == 1:
        pnl_pct = (price / entry_p - 1) * 100
        proceeds = shares * price
        pnl_abs  = proceeds - shares * entry_p
        capital += pnl_abs
        print(f'  SELL {date.date()} {price:.2f} pnl={pnl_pct:+.2f}% reason={row["signal_reason"]}')
        position = 0
        shares   = 0

print(f'\nFinal capital: {capital:.2f} | Return: {(capital/1e6-1)*100:+.2f}%')