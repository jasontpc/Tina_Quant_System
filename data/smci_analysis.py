import sqlite3, math
import pandas as pd
from pathlib import Path

DB_PATH = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\yfinance.db')
conn = sqlite3.connect(str(DB_PATH))

df = pd.read_sql('''
    SELECT date, open, high, low, close, volume, change_pct, rsi_14, sma_20, sma_60, atr_14, macd_hist
    FROM daily_ohlcv WHERE symbol='SMCI' AND date >= '2026-01-01' ORDER BY date
''', conn, parse_dates=['date'])
conn.close()

print('SMCI 最近60天:')
print(df[['date','close','rsi_14','sma_20','sma_60','macd_hist','volume']].tail(60).to_string())

last = df.iloc[-1]
print()
print('--- 關鍵數據 ---')
print('現價:', last['close'])
print('RSI:', last['rsi_14'])
print('MA20:', last['sma_20'] if not pd.isna(last['sma_20']) else 'N/A')
print('MA60:', last['sma_60'] if not pd.isna(last['sma_60']) else 'N/A')
print('ATR14:', last['atr_14'])
print('52w高:', df['close'].max())
print('52w低:', df['close'].min())

mom10 = (df.iloc[-1]['close'] / df.iloc[-11]['close'] - 1) * 100 if len(df) >= 11 else 0
mom30 = (df.iloc[-1]['close'] / df.iloc[-31]['close'] - 1) * 100 if len(df) >= 31 else 0
print('動能10日:', round(mom10, 1), '%')
print('動能30日:', round(mom30, 1), '%')

avg_vol = df['volume'].tail(20).mean()
print('20日均量:', round(avg_vol))
print('今日量:', int(last['volume']))
print('量比:', round(last['volume'] / avg_vol, 2), 'x')