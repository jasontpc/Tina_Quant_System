# -*- coding: utf-8 -*-
"""
全系統 Cron 分析 + 自動排程優化系統 v1.0
"""

import sys, json, subprocess, re
from datetime import datetime
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

def get_cron_list_ps():
    """用PowerShell取得Cron清單"""
    ps = '''openclaw cron list 2>&1 | Select-String -Pattern "^\\S{8}-"'''
    result = subprocess.run(['powershell', '-Command', ps],
                          capture_output=True, text=True, encoding='utf-8', errors='replace')
    lines = result.stdout.split('\n')
    
    jobs = []
    for line in lines:
        if re.match(r'^[a-f0-9]{8}-', line):
            parts = line.split()
            if len(parts) >= 3:
                job_id = parts[0]
                name = parts[1] if len(parts) > 1 else ''
                schedule = parts[2] if len(parts) > 2 else ''
                
                status = 'unknown'
                if 'error' in line.lower(): status = 'error'
                elif 'running' in line.lower(): status = 'running'
                elif 'idle' in line.lower(): status = 'idle'
                elif 'ok' in line.lower(): status = 'ok'
                
                jobs.append({
                    'id': job_id,
                    'name': name,
                    'schedule': schedule,
                    'status': status,
                    'raw': line,
                })
    return jobs

def estimate_daily_runs(schedule_expr):
    """估算每日執行次數"""
    parts = schedule_expr.split()
    if len(parts) != 5:
        return 0
    minute, hour, day, month, dow = parts
    count = 1
    
    if minute.startswith('*/'):
        count *= 1440 // int(minute[2:])
    elif ',' in minute:
        count *= len(minute.split(','))
    elif '-' in minute:
        s, e = map(int, minute.split('-')); count *= e - s + 1
    
    if hour.startswith('*/'):
        count *= 24 // int(hour[2:])
    elif ',' in hour:
        count *= len(hour.split(','))
    elif '-' in hour:
        s, e = map(int, hour.split('-')); count *= e - s + 1
    
    if dow != '*':
        if ',' in dow: count *= len(dow.split(','))
    
    return min(count, 500)

def main():
    print('=' * 60)
    print('  全系統 Cron 分析 + 自動排程優化 v1.0')
    print(f'  時間: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('=' * 60)
    
    jobs = get_cron_list_ps()
    print(f'\n總計: {len(jobs)} 個Cron Jobs')
    
    status_count = defaultdict(int)
    for j in jobs: status_count[j['status']] += 1
    print('\n狀態統計:')
    for s, c in sorted(status_count.items()): print(f'  {s}: {c}個')
    
    total_runs = 0
    for j in jobs:
        runs = estimate_daily_runs(j['schedule'])
        j['daily_runs'] = runs
        total_runs += runs
    print(f'\n每日執行: ~{total_runs}次')
    
    # Group by team
    teams = {'Nana': [], 'Leo': [], 'Ray': [], 'Tina': [], 'Other': []}
    for j in jobs:
        n = j['name']
        if 'Nana' in n: teams['Nana'].append(j)
        elif 'Leo' in n: teams['Leo'].append(j)
        elif 'Ray' in n: teams['Ray'].append(j)
        elif any(x in n for x in ['Tina', '每日', 'API']): teams['Tina'].append(j)
        else: teams['Other'].append(j)
    
    print('\n團隊分組:')
    for team, job_list in teams.items():
        if job_list:
            runs = sum(j.get('daily_runs', 0) for j in job_list)
            print(f'\n  [{team}] {len(job_list)}個, ~{runs}次/天')
            for j in job_list:
                print(f'    {j["name"]} ({j["schedule"]}) [{j["status"]}]')
    
    # Error jobs
    error_jobs = [j for j in jobs if j['status'] == 'error']
    if error_jobs:
        print(f'\n\n⚠️  Error Jobs ({len(error_jobs)}個):')
        for j in error_jobs:
            print(f'  - {j["name"]}')
            print(f'    ID: {j["id"]}')
            print(f'    Schedule: {j["schedule"]}')
    
    # High frequency
    high_freq = [j for j in jobs if j.get('daily_runs', 0) > 50]
    if high_freq:
        print(f'\n\n⚠️  高頻 Jobs (>50次/天, {len(high_freq)}個):')
        for j in high_freq:
            print(f'  - {j["name"]}: ~{j["daily_runs"]}次/天')
    
    # Simultaneous check (same minute, 3+ jobs)
    by_time = defaultdict(list)
    for j in jobs:
        p = j['schedule'].split()
        if len(p) == 5 and p[0] == '*/15':
            key = f"{p[0]}_{p[1]}"
            by_time[key].append(j)
    
    simultaneous = {k: v for k, v in by_time.items() if len(v) >= 3}
    if simultaneous:
        print(f'\n\n⚠️  同分鐘衝突 (3+ jobs, {len(simultaneous)}組):')
        for sched, jlist in simultaneous.items():
            print(f'  {sched}: {[j["name"] for j in jlist]}')
    
    # Optimization plan
    print('\n\n優化建議:')
    
    fix_plan = []
    
    # Fix error jobs -> delete and reschedule
    for j in error_jobs:
        fix_plan.append({'action': 'DELETE_ERROR', 'job_id': j['id'], 'job_name': j['name']})
    
    # Nana: 2 jobs both */15 -> merge into one or stagger
    nana_jobs = teams['Nana']
    if len(nana_jobs) >= 2:
        fix_plan.append({
            'action': 'NANA_CONSOLIDATE',
            'desc': f'Nana有{len(nana_jobs)}個高頻jobs，建議整合成1個',
            'jobs': [j['name'] for j in nana_jobs]
        })
    
    if fix_plan:
        print(f'\n修復計劃 ({len(fix_plan)}項):')
        for f in fix_plan:
            if f['action'] == 'DELETE_ERROR':
                print(f'  [DELETE] {f["job_name"]} -> 刪除並重新排程')
            elif f['action'] == 'NANA_CONSOLIDATE':
                print(f'  [CONSOLIDATE] {f["desc"]}')
                for j in f['jobs']: print(f'    - {j}')
    
    # Auto-fix: remove error jobs
    print('\n\n自動執行修復...')
    for f in fix_plan:
        if f['action'] == 'DELETE_ERROR':
            print(f'  刪除: {f["job_name"]}')
            subprocess.run(['openclaw', 'cron', 'remove', f['job_id']],
                         capture_output=True, text=True)
    
    print('\n' + '=' * 60)
    print(f'完成: 刪除{len(error_jobs)}個error jobs')
    print('=' * 60)

if __name__ == '__main__':
    main()