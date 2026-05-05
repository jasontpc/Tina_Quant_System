# -*- coding: utf-8 -*-
"""Sherry Cron Scheduler - Add Cron Jobs for Sherry ETF System"""
import sys
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

SCRIPTS_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\sherry\scripts'

CRON_JOBS = [
    {
        'name': 'Sherry ETF DCA 每日檢查',
        'schedule': '0 8 * * 1-5',
        'timeout': 60,
        'script': 'sherry_daily_check.py',
        'description': '每日DCA機會檢查，篩選最佳進場ETF'
    },
    {
        'name': 'Sherry ETF 每週DCA報告',
        'schedule': '0 9 * * 1',
        'timeout': 120,
        'script': 'sherry_dca_backtest.py',
        'description': '每週DCA回測報告，分析策略表現'
    },
    {
        'name': 'Sherry ETF 資料庫更新',
        'schedule': '0 7 * * 1-5',
        'timeout': 180,
        'script': 'build_sherry_db.py',
        'description': '每日更新ETF資料庫（覆寫模式）'
    },
]

def print_cron_commands():
    print('╔════════════════════════════════════════════════════════════════╗')
    print('║           Sherry ETF Cron Jobs 安裝命令                   ║')
    print('╚════════════════════════════════════════════════════════════════╝')
    print()
    
    for i, job in enumerate(CRON_JOBS, 1):
        print(f'=== Job {i}: {job["name"]} ===')
        print(f'Schedule: {job["schedule"]} (週一~五 {job["schedule"].split()[1]}:00)')
        print(f'Timeout: {job["timeout"]}s')
        print(f'Description: {job["description"]}')
        print()
        cmd = f'''openclaw cron add \
  --name "{job["name"]}" \
  --cron "{job["schedule"]}" \
  --timeout {job["timeout"]} \
  --announce \
  --message "python teams/sherry/scripts/{job["script"]}" \
  --session isolated'''
        print(cmd)
        print()
    
    print('=' * 70)
    print()
    print('手動安裝方式：')
    print('1. 複製上述命令')
    print('2. 在終端機執行')
    print('3. 確認 cron job 已添加')
    print()

def main():
    print_cron_commands()
    
    print()
    print('=== 當前排程狀態 ===')
    print()
    print('建議排程：')
    print('  07:00  Sherry ETF 資料庫更新')
    print('  08:00  Sherry ETF DCA 每日檢查')
    print('  09:00  現有其他系統（Ray/Maggy等）')
    print('  09:00  (週一) Sherry ETF 每週DCA報告')
    print()

if __name__ == '__main__':
    main()