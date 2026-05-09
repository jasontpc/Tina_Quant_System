import sys, os, json, sqlite3
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

WORKSPACE = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
DB_PATH   = WORKSPACE / 'data' / 'yfinance.db'
conn = sqlite3.connect(str(DB_PATH))

symbol = '2330.TW'
start  = '2024-01-01'
end    = '2026-05-08'

# Load via the same function as backtest_framework
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
df['macd_hist'] = df['macd_hist'].fillna(0)

# Reload btf with fresh import
sys.path.insert(0, str(WORKSPACE / 'scripts'))
import importlib, backtest_framework as btf
importlib.reload(btf)

print('BTF STRATEGIES:', list(btf.STRATEGIES.keys()))
print('BTF load_ohlcv callable:', callable(btf.load_ohlcv))
print('BTF generate_signals callable:', callable(btf.generate_signals))

# Test load_ohlcv
df2 = btf.load_ohlcv(symbol, start, end)
print(f'\nload_ohlcv returned shape: {df2.shape}')
print(f'Columns: {list(df2.columns)}')
print(f'entry_signal sum: {df2["entry_signal"].sum() if "entry_signal" in df2.columns else "N/A"}')

# Test generate_signals
df3 = btf.generate_signals(df.copy(), 'swing')
print(f'\ngenerate_signals returned shape: {df3.shape}')
print(f'entry_signal sum: {df3["entry_signal"].sum()}')
print(f'exit_signal sum: {df3["exit_signal"].sum()}')
print(f'Sample entry rows:')
print(df3[df3['entry_signal']==1][['date','close','rsi_14','sma_20','sma_60','entry_signal','exit_signal','signal_reason']].head(3).to_string())

# Test full run_backtest
result = btf.run_backtest(symbol, 'swing', start, end)
print(f'\nrun_backtest result: {result}')