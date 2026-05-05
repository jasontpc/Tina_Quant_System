"""
資料庫健康檢查腳本
檢查所有資料庫的記錄數量、最新更新的時間戳、中斷的更新
產出: reports/db_health_report_{date}.json
"""

import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
import yfinance as yf

logging.basicConfig(level=logging.INFO, format='%(asctime)s [HEALTH] %(levelname)s %(message)s')
log = logging.getLogger('db_health_check')

DATA_DIR = Path(__file__).parent.parent / 'data'
REPORTS_DIR = Path(__file__).parent.parent / 'reports'
OUT_FILE = REPORTS_DIR / f"db_health_report_{datetime.now().strftime('%Y%m%d')}.json"

# 定義要檢查的資料庫
DATABASES = {
    'tw_history': DATA_DIR / 'tw_history.db',
    'us_history': DATA_DIR / 'us_history.db',
    'unified_trading': DATA_DIR / 'unified_trading.db',
    'portfolio': DATA_DIR / 'portfolio.db',
    'tina_master': DATA_DIR / 'tina_master.db',
    'maggy': DATA_DIR / 'maggy.db',
    'sherry_etf': DATA_DIR / 'sherry_etf.db',
    'vogel': DATA_DIR / 'vogel.db',
}

# 定義要檢查的 watchlist/status JSON 檔
WATCHLISTS = {
    'nana_watchlist': DATA_DIR / 'nana_watchlist.json',
    'leo_watchlist': DATA_DIR / 'leo_watchlist.json',
    'ray_watchlist': DATA_DIR / 'ray_watchlist.json',
    'maggy_watchlist': DATA_DIR / 'maggy_watchlist.json',
    'market_regime': DATA_DIR / 'market_regime.json',
    'watchlist': DATA_DIR / 'watchlist.json',
}

def check_db_record_count(db_path, db_name):
    """檢查資料庫記錄數量"""
    try:
        if not db_path.exists():
            return {'exists': False, 'error': 'file not found', 'tables': {}}
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        table_stats = {}
        for (tbl,) in tables:
            cursor.execute(f"SELECT COUNT(*) FROM [{tbl}]")
            count = cursor.fetchone()[0]
            table_stats[tbl] = count
        conn.close()
        total = sum(table_stats.values())
        return {'exists': True, 'total_records': total, 'tables': table_stats}
    except Exception as e:
        return {'exists': True, 'error': str(e), 'tables': {}}

def check_json_freshness(path, name):
    """檢查 JSON 檔案新舊"""
    try:
        if not path.exists():
            return {'exists': False, 'freshness': 'MISSING', 'age_minutes': -1}
        mtime = path.stat().st_mtime
        dt = datetime.fromtimestamp(mtime)
        age = (datetime.now() - dt).total_seconds() / 60
        if age < 60:
            freshness = 'FRESH'
        elif age < 240:
            freshness = 'STALE'
        elif age < 1440:
            freshness = 'OLD'
        else:
            freshness = 'ANCIENT'
        return {'exists': True, 'freshness': freshness, 'age_minutes': round(age, 1), 'last_updated': dt.isoformat()}
    except Exception as e:
        return {'exists': False, 'error': str(e)}

def check_data_quotas(db_name, db_path):
    """檢查最新報價資料是否足夠新（市場交易日）"""
    try:
        if not db_path.exists():
            return {}
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        # 嘗試找價格 table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name LIKE '%price%' OR name LIKE '%history%' OR name LIKE '%daily%')")
        tables = [r[0] for r in cursor.fetchall()]
        results = {}
        for tbl in tables[:3]:  # 最多檢查3個
            try:
                cursor.execute(f"SELECT MAX(date) FROM [{tbl}]")
                max_date = cursor.fetchone()[0]
                results[tbl] = max_date
            except:
                pass
        conn.close()
        return results
    except:
        return {}

def run_health_check():
    log.info('=== DB Health Check Start ===')
    report = {
        'generated_at': datetime.now().isoformat(),
        'databases': {},
        'watchlists': {},
        'data_quotas': {},
        'summary': {'ok': 0, 'warn': 0, 'error': 0}
    }

    # 檢查 DB
    for name, path in DATABASES.items():
        stats = check_db_record_count(path, name)
        latest = check_data_quotas(name, path)
        report['databases'][name] = {**stats, 'latest_data': latest}
        if not stats.get('exists', False):
            report['summary']['error'] += 1
            log.warning(f"  {name}: FILE MISSING")
        elif stats.get('error'):
            report['summary']['error'] += 1
            log.error(f"  {name}: {stats['error']}")
        elif stats.get('total_records', 0) == 0:
            report['summary']['warn'] += 1
            log.warning(f"  {name}: EMPTY ({stats['total_records']} records)")
        else:
            report['summary']['ok'] += 1
            log.info(f"  {name}: {stats['total_records']} records OK")

    # 檢查 JSON watchlists
    for name, path in WATCHLISTS.items():
        freshness = check_json_freshness(path, name)
        report['watchlists'][name] = freshness
        if not freshness.get('exists'):
            report['summary']['error'] += 1
            log.warning(f"  {name}: MISSING")
        elif freshness.get('freshness') in ('OLD', 'ANCIENT'):
            report['summary']['warn'] += 1
            log.warning(f"  {name}: {freshness['freshness']} ({freshness['age_minutes']}min old)")
        else:
            log.info(f"  {name}: {freshness['freshness']} ({freshness['age_minutes']}min old)")

    # 產出報告
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    log.info(f'Report written to {OUT_FILE}')
    log.info(f"Summary: OK={report['summary']['ok']} WARN={report['summary']['warn']} ERROR={report['summary']['error']}")
    return report

if __name__ == '__main__':
    run_health_check()