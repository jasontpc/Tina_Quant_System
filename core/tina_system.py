# -*- coding: utf-8 -*-
"""
Tina 系統 - 統一入口
整合所有分析、回測、監控功能
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

MENU = """
============================================================
Tina 量化交易系統 - 統一入口
============================================================

【分析模組】
1. 每日波段報告
2. 美股技術面
3. 觀察名單技術面 (富果API)

【回測模組】
4. 全市場回測優化
5. 美股回測優化
6. 觀察名單回測修正

【個股分析】
7. 3034 聯詠 分析
8. 2382 廣達 分析
9. 0056 高股息 分析

【系統工具】
10. 風險計算機
11. 明日建議

【市場概況】
12. 上週績優股
13. 法人資金流向

============================================================
"""

def main():
    print(MENU)
    choice = input('選擇功能 (1-13, Q離開): ').strip()
    
    import subprocess
    
    scripts = {
        '1': 'skills/stock-analyzer/bandwave_system/core/daily_report.py',
        '2': 'skills/stock-analyzer/scripts/us_now.py',
        '3': 'skills/stock-analyzer/scripts/marcus_watchlist_fugle.py',
        '4': 'skills/stock-analyzer/scripts/backtest_optimize.py',
        '5': 'skills/stock-analyzer/scripts/us_backtest_optimize.py',
        '6': 'skills/stock-analyzer/scripts/optimize_watchlist.py',
        '7': 'skills/stock-analyzer/scripts/3034_tech.py',
        '8': 'skills/stock-analyzer/scripts/2382_full.py',
        '9': 'skills/stock-analyzer/scripts/0056_tech.py',
        '10': 'skills/stock-analyzer/bandwave_system/core/risk_calc.py',
        '11': 'skills/stock-analyzer/bandwave_system/core/daily_report.py',
        '12': 'skills/stock-analyzer/scripts/week_top.py',
        '13': 'skills/stock-analyzer/scripts/get_institutional.py',
    }
    
    if choice.upper() == 'Q':
        print('再見！')
        return
    
    if choice in scripts:
        print('\n執行中...\n')
        result = subprocess.run(
            ['.\\venv\\Scripts\\python.exe', scripts[choice]],
            capture_output=True, text=True, encoding='utf-8', errors='replace'
        )
        print(result.stdout)
        if result.stderr:
            print('錯誤:', result.stderr)
    else:
        print('無效選擇')

if __name__ == '__main__':
    main()
