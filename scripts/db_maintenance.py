# -*- coding: utf-8 -*-
"""
DB Maintenance Script - Tina Quant System
Handles vacuum, integrity checks, stale data cleanup.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import sqlite3
import os
import time
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

BASE = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System"
DATA_DIR = f"{BASE}\\data"

MAIN_DBS = [
    "tw_history.db",
    "us_history.db",
    "financial_history.db",
    "tina_master.db",
    "portfolio.db",
    "stock_trends.db",
    "macro_institutional.db",
]


def vacuum_db(db_path):
    """VACUUM a database"""
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("VACUUM")
        conn.close()
        size = os.path.getsize(db_path) / 1024
        log.info(f"  VACUUM {os.path.basename(db_path)}: {size:.0f} KB")
        return True, size
    except Exception as e:
        log.error(f"  VACUUM {os.path.basename(db_path)} failed: {e}")
        return False, 0


def integrity_check(db_path):
    """PRAGMA integrity_check"""
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("PRAGMA integrity_check")
        result = cur.fetchone()[0]
        conn.close()
        ok = result == "ok"
        log.info(f"  Integrity {os.path.basename(db_path)}: {result}")
        return ok, result
    except Exception as e:
        log.error(f"  Integrity check failed for {db_path}: {e}")
        return False, str(e)


def analyze_db(db_path):
    """Run ANALYZE for query optimization"""
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("ANALYZE")
        conn.close()
        log.info(f"  ANALYZE {os.path.basename(db_path)}: OK")
        return True
    except Exception as e:
        log.error(f"  ANALYZE failed: {e}")
        return False


def get_db_stats(db_path):
    """Get row counts and last update for each table"""
    stats = {}
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [t[0] for t in cur.fetchall()]
        for t in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {t}")
                stats[t] = cur.fetchone()[0]
            except:
                stats[t] = -1
        conn.close()
    except Exception as e:
        log.error(f"  Stats failed for {db_path}: {e}")
    return stats


def cleanup_stale_trades(db_path, days=90):
    """Delete old unverified RSI signals and trades"""
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cutoff = datetime.now().strftime("%Y-%m-%d")

        # Clean old unverified signals
        try:
            cur.execute("DELETE FROM rsi_signals WHERE verified=0 AND date < date('now', '-90 days')")
            deleted = cur.rowcount
            log.info(f"  Deleted {deleted} stale unverified RSI signals")
        except:
            pass

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log.error(f"  Cleanup failed for {db_path}: {e}")
        return False


def main():
    log.info("=== DB Maintenance ===")
    start = datetime.now()
    results = []

    for db_name in MAIN_DBS:
        db_path = os.path.join(DATA_DIR, db_name)
        if not os.path.exists(db_path):
            log.warning(f"  DB not found: {db_name}")
            continue

        log.info(f"\nProcessing {db_name}...")
        size = os.path.getsize(db_path) / 1024
        log.info(f"  Size: {size:.0f} KB")

        # Integrity check
        ok, detail = integrity_check(db_path)
        results.append({"db": db_name, "integrity": ok, "detail": detail})

        # Stats
        stats = get_db_stats(db_path)
        log.info(f"  Tables: {stats}")

        # Cleanup
        if db_name in ("tw_history.db", "us_history.db"):
            cleanup_stale_trades(db_path)

        # Vacuum
        ok, new_size = vacuum_db(db_path)
        results[-1]["vacuum_ok"] = ok
        results[-1]["size_kb"] = new_size

        # Analyze
        ok = analyze_db(db_path)
        results[-1]["analyze_ok"] = ok

        time.sleep(0.1)

    elapsed = (datetime.now() - start).total_seconds()
    log.info(f"\nDone. Time={elapsed:.1f}s")

    # Save report
    import json
    report_path = os.path.join(BASE, "reports", f"db_maintenance_{datetime.now().strftime('%Y%m%d_%H%M')}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({"results": results, "elapsed_s": elapsed, "timestamp": datetime.now().isoformat()}, f, indent=2, default=str)
    log.info(f"Report: {report_path}")

    return results


if __name__ == "__main__":
    main()