# -*- coding: utf-8 -*-
"""
全系統 Cron 深度分析 + 整合優化系統 v2.0
分析所有Cron jobs，自動識別衝突/重疊/冗餘，自動執行整合
"""

import sys, json, subprocess, re
from datetime import datetime
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

def get_all_crons():
    """取得所有Cron jobs"""
    result = subprocess.run(['openclaw', 'cron', 'list'],
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

def count_daily_runs(sched):
    """計算每日執行次數"""
    p = sched.split()
    if len(p) != 5: return 0
    m, h, d, mo, dow = p
    c = 1
    
    if m.startswith('*/'):
        c *= 1440 // int(m[2:])
    elif ',' in m:
        c *= len(m.split(','))
    elif '-' in m:
        s,e = map(int, m.split('-')); c *= e-s+1
    
    if h.startswith('*/'):
        c *= 24 // int(h[2:])
    elif ',' in h:
        c *= len(h.split(','))
    elif '-' in h:
        s,e = map(int, h.split('-')); c *= e-s+1
    
    if dow != '*':
        if ',' in dow: c *= len(dow.split(','))
    
    return min(c, 1000)

def main():
    print('=' * 65)
    print('  全系統 Cron 深度分析 + 整合優化 v2.0')
    print(f'  時間: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('=' * 65)
    
    jobs = get_all_crons()
    print(f'\n[1] Cron Jobs 總數: {len(jobs)}個')
    
    # Stats
    status_count = defaultdict(int)
    for j in jobs: status_count[j['status']] += 1
    print(f'\n[2] 狀態統計:')
    for s, c in sorted(status_count.items()): print(f'    {s}: {c}個')
    
    # Daily runs
    total_runs = 0
    for j in jobs:
        j['runs'] = count_daily_runs(j['schedule'])
        total_runs += j['runs']
    print(f'\n[3] 每日總執行: ~{total_runs}次')
    
    # Group by team
    teams = defaultdict(list)
    for j in jobs:
        n = j['name']
        if 'Nana' in n: teams['Nana'].append(j)
        elif 'Leo' in n: teams['Leo'].append(j)
        elif 'Ray' in n: teams['Ray'].append(j)
        elif any(x in n for x in ['每日', 'API', '早盤']): teams['Tina'].append(j)
        else: teams['Other'].append(j)
    
    print(f'\n[4] 團隊 Jobs 統計:')
    team_runs = {}
    for t, jl in sorted(teams.items()):
        runs = sum(j['runs'] for j in jl)
        team_runs[t] = runs
        print(f'    {t}: {len(jl)}個 Jobs, ~{runs}次/天')
    
    # Issues
    print(f'\n[5] 問題分析:')
    
    # A. Same schedule jobs
    sched_groups = defaultdict(list)
    for j in jobs:
        sched_groups[j['schedule']].append(j)
    
    duplicates = {s: v for s, v in sched_groups.items() if len(v) > 1}
    if duplicates:
        print(f'\n  ⚠️  同排程衝突 ({len(duplicates)}組):')
        for s, jl in duplicates.items():
            print(f'    排程: {s}')
            for j in jl: print(f'      - {j["name"]} [{j["status"]}]')
    
    # B. High frequency
    high_freq = [j for j in jobs if j['runs'] > 100]
    if high_freq:
        print(f'\n  ⚠️  高頻 Jobs (>100次/天, {len(high_freq)}個):')
        for j in high_freq:
            print(f'    - {j["name"]}: {j["schedule"]} (~{j["runs"]}次/天)')
    
    # C. Error jobs
    errors = [j for j in jobs if j['status'] == 'error']
    if errors:
        print(f'\n  ⚠️  Error Jobs ({len(errors)}個):')
        for j in errors: print(f'    - {j["name"]} ({j["id"]})')
    
    # Consolidate plan
    print(f'\n[6] 整合優化計劃:')
    
    to_remove = []
    to_add = []
    
    # Issue 1: Nana 交易預測 + 自主交易 both */15 at same time -> merge
    nana_15 = [j for j in teams['Nana'] if '*/15' in j['schedule'] and j['status'] in ['ok', 'idle']]
    if len(nana_15) >= 2:
        print(f'\n  【Nana × 2 → 整合成1個】')
        print(f'    移除: Nana交易預測, Nana自主交易')
        to_remove.extend([nana_15[0]['id'], nana_15[1]['id']])
        to_add.append({
            'name': 'Nana 交易分析整合',
            'cron': '*/30 0-7,9-12,13-23 * * *',
            'msg': 'Nana整合分析：執行trade_predictor.py+autonomous_trader.py（1）分析10檔股票RSI/BIAS/ATR，（2）自主交易模拟進出场，（3）根據市場體制動態調整進場門檻（OVERBOUGHT時禁止進場）。（原2個*/15 job整合）'
        })
        print(f'    新排程: */30 0-7,9-12,13-23 * * * (~32次/天)')
    
    # Issue 2: Leo */15 same as new Nana */30 -> stagger
    print(f'\n  【Leo 排程調整】')
    leo_job = [j for j in teams['Leo'] if j['status'] == 'idle']
    if leo_job:
        print(f'    調整: Leo */15 0-7,13-23 → */30 0-7,13-23')
        to_remove.append(leo_job[0]['id'])
        to_add.append({
            'name': 'Leo 每30分鐘自主學習',
            'cron': '*/30 0-7,13-23 * * *',
            'msg': 'Leo自主學習迴圈：執行leo_autonomous_cycle.py（1）分析8檔AI科技股RSI/MA20，（2）檢查波段進出场，（3）記錄模擬交易並計算勝率/報酬。（調整自*/15）'
        })
    
    # Issue 3: Ray */20 -> */30 (high frequency)
    ray_20 = [j for j in teams['Ray'] if '*/20' in j['schedule']]
    if ray_20:
        print(f'\n  【Ray 每20分鐘 → 每30分鐘】')
        for j in ray_20:
            print(f'    調整: {j["name"]} {j["schedule"]} → */30')
            to_remove.append(j['id'])
        to_add.append({
            'name': 'Ray 每30分鐘系統優化（工作日）',
            'cron': '*/30 0-5 * * 1-5',
            'msg': 'Ray每30分鐘自主優化：評估所有ETF技術面，根據entry_threshold=50決策是否DCA加碼，檢查持倉狀況。（調整自*/20）'
        })
    
    # Issue 4: Ray 每60分鐘系統檢討 -> every 2 hours
    ray_60 = [j for j in teams['Ray'] if '*/1' in j['schedule'] and j['status'] == 'idle']
    if ray_60:
        print(f'\n  【Ray 每60分鐘 → 每2小時】')
        for j in ray_60:
            print(f'    調整: {j["name"]} {j["schedule"]} → 0 */2')
            to_remove.append(j['id'])
        to_add.append({
            'name': 'Ray 每2小時系統檢討（盤後）',
            'cron': '0 */2 * * 1-5',
            'msg': 'Ray每2小時系統檢討：分析大盤+ETF技術面，評估市場趨勢，檢查理想進場價。（調整自每60分鐘）'
        })
    
    # Issue 5: Nana */3hours -> every 4 hours
    nana_3h = [j for j in teams['Nana'] if '*/3' in j['schedule']]
    if nana_3h:
        print(f'\n  【Nana 每3小時 → 每4小時】')
        for j in nana_3h:
            print(f'    調整: {j["name"]} → 0 */4')
            to_remove.append(j['id'])
        to_add.append({
            'name': 'Nana 每4小時自主學習',
            'cron': '0 */4 * * *',
            'msg': 'Nana自主學習（整合模擬交易+回測+開發）：每4小時執行一次。（調整自每3小時）'
        })
    
    print(f'\n[7] 執行整合:')
    print(f'  移除: {len(to_remove)}個 Jobs')
    print(f'  新增: {len(to_add)}個 Jobs')
    
    # Execute removals
    removed = 0
    for rid in to_remove:
        r = subprocess.run(['openclaw', 'cron', 'remove', rid],
                         capture_output=True, text=True, encoding='utf-8', errors='replace')
        if 'removed' in r.stdout.lower() or r.returncode == 0:
            removed += 1
    print(f'  實際移除: {removed}個')
    
    # Execute additions
    added = 0
    for a in to_add:
        r = subprocess.run(['openclaw', 'cron', 'add',
                          '--name', a['name'],
                          '--cron', a['cron'],
                          '--session', 'isolated',
                          '--announce', '--to', 'telegram:1616824689',
                          '--timeout-seconds', '300',
                          '--message', a['msg']],
                         capture_output=True, text=True, encoding='utf-8', errors='replace')
        if r.returncode == 0 or 'id' in r.stdout.lower():
            added += 1
    print(f'  實際新增: {added}個')
    
    # Summary
    print(f'\n' + '=' * 65)
    print('  整合完成')
    print('=' * 65)
    
    new_total = len(jobs) - removed + added
    print(f'  原始 Jobs: {len(jobs)}個 → 整合後: {new_total}個')
    print(f'  移除: {removed}個 | 新增: {added}個')
    print(f'  每日執行: ~{total_runs}次 → 預計減少~{int(total_runs * 0.4)}次')

if __name__ == '__main__':
    main()