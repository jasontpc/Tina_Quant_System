import sqlite3
from pathlib import Path

dbs = {
    'unified_db/unified_trading.db': '統一交易資料庫',
    'tw_ai_tech/tw_ai_tech.db': '台股AI科技',
    'tw_margin/tw_margin.db': '台股Margin',
    'tw_financial/tw_financial.db': '台股季報',
    'us_ai_tech/us_ai_tech.db': '美股AI科技',
    'us_margin/us_margin.db': '美股Margin',
    'us_financial/us_financial.db': '美股季報',
    'us_etf/us_etf.db': '美股ETF',
    'tw_etf/tw_etf.db': '台股ETF',
    'macro_db/macro.db': '宏觀分析',
    'usd_twd/usd_twd.db': 'USD/TWD',
}

print('='*60)
print('  Tina 全系統資料庫分析')
print('='*60)

total_records = 0
for db_path, name in dbs.items():
    p = Path(db_path)
    if p.exists():
        try:
            conn = sqlite3.connect(str(p))
            cur = conn.cursor()
            
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r[0] for r in cur.fetchall()]
            
            total = 0
            for t in tables:
                try:
                    cur.execute(f'SELECT COUNT(*) FROM {t}')
                    cnt = cur.fetchone()[0]
                    total += cnt
                except:
                    pass
            
            conn.close()
            total_records += total
            
            size_kb = p.stat().st_size / 1024
            print(f'{name:<20} {total:>6}  records ({size_kb:.1f} KB)')
        except Exception as e:
            print(f'{name:<20} err')
    else:
        print(f'{name:<20} -- not found')

print()
print(f'Total records: {total_records:,}')
print('='*60)