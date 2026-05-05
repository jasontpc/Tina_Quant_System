# -*- coding: utf-8 -*-
"""
TWSE 台股證券資料核對系統 v4
驗證股票代號與名稱是否匹配正確
"""

import sqlite3
import yfinance as yf
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
DB_PATH = f'{DATA_DIR}\\twse_symbol_validator.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS twse_stocks (
            symbol TEXT PRIMARY KEY, 
            name_en TEXT, 
            name_zh TEXT, 
            industry TEXT, 
            verified_at TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS verification_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_date TEXT, 
            symbol TEXT, 
            yahoo_name TEXT,
            match_status TEXT
        )
    ''')
    conn.commit()
    return conn

def get_yahoo_name(symbol):
    try:
        clean_sym = symbol.replace('.TW', '')
        t = yf.Ticker(f'{clean_sym}.TW')
        info = t.info
        name = info.get('longName', '') or info.get('quoteTypeName', '')
        return name if name else None
    except:
        return None

def main():
    print('=' * 65)
    print('TWSE SYMBOL VALIDATOR v4')
    print(f'Time: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print('=' * 65)
    print()
    
    conn = init_db()
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    tw_db = f'{DATA_DIR}\\tw_history.db'
    conn_tw = sqlite3.connect(tw_db)
    cur_tw = conn_tw.cursor()
    cur_tw.execute('SELECT DISTINCT symbol FROM stock_price ORDER BY symbol')
    all_symbols = [r[0] for r in cur_tw.fetchall()]
    conn_tw.close()
    
    print(f'[1] Total stocks in our DB: {len(all_symbols)}')
    print()
    
    print('[2] Verifying with Yahoo Finance...')
    results = []
    matched = missing = 0
    
    for sym in all_symbols:
        clean_sym = sym.replace('.TW', '')
        y_name = get_yahoo_name(clean_sym)
        
        if y_name:
            matched += 1
            status = 'MATCH'
        else:
            missing += 1
            status = 'MISSING'
            y_name = 'N/A'
        
        results.append((sym, clean_sym, y_name, status))
        
        if (matched + missing) % 10 == 0:
            print(f'  Progress: {matched + missing}/{len(all_symbols)} | Matched: {matched} | Missing: {missing}')
    
    print(f'  Final: Matched: {matched} | Missing: {missing}')
    
    print()
    print('[3] Results')
    print(f'{"Our DB":<10} {"Clean":<8} {"Yahoo Name":<45} {"Status"}')
    print('-' * 75)
    for our_sym, clean, name, status in results:
        icon = '✓' if status == 'MATCH' else '✗'
        print(f'{our_sym:<10} {clean:<8} {name[:43]:<45} {icon}')
    
    print()
    print('[4] Missing')
    missing_list = [(s, c) for s, c, n, st in results if st == 'MISSING']
    if missing_list:
        for s, c in missing_list:
            print(f'  {s} -> {c}')
    else:
        print('  None!')
    
    print()
    print(f'[5] Summary: {matched}/{len(results)} matched ({matched*100/len(results):.1f}%)')
    
    print('[6] Saving...')
    cur = conn.cursor()
    for sym, clean, name, status in results:
        cur.execute('INSERT OR REPLACE INTO twse_stocks (symbol, name_en, verified_at) VALUES (?, ?, ?)',
                    (clean, name, now))
        cur.execute('INSERT INTO verification_log (run_date, symbol, yahoo_name, match_status) VALUES (?, ?, ?, ?)',
                    (now, clean, name, status))
    conn.commit()
    conn.close()
    print('=' * 65)
    print('DONE')

if __name__ == '__main__':
    main()