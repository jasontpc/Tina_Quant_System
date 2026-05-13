# -*- coding: utf-8 -*-
"""Tina System Cron Scheduler - Auto-Optimization"""
import sys
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

def print_cron_schedule():
    print('╔════════════════════════════════════════════════════════════════════════╗')
    print('║           Tina 全系統 Cron 排程設定（建議）                     ║')
    print('╚════════════════════════════════════════════════════════════════════════╝')
    print()
    
    schedules = [
        # Time, Name, Script, Description
        ('07:00', 'Tina 全系統資料庫更新', 'python tina_full_optimizer.py',
         '更新所有系統資料庫（TW/US/Vogel）'),
        ('08:00', 'Maggy AI/科技股每日檢查', 'python teams/maggy/scripts/maggy_ai_strategy.py',
         'Maggy AI股票篩選與進場信號'),
        ('08:30', 'Sherry ETF DCA 每日檢查', 'python teams/sherry/scripts/sherry_daily_check.py',
         'Sherry ETF DCA機會檢查'),
        ('09:00', 'Vogel 台指期分析', 'python teams/vogel/vogel_signals.py',
         '台指期BB信號追蹤'),
        ('09:30', 'Nana 波段候選掃描', 'python teams/nana/autonomous_trader.py',
         '台股波段候選'),
        ('10:00', 'Ray DCA 市場分析', 'python teams/ray/scripts/ray_etf_dca.py',
         '台股ETF DCA分析'),
        ('15:00', '美股收盤分析', 'python teams/maggy/scripts/maggy_daily_check.py',
         '美股收盤RSI更新'),
        ('16:00', '台股收盤觀察', 'python teams/nana/nana_today.py',
         '台股收盤分析'),
        ('20:00', 'Maggy 深度學習優化', 'python teams/maggy/scripts/maggy_enhanced_learning.py',
         'Maggy策略深度優化'),
        ('22:00', 'Tina 系統夜間健檢', 'python tina_full_optimizer.py',
         '全系統狀態確認'),
    ]
    
    weekly = [
        ('週一 09:00', '全系統每週回顧', 'all systems',
         '每週策略回顧與調整'),
        ('週日 10:00', 'Maggy 每週波段報告', 'python teams/maggy/scripts/maggy_backtest.py',
         'Maggy一週回測分析'),
    ]
    
    print('=== 每日排程 ===\n')
    print('時間      名稱                                      間隔')
    print('-' * 80)
    for time, name, script, desc in schedules:
        print(f'{time:<10} {name:<45} {desc}')
    
    print('\n\n=== 每週排程 ===\n')
    for time, name, script, desc in weekly:
        print(f'{time:<12} {name:<40} {desc}')
    
    print('\n\n=== Cron 安裝命令 ===\n')
    
    for time, name, script, desc in schedules:
        print(f'# {name}')
        print(f'# {desc}')
        hour, minute = time.split(':')
        cron_expr = f'0 {hour} * * 1-5'
        print(f'openclaw cron add --name "{name}" --cron "{cron_expr}" --timeout 120 --announce --message "cd Tina_Quant_System && {script}" --session isolated')
        print()

def main():
    print_cron_schedule()
    
    print('=' * 80)
    print()
    print('📝 建議：直接複製上述命令到終端機執行')
    print('⏰ 間隔：建議每系統最少間隔30分鐘')
    print('🔄 自動化：系統將自動學習、優化、迭代')

if __name__ == '__main__':
    main()