# -*- coding: utf-8 -*-
"""更新關鍵股票最新報價到 DB"""
import yfinance as yf, sqlite3, sys
from pathlib import Path
from datetime import date, timedelta

sys.stdout.reconfigure(encoding='utf-8')
DB = Path('data/yfinance.db')

CRITICAL = ['2330.TW','2382.TW','3665.TW','0050.TW','SPY','QQQ','2359.TW','8299.TW','5269.TW','3711.TW','2464.TW','1590.TW','MSFT','CRM','1519.TW','3324.TWO','4966.TWO','3037.TW']
conn = sqlite3.connect(str(DB))
c = conn.cursor()

for sym in CRITICAL:
    try:
        tk = yf.Ticker(sym)
        h = tk.history(period='5d')
        if h is None or len(h) == 0:
            print(f'SKIP {sym}: no data')
            continue

        last_date = h.index[-1].strftime('%Y-%m-%d')
        last_price = float(h.iloc[-1]['Close'])

        c.execute('SELECT COUNT(*) FROM daily_ohlcv WHERE symbol=? AND date=?', (sym, last_date))
        exists = c.fetchone()[0]

        if exists == 0:
            o = float(h.iloc[-1]['Open'])
            high = float(h.iloc[-1]['High'])
            low = float(h.iloc[-1]['Low'])
            vol = int(h.iloc[-1]['Volume'])
            c.execute('INSERT INTO daily_ohlcv (symbol,date,open,high,low,close,volume) VALUES (?,?,?,?,?,?,?)',
                (sym, last_date, o, high, low, last_price, vol))
            conn.commit()
            print(f'+ {sym} {last_date} ${last_price}')
        else:
            print(f'  {sym} {last_date} ${last_price} (exists)')

    except Exception as e:
        print(f'ERR {sym}: {str(e)[:60]}')

conn.close()
print('Done')