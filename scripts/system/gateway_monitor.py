# -*- coding: utf-8 -*-
"""
Gateway 崩潰監控腳本（極簡版）
頻率：每 15 分鐘執行
"""

import subprocess
import json
from datetime import datetime
from pathlib import Path

WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace")
LOG_FILE = WORKSPACE / "logs" / "gateway_monitor.log"

def run_cmd(cmd, timeout=8):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout, encoding='utf-8', errors='replace')
        return r.stdout.strip() + r.stderr.strip()
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    except Exception as e:
        return str(e)

def main():
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 快速檢查 gateway version
    result = run_cmd('openclaw --version', 5)
    
    if '2026' in result:
        status = "OK"
        msg = f"[{ts}] Gateway OK: {result[:50]}"
    else:
        status = "DOWN"
        msg = f"[{ts}] ALERT Gateway DOWN: {result[:100]}"
        
        # 嘗試重啟
        restart = run_cmd('openclaw gateway start 2>&1', 30)
        msg += f" | Restart: {restart[:80]}"
    
    # 寫入日誌
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')
    
    print(status)

if __name__ == '__main__':
    main()