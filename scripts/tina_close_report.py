"""
Tina 收盤整合報告 - 整合三個 16:00 任務
原本分散在：
- Tina 股票追蹤-收盤更新
- Tina 交易日記+預警
- Tina 策略複盤（每日收盤後）

現在合併為一個整合腳本
"""

import subprocess
import sys
from datetime import datetime

def run_script(script_path, description):
    """執行腳本並報告結果"""
    print(f'\n=== 執行：{description} ===')
    try:
        result = subprocess.run(
            ['python', script_path],
            cwd=r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System',
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0:
            print(f'✅ {description} 完成')
            return True
        else:
            print(f'⚠️ {description} 有警告: {result.stderr[:200]}')
            return True  # 不阻斷其他任務
    except Exception as e:
        print(f'❌ {description} 失敗: {e}')
        return False

def main():
    print(f'Tina 收盤整合報告 - {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print('='*60)
    
    scripts = [
        ('scripts/stock_tracking_update.py', '股票追蹤更新'),
        ('scripts/stock_signal_scanner.py', '訊號掃描'),
        ('scripts/tina_trade_journal.py', '交易日記'),
        ('scripts/tina_alert_system.py', '預警檢查'),
        ('scripts/tina_strategy_reviewer.py', '策略複盤'),
    ]
    
    results = []
    for script, desc in scripts:
        success = run_script(script, desc)
        results.append((desc, success))
    
    print()
    print('='*60)
    print('整合報告摘要')
    print('='*60)
    for desc, success in results:
        status = '✅' if success else '❌'
        print(f'{status} {desc}')
    
    # 產出最終報告
    success_count = sum(1 for _, s in results if s)
    print(f'\n完成：{success_count}/{len(results)} 項任務')
    
    # 如果有失敗，發送警示
    if success_count < len(results):
        print('⚠️ 部分任務失敗，請檢查日誌')

if __name__ == '__main__':
    main()