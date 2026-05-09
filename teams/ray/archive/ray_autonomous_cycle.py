# -*- coding: utf-8 -*-
"""
Ray Autonomous Cycle — 自主循環整合
功能：整合所有 Ray 自主模組，每 5 分鐘執行一次自主學習循環
"""
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\ray')
RAY_STATUS_FILE = BASE_DIR / 'ray_status.md'


def log_step(step_num, step_name, status, message=''):
    """格式化輸出步驟狀態"""
    status_icon = '✓' if status == 'OK' else ('⚠️' if status == 'WARN' else '✗')
    print(f'[{step_num}] {status_icon} {step_name}: {message}')


def update_ray_status(detail_text):
    """更新 ray_status.md"""
    now = datetime.now()
    timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
    
    if RAY_STATUS_FILE.exists():
        with open(RAY_STATUS_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
    else:
        content = '# Ray Status\n\n'
    
    # 找到或創建 autonomous_cycle 小節
    marker = '## Ray 自主循環'
    if marker in content:
        # 更新現有章節
        start = content.find(marker)
        end = content.find('\n##', start + 1)
        if end == -1:
            end = len(content)
        header = content[start:end]
        
        # 更新 last_run
        if 'Last Run:' in header:
            import re
            header = re.sub(r'Last Run:.*', f'Last Run: {timestamp}', header)
        else:
            header = header + f'\n- Last Run: {timestamp}'
        
        content = content[:start] + header + content[end:]
    else:
        content = content + f'\n{marker}\n- Last Run: {timestamp}\n'

    with open(RAY_STATUS_FILE, 'w', encoding='utf-8') as f:
        f.write(content)


def run_python_script(script_path):
    """執行 Python 腳本並返回結果"""
    try:
        result = subprocess.run(
            ['python', str(script_path)],
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=120
        )
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {'success': False, 'stdout': '', 'stderr': 'Timeout', 'returncode': -1}
    except Exception as e:
        return {'success': False, 'stdout': '', 'stderr': str(e), 'returncode': -1}


def run_autonomous_cycle():
    """Ray 自主循環主流程"""
    print('=' * 60)
    print('Ray 自主循環 — 每5分鐘執行')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('=' * 60)
    print()
    
    now = datetime.now()
    step = 1
    
    # Step 1: 系統狀態檢查
    print(f'[{step}] 系統狀態檢查...')
    step += 1
    result = run_python_script(BASE_DIR / 'ray_system_review.py')
    if result['success']:
        log_step(1, '系統狀態', 'OK', '所有腳本正常')
    else:
        log_step(1, '系統狀態', 'WARN', f'檢查完成（見上方）')
    print()
    
    # Step 2: 更新 ETF 市場數據 (在 autonomous_trader 內一並執行)
    print(f'[{step}] 更新 ETF 市場數據...')
    step += 1
    print('  → 併入交易模擬 Step 3 中執行')
    print()
    
    # Step 3: 執行交易模擬
    print(f'[{step}] 執行交易模擬...')
    step += 1
    result = run_python_script(BASE_DIR / 'ray_autonomous_trader.py')
    if result['success']:
        log_step(3, '交易模擬', 'OK', '模擬完成')
    else:
        log_step(3, '交易模擬', 'WARN', '見上方輸出')
    print()
    
    # Step 4: DCA vs Buy&Hold 分析（每6小時執行一次，此處只做標記）
    print(f'[{step}] DCA vs Buy&Hold 分析...')
    step += 1
    # 每6小時 = 720 分鐘。設定計數，在倍數執行時觸發
    # 這裡用簡單計數：假設每5分鐘執行一次，720/5=144次觸發一次
    # 為簡化，每次只檢查日期是否變化來決定是否執行
    should_run = (now.hour % 6 == 0 and now.minute < 10)  # 每6小時的前10分鐘內執行
    
    if should_run:
        result = run_python_script(BASE_DIR / 'ray_bh_vs_dca.py')
        if result['success']:
            log_step(4, 'DCA vs B&H', 'OK', '分析完成')
        else:
            log_step(4, 'DCA vs B&H', 'WARN', '見上方')
    else:
        log_step(4, 'DCA vs B&H', 'SKIP', f'每6小時執行一次（下次: {((6 - now.hour % 6) % 6)}h後）')
    print()
    
    # Step 5: 自主學習
    print(f'[{step}] 執行自主學習...')
    step += 1
    result = run_python_script(BASE_DIR / 'ray_learner.py')
    if result['success']:
        log_step(5, '自主學習', 'OK', '學習完成')
    else:
        log_step(5, '自主學習', 'WARN', '見上方')
    print()
    
    # Step 6: 更新 ray_status.md
    print(f'[{step}] 更新系統狀態文件...')
    step += 1
    status_detail = f'自主循環完成 | {now.strftime("%Y-%m-%d %H:%M:%S")}'
    update_ray_status(status_detail)
    log_step(6, '狀態更新', 'OK', 'ray_status.md 已更新')
    print()
    
    # Step 7: 是否需要立即優化
    print(f'[{step}] 檢查是否需要立即優化...')
    step += 1
    recommendations_file = BASE_DIR / 'ray_recommendations.json'
    if recommendations_file.exists():
        try:
            with open(recommendations_file, 'r', encoding='utf-8') as f:
                rec_data = json.load(f)
            recent_recs = rec_data.get('recommendations', [])
            if recent_recs:
                log_step(7, '優化檢查', 'WARN', f'發現 {len(recent_recs)} 項建議待套用')
                print('  最近建議:')
                for rec in recent_recs[:3]:
                    print(f'    • {rec.get("type", "unknown")}: {rec.get("reason", "")[:60]}')
            else:
                log_step(7, '優化檢查', 'OK', '無待套用建議')
        except:
            log_step(7, '優化檢查', 'WARN', '建議檔案讀取失敗')
    else:
        log_step(7, '優化檢查', 'OK', '尚無建議資料')
    print()
    
    # 完成
    print('=' * 60)
    print(f'Ray 自主循環完成 — {now.strftime("%Y-%m-%d %H:%M:%S")}')
    print('=' * 60)


if __name__ == '__main__':
    run_autonomous_cycle()
