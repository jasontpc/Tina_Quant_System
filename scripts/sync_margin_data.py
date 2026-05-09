"""
台股 Margin 資料同步腳本（統合作業）
統一 TWSE API + FinMind API → data/tw_margin.db
取代獨立的 fetch_twse_margin.py 和 fetch_margin_finmind.py
"""
import sqlite3, requests, json
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / 'data' / 'tw_margin.db'
TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjJ9.1LHB4yKHeZFoXStyjK2W9F6X3nZLMA1IfPWpDVlv6K0'
FINMIND_BASE = 'https://api.finmindtrade.com/api/v4/data'

# 監控名單
STOCKS = ['2330','2454','2379','3035','3653','2382','3034','4938','2376','3665',
          '6153','2317','6706','6271','3016','6230','6230','2303','3515','4979']

def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS margin_summary
                 (stock_id TEXT, date TEXT, margin_buy INTEGER, margin_repay INTEGER,
                  margin_balance INTEGER, short_cover INTEGER, short_sell INTEGER,
                  short_balance INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                  UNIQUE(stock_id, date))''')
    conn.commit()
    return conn

def fetch_finmind(conn, symbol, days=5):
    """FinMind 取得融資融券（最新 API）"""
    end = datetime.now().strftime('%Y-%m-%d')
    start = (datetime.now() - timedelta(days)).strftime('%Y-%m-%d')
    params = {'dataset':'TaiwanStockShortVolume', 'data_id':symbol,
              'start_date':start, 'end_date':end, 'token':TOKEN}
    try:
        r = requests.get(FINMIND_BASE, params=params, timeout=15)
        data = r.json().get('data', [])
        saved = 0
        for row in data:
            date_str = row.get('date','')
            conn.execute('''INSERT OR IGNORE INTO margin_summary
                          (stock_id, date, margin_buy, margin_balance, short_sell, short_balance)
                          VALUES (?,?,?,?,?,?)''',
                        (symbol, date_str,
                         row.get('ShortSaleBuy',0), row.get('ShortSaleBalance',0),
                         row.get('ShortSale',0), row.get('ShortSaleBalance',0)))
            saved += 1
        conn.commit()
        print(f'  {symbol}: FinMind {saved} rows')
        return saved
    except Exception as e:
        print(f'  {symbol}: FinMind ERROR {e}')
        return 0

def fetch_twse(conn, date_str):
    """TWSE API 取得融資融券"""
    url = f'https://openapi.twse.com.tw/v1/BFIAUU_d/{date_str}'
    try:
        r = requests.get(url, timeout=15)
        if r.text.startswith('{') or not r.text.strip():
            print(f'  TWSE {date_str}: no data')
            return 0
        # CSV format
        lines = r.text.strip().split('\n')
        saved = 0
        for line in lines[1:]:
            parts = line.split(',')
            if len(parts) < 9: continue
            sid = parts[0].strip()
            if sid not in STOCKS: continue
            conn.execute('''INSERT OR IGNORE INTO margin_summary
                          (stock_id, date, margin_buy, margin_repay, margin_balance,
                           short_cover, short_sell, short_balance)
                          VALUES (?,?,?,?,?,?,?,?)''',
                        (sid, date_str,
                         int(parts[3].strip()) if parts[3].strip() else 0,
                         int(parts[4].strip()) if parts[4].strip() else 0,
                         int(parts[5].strip()) if parts[5].strip() else 0,
                         int(parts[6].strip()) if parts[6].strip() else 0,
                         int(parts[7].strip()) if parts[7].strip() else 0,
                         int(parts[8].strip()) if parts[8].strip() else 0))
            saved += 1
        conn.commit()
        print(f'  TWSE {date_str}: {saved} rows')
        return saved
    except Exception as e:
        print(f'  TWSE {date_str}: ERROR {e}')
        return 0

def main():
    print(f'[Margin Sync] Starting at {datetime.now().strftime("%H:%M:%S")}')
    conn = init_db()
    
    today = datetime.now().strftime('%Y-%m-%d')
    today_str = datetime.now().strftime('%Y%m%d')
    
    # 1. FinMind (5 days back)
    print('\n[FinMind]')
    total = 0
    for sym in STOCKS:
        total += fetch_finmind(conn, sym, days=5)
    print(f'FinMind total: {total} rows')
    
    # 2. TWSE today
    print('\n[TWSE]')
    total += fetch_twse(conn, today_str)
    
    conn.close()
    print(f'\n[Margin Sync] Done. Total: {total} rows')

if __name__ == '__main__':
    main()