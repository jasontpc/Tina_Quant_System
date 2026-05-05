# -*- coding: utf-8 -*-
"""Tina 全系統資料庫擴展 - Enhance All Databases for Better Trading"""
import sys, sqlite3, json, os, yfinance
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'

def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50
    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(diff if diff > 0 else 0)
        losses.append(abs(diff) if diff < 0 else 0)
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    rs = avg_gain / avg_loss if avg_loss > 0 else 100
    return 100 - (100 / (1 + rs))

def get_current_databases():
    """Check current database status"""
    print('╔══════════════════════════════════════════════════════════════╗')
    print('║     全系統資料庫現況與擴展規劃                       ║')
    print('╚══════════════════════════════════════════════════════════════╝')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
    
    dbs = {
        'tw_history.db': ('台股歷史', 'daily_ohlcv'),
        'us_history.db': ('美股歷史', 'daily_ohlcv'),
        'maggy_ai_tech.db': ('Maggy AI', 'daily_ohlcv'),
        'sherry_etf.db': ('Sherry ETF', 'etf_daily'),
        'sherry_backtest.db': ('Sherry DCA回測', 'dca_sim'),
        'maggy_sim_trades.db': ('模擬交易', 'sim_trades'),
        'vogel_indicators.db': ('Vogel台指', 'daily'),
        'fugle.db': ('Fugle報價', 'quote_latest'),
    }
    
    total_size = 0
    for db_name, (desc, table) in dbs.items():
        path = f'{DATA_DIR}\\{db_name}'
        if os.path.exists(path):
            size = os.path.getsize(path) / 1024
            total_size += size
            conn = sqlite3.connect(path)
            cur = conn.cursor()
            try:
                cnt = cur.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
                syms = 0
                try:
                    syms = cur.execute(f'SELECT COUNT(DISTINCT symbol) FROM {table}').fetchone()[0]
                except:
                    pass
                print(f'{desc:<18} {size:>8.0f}KB {cnt:>10,}筆 {syms:>5}檔')
            except Exception as e:
                print(f'{desc:<18} {size:>8.0f}KB ERROR: {e}')
            conn.close()
    
    print(f'\n總大小: {total_size:.0f} KB ({total_size/1024:.1f} MB)')

def expand_us_stocks():
    """Expand US stocks database"""
    print('\n\n=== 擴展美股歷史資料庫 ===\n')
    
    NEW_STOCKS = {
        # More AI/Tech
        'AVGO': 'Broadcom', 'ORCL': 'Oracle', 'IBM': 'IBM', 'INFY': 'Infosys',
        'VMW': 'VMware', 'CSCO': 'Cisco', 'QCOM': 'Qualcomm', 'TXN': 'Texas Instruments',
        'NOW': 'ServiceNow', 'SNOW': 'Snowflake', 'TEAM': 'Atlassian', 'DOCU': 'DocuSign',
        'ZM': 'Zoom', 'OKTA': 'Okta', 'SQ': 'Block', 'SHOP': 'Shopify',
        # More Finance
        'BLK': 'BlackRock', 'SCHW': 'Charles Schwab', 'COF': 'Capital One',
        'USB': 'US Bancorp', 'PNC': 'PNC Financial', 'TFC': 'Truist',
        # More Energy
        'SLB': 'Schlumberger', 'EOG': 'EOG Resources', 'PSX': 'Phillips 66',
        'MPC': 'Marathon Petroleum', 'VLO': 'Valero',
        # More Industrial
        'CAT': 'Caterpillar', 'DE': 'John Deere', 'BA': 'Boeing', 'HON': 'Honeywell',
        'UNP': 'Union Pacific', 'CSX': 'CSX Corp', 'NSC': 'Norfolk Southern',
        # More Healthcare
        'UNH': 'UnitedHealth', 'ABBV': 'AbbVie', 'MRK': 'Merck', 'PFE': 'Pfizer',
        'LLY': 'Eli Lilly', 'TMO': 'Thermo Fisher', 'DHR': 'Danaher', 'AMGN': 'Amgen',
    }
    
    db = f'{DATA_DIR}\\us_history.db'
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    
    added = 0
    for sym, name in NEW_STOCKS.items():
        try:
            cur.execute('SELECT COUNT(*) FROM stock_summary WHERE symbol=?', (sym,))
            if cur.fetchone()[0] > 0:
                continue
            
            t = yfinance.Ticker(sym)
            hist = t.history(period='3y')
            
            if len(hist) < 200:
                continue
            
            closes = hist['Close'].tolist()
            dates = hist.index.strftime('%Y-%m-%d').tolist()
            
            rsi = calc_rsi(closes)
            high_52w = max(closes[-252:]) if len(closes) >= 252 else max(closes)
            low_52w = min(closes[-252:]) if len(closes) >= 252 else min(closes)
            
            cur.execute('''INSERT INTO stock_summary (symbol, name, sector, current_price, current_rsi, 
                current_zone, high_52w, low_52w, total_records, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (sym, name, 'STOCK', closes[-1], rsi, 'NEUTRAL', high_52w, low_52w, len(hist), dates[-1]))
            conn.commit()
            added += 1
            print(f'+ {sym} {name}: RSI={rsi:.1f}')
        except Exception as e:
            pass
    
    conn.close()
    print(f'\n新增 {added} 檔股票')
    return added

def expand_ai_tech():
    """Expand Maggy AI/Tech database"""
    print('\n\n=== 擴展 Maggy AI/科技股資料庫 ===\n')
    
    NEW_AI = {
        'AVGO': ('Broadcom', 'AI/Semi', 'Leader'),
        'ORCL': ('Oracle', 'AI/Cloud', 'Leader'),
        'INFY': ('Infosys', 'AI/IT', 'Leader'),
        'SNOW': ('Snowflake', 'AI/Data', 'Leader'),
        'TEAM': ('Atlassian', 'AI/Enterprise', 'Leader'),
        'DOCU': ('DocuSign', 'AI/Saas', 'Leader'),
        'SHOP': ('Shopify', 'AI/Ecommerce', 'Leader'),
        'BLK': ('BlackRock', 'AI/Finance', 'Leader'),
        'IBM': ('IBM', 'AI/Hybrid', 'Legacy'),
        'TXN': ('Texas Instruments', 'AI/Semi', 'Leader'),
        'QCOM': ('Qualcomm', 'AI/Semi', 'Challenger'),
    }
    
    db = f'{DATA_DIR}\\maggy_ai_tech.db'
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    
    added = 0
    for sym, info in NEW_AI.items():
        name, sector, subsector = info
        try:
            cur.execute('SELECT COUNT(*) FROM stock_summary WHERE symbol=?', (sym,))
            if cur.fetchone()[0] > 0:
                continue
            
            t = yfinance.Ticker(sym)
            hist = t.history(period='3y')
            
            if len(hist) < 200:
                continue
            
            closes = hist['Close'].tolist()
            dates = hist.index.strftime('%Y-%m-%d').tolist()
            
            rsi = calc_rsi(closes)
            high_52w = max(closes[-252:]) if len(closes) >= 252 else max(closes)
            low_52w = min(closes[-252:]) if len(closes) >= 252 else min(closes)
            
            cur.execute('''INSERT INTO stock_summary (symbol, name, sector, subsector, current_price, current_rsi, 
                current_zone, high_52w, low_52w, total_records, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (sym, name, sector, subsector, closes[-1], rsi, 'NEUTRAL', high_52w, low_52w, len(hist), dates[-1]))
            conn.commit()
            added += 1
            print(f'+ {sym} {name}: RSI={rsi:.1f}')
        except Exception as e:
            pass
    
    conn.close()
    print(f'\n新增 {added} 檔AI/科技股')
    return added

def build_trade_archive():
    """Build comprehensive trade archive for learning"""
    print('\n\n=== 建立交易歸檔資料庫 ===\n')
    
    ARCHIVE_DB = f'{DATA_DIR}\\trade_archive.db'
    conn = sqlite3.connect(ARCHIVE_DB)
    cur = conn.cursor()
    
    cur.execute('''CREATE TABLE IF NOT EXISTS trade_archive (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        system TEXT NOT NULL,
        symbol TEXT NOT NULL,
        entry_date TEXT,
        entry_price REAL,
        exit_date TEXT,
        exit_price REAL,
        shares INTEGER,
        return_pct REAL,
        return_amount REAL,
        holding_days INTEGER,
        entry_rsi REAL,
        exit_rsi REAL,
        strategy TEXT,
        exit_reason TEXT,
        market_regime TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    cur.execute('''CREATE TABLE IF NOT EXISTS trade_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        system TEXT NOT NULL,
        symbol TEXT NOT NULL,
        total_trades INTEGER DEFAULT 0,
        winning_trades INTEGER DEFAULT 0,
        losing_trades INTEGER DEFAULT 0,
        win_rate REAL DEFAULT 0,
        avg_return REAL DEFAULT 0,
        total_return REAL DEFAULT 0,
        best_trade REAL DEFAULT 0,
        worst_trade REAL DEFAULT 0,
        avg_holding_days REAL DEFAULT 0,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(system, symbol)
    )''')
    
    # Aggregate from sim_trades
    try:
        sim_db = f'{DATA_DIR}\\maggy_sim_trades.db'
        sim_conn = sqlite3.connect(sim_db)
        sim_cur = sim_conn.cursor()
        
        # Copy closed trades
        sim_cur.execute('''SELECT symbol, entry_date, entry_price, exit_date, exit_price,
            quantity, return_pct, return_amount, holding_days, entry_rsi, exit_rsi, exit_reason 
            FROM closed_positions''')
        
        for r in sim_cur.fetchall():
            sym, entry_dt, entry_px, exit_dt, exit_px, qty, ret_pct, ret_amt, hold, ent_rsi, ex_rsi, reason = r
            cur.execute('''INSERT INTO trade_archive 
                (system, symbol, entry_date, entry_price, exit_date, exit_price, shares,
                return_pct, return_amount, holding_days, entry_rsi, exit_rsi, strategy, exit_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                ('Maggy', sym, entry_dt, entry_px, exit_dt, exit_px, qty or 0,
                 ret_pct or 0, ret_amt or 0, hold or 0, ent_rsi or 50, ex_rsi or 50, 'RSI_Rev', reason or ''))
        
        sim_conn.close()
        conn.commit()
        
        # Calculate stats
        cur.execute('''SELECT symbol, COUNT(*), 
            SUM(CASE WHEN return_pct > 0 THEN 1 ELSE 0 END),
            AVG(return_pct), SUM(return_pct),
            MAX(return_pct), MIN(return_pct), AVG(holding_days)
            FROM trade_archive GROUP BY symbol''')
        
        for r in cur.fetchall():
            sym, total, wins, avg_ret, tot_ret, best, worst, avg_hold = r
            wr = wins / total * 100 if total > 0 else 0
            cur.execute('''INSERT OR REPLACE INTO trade_stats
                (system, symbol, total_trades, winning_trades, avg_return, total_return,
                best_trade, worst_trade, avg_holding_days)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                ('Maggy', sym, total, wins or 0, avg_ret or 0, tot_ret or 0, best or 0, worst or 0, avg_hold or 0))
        
        conn.commit()
        print(f'交易歸檔：已建立')
        
    except Exception as e:
        print(f'Error: {e}')
    
    # Stats
    cur.execute('SELECT COUNT(*) FROM trade_archive')
    total_trades = cur.fetchone()[0]
    cur.execute('SELECT COUNT(DISTINCT symbol) FROM trade_archive')
    total_syms = cur.fetchone()[0]
    
    print(f'歸檔交易: {total_trades}筆')
    print(f'涵蓋股票: {total_syms}檔')
    
    conn.close()

def main():
    get_current_databases()
    
    added_us = expand_us_stocks()
    added_ai = expand_ai_tech()
    build_trade_archive()
    
    print('\n\n=== 資料庫擴展完成 ===')
    print(f'新增美股: {added_us}檔')
    print(f'新增AI股: {added_ai}檔')
    print('交易歸檔: 已建立')

if __name__ == '__main__':
    main()