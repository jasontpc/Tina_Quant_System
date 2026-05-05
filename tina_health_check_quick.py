# -*- coding: utf-8 -*-
"""Tina 系統健檢（夜間）- 快速版"""
import sys, sqlite3, os
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'

def check_databases():
    """快速檢查所有資料庫狀態"""
    print('=== Tina 系統健檢（夜間）===\n')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
    
    dbs = [
        ('tw_history.db', '台股歷史'),
        ('us_history.db', '美股歷史'),
        ('maggy_ai_tech.db', 'Maggy AI/科技'),
        ('sherry_etf.db', 'Sherry ETF'),
        ('maggy_sim_trades.db', '模擬交易'),
        ('vogel_indicators.db', 'Vogel 台指'),
    ]
    
    issues = []
    total = 0
    
    for db_name, desc in dbs:
        path = f'{DATA_DIR}\\{db_name}'
        if os.path.exists(path):
            size = os.path.getsize(path) / 1024
            conn = sqlite3.connect(path)
            cur = conn.cursor()
            
            try:
                tables = [t[0] for t in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
                for table in tables:
                    cnt = cur.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
                    total += cnt
                
                status = 'OK'
                print(f'{desc:<18} {size:>7.0f}KB {status}')
            except Exception as e:
                print(f'{desc:<18} ERROR: {e}')
                issues.append(f'{desc}: {e}')
            conn.close()
        else:
            print(f'{desc:<18} NOT FOUND')
            issues.append(f'{desc}: NOT FOUND')
    
    print(f'\n總記錄: {total:,}')
    
    if issues:
        print(f'\n⚠️ 問題: {len(issues)}個')
        for i in issues:
            print(f'  - {i}')
    else:
        print('\n✅ 所有資料庫正常')

def quick_market_check():
    """快速市場檢查"""
    print('\n=== 市場狀態 ===\n')
    
    # Check Maggy for entry signals
    ai_db = f'{DATA_DIR}\\maggy_ai_tech.db'
    if os.path.exists(ai_db):
        conn = sqlite3.connect(ai_db)
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) FROM stock_summary WHERE current_rsi < 35")
        low = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM stock_summary WHERE current_rsi > 70")
        high = cur.fetchone()[0]
        
        print(f'Maggy AI/科技股: RSI<35={low}檔, RSI>70={high}檔')
        
        cur.execute("SELECT symbol, current_rsi FROM stock_summary WHERE current_rsi < 35 ORDER BY current_rsi LIMIT 3")
        for r in cur.fetchall():
            print(f'  🟢 {r[0]}: RSI={r[1]:.1f}')
        
        conn.close()
    
    # Check Vogel TX
    vogel_db = f'{DATA_DIR}\\vogel_indicators.db'
    if os.path.exists(vogel_db):
        conn = sqlite3.connect(vogel_db)
        cur = conn.cursor()
        cur.execute("SELECT date, close, rsi_14, zone FROM daily ORDER BY date DESC LIMIT 1")
        r = cur.fetchone()
        if r:
            print(f'\nVogel 台指: TX={r[1]:.0f} RSI={r[2]:.1f} Zone={r[3]}')
        conn.close()
    
    print('\n✅ 健檢完成')

if __name__ == '__main__':
    check_databases()
    quick_market_check()