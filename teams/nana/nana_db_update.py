# -*- coding: utf-8 -*-
"""Nana 波段每日DB收盤更新
=========================
yfinance + limitup.db 增量更新
"""
import sys, sqlite3
from pathlib import Path
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
YFIN_DB = WORKSPACE / "data" / "yfinance.db"
LU_DB = WORKSPACE / "data" / "limitup.db"

TW_STOCKS = ['2382.TW', '2330.TW', '3665.TW', '2317.TW', '3034.TW',
             '2454.TW', '4961.TW', '3231.TW', '3017.TW', '3717.TW']
US_STOCKS = ['SOXL', 'SOXS', 'TQQQ', 'UPRO', 'SPXL', 'QQQ', 'SPY']

def update_yfinance(symbols):
    import yfinance as yf
    conn = sqlite3.connect(YFIN_DB)
    c = conn.cursor()
    updated = 0
    for sym in symbols:
        try:
            tk = yf.Ticker(sym.replace('.TW', ''))
            if '.TW' in sym:
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
    print(f'[Nana DB Update] {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    all_syms = TW_STOCKS + US_STOCKS
    print(f'Updating {len(all_syms)} symbols...')
    n = update_yfinance(all_syms)
    print(f'Inserted {n} new rows into yfinance.db')
    print(f'[OK] Nana DB update complete')

if __name__ == '__main__':
    main()
