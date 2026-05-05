# -*- coding: utf-8 -*-
"""
Full DB Updater - Tina Quant System
Master orchestrator that runs all database update tasks.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import logging
import subprocess
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[
    logging.FileHandler(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\logs\full_db_updater.log", encoding='utf-8'),
    logging.StreamHandler()
])
log = logging.getLogger(__name__)

BASE = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System"
SCRIPTS_DIR = f"{BASE}\\scripts"


def run_script(name, script_path, timeout=600):
    """Run a Python script and capture results"""
    log.info(f"\n=== Running {name} ===")
    start = datetime.now()
    try:
        result = subprocess.run(
            ["python", script_path],
            capture_output=True, text=True, timeout=timeout,
            cwd=BASE, encoding='utf-8'
        )
        elapsed = (datetime.now() - start).total_seconds()
        success = result.returncode == 0

        if success:
            log.info(f"  ✓ {name} OK ({elapsed:.1f}s)")
        else:
            log.error(f"  ✗ {name} FAILED (exit {result.returncode})")
            log.error(f"  stderr: {result.stderr[:500]}")

        return {
            "script": name,
            "path": script_path,
            "success": success,
            "elapsed_s": elapsed,
            "stdout": result.stdout[-500:] if result.stdout else "",
            "stderr": result.stderr[-500:] if result.stderr else "",
        }
    except subprocess.TimeoutExpired:
        log.error(f"  ✗ {name} TIMEOUT ({timeout}s)")
        return {"script": name, "path": script_path, "success": False, "elapsed_s": timeout, "error": "timeout"}
    except Exception as e:
        log.error(f"  ✗ {name} EXCEPTION: {e}")
        return {"script": name, "path": script_path, "success": False, "elapsed_s": 0, "error": str(e)}


def main():
    log.info("=" * 60)
    log.info("FULL DB UPDATER STARTED")
    log.info("=" * 60)
    start_time = datetime.now()

    results = []

    # 1. Trade History Updater
    r = run_script(
        "trade_history_updater",
        f"{SCRIPTS_DIR}\\trade_history_updater.py",
        timeout=600
    )
    results.append(r)

    # 2. Financial Data Fetcher
    r = run_script(
        "financial_data_fetcher",
        f"{SCRIPTS_DIR}\\financial_data_fetcher.py",
        timeout=600
    )
    results.append(r)

    # 3. DB Maintenance
    r = run_script(
        "db_maintenance",
        f"{SCRIPTS_DIR}\\db_maintenance.py",
        timeout=300
    )
    results.append(r)

    # 4. Core DB Updater (existing script)
    r = run_script(
        "core_db_updater",
        f"{SCRIPTS_DIR}\\core_db_updater.py",
        timeout=600
    )
    results.append(r)

    total_elapsed = (datetime.now() - start_time).total_seconds()

    log.info("\n" + "=" * 60)
    log.info("FULL DB UPDATER COMPLETED")
    log.info("=" * 60)

    success_count = sum(1 for r in results if r["success"])
    log.info(f"Results: {success_count}/{len(results)} succeeded in {total_elapsed:.1f}s")

    for r in results:
        status = "✓" if r["success"] else "✗"
        log.info(f"  {status} {r['script']} ({r['elapsed_s']:.1f}s)")

    # Save results
    report = {
        "timestamp": start_time.isoformat(),
        "total_elapsed_s": total_elapsed,
        "results": results,
        "summary": {
            "total": len(results),
            "success": success_count,
            "failed": len(results) - success_count,
        }
    }

    report_path = f"{BASE}\\reports\\full_db_updater_{start_time.strftime('%Y%m%d_%H%M')}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    log.info(f"Report saved: {report_path}")

    return report


if __name__ == "__main__":
    main()