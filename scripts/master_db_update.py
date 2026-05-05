# -*- coding: utf-8 -*-
"""
全系統資料庫主動更新整合腳本
Master Database Update Script v2
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import sqlite3
import yfinance as yf
import pandas as pd
from datetime import datetime
import time

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
sys.path.insert(0, DATA_DIR)

def update_tw_history():
    """Update Taiwan stock history database"""
    db = f'{DATA_DIR}\\tw_history.db'
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    
    cur.execute("SELECT symbol FROM stocks ORDER BY symbol LIMIT 80")
    stocks = [r[0] for r in cur.fetchall()]
    conn.close()
    
    success = 0
    for sym in stocks[:30]:
        try:
            t = yf.Ticker(f'{sym}.TW')
            h = t.history(period='5d')
            if h.empty: continue
            price = float(h['Close'].iloc[-1])
            
            conn2 = sqlite3.connect(db)
            cur2 = conn2.cursor()
            today = datetime.now().strftime('%Y-%m-%d')
            cur2.execute('''
                INSERT OR IGNORE INTO stock_price (symbol, date, close)
                VALUES (?, ?, ?)
            ''', (sym, today, price))
            conn2.commit()
            conn2.close()
            success += 1
        except: pass
    
    return success, f'{success}/{min(30, len(stocks))} stocks'

def update_us_history():
    """Update US stock history database"""
    db = f'{DATA_DIR}\\us_history.db'
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    
    cur.execute("SELECT symbol FROM stock_summary ORDER BY symbol LIMIT 100")
    stocks = [r[0] for r in cur.fetchall()]
    conn.close()
    
    success = 0
    for sym in stocks[:50]:
        try:
            t = yf.Ticker(sym)
            h = t.history(period='5d')
            if h.empty: continue
            price = float(h['Close'].iloc[-1])
            
            conn2 = sqlite3.connect(db)
            cur2 = conn2.cursor()
            today = datetime.now().strftime('%Y-%m-%d')
            cur2.execute('''
                INSERT OR IGNORE INTO stock_price (symbol, date, close)
                VALUES (?, ?, ?)
            ''', (sym, today, price))
            conn2.commit()
            conn2.close()
            success += 1
            time.sleep(0.2)
        except: pass
    
    return success, f'{success}/{min(50, len(stocks))} stocks'

def update_etf_history():
    """Update Taiwan ETF history database"""
    db = f'{DATA_DIR}\\etf_history.db'
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    
    cur.execute("SELECT symbol FROM etf_list ORDER BY symbol")
    etfs = [r[0] for r in cur.fetchall()]
    conn.close()
    
    success = 0
    for sym in etfs:
        try:
            t = yf.Ticker(f'{sym}.TW')
            h = t.history(period='5d')
            if h.empty: continue
            price = float(h['Close'].iloc[-1])
            
            conn2 = sqlite3.connect(db)
            cur2 = conn2.cursor()
            today = datetime.now().strftime('%Y-%m-%d')
            cur2.execute('''
                INSERT OR IGNORE INTO etf_price (symbol, date, close)
                VALUES (?, ?, ?)
            ''', (sym, today, price))
            conn2.commit()
            conn2.close()
            success += 1
            time.sleep(0.3)
        except: pass
    
    return success, f'{success}/{len(etfs)} ETFs'

def verify_db_integrity(db_path, table_query):
    """Verify database integrity"""
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Get table count
        if isinstance(table_query, str):
            cur.execute(f'SELECT COUNT(*) FROM {table_query}')
        else:
            cur.execute(f'SELECT COUNT(*) FROM {table_query[0]} WHERE symbol IN ({"?".join([""]*len(table_query[1]))})', table_query[1])
        count = cur.fetchone()[0]
        
        # Get recent dates
        tables_with_date = ['stock_price', 'etf_price', 'daily_prices', 'trending_signals', 'keywords', 'daily_data', 'daily_ohlcv']
        has_date = any(t in table_query[0] if isinstance(table_query, tuple) else t == table_query for t in tables_with_date)
        
        recent_dates = []
        date_count = 0
        try:
            if has_date:
                date_col = 'date' if 'date' in [col[1] for col in cur.execute(f'PRAGMA table_info({table_query[0]})').fetchall()] else 'updated_at'
                cur.execute(f'SELECT MAX({date_col}) FROM {table_query[0]}')
                last_date = cur.fetchone()[0]
                cur.execute(f'SELECT COUNT(DISTINCT {date_col}) FROM {table_query[0]}')
                date_count = cur.fetchone()[0]
                recent_dates = [str(last_date)] if last_date else []
        except: pass
        
        conn.close()
        return {'count': count, 'recent_dates': recent_dates, 'date_count': date_count, 'table': table_query[0] if isinstance(table_query, tuple) else table_query}
    except Exception as e:
        return {'error': str(e), 'table': table_query[0] if isinstance(table_query, tuple) else table_query}

def main():
    print('=' * 65)
    print('MASTER DATABASE UPDATE + INTEGRITY CHECK v2')
    print(f'Time: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print('=' * 65)
    print()
    
    results = []
    
    # Update databases
    print('[1] TW History 更新...')
    try:
        count, msg = update_tw_history()
        print(f'    {msg}')
        results.append(('TW History', msg))
    except Exception as e:
        print(f'    ERROR: {e}')
        results.append(('TW History', f'ERROR: {e}'))
    
    print('[2] US History 更新...')
    try:
        count, msg = update_us_history()
        print(f'    {msg}')
        results.append(('US History', msg))
    except Exception as e:
        print(f'    ERROR: {e}')
        results.append(('US History', f'ERROR: {e}'))
    
    print('[3] ETF History 更新...')
    try:
        count, msg = update_etf_history()
        print(f'    {msg}')
        results.append(('ETF History', msg))
    except Exception as e:
        print(f'    ERROR: {e}')
        results.append(('ETF History', f'ERROR: {e}'))
    
    print('[4] TW Active ETF 追蹤...')
    try:
        # Run the tracker directly
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            'tw_active_etf_tracker',
            f'{DATA_DIR}\\..\\scripts\\tw_active_etf_tracker.py'
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        count = module.main()
        msg = f'{count} ETFs'
        print(f'    {msg}')
        results.append(('TW Active ETF', msg))
    except Exception as e:
        print(f'    ERROR: {e}')
        results.append(('TW Active ETF', f'ERROR: {e}'))
    
    print('[5] Yuan Zheng2 00631L 追蹤...')
    try:
        db_yuan = f'{DATA_DIR}\\yuan_zheng2.db'
        conn = sqlite3.connect(db_yuan)
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM daily_data')
        total = cur.fetchone()[0]
        cur.execute('SELECT date FROM daily_data ORDER BY date DESC LIMIT 1')
        row = cur.fetchone()
        today = datetime.now().strftime('%Y-%m-%d')
        if row and row[0] != today:
            conn.close()
            spec = importlib.util.spec_from_file_location(
                'yuan_zheng2_tracker',
                f'{DATA_DIR}\\..\\scripts\\yuan_zheng2_tracker.py'
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            msg = 'Updated'
        else:
            msg = f'Already current ({total} rows)'
            conn.close()
        print(f'    {msg}')
        results.append(('Yuan Zheng2', msg))
    except Exception as e:
        print(f'    ERROR: {e}')
        results.append(('Yuan Zheng2', f'ERROR: {e}'))
    
    print('[6] Trending Signals 檢查...')
    try:
        db = f'{DATA_DIR}\\stock_trends.db'
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM trending_signals')
        count = cur.fetchone()[0]
        conn.close()
        msg = f'{count} stocks'
        print(f'    {msg}')
        results.append(('Trending Signals', msg))
    except Exception as e:
        print(f'    ERROR: {e}')
        results.append(('Trending Signals', f'ERROR: {e}'))
    
    print('[7] Portfolio 持倉追蹤...')
    try:
        db_port = f'{DATA_DIR}\\portfolio.db'
        conn = sqlite3.connect(db_port)
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM holdings')
        count = cur.fetchone()[0]
        cur.execute('SELECT SUM(market_value), SUM(unrealized_pnl) FROM holdings')
        row = cur.fetchone()
        conn.close()
        msg = f'{count} positions, MV=${row[0] or 0:,.0f}'
        print(f'    {msg}')
        results.append(('Portfolio', msg))
    except Exception as e:
        print(f'    ERROR: {e}')
        results.append(('Portfolio', f'ERROR: {e}'))
    
    # Integrity check
    print()
    print('=' * 65)
    print('INTEGRITY CHECK')
    print('=' * 65)
    print()
    
    dbs = [
        (f'{DATA_DIR}\\tw_history.db', 'stock_price', 'TW History'),
        (f'{DATA_DIR}\\us_history.db', 'stock_price', 'US History'),
        (f'{DATA_DIR}\\etf_history.db', 'etf_price', 'ETF History'),
        (f'{DATA_DIR}\\tw_active_etf.db', 'etf_daily', 'TW Active ETF'),
        (f'{DATA_DIR}\\yuan_zheng2.db', 'daily_data', 'Yuan Zheng2'),
        (f'{DATA_DIR}\\stock_trends.db', 'trending_signals', 'Trending Signals'),
        (f'{DATA_DIR}\\threads_trending.db', 'keywords', 'Trending Keywords'),
        (f'{DATA_DIR}\\portfolio.db', 'holdings', 'Portfolio'),
    ]
    
    all_ok = True
    for db_path, table, name in dbs:
        try:
            info = verify_db_integrity(db_path, table)
            if 'error' in info:
                print(f'  {name}: ERROR - {info["error"]}')
                all_ok = False
            else:
                recent = ', '.join(info['recent_dates'][:3]) if info['recent_dates'] else 'N/A'
                status = 'OK' if info['count'] > 0 else 'EMPTY'
                print(f'  {name}: {status} | {info["count"]} rows | Last: {recent}')
        except Exception as e:
            print(f'  {name}: ERROR - {e}')
            all_ok = False
    
    print()
    print('=' * 65)
    print('UPDATE SUMMARY')
    print('=' * 65)
    for name, msg in results:
        print(f'  {name}: {msg}')
    
    print()
    print(f'Overall: {"ALL OK" if all_ok else "ISSUES FOUND"}')
    print('=' * 65)
    
    return all_ok

if __name__ == '__main__':
    ok = main()
    sys.exit(0 if ok else 1)