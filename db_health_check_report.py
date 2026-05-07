# -*- coding: utf-8 -*-
import sqlite3, os

data_dir = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
DB_LIST = [
    'yfinance.db', 'nana_stocks.db', 'leo_stocks.db',
    'etf.db', 'sherry_etf.db', 'us_history.db',
    'tw_history.db', 'master_backtest.db', 'sherry_backtest.db',
    'tw_margin.db', 'macro_institutional.db', 'leverage_etf.db',
]

print("=== Tina 全系統數據庫健檢 ===\n")
print(f"{'資料庫':<22} {'大小':>8} {'Table數':>8} {'總筆數':>12} {'最新日期':>12} {'狀態':>6}")
print("-" * 72)

for db in DB_LIST:
    path = os.path.join(data_dir, db)
    if not os.path.exists(path):
        print(f"{db:<22} {'N/A':>8}")
        continue
    sz = os.path.getsize(path) / 1024 / 1024
    try:
        conn = sqlite3.connect(path)
        conn.execute('PRAGMA journal_mode=WAL')
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        total_rows = 0
        latest = 'N/A'
        for t in tables:
            try:
                cnt = cur.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
                total_rows += cnt
                # find date column for latest
                col_q = cur.execute(f"PRAGMA table_info(\"{t}\")").fetchall()
                date_cols = [c[1] for c in col_q if c[1].lower() in ('date','trade_date','updated_at')]
                if not date_cols and 'date' in t.lower(): date_cols = [c[1] for c in col_q]
                if date_cols:
                    row = cur.execute(f'SELECT MAX("{date_cols[0]}") FROM "{t}"').fetchone()[0]
                    if row and (latest == 'N/A' or str(row) > str(latest)):
                        latest = str(row)
            except: pass
        conn.close()
        status = "OK" if sz < 500 else "WARN"
        print(f"{db:<22} {sz:>7.1f}MB {len(tables):>8} {total_rows:>12,} {latest:>12} {status:>6}")
    except Exception as e:
        print(f"{db:<22} ERROR: {e}")

# WAL 檢查
print("\n=== WAL 檔案（可清理）===")
import glob
wal_files = glob.glob(os.path.join(data_dir, "*.db-wal")) + glob.glob(os.path.join(data_dir, "*.db-shm"))
for f in wal_files:
    sz = os.path.getsize(f) / 1024
    print(f"  {os.path.basename(f)} - {sz:.1f} KB")

# 磁碟空間
import shutil
total, used = shutil.disk_usage("C:\\")[:2]
print(f"\n=== 磁碟空間 ===")
print(f"  C: 總 {total//(1024**3)} GB | 已用 {used//(1024**3)} GB | 可用 {(total-used)//(1024**3)} GB")

print("\n✅ 健檢完成")