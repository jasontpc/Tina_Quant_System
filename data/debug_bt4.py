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

# Run backtest via backtest_framework
sys.path.insert(0, str(WORKSPACE / 'scripts'))
import importlib
import backtest_framework as btf
importlib.reload(btf)

result = btf.run_backtest(symbol, 'swing', start, end)
print('Result:', result)