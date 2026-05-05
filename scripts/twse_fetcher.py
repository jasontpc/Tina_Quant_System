"""TWSE Data Fetcher v3 - TWSE 證交所資料優化版
==============================================
目標：將 MI_5MINS 即時行情寫入本地 SQLite，支援追蹤市場广度

對比現有資料源：
- yfinance：個股日K/分K（主力）
- FinMind：法人/財務（主力）
- TWSE MI_5MINS：5秒級市場广度（補充，市場領先指標）
"""

import os
import json
import sqlite3
from datetime import datetime, date
import subprocess

WORKSPACE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System'
DB_PATH = os.path.join(WORKSPACE, 'data', 'twse_data.db')
LOG_DIR = os.path.join(WORKSPACE, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)


# MI_5MINS field mapping (Big5 編碼混亂，用位置對應)
# Position: 0=時間, 1=累計委託買進筆數, 2=累計委託買進數量,
#           3=累計委託賣出筆數, 4=累計委託賣出數量,
#           5=成交筆數, 6=成交數量, 7=成交金額
MI_5MINS_FIELDS = [
    'time', 'bid_count_acc', 'bid_vol_acc',
    'ask_count_acc', 'ask_vol_acc',
    'trade_count', 'trade_vol', 'trade_value'
]

MI_INDEX_FIELDS = [
    'category', 'value', 'count', 'volume'
]


def get_db_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def init_db():
    conn = get_db_connection()
    c = conn.cursor()

    # MI_5MINS: 5秒級委託/成交資料
    c.execute('''
        CREATE TABLE IF NOT EXISTS twse_mi_5mins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tradedate TEXT NOT NULL,
            traded_time TEXT NOT NULL,
            bid_count_acc INTEGER,
            bid_vol_acc INTEGER,
            ask_count_acc INTEGER,
            ask_vol_acc INTEGER,
            trade_count INTEGER,
            trade_vol INTEGER,
            trade_value INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(tradedate, traded_time)
        )
    ''')

    # MI_INDEX: 大盤日資料
    c.execute('''
        CREATE TABLE IF NOT EXISTS twse_mi_index (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tradedate TEXT NOT NULL,
            title TEXT,
            data TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(tradedate, title)
        )
    ''')

    # 市場廣度快照（每天收盤後計算）
    c.execute('''
        CREATE TABLE IF NOT EXISTS twse_market_breadth (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tradedate TEXT NOT NULL,
            close_time TEXT,
            total_trade_count INTEGER,
            total_trade_vol INTEGER,
            total_trade_value INTEGER,
            last_price REAL,
            change REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(tradedate)
        )
    ''')

    # Fetch log
    c.execute('''
        CREATE TABLE IF NOT EXISTS fetch_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            endpoint TEXT,
            status TEXT,
            bytes INTEGER,
            rows INTEGER,
            error TEXT
        )
    ''')

    conn.commit()
    return conn


def save_mi_5mins(conn, tradedate, rows):
    """寫入 MI_5MINS 資料"""
    if not rows:
        return 0

    c = conn.cursor()
    saved = 0
    for row in rows:
        if len(row) < 8:
            continue
        try:
            t = row[0]
            bid_count = int(row[1].replace(',', ''))
            bid_vol = int(row[2].replace(',', ''))
            ask_count = int(row[3].replace(',', ''))
            ask_vol = int(row[4].replace(',', ''))
            trade_count = int(row[5].replace(',', ''))
            trade_vol = int(row[6].replace(',', ''))
            trade_value = int(row[7].replace(',', ''))

            c.execute('''
                INSERT OR REPLACE INTO twse_mi_5mins
                (tradedate, traded_time, bid_count_acc, bid_vol_acc,
                 ask_count_acc, ask_vol_acc, trade_count, trade_vol, trade_value)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (tradedate, t, bid_count, bid_vol, ask_count, ask_vol,
                  trade_count, trade_vol, trade_value))
            saved += 1
        except Exception as e:
            pass  # Skip invalid rows

    conn.commit()
    return saved


def save_mi_index(conn, tradedate, title, data):
    """寫入 MI_INDEX 資料"""
    c = conn.cursor()
    try:
        c.execute('''
            INSERT OR REPLACE INTO twse_mi_index (tradedate, title, data)
            VALUES (?, ?, ?)
        ''', (tradedate, title, json.dumps(data, ensure_ascii=False)))
        conn.commit()
        return True
    except Exception:
        return False


def compute_market_breadth(conn, tradedate):
    """計算收盤後市場广度"""
    c = conn.cursor()

    # 取得收盤最後一筆（13:30:00 或最後一筆）
    c.execute('''
        SELECT traded_time, trade_count, trade_vol, trade_value
        FROM twse_mi_5mins
        WHERE tradedate = ?
        ORDER BY traded_time DESC
        LIMIT 1
    ''', (tradedate,))
    row = c.fetchone()
    if not row:
        return None

    return {
        'tradedate': tradedate,
        'close_time': row[0],
        'total_trade_count': row[1],
        'total_trade_vol': row[2],
        'total_trade_value': row[3],
    }


def fetch_mi_5mins():
    """抓取 MI_5MINS 5秒級行情"""
    import requests

    url = 'https://www.twse.com.tw/exchangeReport/MI_5MINS?response=json'
    try:
        r = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        if r.status_code != 200:
            return None, f'HTTP {r.status_code}'

        data = r.json()
        if data.get('stat') != 'OK':
            return None, f"stat={data.get('stat')}"

        tradedate = data.get('date', '')
        rows = data.get('data', [])
        return {
            'tradedate': tradedate,
            'rows': rows,
            'total': len(rows)
        }, 'OK'
    except Exception as e:
        return None, str(e)


def fetch_mi_index():
    """抓取 MI_INDEX 大盤指數"""
    import requests

    url = 'https://www.twse.com.tw/exchangeReport/MI_INDEX?response=json&index=IX0001'
    try:
        r = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        if r.status_code != 200:
            return None, f'HTTP {r.status_code}'

        data = r.json()
        if data.get('stat') != 'OK':
            return None, f"stat={data.get('stat')}"

        return data, 'OK'
    except Exception as e:
        return None, str(e)


def log_fetch(conn, endpoint, status, bytes_count, rows=0, error=''):
    c = conn.cursor()
    c.execute('''
        INSERT INTO fetch_log (timestamp, endpoint, status, bytes, rows, error)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (datetime.now().isoformat(), endpoint, status, bytes_count, rows, error))
    conn.commit()


def run():
    print('[TWSE Data Fetcher v3]')
    print('=' * 60)

    conn = init_db()
    today = date.today().strftime('%Y%m%d')
    now = datetime.now().strftime('%H:%M:%S')

    # 1. Fetch MI_5MINS
    print('\n[1] MI_5MINS (5-sec order book)...')
    result, status = fetch_mi_5mins()
    if result:
        rows_saved = save_mi_5mins(conn, result['tradedate'], result['rows'])
        print(f'  [OK] {result["tradedate"]}: {result["total"]} rows, saved={rows_saved}')
        log_fetch(conn, 'MI_5MINS', 'OK', result['total'] * 50, result['total'])
    else:
        print(f'  [FAIL] {status}')
        log_fetch(conn, 'MI_5MINS', 'FAIL', 0, 0, status)

    # 2. Fetch MI_INDEX
    print('\n[2] MI_INDEX (market index)...')
    data, status = fetch_mi_index()
    if data:
        tradedate = data.get('date', today)
        # MI_INDEX structure: tables[{}] with title and data
        tables = data.get('tables', [])
        for t in tables:
            title = t.get('title', '')
            rows = t.get('data', [])
            if title and rows:
                save_mi_index(conn, tradedate, title, rows)
        print(f'  [OK] {tradedate}: {len(tables)} tables')
        log_fetch(conn, 'MI_INDEX', 'OK', len(json.dumps(data)), len(tables))
    else:
        print(f'  [FAIL] {status}')
        log_fetch(conn, 'MI_INDEX', 'FAIL', 0, 0, status)

    # 3. Compute market breadth
    print('\n[3] Market Breadth...')
    breadth = compute_market_breadth(conn, today)
    if breadth:
        print(f'  [OK] {breadth["tradedate"]} @ {breadth["close_time"]}')
        print(f'      trade_count={breadth["total_trade_count"]:,}')
        print(f'      trade_vol={breadth["total_trade_vol"]:,}')
        print(f'      trade_value={breadth["total_trade_value"]:,}')
    else:
        print('  [INFO] No 5mins data for today yet')

    # 4. Summary
    print('\n[4] DB Summary...')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM twse_mi_5mins')
    print(f'  twse_mi_5mins rows: {c.fetchone()[0]:,}')
    c.execute('SELECT COUNT(*) FROM twse_mi_index')
    print(f'  twse_mi_index rows: {c.fetchone()[0]:,}')
    c.execute('SELECT COUNT(*) FROM fetch_log')
    print(f'  fetch_log entries: {c.fetchone()[0]:,}')

    conn.close()
    print(f'\n[OK] DB: {DB_PATH}')
    print('[DONE]')


if __name__ == '__main__':
    run()
