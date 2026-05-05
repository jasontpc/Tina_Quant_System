"""
Master DB Scheduler - 統一排程總管
驅動所有團隊資料庫更新、健康檢查、優化任務
"""

import subprocess
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [SCHEDULER] %(levelname)s %(message)s')
log = logging.getLogger('master_scheduler')

SCRIPTS_DIR = Path(__file__).parent

TEAM_UPDATERS = [
    ('nana_db_updater.py', 'NANA'),
    ('leo_db_updater.py', 'LEO'),
    ('ray_db_updater.py', 'RAY'),
    ('maggy_db_updater.py', 'MAGGY'),
    ('core_db_updater.py', 'CORE'),
]

HEALTH_CHECK = 'db_health_check.py'
DB_OPTIMIZER = 'db_optimizer.py'

def run_script(script_name, team_label):
    """執行單一腳本"""
    script_path = SCRIPTS_DIR / script_name
    log.info(f'Running {team_label} ({script_name})...')
    try:
        result = subprocess.run(
            ['python', str(script_path)],
            capture_output=True,
            text=True,
            timeout=120,
            encoding='utf-8',
            errors='replace'
        )
        if result.returncode == 0:
            log.info(f'  {team_label}: OK')
            return True
        else:
            log.error(f'  {team_label}: FAILED (exit {result.returncode})')
            if result.stderr:
                log.error(f'  stderr: {result.stderr[:500]}')
            return False
    except subprocess.TimeoutExpired:
        log.error(f'  {team_label}: TIMEOUT')
        return False
    except Exception as e:
        log.error(f'  {team_label}: ERROR - {e}')
        return False

def run_all_team_updates():
    """執行所有團隊資料庫更新"""
    log.info('=== Master Scheduler: All Team DB Updates ===')
    results = {}
    for script, team in TEAM_UPDATERS:
        results[team] = run_script(script, team)
    return results

def run_health_check():
    """執行健康檢查"""
    log.info('=== Master Scheduler: Health Check ===')
    return run_script(HEALTH_CHECK, 'HEALTH')

def run_optimizer():
    """執行優化"""
    log.info('=== Master Scheduler: DB Optimizer ===')
    return run_script(DB_OPTIMIZER, 'OPTIMIZER')

def run_full_cycle():
    """執行完整循環：更新 -> 健康檢查 -> 優化"""
    log.info('=== Full DB Update Cycle Start ===')
    start = datetime.now()

    results = {
        'teams': run_all_team_updates(),
        'health': run_health_check(),
        'optimizer': run_optimizer(),
        'finished_at': None,
        'duration_sec': None
    }

    elapsed = (datetime.now() - start).total_seconds()
    results['finished_at'] = datetime.now().isoformat()
    results['duration_sec'] = round(elapsed, 1)

    ok = sum(1 for v in results['teams'].values() if v)
    total = len(results['teams'])
    log.info(f'=== Cycle Done in {elapsed:.1f}s. Teams OK: {ok}/{total} ===')
    return results

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--health-only':
        run_health_check()
    elif len(sys.argv) > 1 and sys.argv[1] == '--optimize':
        run_optimizer()
    else:
        run_full_cycle()