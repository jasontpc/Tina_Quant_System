# -*- coding: utf-8 -*-
"""
Tina ETF 定期更新腳本
=====================
每日/每週自動更新 ETF 本地資料庫
Cron: 0 16 * * 1-5（每日收盤更新）
"""
import yfinance as yf
import sqlite3
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
ETF_DB = WORKSPACE / "data" / "etf.db"

ETF_LIST = [
    ('0050.TW', '元大台灣50'), ('0056.TW', '元大高股息'),
    ('0051.TW', '元大台灣50單日反向'), ('0052.TW', '元大藍籌30'),
    ('0053.TW', '元大電子'), ('0055.TW', '元大MSCI金融'),
    ('0057.TW', '元大MSCI美國'),
    ('006208.TW', '富邦台50'), ('006203.TW', '富邦台50單日反向'),
    ('006204.TW', '富邦科技'),
    ('00713.TW', '元大高息低波'), ('00757.TW', '統一大FANG+'),
    ('00881.TW', '國泰台灣5G+'),
    ('00631L.TW', '元大台灣50正2'), ('00632R.TW', '元大台灣50反1'),
    ('00634R.TW', '元大科技正面'),
    ('00646.TW', '富邦S&P500'), ('00662.TW', '富邦NASDAQ100'),
    ('00891.TW', '中信中國50'), ('00892.TW', '中信特選高股息'),
    ('00895.TW', '中信關鍵半導體'), ('00896.TW', '中信綠能及電動車'),
    ('00701.TW', '國泰中型100'), ('00702.TW', '國泰20年美債'),
    ('00703.TW', '國泰5G'),
]


def update_etf(conn, symbol, name):
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM etf_info WHERE symbol=?', (symbol,))
    if c.fetchone()[0] == 0:
        c.execute('INSERT INTO etf_info (symbol, name, updated_at) VALUES (?, ?, ?)',
            (symbol, name, datetime.now().strftime('%Y-%m-%d')))

    tk = yf.Ticker(symbol)
    h = tk.history(period='60d')  # Only last 60 days for incremental
    if len(h) < 1:
        return {'symbol': symbol, 'name': name, 'inserted': 0, 'error': 'no data'}

    inserted = 0
    for i in range(len(h)):
        dt = h.index[i].strftime('%Y-%m-%d')
        row = h.iloc[i]
        try:
            c.execute('SELECT COUNT(*) FROM etf_daily WHERE symbol=? AND date=?', (symbol, dt))
            if c.fetchone()[0] == 0:
                c.execute('''INSERT INTO etf_daily (symbol,date,open,high,low,close,volume)
                    VALUES (?,?,?,?,?,?,?)''',
                    (symbol, dt, float(row['Open']), float(row['High']),
                     float(row['Low']), float(row['Close']), int(row['Volume'])))
                inserted += 1
        except: pass

    conn.commit()
    return {'symbol': symbol, 'name': name, 'inserted': inserted}


def main():
    print('='*60)
    print('  Tina ETF 定期更新')
    print('  ' + datetime.now().strftime('%Y-%m-%d %H:%M'))
    print('='*60)
    print()

    conn = sqlite3.connect(str(ETF_DB))
    total_inserted = 0
    updated = 0

    for symbol, name in ETF_LIST:
        result = update_etf(conn, symbol, name)
        if result['inserted'] > 0:
            print('  + ' + symbol + ' ' + name + ' +' + str(result['inserted']) + ' rows')
            total_inserted += result['inserted']
            updated += 1
        else:
            print('  . ' + symbol + ' ' + name + ' (up to date)')

    conn.close()

    print()
    print('Summary: ' + str(total_inserted) + ' new rows / ' + str(updated) + ' ETFs updated')
    print('='*60)


if __name__ == '__main__':
    main()