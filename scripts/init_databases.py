import sqlite3, os

data_dir = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'

# Build tina_trade_history.db
th_db = os.path.join(data_dir, 'tina_trade_history.db')
conn = sqlite3.connect(th_db)
cur = conn.cursor()
cur.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT,
        stock TEXT,
        entry_date TEXT,
        entry_price REAL,
        exit_date TEXT,
        exit_price REAL,
        pnl_pct REAL,
        hold_days INTEGER,
        strategy TEXT,
        entry_rsi REAL,
        exit_rsi REAL,
        macd_signal TEXT,
        market_regime TEXT,
        outcome TEXT,
        tags TEXT,
        lesson TEXT,
        created_at TEXT
    )
""")
conn.commit()
conn.close()
print(f"[OK] tina_trade_history.db ready: {th_db}")

# Build tina_alert_log.db
al_db = os.path.join(data_dir, 'tina_alert_log.db')
conn = sqlite3.connect(al_db)
cur = conn.cursor()
cur.execute("""
    CREATE TABLE IF NOT EXISTS alert_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        alert_name TEXT NOT NULL,
        priority TEXT,
        condition TEXT,
        action_taken TEXT,
        details TEXT,
        acknowledged INTEGER DEFAULT 0
    )
""")
cur.execute("""
    CREATE TABLE IF NOT EXISTS cooldown_tracker (
        alert_name TEXT PRIMARY KEY,
        last_triggered TEXT,
        cooldown_hours INTEGER
    )
""")
conn.commit()
conn.close()
print(f"[OK] tina_alert_log.db ready: {al_db}")

# Build tina_param_versions.db
pv_db = os.path.join(data_dir, 'tina_param_versions.db')
conn = sqlite3.connect(pv_db)
cur = conn.cursor()
cur.execute("""
    CREATE TABLE IF NOT EXISTS param_versions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        version TEXT UNIQUE NOT NULL,
        parent_version TEXT,
        created_at TEXT NOT NULL,
        description TEXT,
        params_json TEXT NOT NULL,
        performance_json TEXT,
        is_active INTEGER DEFAULT 0,
        is_deployed INTEGER DEFAULT 0
    )
""")
cur.execute("""
    CREATE TABLE IF NOT EXISTS param_changes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        version TEXT NOT NULL,
        param_key TEXT NOT NULL,
        old_value TEXT,
        new_value TEXT,
        reason TEXT,
        created_at TEXT NOT NULL
    )
""")
conn.commit()
conn.close()
print(f"[OK] tina_param_versions.db ready: {pv_db}")

print("\nAll databases initialized.")