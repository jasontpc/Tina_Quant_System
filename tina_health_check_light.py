# -*- coding: utf-8 -*-
"""
Tina 全系統健康檢查 - 輕量版 (2026-04-30)
修復 timeout 問題，移除所有 blocking 動作
"""

import sys, json, subprocess, re
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
TEAMS_DIR = WORKSPACE / "teams"
REPORT_FILE = TEAMS_DIR / "tina_health_report.json"

def run_cmd(cmd, timeout=5):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout, encoding='utf-8', errors='replace')
        return result.stdout.strip()
    except:
        return ""

def check_cron_jobs():
    output = run_cmd('openclaw cron list', 10)
    lines = output.split('\n')
    jobs = []
    for line in lines[1:]:
        if line.strip():
            parts = re.split(r'\s+', line.strip(), maxsplit=8)
            if len(parts) >= 8:
                job_id = parts[0]
                name = parts[1]
                status = parts[5]
                jobs.append({'id': job_id, 'name': name, 'status': status})
    error_jobs = [j for j in jobs if j['status'] == 'error']
    ok_jobs = [j for j in jobs if j['status'] == 'ok']
    return {'total': len(jobs), 'ok': len(ok_jobs), 'error': len(error_jobs), 'errors': error_jobs}

def check_scripts():
    scripts = {
        'nana_v64': r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\nana\nana_v64.py",
        'leo_v70': r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\leadtrades\leos\leo_v70.py",
        'ray_dca': r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\ray\dca_market_brief.py",
    }
    results = {}
    for name, path in scripts.items():
        exists = Path(path).exists()
        results[name] = {'exists': exists, 'path': path}
    return results

def main():
    report = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'cron': check_cron_jobs(),
        'scripts': check_scripts(),
    }
    
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(json.dumps(report, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()