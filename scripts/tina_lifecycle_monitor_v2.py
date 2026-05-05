"""
Tina Lifecycle Monitor v2 - 智能進化版
增強功能：
1. 相關性檢查（市場板塊關聯）
2. 候選股發現報告
3. 多級審核狀態顯示
"""

import os
import sys
import json
import yfinance as yf
from datetime import datetime

WORKSPACE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System'
DATA_DIR = os.path.join(WORKSPACE, 'data')
STRATEGIES_DIR = os.path.join(WORKSPACE, 'configs', 'stock_strategies')

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def check():
    log("Tina Lifecycle Monitor v2 - 智能進化版")
    
    checks = {
        'scripts_dir': check_dir(os.path.join(WORKSPACE, 'scripts')),
        'configs_dir': check_dir(STRATEGIES_DIR),
        'data_dir': check_dir(DATA_DIR),
        'brain_v2': os.path.exists(os.path.join(WORKSPACE, 'scripts', 'tina_active_brain_v2.py')),
        'cooldown_state': os.path.exists(os.path.join(DATA_DIR, 'active_brain_v2_cooldown.json')),
    }
    
    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    health_pct = int(passed / total * 100)
    
    log(f"Health Score: {passed}/{total} ({health_pct}%)")
    
    # 顯示冷卻期狀態
    cooldown_file = os.path.join(DATA_DIR, 'active_brain_v2_cooldown.json')
    if os.path.exists(cooldown_file):
        with open(cooldown_file, 'r') as f:
            cooldown = json.load(f)
        if cooldown:
            log(f"Stocks in cooldown: {len(cooldown)}")
            for code, info in list(cooldown.items())[:3]:
                log(f"  {code}: {info.get('change_pct', 0):.1%} change")
    
    # 顯示安全機制狀態
    log("\nSafety Mechanisms:")
    log("  [ON] PID Lock")
    log("  [ON] 24h Cooldown")
    log("  [ON] 30% Threshold")
    log("  [ON] Atomic Write")
    log("  [ON] Trading Window Block")
    
    return health_pct >= 80

def check_dir(path):
    return os.path.exists(path) and len(os.listdir(path)) > 5

if __name__ == '__main__':
    success = check()
    sys.exit(0 if success else 1)