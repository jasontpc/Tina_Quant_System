# -*- coding: utf-8 -*-
"""
Ray System Review — 每小時系統檢討模組
功能：檢查所有腳本是否正常運行、數據是否更新、檢查是否有錯誤
"""
import json
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\ray')


def check_file_exists(path, name):
    """檢查檔案是否存在"""
    if path.exists():
        return {'name': name, 'status': 'OK', 'message': f'存在 ({path.stat().st_size:,} bytes)'}
    else:
        return {'name': name, 'status': 'MISSING', 'message': '檔案不存在'}


def check_json_valid(path, name):
    """檢查 JSON 是否有效"""
    if not path.exists():
        return {'name': name, 'status': 'MISSING', 'message': '檔案不存在'}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return {'name': name, 'status': 'OK', 'message': f'有效 JSON ({len(str(data))} chars)'}
    except json.JSONDecodeError as e:
        return {'name': name, 'status': 'ERROR', 'message': f'JSON 解析錯誤: {e}'}
    except Exception as e:
        return {'name': name, 'status': 'ERROR', 'message': f'讀取錯誤: {e}'}


def check_data_freshness(path, max_age_hours=24):
    """檢查數據是否夠新"""
    if not path.exists():
        return {'name': path.name, 'status': 'MISSING', 'message': '檔案不存在'}
    
    try:
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        age = datetime.now() - mtime
        age_hours = age.total_seconds() / 3600
        
        if age_hours < 1:
            age_str = f'{age.total_seconds():.0f} 秒前'
            status = 'OK'
        elif age_hours < max_age_hours:
            age_str = f'{age_hours:.1f} 小時前'
            status = 'OK'
        else:
            age_str = f'{age_hours:.1f} 小時前 (過舊)'
            status = 'STALE'
        
        return {'name': path.name, 'status': status, 'message': f'更新時間: {age_str}'}
    except Exception as e:
        return {'name': path.name, 'status': 'ERROR', 'message': f'時間檢查錯誤: {e}'}


def check_script_syntax(script_path):
    """檢查 Python 腳本語法"""
    if not script_path.exists():
        return {'name': script_path.name, 'status': 'MISSING', 'message': '檔案不存在'}
    
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            code = f.read()
        compile(code, str(script_path), 'exec')
        return {'name': script_path.name, 'status': 'OK', 'message': '語法正確'}
    except SyntaxError as e:
        return {'name': script_path.name, 'status': 'SYNTAX_ERROR', 'message': f'語法錯誤: {e}'}
    except Exception as e:
        return {'name': script_path.name, 'status': 'ERROR', 'message': f'編譯錯誤: {e}'}


def run_system_review():
    """主執行流程"""
    print('=== Ray 每小時系統檢討 ===')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print()
    
    checks = []
    
    # 1. 檢查核心腳本
    print('[Step 1] 檢查核心腳本...')
    core_scripts = [
        'ray_alert_agent.py',
        'ray_etf_dca.py',
        'ray_autonomous_trader.py',
        'ray_backtester.py',
        'ray_bh_vs_dca.py',
        'ray_learner.py',
        'ray_system_review.py',
        'ray_autonomous_cycle.py'
    ]
    
    for script in core_scripts:
        path = BASE_DIR / script
        result = check_file_exists(path, script)
        checks.append(result)
        print(f'  {result["status"]:10s} {result["name"]:<30s} {result["message"]}')
    print()
    
    # 2. 檢查 JSON 檔案
    print('[Step 2] 檢查 JSON 檔案...')
    json_files = [
        ('autonomous_trades.json', '虛擬交易'),
        ('ray_recommendations.json', 'DCA 建議')
    ]
    
    for fname, desc in json_files:
        path = BASE_DIR / fname
        result = check_json_valid(path, f'{fname} ({desc})')
        checks.append(result)
        print(f'  {result["status"]:10s} {result["name"]:<40s} {result["message"]}')
    print()
    
    # 3. 檢查數據新鮮度
    print('[Step 3] 檢查數據新鮮度...')
    data_files = [
        BASE_DIR / 'autonomous_trades.json',
        BASE_DIR / 'reports' / 'backtest_report.json',
        BASE_DIR / 'reports' / 'bh_vs_dca_report.json'
    ]
    
    for path in data_files:
        if path.exists():
            result = check_data_freshness(path, max_age_hours=24)
            checks.append(result)
            print(f'  {result["status"]:10s} {result["name"]:<40s} {result["message"]}')
    print()
    
    # 4. 檢查目錄結構
    print('[Step 4] 檢查目錄結構...')
    directories = ['reports', 'scripts', 'tiers']
    for d in directories:
        path = BASE_DIR / d
        if path.exists():
            print(f'  OK       {d}/ (目錄存在)')
        else:
            print(f'  MISSING  {d}/ (目錄不存在)')
            checks.append({'name': f'{d}/', 'status': 'MISSING', 'message': '目錄不存在'})
    print()
    
    # 5. 總結
    print('=' * 60)
    print('[系統檢討總結]')
    print('=' * 60)
    
    ok_count = sum(1 for c in checks if c['status'] == 'OK')
    error_count = sum(1 for c in checks if c['status'] in ('ERROR', 'SYNTAX_ERROR'))
    missing_count = sum(1 for c in checks if c['status'] == 'MISSING')
    stale_count = sum(1 for c in checks if c['status'] == 'STALE')
    
    print(f'  正常: {ok_count}')
    print(f'  錯誤: {error_count}')
    print(f'  缺失: {missing_count}')
    print(f'  過舊: {stale_count}')
    print()
    
    if error_count > 0 or missing_count > 0:
        print('  ⚠️  系統需要介入')
        for c in checks:
            if c['status'] in ('ERROR', 'SYNTAX_ERROR', 'MISSING'):
                print(f'    • {c["name"]}: {c["message"]}')
    elif stale_count > 0:
        print('  ⚠️  部分數據過舊，建議更新')
    else:
        print('  ✓ 系統正常運行')
    
    print()
    return {
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'ok': ok_count,
            'errors': error_count,
            'missing': missing_count,
            'stale': stale_count
        },
        'checks': checks
    }


if __name__ == '__main__':
    result = run_system_review()
