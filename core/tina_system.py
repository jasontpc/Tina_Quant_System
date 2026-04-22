# -*- coding: utf-8 -*-
"""
Tina 量化交易系統 - 統一入口
整合所有分析、回測、監控功能

自動日誌功能:
- trade.log: 交易紀錄 (進場/出場/盈虧)
- system.log: 系統錯誤
- api.log: API 呼叫狀態
"""

import sys
import os
import logging
from datetime import datetime

# 確保目錄存在
os.makedirs(os.path.dirname(__file__) + '/../logs', exist_ok=True)

# === 日誌設定 ===
LOG_DIR = os.path.dirname(__file__) + '/../logs'

def get_logger(name, filename):
    """取得日誌器"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        handler = logging.FileHandler(
            os.path.join(LOG_DIR, filename), 
            encoding='utf-8'
        )
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger

# 日誌器實例
trade_logger = get_logger('trade', 'trade.log')
system_logger = get_logger('system', 'system.log')
api_logger = get_logger('api', 'api.log')

# === 交易紀錄裝飾器 ===
def log_trade(func):
    """自動紀錄交易進出场"""
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        
        # 自動寫入 trade.log
        if isinstance(result, dict):
            action = result.get('action', 'UNKNOWN')
            code = result.get('code', '')
            price = result.get('price', 0)
            reason = result.get('reason', '')
            
            if action == 'BUY':
                trade_logger.info(f'買入 {code} @ {price} | {reason}')
            elif action == 'SELL':
                pnl = result.get('pnl', 0)
                pnl_pct = result.get('pnl_pct', 0)
                trade_logger.info(f'賣出 {code} @ {price} | 盈虧: {pnl:+.2f} ({pnl_pct:+.2f}%) | {reason}')
            elif action == 'SIGNAL':
                score = result.get('score', 0)
                trade_logger.info(f'進場信號 {code} @ {price} | Score: {score} | {reason}')
        
        return result
    return wrapper

# === API 呼叫裝飾器 ===
def log_api(func):
    """自動紀錄 API 呼叫"""
    def wrapper(*args, **kwargs):
        start = datetime.now()
        api_logger.info(f'API 呼叫: {func.__name__}')
        
        try:
            result = func(*args, **kwargs)
            duration = (datetime.now() - start).total_seconds()
            api_logger.info(f'API 成功: {func.__name__} ({duration:.2f}s)')
            return result
        except Exception as e:
            duration = (datetime.now() - start).total_seconds()
            api_logger.error(f'API 錯誤: {func.__name__} ({duration:.2f}s) - {str(e)}')
            raise
    
    return wrapper

# === 系統日誌 ===
def log_system(action, details=''):
    """寫入系統日誌"""
    system_logger.info(f'{action} | {details}')

# === 版本資訊 ===
VERSION = 'v3.12'
BUILD = '2026-04-22'
SYSTEM_STATUS = 'STABLE'

# === 主選單 ===
MENU = f"""
============================================================
Tina 量化交易系統 - 統一入口
版本: {VERSION} | Build: {BUILD} | 狀態: {SYSTEM_STATUS}
============================================================

【分析模組】
1. 每日波段報告
2. 美股技術面
3. 觀察名單技術面

【回測模組】
4. 全市場回測優化
5. 觀察名單回測

【系統工具】
6. 風險計算機
7. 查看 trade.log
8. 查看 system.log
9. 查看 api.log

【市場概況】
10. 上週績優股
11. 法人資金流向

============================================================
"""

def main():
    print(MENU)
    log_system('SYSTEM', 'Tina 系統啟動')
    
    choice = input('選擇功能 (1-11, Q離開): ').strip()
    
    if choice == 'Q' or choice == 'q':
        log_system('SYSTEM', 'Tina 系統關閉')
        return
    
    scripts = {
        '1': 'skills/stock-analyzer/bandwave_system/core/daily_report.py',
        '2': 'skills/stock-analyzer/scripts/us_now.py',
        '3': 'skills/stock-analyzer/scripts/marcus_watchlist_fugle.py',
        '4': 'skills/stock-analyzer/scripts/backtest_optimize.py',
        '5': 'skills/stock-analyzer/scripts/watchlist_report.py',
        '6': 'skills/stock-analyzer/bandwave_system/core/risk_calc.py',
        '10': 'skills/stock-analyzer/scripts/week_top.py',
        '11': 'skills/stock-analyzer/scripts/get_institutional_trades.py',
    }
    
    log_viewers = {
        '7': ('trade.log', trade_logger),
        '8': ('system.log', system_logger),
        '9': ('api.log', api_logger),
    }
    
    if choice in scripts:
        import subprocess
        log_system('RUN_SCRIPT', scripts[choice])
        result = subprocess.run(
            ['python', scripts[choice]],
            capture_output=False
        )
    
    elif choice in log_viewers:
        filename, logger = log_viewers[choice]
        print(f'\n=== {filename} (最近20筆) ===\n')
        log_file = os.path.join(LOG_DIR, filename)
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines[-20:]:
                    print(line.strip())
        else:
            print('(空)')
    
    else:
        print('無效選擇')
    
    input('\n按 Enter 繼續...')
    main()

if __name__ == '__main__':
    log_system('SYSTEM', '=== Tina 系統初始化完成 ===')
    main()
