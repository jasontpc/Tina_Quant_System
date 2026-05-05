# -*- coding: utf-8 -*-
"""
Gateway 狀態檢查
================
正常運作不回報，失敗才回報
"""
import socket
import sys
import json
from pathlib import Path

WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
DATA = WORKSPACE / "data"

def check_gateway():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('127.0.0.1', 18789))
        sock.close()
        return result == 0
    except:
        return False

if __name__ == '__main__':
    status = check_gateway()
    
    if status:
        # 正常 → 不回報
        sys.exit(0)
    else:
        # 失敗 → 回報
        print("🔴 Gateway 狀態: STOPPED")
        print("時間:", __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M'))
        
        # 記錄失敗
        log = DATA / "gateway_fail_log.json"
        try:
            if log.exists():
                with open(log, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            else:
                logs = []
            
            logs.append({
                'time': __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M'),
                'status': 'STOPPED'
            })
            
            # 只保留最近10筆記錄
            logs = logs[-10:]
            
            with open(log, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
        except:
            pass
        
        sys.exit(1)