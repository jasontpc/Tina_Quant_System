# -*- coding: utf-8 -*-
"""Maggy 美股每日DB收盤更新
=========================
yfinance + stocktwits_sentiment.db 更新（US AI Tech）
"""
import sys, sqlite3
from pathlib import Path
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
YFIN_DB = WORKSPACE / "data" / "yfinance.db"

US_STOCKS = ['NVDA', 'AMD', 'INTC', 'ASML', 'AVGO', 'QCOM', 'MU',
             'MSFT', 'GOOGL', 'META', 'AMZN', 'TSLA', 'AAPL']

def update_yfinance(symbols):
    import yfinance as yf
    conn = sqlite3.connect(YFIN_DB)
    c = conn.cursor()
    updated = 0
    for sym in symbols:
        try:
            tk = yf.Ticker(sym)
            hist = tk.history(period="5d")
            if len(hist) < 1:
                continue
            last = hist.iloc[-1]
            dt = hist.index[-1].strftime('%Y-%m-%d')
            c.execute('SELECT COUNT(*) FROM daily_ohlcv WHERE symbol=? AND date=?', (sym, dt))
            exists = c.fetchone()[0] > 0
            if not exists:
                c.execute('''
                    INSERT OR IGNORE INTO daily_ohlcv
                    (symbol, date, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (sym, dt, float(last['Open']), float(last['High']),
                     float(last['Low']), float(last['Close']), int(last['Volume'])))
                updated += 1
        except Exception as e:
            print(f'  {sym}: {e}')
    conn.commit()
    conn.close()
    return updated

def main():
    print(f'[Maggy DB Update] {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print(f'Updating {len(US_STOCKS)} US stocks...')
    n = update_yfinance(US_STOCKS)
    print(f'Inserted {n} new rows into yfinance.db')
    print(f'[OK] Maggy DB update complete')

if __name__ == '__main__':
    main()
