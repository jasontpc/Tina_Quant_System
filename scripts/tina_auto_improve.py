# -*- coding: utf-8 -*-
"""
Tina 系統自動化改善腳本
=====================
每日自動執行，持續改善系統

功能：
1. Cron Job 健康檢查
2. 空檔案/零位元檔案清理
3. DB 健康檢查
4. 記憶系統檢查
"""

import sys, os, json
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
MEMORY_FILE = Path(r'C:\Users\USER\.openclaw\workspace\MEMORY.md')
LEDGER_FILE = WORKSPACE / 'data' / 'experience_ledger.json'
LOG_FILE = WORKSPACE / 'data' / 'system_auto_improve.json'

print('='*70)
print('Tina 系統自動化改善')
print('='*70)
print(f'時間：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print()

# ========== 1. Cron Job 健康檢查 ==========
print('[1/5] Cron Job 健康檢查')
print('-'*50)

# 預設值
error_count = 0
ok_count = 0
idle_count = 0

try:
    import subprocess
    result = subprocess.run(
        ['powershell', '-Command', 'openclaw cron list'],
        capture_output=True, timeout=15
    )
    if result.returncode == 0:
        try:
            output = result.stdout.decode('utf-8', errors='ignore')
            lines = output.split('\n')
            error_count = sum(1 for l in lines if 'error' in l.lower())
            ok_count = sum(1 for l in lines if 'ok' in l.lower())
            idle_count = sum(1 for l in lines if 'idle' in l.lower())
        except:
            pass
except Exception as e:
    print(f'  [WARN] Cron 檢查失敗：{e}')

print(f'  OK: {ok_count}')
print(f'  Error: {error_count}')
print(f'  Idle: {idle_count}')

# ========== 2. 空檔案清理 ==========
print()
print('[2/5] 空檔案清理')
print('-'*50)

data_dir = WORKSPACE / 'data'
zero_files = []

for f in data_dir.glob('*.db'):
    if f.stat().st_size == 0:
        zero_files.append(f)
        print(f'  發現空檔案：{f.name}')

if not zero_files:
    print('  沒有空檔案 ✅')

# ========== 3. DB 健康檢查 ==========
print()
print('[3/5] DB 健康檢查')
print('-'*50)

dbs = {
    'yfinance.db': 100 * 1024 * 1024,
    'tw_history.db': 5 * 1024 * 1024,
    'us_history.db': 15 * 1024 * 1024,
}

for db_name, max_size in dbs.items():
    db_path = data_dir / db_name
    if db_path.exists():
        size = db_path.stat().st_size
        size_mb = size / 1024 / 1024
        max_mb = max_size / 1024 / 1024
        status = '⚠️' if size > max_size else '✅'
        print(f'  {status} {db_name}: {size_mb:.1f}MB / {max_mb:.0f}MB')

# ========== 4. 記憶系統檢查 ==========
print()
print('[4/5] 記憶系統檢查')
print('-'*50)

if MEMORY_FILE.exists():
    size = MEMORY_FILE.stat().st_size
    print(f'  MEMORY.md: {size:,} bytes ✅')
else:
    print('  MEMORY.md: ⚠️ 不存在')

if LEDGER_FILE.exists():
    size = LEDGER_FILE.stat().st_size
    print(f'  experience_ledger.json: {size:,} bytes ✅')
else:
    print('  experience_ledger.json: ⚠️ 不存在')

lessons_dir = Path.home() / '.openclaw' / 'workspace' / 'memory' / 'lessons'
if lessons_dir.exists():
    wins = len(list((lessons_dir / 'wins').glob('*.md'))) if (lessons_dir / 'wins').exists() else 0
    losses = len(list((lessons_dir / 'losses').glob('*.md'))) if (lessons_dir / 'losses').exists() else 0
    print(f'  lessons: wins={wins}, losses={losses}')
else:
    print('  lessons: ⚠️ 不存在')

# ========== 5. 寫入改善日誌 ==========
print()
print('[5/5] 寫入改善日誌')
print('-'*50)

log = {
    'timestamp': datetime.now().isoformat(),
    'cron': {
        'ok': ok_count,
        'error': error_count,
        'idle': idle_count
    },
    'zero_files': [f.name for f in zero_files],
    'dbs': {
        db: (data_dir / db).stat().st_size for db in dbs if (data_dir / db).exists()
    },
    'memory': {
        'memory_md': MEMORY_FILE.stat().st_size if MEMORY_FILE.exists() else 0,
        'ledger': LEDGER_FILE.stat().st_size if LEDGER_FILE.exists() else 0
    }
}

with open(LOG_FILE, 'w', encoding='utf-8') as f:
    json.dump(log, f, ensure_ascii=False, indent=2)

print(f'  已寫入：{LOG_FILE.name}')

# ========== 總結 ==========
print()
print('='*70)
print('自動化改善完成')
print('='*70)

if error_count > 0:
    print(f'⚠️ 警告：{error_count} 個 Cron Job 錯誤')
else:
    print('✅ Cron Job 全部正常')

if zero_files:
    print(f'⚠️ 發現 {len(zero_files)} 個空檔案')
else:
    print('✅ 沒有空檔案')
