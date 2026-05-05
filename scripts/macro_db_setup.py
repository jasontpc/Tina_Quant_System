"""
Macro & Institutional Database Setup
建立宏觀法人資料庫結構
"""
import sqlite3
import os
from datetime import datetime

DB_PATH = "./data/macro_institutional.db"

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def create_tables():
    conn = get_connection()
    cur = conn.cursor()
    
    # 1. 每日法人買賣超（三大法人）
    cur.execute("""
        CREATE TABLE IF NOT EXISTS institutional_daily (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            stock_id TEXT,
            stock_name TEXT,
            foreign_buy INTEGER DEFAULT 0,
            foreign_sell INTEGER DEFAULT 0,
            foreign_net INTEGER DEFAULT 0,
            trust_buy INTEGER DEFAULT 0,
            trust_sell INTEGER DEFAULT 0,
            trust_net INTEGER DEFAULT 0,
            dealer_buy INTEGER DEFAULT 0,
            dealer_sell INTEGER DEFAULT 0,
            dealer_net INTEGER DEFAULT 0,
            total_net INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, stock_id)
        )
    """)
    
    # 2. 產業資金流向
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sector_flow (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            sector TEXT NOT NULL,
            foreign_net INTEGER DEFAULT 0,
            trust_net INTEGER DEFAULT 0,
            dealer_net INTEGER DEFAULT 0,
            total_net INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, sector)
        )
    """)
    
    # 3. ETF 持股變化
    cur.execute("""
        CREATE TABLE IF NOT EXISTS etf_holding (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            etf_id TEXT NOT NULL,
            etf_name TEXT,
            stock_id TEXT NOT NULL,
            stock_name TEXT,
            shares INTEGER DEFAULT 0,
            change INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, etf_id, stock_id)
        )
    """)
    
    # 4. 融資融券餘額
    cur.execute("""
        CREATE TABLE IF NOT EXISTS margin_balance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            stock_id TEXT NOT NULL,
            stock_name TEXT,
            margin_balance INTEGER DEFAULT 0,
            margin_balance_value INTEGER DEFAULT 0,
            short_balance INTEGER DEFAULT 0,
            margin_call_ratio REAL DEFAULT 0,
            balance_change INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, stock_id)
        )
    """)
    
    # 5. 美股資金流向
    cur.execute("""
        CREATE TABLE IF NOT EXISTS us_fund_flow (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            symbol TEXT NOT NULL,
            sector TEXT,
            net_flow_billion REAL DEFAULT 0,
            price_change REAL DEFAULT 0,
            volume_billion REAL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, symbol)
        )
    """)
    
    # 6. 宏觀指標
    cur.execute("""
        CREATE TABLE IF NOT EXISTS macro_indicators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            indicator TEXT NOT NULL,
            value REAL DEFAULT 0,
            change_pct REAL DEFAULT 0,
            source TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, indicator)
        )
    """)
    
    # Indexes
    cur.execute("CREATE INDEX IF NOT EXISTS idx_inst_date ON institutional_daily(date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sector_date ON sector_flow(date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_margin_date ON margin_balance(date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_usflow_date ON us_fund_flow(date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_macro_date ON macro_indicators(date)")
    
    conn.commit()
    conn.close()
    print(f"[{datetime.now():%H:%M:%S}] Database tables created at {DB_PATH}")

def cleanup_old_data(days=730):
    """清理超過 N 天的舊資料"""
    conn = get_connection()
    cur = conn.cursor()
    cutoff = f"datetime('now', '-{days} days')"
    
    tables = ['institutional_daily', 'sector_flow', 'etf_holding', 
              'margin_balance', 'us_fund_flow', 'macro_indicators']
    
    for table in tables:
        try:
            cur.execute(f"DELETE FROM {table} WHERE created_at < {cutoff}")
            print(f"  Cleaned {table}: {cur.rowcount} rows removed")
        except Exception as e:
            print(f"  Warning {table}: {e}")
    
    conn.commit()
    conn.close()
    print(f"[{datetime.now():%H:%M:%S}] Cleanup completed (retention: {days} days)")

if __name__ == "__main__":
    create_tables()
    cleanup_old_data()
