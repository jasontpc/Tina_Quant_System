# -*- coding: utf-8 -*-
"""
Vogel - ?°æ??Ÿï?TXï¼‰è‡ªä¸»äº¤?“ç???v1.2
ä¿®æ­£ï¼šåª?–å–®ä¸€?ˆå??ˆç?ï¼ˆé??¹å·®ï¼‰ï??–è???"""
import sys, sqlite3, os, requests
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
VOGEL_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\vogel'

TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSJ9.oCdQO1qNRUCYxHZSVuRQCqlF7X2DbQ77wury5ARCKzM'
BASE = 'https://api.finmindtrade.com/api/v4/data'

BB_PERIOD = 20
RSI_PERIOD = 14
ATR_PERIOD = 14

def fetch_futures_daily(symbol='TX', days=500):
    end = datetime.now().strftime('%Y-%m-%d')
    start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    r = requests.get(f'{BASE}/data', params={
        'dataset': 'TaiwanFuturesDaily',
        'data_id': symbol,
        'start_date': start,
        'end_date': end
    }, headers={'Authorization': f'Bearer {TOKEN}'}, timeout=30)
    
    if r.status_code != 200: return None
    return r.json().get('data', [])

def select_near_contract(data):
    """?¸æ?è¿‘æ??®ä??†å¨©?ˆç?ï¼ˆç„¡/?œç?ï¼‰â€?ä»¥æ??°æ—¥?Ÿç‚ºæº?""
    # Filter: only single-month contracts (no '/' in contract_date)
    single = [d for d in data if '/' not in str(d.get('contract_date', ''))]
    
    if not single:
        print(f'No single-month contracts found! Total: {len(data)}')
        return None, None, {}
    
    # Group by contract_date
    from collections import defaultdict
    by_contract = defaultdict(list)
    for d in single:
        by_contract[d['contract_date']].append(d)
    
    # For each contract, get its latest date and record count
    contract_info = {}
    for cd, items in by_contract.items():
        latest_date = max(x['date'] for x in items if x.get('date'))
        contract_info[cd] = {'latest': latest_date, 'count': len(items), 'items': items}
    
    # Pick contract with the most recent date (>= 2025-01-01 and has enough records)
    # Sort by latest date descending, then by count descending
    sorted_contracts = sorted(contract_info.items(), 
                               key=lambda x: (x[1]['latest'], x[1]['count']), 
                               reverse=True)
    
    # Find first contract with recent data (latest >= 2025-10-01) and enough records
    main_cd = None
    for cd, info in sorted_contracts:
        if info['latest'] >= '2025-10-01' and info['count'] >= 50:
            main_cd = cd
            break
    
    if not main_cd:
        # Fallback: most records with any recent date
        main_cd = sorted_contracts[0][0]
    
    # Build filtered list: date >= 2024-01-01, contract = main_cd
    filtered = [d for d in single if d.get('contract_date') == main_cd and d.get('date', '') >= '2024-01-01']
    filtered.sort(key=lambda x: x.get('date', ''))
    
    contract_records = {cd: info['count'] for cd, info in contract_info.items()}
    return filtered, main_cd, contract_records

def calc_indicators(data):
    closes = [d.get('close') for d in data]
    results = []
    
    for i, d in enumerate(data):
        d = d.copy()
        c = d.get('close')
        
        # BB
        start_idx = max(0, i - BB_PERIOD + 1)
        window = [closes[j] for j in range(start_idx, i+1) if closes[j] is not None]
        if len(window) >= BB_PERIOD:
            ma = sum(window) / BB_PERIOD
            variance = sum((x - ma) ** 2 for x in window) / BB_PERIOD
            std = variance ** 0.5
            d['bb_upper'] = round(ma + 2*std, 2)
            d['bb_middle'] = round(ma, 2)
            d['bb_lower'] = round(ma - 2*std, 2)
        else:
            d['bb_upper'] = d['bb_middle'] = d['bb_lower'] = None
        
        # RSI
        d['rsi'] = None
        if i >= RSI_PERIOD and c is not None:
            gains, losses = 0, 0
            for j in range(i-RSI_PERIOD+1, i+1):
                if closes[j] is not None and closes[j-1] is not None:
                    diff = closes[j] - closes[j-1]
                    if diff > 0: gains += diff
                    else: losses += abs(diff)
            avg_gain = gains / RSI_PERIOD
            avg_loss = losses / RSI_PERIOD
            rs = avg_gain / avg_loss if avg_loss else 100
            d['rsi'] = round(100 - (100 / (1 + rs)), 2)
        
        # ATR
        d['atr'] = None
        if i >= ATR_PERIOD:
            trs = []
            for j in range(i-ATR_PERIOD+1, i+1):
                high = data[j].get('max', 0) or 0
                low = data[j].get('min', 0) or 0
                prev = closes[j-1] if closes[j-1] is not None else c
                tr = max(high - low, abs(high - prev), abs(low - prev))
                trs.append(tr)
            d['atr'] = round(sum(trs) / ATR_PERIOD, 2) if trs else None
        
        results.append(d)
    
    return results

def build_db():
    db_path = os.path.join(DATA_DIR, 'vogel.db')
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS futures_daily (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE,
            futures_id TEXT,
            contract_date TEXT,
            open REAL, high REAL, low REAL, close REAL,
            spread REAL, spread_per REAL, volume INTEGER,
            open_interest INTEGER,
            bb_upper REAL, bb_middle REAL, bb_lower REAL,
            rsi REAL, atr REAL
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, futures_id TEXT, strategy TEXT,
            signal_type TEXT, price REAL, rsi REAL, atr REAL,
            reason TEXT, status TEXT DEFAULT 'pending',
            entered_price REAL, exited_price REAL,
            pnl_pct REAL, held_days INTEGER
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS db_version (
            version TEXT, updated_at TEXT
        )
    ''')
    
    conn.commit()
    return conn, cur

def main():
    print('=== Vogel v1.2 - ?°æ??Ÿç???===\n')
    
    conn, cur = build_db()
    
    print('Fetching TX daily from FinMind...')
    raw = fetch_futures_daily('TX', days=600)
    if not raw: print('No data'); return
    
    result = select_near_contract(raw)
    if not result[0]: print('No valid contract'); return
    
    data, main_cd, valid_contracts = result
    
    print(f'Main contract: {main_cd} ({len(data)} records)')
    print(f'Available contracts: {valid_contracts}')
    
    # Store
    cur.execute('DELETE FROM futures_daily WHERE futures_id="TX" AND contract_date=?', (main_cd,))
    
    indicators = calc_indicators(data)
    
    for d in indicators:
        cur.execute('''
            INSERT OR REPLACE INTO futures_daily 
            (date, futures_id, contract_date, open, high, low, close, spread, spread_per, volume, open_interest,
             bb_upper, bb_middle, bb_lower, rsi, atr)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (d['date'], 'TX', main_cd, d.get('open'), d.get('max'), d.get('min'), d.get('close'),
              d.get('spread'), d.get('spread_per'), d.get('volume'), d.get('open_interest'),
              d.get('bb_upper'), d.get('bb_middle'), d.get('bb_lower'), d.get('rsi'), d.get('atr')))
    
    conn.commit()
    
    # Stats
    cur.execute('SELECT MIN(date), MAX(date), COUNT(*) FROM futures_daily WHERE futures_id="TX"')
    min_d, max_d, cnt = cur.fetchone()
    print(f'\nDB: {min_d} to {max_d} ({cnt} records)')
    
    # Latest 10
    cur.execute('SELECT date,close,rsi,atr,bb_upper,bb_middle,bb_lower FROM futures_daily WHERE futures_id="TX" ORDER BY date DESC LIMIT 10')
    rows = cur.fetchall()
    
    print(f'\n=== Latest 10 TX ({main_cd}) ===')
    print(f'{"Date":<12} {"Close":>8} {"RSI":>6} {"ATR":>8} {"BB_Upper":>8} {"BB_Mid":>8} {"BB_Lower":>8}')
    for r in reversed(rows):
        rsi_v = f'{r[2]:.1f}' if r[2] else 'N/A'
        atr_v = f'{r[3]:.0f}' if r[3] else 'N/A'
        bu = f'{r[4]:.0f}' if r[4] else 'N/A'
        bm = f'{r[5]:.0f}' if r[5] else 'N/A'
        bl = f'{r[6]:.0f}' if r[6] else 'N/A'
        print(f'{r[0]:<12} {r[1]:>8.0f} {rsi_v:>6} {atr_v:>8} {bu:>8} {bm:>8} {bl:>8}')
    
    conn.close()
    print('\n=== Vogel v1.2 Ready ===')

if __name__ == '__main__':
    main()
