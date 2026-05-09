import sqlite3, json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

WORKSPACE = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
DB_PATH   = WORKSPACE / 'data' / 'yfinance.db'

symbols = ['2330.TW','3443.TW','2451.TW','3260.TW','6669.TW','2382.TW','3515.TW','6531.TW',
           'AMD','NVDA','AVGO','META','GOOGL','AMZN','MSFT','ANET','SMCI']

conn = sqlite3.connect(str(DB_PATH))
c = conn.cursor()

results = {}
for sym in symbols:
    df = pd.read_sql('''
        SELECT date, close, rsi_14, sma_20, sma_60, atr_14, macd_hist, change_pct, volume
        FROM daily_ohlcv WHERE symbol=? AND date >= '2026-01-01' ORDER BY date DESC LIMIT 60
    ''', conn, params=(sym,))
    
    if df.empty:
        results[sym] = None
        continue
    
    last = df.iloc[0]
    prev30 = df.iloc[min(29, len(df)-1)]
    
    mom10  = (last['close'] / df.iloc[min(9,len(df)-1)]['close'] - 1) * 100 if len(df)>=10 else 0
    mom30  = (last['close'] / prev30['close'] - 1) * 100 if len(df)>=30 else 0
    
    # Calculate ATR
    df2 = pd.read_sql('''
        SELECT high, low, close FROM daily_ohlcv WHERE symbol=? AND date >= '2026-01-01' ORDER BY date DESC LIMIT 20
    ''', conn, params=(sym,))
    if len(df2) >= 14:
        trs = []
        for i in range(1, len(df2)):
            tr = max(df2.iloc[i]['high']-df2.iloc[i]['low'],
                     abs(df2.iloc[i]['high']-df2.iloc[i-1]['close']),
                     abs(df2.iloc[i]['low']-df2.iloc[i-1]['close']))
            trs.append(tr)
        atr = np.mean(trs[-14:])
    else:
        atr = 0
    
    results[sym] = {
        'date':     str(last['date'])[:10],
        'close':    round(float(last['close']), 2),
        'rsi':      round(float(last['rsi_14']), 1) if last['rsi_14'] else None,
        'sma20':    round(float(last['sma_20']), 2) if last['sma_20'] else None,
        'sma60':    round(float(last['sma_60']), 2) if last['sma_60'] else None,
        'atr':      round(float(atr), 2),
        'atr_pct':  round(float(atr/last['close']*100), 2) if last['close'] else 0,
        'macd_hist': round(float(last['macd_hist']), 3) if last['macd_hist'] else 0,
        'mom10':    round(float(mom10), 1),
        'mom30':    round(float(mom30), 1),
        'chg_pct':  round(float(last['change_pct']), 2) if last['change_pct'] else 0,
        'volume':   int(last['volume']) if last['volume'] else 0,
    }

conn.close()

print(json.dumps(results, ensure_ascii=False, indent=2))