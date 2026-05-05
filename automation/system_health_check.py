# -*- coding: utf-8 -*-
"""
全系統健檢優化分析系統 v1.0
功能：
  1. 全系統健康檢查（所有團隊+Cron）
  2. 自動分析問題與優化機會
  3. 執行建議並整合入Cron排程
"""

import sys, os, json, yfinance as yf, pandas as pd, numpy as np, subprocess, re
from datetime import datetime, date
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System'
TEAMS_DIR = os.path.join(BASE_DIR, 'teams')

# ── 健檢項目 ────────────────────────────────
CHECK_ITEMS = {
    'Nana': {
        'skills': ['autonomous_trader.py', 'trade_predictor.py', 'nana_autonomous_develop.py', 'nana_sim_backtest.py', 'nana_v58.py'],
        'reports': ['autonomous_trades.json', 'trade_predictions.json', 'nana_learnings.json', 'nana_backtest_learnings.json'],
        'crons': [],
    },
    'Leo': {
        'skills': ['leo_analyzer.py', 'leo_autonomous_cycle.py'],
        'reports': ['leo_trades.json', 'leo_learnings.json', 'leo_analysis.json'],
        'crons': [],
    },
    'Ray': {
        'skills': ['ray_autonomous_trader.py', 'ray_dca_portfolio.py', 'ray_dca_cost_analyzer.py', 'ray_etf_dca.py'],
        'reports': ['dca_portfolio_plan.json', 'dca_cost_analysis.json', 'ray_status.json'],
        'crons': [],
    },
    'Tina': {
        'skills': ['heartbeat_check.py', 'system_monitor.py'],
        'reports': ['MEMORY.md', 'HEARTBEAT.md'],
        'crons': [],
    },
}

def check_team_health(team, info):
    """檢查團隊健康狀態"""
    print(f'\n  [{team}]')
    results = {'skills': [], 'reports': [], 'crons': [], 'score': 0, 'issues': []}
    
    # 檢查腳本
    team_dir = os.path.join(TEAMS_DIR, team.lower())
    scripts_dir = os.path.join(team_dir, 'scripts') if os.path.exists(os.path.join(team_dir, 'scripts')) else team_dir
    for skill in info['skills']:
        path = os.path.join(scripts_dir, skill)
        if os.path.exists(path):
            size = os.path.getsize(path)
            results['skills'].append({'name': skill, 'status': 'OK', 'size': size})
        else:
            results['skills'].append({'name': skill, 'status': 'MISSING', 'size': 0})
            results['issues'].append(f'{skill} 缺失')
    
    # 檢查報告
    reports_dir = os.path.join(team_dir, 'reports')
    for rep in info['reports']:
        path = os.path.join(reports_dir, rep) if os.path.exists(reports_dir) else os.path.join(team_dir, rep)
        if os.path.exists(path):
            size = os.path.getsize(path)
            mtime = datetime.fromtimestamp(os.path.getmtime(path)).strftime('%m/%d %H:%M')
            results['reports'].append({'name': rep, 'status': 'OK', 'size': size, 'mtime': mtime})
        else:
            results['reports'].append({'name': rep, 'status': 'MISSING', 'size': 0, 'mtime': None})
            results['issues'].append(f'{rep} 缺失')
    
    # 健康分數
    total = len(info['skills']) + len(info['reports'])
    ok = sum(1 for s in results['skills'] if s['status'] == 'OK') + sum(1 for r in results['reports'] if r['status'] == 'OK')
    results['score'] = int(ok / total * 100) if total > 0 else 0
    
    return results

def check_cron_health():
    """檢查Cron健康狀態"""
    print('\n  [Cron]')
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
                jobs.append({'id': job_id, 'name': name, 'schedule': schedule, 'status': status})
    
    # 統計
    error_count = sum(1 for j in jobs if j['status'] == 'error')
    ok_count = sum(1 for j in jobs if j['status'] == 'ok')
    idle_count = sum(1 for j in jobs if j['status'] == 'idle')
    running_count = sum(1 for j in jobs if j['status'] == 'running')
    
    print(f'    總 Jobs: {len(jobs)}')
    print(f'    OK: {ok_count} | Idle: {idle_count} | Running: {running_count} | Error: {error_count}')
    
    issues = []
    if error_count > 0:
        issues.append(f'{error_count}個Error Jobs需要修復')
    
    # 高頻檢查
    high_freq = [j for j in jobs if '*/15' in j['schedule'] or '*/10' in j['schedule']]
    if high_freq:
        issues.append(f'{len(high_freq)}個高頻Jobs（*/15或*/10）')
    
    return {
        'jobs': jobs,
        'total': len(jobs),
        'error': error_count,
        'ok': ok_count,
        'idle': idle_count,
        'running': running_count,
        'issues': issues,
        'score': int((len(jobs) - error_count) / len(jobs) * 100) if len(jobs) > 0 else 0,
    }

def analyze_market_and_suggest():
    """分析市場狀態並給出建議"""
    print('\n  [市場分析]')
    twii = yf.Ticker('^TWII').history(period='1mo')
    if len(twii) < 20:
        print('    市場數據不足')
        return None
    
    closes = twii['Close'].dropna()
    delta = closes.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rsi = (100 - (100 / (1 + gain / loss))).iloc[-1]
    ma20 = closes.rolling(20).mean().iloc[-1]
    ma60 = closes.rolling(60).mean().iloc[-1] if len(closes) >= 60 else ma20
    
    cur = closes.iloc[-1]
    regime = 'BULL' if ma20 > ma60 and rsi > 50 else 'BEAR' if ma20 < ma60 and rsi < 50 else 'NEUTRAL'
    if rsi > 80: regime = 'OVERBOUGHT'
    elif rsi < 40: regime = 'OVERSOLD'
    
    # 位置
    yr = closes.max() - closes.min()
    pos = (cur - closes.min()) / yr * 100 if yr > 0 else 50
    
    print(f'    TWII: {cur:.2f} | RSI: {rsi:.1f} | Regime: {regime}')
    print(f'    1年位置: {pos:.1f}%')
    
    suggestions = []
    if regime == 'OVERBOUGHT' or pos > 85:
        suggestions.append({
            'type': 'MARKET_WARNING',
            'desc': '市場過熱，全面觀望',
            'action': 'Nana禁止進場，Leo等待回調，Ray DCA暫停'
        })
    elif regime == 'BULL':
        suggestions.append({
            'type': 'BULL_MARKET',
            'desc': '多頭市場，順勢而為',
            'action': 'Leo可積極操作，Nana正常進場，Ray DCA 1x'
        })
    elif regime == 'BEAR':
        suggestions.append({
            'type': 'BEAR_MARKET',
            'desc': '空頭市場，提高防禦',
            'action': 'Leo觀望，Ray DCA 2x加碼，等待觸底'
        })
    
    return {
        'twii': cur,
        'rsi': rsi,
        'regime': regime,
        'position': pos,
        'suggestions': suggestions,
    }

def auto_fix_and_integrate(cron_health, market_data):
    """自動修復並整合"""
    print('\n  [自動修復與整合]')
    fixes = []
    jobs = cron_health['jobs']
    
    # Fix 1: Error jobs
    error_jobs = [j for j in jobs if j['status'] == 'error']
    if error_jobs:
        for j in error_jobs:
            print(f'    修復Error: {j["name"]}')
            r = subprocess.run(['openclaw', 'cron', 'remove', j['id']],
                             capture_output=True, text=True, encoding='utf-8', errors='replace')
            fixes.append({'action': 'DELETE_ERROR', 'name': j['name'], 'id': j['id']})
    
    # Fix 2: Market-based adjustment
    if market_data:
        regime = market_data['regime']
        pos = market_data['position']
        
        if regime == 'OVERBOUGHT' or pos > 85:
            # Add market warning cron
            fixes.append({
                'action': 'MARKET_WARNING',
                'desc': f'市場過熱({regime}, {pos:.0f}%位置)，建議全部觀望'
            })
    
    return fixes

def main():
    print('=' * 65)
    print('  全系統健檢優化分析系統 v1.0')
    print(f'  時間: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('=' * 65)
    
    all_healthy = True
    team_scores = {}
    
    # 1. 團隊健檢
    print('\n[Step 1] 團隊健康檢查')
    for team, info in CHECK_ITEMS.items():
        results = check_team_health(team, info)
        score = results['score']
        team_scores[team] = score
        status = '✅ 健康' if score >= 80 else '⚠️ 注意' if score >= 50 else '❌ 異常'
        print(f'  [{team}] {status} ({score}%)')
        if score < 80:
            all_healthy = False
        for issue in results['issues']:
            print(f'    ⚠️ {issue}')
    
    # 2. Cron健檢
    print('\n[Step 2] Cron健康檢查')
    cron_health = check_cron_health()
    for issue in cron_health['issues']:
        print(f'  ⚠️ {issue}')
    
    # 3. 市場分析
    print('\n[Step 3] 市場分析與建議')
    market_data = analyze_market_and_suggest()
    if market_data:
        for s in market_data['suggestions']:
            print(f'  💡 {s["type"]}: {s["desc"]}')
            print(f'     → {s["action"]}')
    
    # 4. 自動修復
    print('\n[Step 4] 自動修復與整合')
    fixes = auto_fix_and_integrate(cron_health, market_data)
    print(f'  已執行 {len(fixes)} 項修復')
    
    # 5. 整體評分
    print('\n[Step 5] 整體評分')
    cron_score = cron_score = cron_health['score']
    avg_team_score = sum(team_scores.values()) / len(team_scores) if team_scores else 0
    overall = int((avg_team_score * 0.4 + cron_score * 0.6))
    
    print(f'  團隊健康度: {avg_team_score:.0f}%')
    print(f'  Cron健康度: {cron_score}%')
    print(f'  整體評分: {overall}%')
    
    if overall >= 80:
        print('  等級: 🟢 優秀')
    elif overall >= 60:
        print('  等級: 🟡 良好')
    else:
        print('  等級: 🔴 需要優化')
    
    print('\n' + '=' * 65)
    print('  健檢完成')
    print('=' * 65)
    
    return {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'team_scores': team_scores,
        'cron_health': cron_health,
        'market_data': market_data,
        'fixes': fixes,
        'overall': overall,
    }

if __name__ == '__main__':
    main()