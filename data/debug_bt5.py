import sys, os, json
import numpy as np
import pandas as pd
import sqlite3
from pathlib import Path

WORKSPACE = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
DB_PATH   = WORKSPACE / 'data' / 'yfinance.db'

# Manually run all steps
conn = sqlite3.connect(str(DB_PATH))
df = pd.read_sql('''
    SELECT date, open, high, low, close, volume,
           change_pct, sma_20, sma_60, sma_120,
           rsi_14, atr_14, macd, macd_sig, macd_hist,
           bb_upper, bb_middle, bb_lower, vol_ratio
    FROM daily_ohlcv
    WHERE symbol=? AND date >= ? AND date <= ?
    ORDER BY date
''', conn, params=('2330.TW', '2024-01-01', '2026-05-08'), parse_dates=['date'])
conn.close()

print('Loaded df:', df.shape)
df = df[df['close'] > 0].copy()
print('After >0 filter:', df.shape)
df['rsi_14'] = df['rsi_14'].fillna(50)
df['atr_14'] = df['atr_14'].fillna(df['close'] * 0.02)
df['sma_20'] = df['sma_20'].fillna(df['close'])
df['sma_60'] = df['sma_60'].fillna(df['close'])
df['macd_hist'] = df['macd_hist'].fillna(0)

# Check entry signals
params = {
    'entry_rsi_max': 55, 'entry_rsi_min': 30,
    'ma_required': True, 'min_atr_pct': 0.005,
    'stop_loss_pct': 0.08, 'stop_loss_atr_x': 1.5,
    'take_profit_pct': 0.10, 'trailing_atr_x': 2.0,
    'max_hold_days': 7, 'position_pct': 0.10,
    'dca_frequency_days': 1
}

closes = df['close'].values
highs  = df['high'].values
lows   = df['low'].values
rsi    = df['rsi_14'].values
sma20  = df['sma_20'].values
sma60  = df['sma_60'].values

def calc_atr(highs, lows, closes, period=14):
    trs = np.zeros(len(highs))
    trs[1:] = np.maximum(highs[1:] - lows[1:], np.maximum(
        np.abs(highs[1:] - closes[:-1]), np.abs(lows[1:] - closes[:-1])))
    return pd.Series(trs).rolling(period).mean().fillna(0).values

atr14 = calc_atr(highs, lows, closes, 14)

entry_signals = [0] * len(df)
exit_signals  = [0] * len(df)
signal_reasons = [''] * len(df)

in_pos = False; entry_p = 0.0; entry_atr = 0.0; entry_idx = 0; high_water = 0.0

for i in range(50, len(df)):
    price = closes[i]; date = df['date'].iloc[i]

    if not in_pos:
        can_entry = True
        if rsi[i] >= params['entry_rsi_max'] or rsi[i] < params['entry_rsi_min']:
            can_entry = False
        if params['ma_required'] and not (sma20[i] > sma60[i]):
            can_entry = False
        if atr14[i] / price < params['min_atr_pct']:
            can_entry = False

        if can_entry:
            entry_signals[i] = 1
            signal_reasons[i] = f'ENTRY:RSI={rsi[i]:.1f}'
            in_pos = True; entry_p = price; entry_atr = atr14[i]; entry_idx = i; high_water = price
    else:
        high_water = max(high_water, price)
        ret_from_entry = (price / entry_p - 1) * 100
        days_held = i - entry_idx
        should_exit = False; exit_reason = ''

        if price <= entry_p * (1 - params['stop_loss_pct']):
            should_exit = True; exit_reason = f'SL:{ret_from_entry:.1f}%'
        elif params.get('stop_loss_atr_x') and price <= entry_p - entry_atr * params['stop_loss_atr_x']:
            should_exit = True; exit_reason = f'SL_ATR:{ret_from_entry:.1f}%'
        if not should_exit and i - entry_idx >= params['max_hold_days']:
            should_exit = True; exit_reason = f'HOLD_MAX:{days_held}d'

        if should_exit:
            exit_signals[i] = 1
            signal_reasons[i] = signal_reasons[i] + f' | {exit_reason}' if signal_reasons[i] else f'EXIT: {exit_reason}'
            in_pos = False

df['entry_signal'] = entry_signals
df['exit_signal']  = exit_signals
df['signal_reason'] = signal_reasons

print(f'Total entries: {sum(entry_signals)}, Total exits: {sum(exit_signals)}')
print(f'Entries: {[i for i, e in enumerate(entry_signals) if e]}')
print(f'Exits:   {[i for i, e in enumerate(exit_signals) if e]}')

# Simulate trades
capital = 1_000_000; position = 0; shares = 0; entry_price = 0; entry_date = None; trades = []

for i, row in df.iterrows():
    price = row['close']; date = row['date']

    if row['entry_signal'] == 1 and position == 0:
        alloc = capital * params['position_pct']
        shares = int(alloc / price)
        entry_price = price; position = 1
        entry_date = date

    elif row['exit_signal'] == 1 and position == 1:
        pnl_pct = (price / entry_price - 1) * 100
        pnl_abs = shares * (price - entry_price)
        capital += pnl_abs
        trades.append({'entry': str(entry_date)[:10], 'exit': str(date)[:10], 'pnl_pct': pnl_pct, 'reason': row['signal_reason']})
        position = 0; shares = 0

if position == 1:
    last_p = df['close'].iloc[-1]
    pnl_pct = (last_p / entry_price - 1) * 100
    capital += shares * (last_p - entry_price)
    trades.append({'entry': str(entry_date)[:10], 'exit': str(df['date'].iloc[-1])[:10], 'pnl_pct': pnl_pct, 'reason': 'END'})

print(f'\nTrades: {len(trades)}')
for t in trades:
    print(f'  {t["entry"]} -> {t["exit"]} | {t["pnl_pct"]:+.2f}% | {t["reason"]}')
print(f'\nFinal capital: {capital:.2f} | Return: {(capital/1e6-1)*100:+.2f}%')