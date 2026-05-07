"""FinMind Data Fetcher - 全方位台股資料庫
====================================
目標：建立 FinMind 本地 SQLite，涵蓋法人/籌碼/財務/技術面

資料集優先級：
  P1 (法人籌碼): TaiwanStockInstitutionalInvestorsBuySell, TaiwanStockMarginPurchaseShortSale
  P2 (價格技術): TaiwanStockPrice, TaiwanStockKBar, TaiwanStockPER
  P3 (財務基本面): TaiwanStockFinancialStatements, TaiwanStockBalanceSheet, TaiwanStockMonthRevenue
  P4 (期貨): TaiwanFuturesDaily, TaiwanFuturesInstitutionalInvestors
"""

import os
import json
import sqlite3
from datetime import datetime, date, timedelta
import time

WORKSPACE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System'
DB_PATH = os.path.join(WORKSPACE, 'data', 'finmind.db')
FINMIND_TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjF9.ivums9mfJUrM2MYazJiOEg49RiYLOJMZtejqX79YWS8'
BASE_URL = 'https://api.finmindtrade.com/api/v4/data'

# Jo's core stocks
CORE_STOCKS = ['2330', '2382', '2317', '2454', '3034', '3665', '0050', '00713']

# Priority datasets
DATASETS = {
    'TaiwanStockPrice': {
        'desc': '日K價格', 'priority': 1,
        'params': {'data_id': '{stock}', 'start_date': '{start}', 'end_date': '{end}'}
    },
    'TaiwanStockInstitutionalInvestorsBuySell': {
        'desc': '三大法人買賣', 'priority': 1,
        'params': {'data_id': '{stock}', 'start_date': '{start}', 'end_date': '{end}'}
    },
    'TaiwanStockMarginPurchaseShortSale': {
        'desc': '資券融餘額', 'priority': 2,
        'params': {'data_id': '{stock}', 'start_date': '{start}', 'end_date': '{end}'}
    },
    'TaiwanStockTotalInstitutionalInvestors': {
        'desc': '總法人買賣', 'priority': 1,
        'params': {'data_id': '{stock}', 'start_date': '{start}', 'end_date': '{end}'}
    },
    'TaiwanFuturesInstitutionalInvestors': {
        'desc': '期貨法人持仓', 'priority': 2,
        'params': {'data_id': 'TX', 'start_date': '{start}', 'end_date': '{end}'}
    },
    'TaiwanFuturesDaily': {
        'desc': '期貨日行情', 'priority': 2,
        'params': {'data_id': 'TX', 'start_date': '{start}', 'end_date': '{end}'}
    },
    'TaiwanStockPER': {
        'desc': '本益比/殖利率', 'priority': 2,
        'params': {'data_id': '{stock}', 'start_date': '{start}', 'end_date': '{end}'}
    },
    'TaiwanStockMonthRevenue': {
        'desc': '月營收', 'priority': 3,
        'params': {'data_id': '{stock}', 'start_date': '{start}', 'end_date': '{end}'}
    },
    'TaiwanStockFinancialStatements': {
        'desc': '財務報表', 'priority': 3,
        'params': {'data_id': '{stock}', 'start_date': '{start}', 'end_date': '{end}'}
    },
}


def get_db_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def init_db(conn):
    c = conn.cursor()

    # Price data
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_price (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_id TEXT, date TEXT,
            open REAL, high REAL, low REAL, close REAL,
            volume INTEGER, turnover REAL,
            spread INTEGER,
            UNIQUE(stock_id, date)
        )
    ''')

    # Institutional buy/sell
    c.execute('''
        CREATE TABLE IF NOT EXISTS institutional (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_id TEXT, date TEXT,
            buy_volume INTEGER, sell_volume INTEGER,
            net_volume INTEGER,
            UNIQUE(stock_id, date)
        )
    ''')

    # Margin balance
    c.execute('''
        CREATE TABLE IF NOT EXISTS margin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_id TEXT, date TEXT,
            margin_balance INTEGER, short_balance INTEGER,
            margin_ratio REAL,
            UNIQUE(stock_id, date)
        )
    ''')

    # PER / Dividend yield
    c.execute('''
        CREATE TABLE IF NOT EXISTS per_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_id TEXT, date TEXT,
            per REAL, yield REAL, pbr REAL,
            UNIQUE(stock_id, date)
        )
    ''')

    # Futures
    c.execute('''
        CREATE TABLE IF NOT EXISTS futures_daily (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, contract TEXT,
            open REAL, high REAL, low REAL, close REAL,
            volume INTEGER, open_interest INTEGER,
            UNIQUE(contract, date)
        )
    ''')

    # Futures institutional
    c.execute('''
        CREATE TABLE IF NOT EXISTS futures_institutional (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, contract TEXT,
            buy_volume INTEGER, sell_volume INTEGER,
            UNIQUE(contract, date)
        )
    ''')

    # Month revenue
    c.execute('''
        CREATE TABLE IF NOT EXISTS month_revenue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_id TEXT, year_month TEXT,
            revenue INTEGER, accum_revenue INTEGER,
            UNIQUE(stock_id, year_month)
        )
    ''')

    # Fetch log
    c.execute('''
        CREATE TABLE IF NOT EXISTS fetch_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT, dataset TEXT, stock_id TEXT,
            status TEXT, rows INTEGER, error TEXT
        )
    ''')

    # Stock list
    c.execute('''
        CREATE TABLE IF NOT EXISTS stock_list (
            stock_id TEXT PRIMARY KEY,
            stock_name TEXT, industry TEXT, type TEXT
        )
    ''')

    # Indexes
    c.execute('CREATE INDEX IF NOT EXISTS idx_price ON daily_price(stock_id, date)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_inst ON institutional(stock_id, date)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_margin ON margin(stock_id, date)')

    conn.commit()


def fetch_finmind(dataset, params_override=None):
    """Fetch from FinMind API"""
    import requests

    params = {
        'dataset': dataset,
        'token': FINMIND_TOKEN,
    }
    if params_override:
        params.update(params_override)

    try:
        r = requests.get(BASE_URL, params=params, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if data.get('status') == 200:
                return data.get('data', []), 'OK'
            return [], f"status={data.get('status')} {data.get('message', '')}"
        return [], f"HTTP {r.status_code}"
    except Exception as e:
        return [], str(e)


def fetch_stock_list():
    """抓取股票清單"""
    rows, status = fetch_finmind('TaiwanStockInfo')
    if rows:
        conn = get_db_conn()
        c = conn.cursor()
        saved = 0
        for row in rows:
            try:
                c.execute('''
                    INSERT OR IGNORE INTO stock_list (stock_id, stock_name, industry, type)
                    VALUES (?, ?, ?, ?)
                ''', (row.get('stock_id', ''), row.get('stock_name', ''),
                      row.get('industry_category', ''), row.get('type', '')))
                saved += 1
            except Exception:
                pass
        conn.commit()
        conn.close()
        return saved
    return 0


def fetch_and_save_price(conn, stock_id, start, end):
    """抓取日K價格"""
    rows, status = fetch_finmind('TaiwanStockPrice', {
        'data_id': stock_id, 'start_date': start, 'end_date': end
    })
    if not rows:
        return 0
    c = conn.cursor()
    saved = 0
    for row in rows:
        try:
            c.execute('''
                INSERT OR REPLACE INTO daily_price
                (stock_id, date, open, high, low, close, volume, turnover, spread)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                stock_id, row.get('date'),
                row.get('open'), row.get('max'), row.get('min'), row.get('close'),
                row.get('Trading_Volume'), row.get('Trading_money'),
                row.get('spread')
            ))
            saved += 1
        except Exception:
            pass
    conn.commit()
    return saved


def fetch_and_save_institutional(conn, stock_id, start, end):
    """抓取法人買賣"""
    rows, status = fetch_finmind('TaiwanStockInstitutionalInvestorsBuySell', {
        'data_id': stock_id, 'start_date': start, 'end_date': end
    })
    if not rows:
        return 0
    c = conn.cursor()
    saved = 0
    for row in rows:
        try:
            c.execute('''
                INSERT OR REPLACE INTO institutional
                (stock_id, date, buy_volume, sell_volume, net_volume)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                stock_id, row.get('date'),
                row.get('buy_volume', 0), row.get('sell_volume', 0),
                row.get('buy_volume', 0) - row.get('sell_volume', 0)
            ))
            saved += 1
        except Exception:
            pass
    conn.commit()
    return saved


def fetch_and_save_margin(conn, stock_id, start, end):
    """抓取資券資料"""
    rows, status = fetch_finmind('TaiwanStockMarginPurchaseShortSale', {
        'data_id': stock_id, 'start_date': start, 'end_date': end
    })
    if not rows:
        return 0
    c = conn.cursor()
    saved = 0
    for row in rows:
        try:
            c.execute('''
                INSERT OR REPLACE INTO margin
                (stock_id, date, margin_balance, short_balance, margin_ratio)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                stock_id, row.get('date'),
                row.get('MarginPurchaseBuy'), row.get('ShortSaleSell'),
                row.get('MarginRatio')
            ))
            saved += 1
        except Exception:
            pass
    conn.commit()
    return saved


def run():
    print('[FinMind Data Fetcher v1]')
    print('=' * 60)

    conn = get_db_conn()
    init_db(conn)

    end = date.today().strftime('%Y-%m-%d')
    start = (date.today() - timedelta(days=365)).strftime('%Y-%m-%d')

    # 1. Fetch stock list
    print(f'\n[1] Stock List...')
    saved = fetch_stock_list()
    print(f'  [OK] {saved} stocks saved')

    # 2. Fetch core stocks data
    print(f'\n[2] Core Stocks (P1 datasets)...')
    for stock in CORE_STOCKS:
        print(f'\n  --- {stock} ---')

        # Price
        rows, status = fetch_and_save_price(conn, stock, start, end), 'OK'
        print(f'    Price: {rows} rows')

        # Institutional
        rows = fetch_and_save_institutional(conn, stock, start, end)
        print(f'    Inst: {rows} rows')

        # Margin
        rows = fetch_and_save_margin(conn, stock, start, end)
        print(f'    Margin: {rows} rows')

        time.sleep(0.3)  # rate limit

    # 3. Futures
    print(f'\n[3] Futures...')
    for contract in ['TX', 'MTX']:
        rows, _ = fetch_finmind('TaiwanFuturesDaily', {
            'data_id': contract, 'start_date': start, 'end_date': end
        })
        if rows:
            c = conn.cursor()
            saved = 0
            for row in rows:
                try:
                    c.execute('''
                        INSERT OR REPLACE INTO futures_daily
                        (date, contract, open, high, low, close, volume, open_interest)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        row.get('date'), contract,
                        row.get('open'), row.get('max'), row.get('min'), row.get('close'),
                        row.get('volume'), row.get('open_interest')
                    ))
                    saved += 1
                except Exception:
                    pass
            conn.commit()
            print(f'  {contract}: {saved} rows')
        time.sleep(0.3)

    # 4. DB summary
    print(f'\n[4] DB Summary...')
    c = conn.cursor()
    tables = ['daily_price', 'institutional', 'margin', 'per_data',
              'futures_daily', 'stock_list', 'month_revenue']
    for t in tables:
        try:
            cnt = c.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
            print(f'  {t}: {cnt:,} rows')
        except Exception:
            print(f'  {t}: N/A')

    conn.close()
    print(f'\n[OK] DB: {DB_PATH}')
    print('[DONE]')


if __name__ == '__main__':
    run()
