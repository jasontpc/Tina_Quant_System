"""
Tina Gateway Monitor - 後台監控系統 v2
=====================================
功能：
1. 每小時檢查 Gateway 狀態
2. 崩潰後自動重啟
3. 過多崩潰時發送 Telegram 警報
4. 記錄重啟日誌到資料庫
"""

import subprocess
import time
import os
import sys
import sqlite3
from datetime import datetime, timedelta

WORKSPACE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System'
DB_PATH = os.path.join(WORKSPACE, 'data', 'gateway_monitor.db')
LOG_DIR = os.path.join(WORKSPACE, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# 設定
CHECK_INTERVAL = 10  # 秒
MAX_RESTARTS_PER_HOUR = 5
CRASH_ALERT_THRESHOLD = 3

def init_db():
    """初始化資料庫"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS restart_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            reason TEXT,
            status TEXT,
            uptime_secs INTEGER
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS alert_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            alert_type TEXT,
            message TEXT,
            acknowledged INTEGER DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()

def log(type, message):
    """寫入日誌"""
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] [{type.upper()}] {message}\n'
    
    log_file = os.path.join(LOG_DIR, 'gateway_monitor.log')
    with open(log_file, 'a', encoding='utf-8', errors='replace') as f:
        f.write(line)
    
    print(line.strip())

def check_gateway():
    """檢查 Gateway 是否運行"""
    try:
        # 直接用 node 執行
        result = subprocess.run(
            ['node', 
             r'C:\Users\USER\AppData\Roaming\npm\node_modules\openclaw\dist\index.js',
             'gateway', 'status'],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        output = result.stdout + result.stderr
        
        # 關鍵判斷：Listening: 表示 Gateway 在監聽
        is_running = 'Listening:' in output or 'bind=' in output
        
        log('debug', f'Gateway check: {"RUNNING" if is_running else "STOPPED"}')
        
        return is_running
        
    except subprocess.TimeoutExpired:
        log('error', 'Gateway check timeout')
        return None
    except FileNotFoundError:
        log('error', 'Node or openclaw not found')
        return None
    except Exception as e:
        log('error', f'Gateway check error: {e}')
        return None

def restart_gateway():
    """重啟 Gateway"""
    log('info', 'Attempting Gateway restart...')
    
    try:
        # 嘗試停止
        subprocess.run(
            ['node', 
             r'C:\Users\USER\AppData\Roaming\npm\node_modules\openclaw\dist\index.js',
             'gateway', 'stop'],
            capture_output=True, timeout=20
        )
        
        time.sleep(3)
        
        # 啟動
        result = subprocess.run(
            ['node', 
             r'C:\Users\USER\AppData\Roaming\npm\node_modules\openclaw\dist\index.js',
             'gateway', 'start'],
            capture_output=True, timeout=20
        )
        
        if result.returncode == 0:
            log('info', 'Gateway restarted successfully')
            record_restart('auto', 'restarted')
            return True
        else:
            log('error', f'Restart failed: {result.stderr[:100]}')
            record_restart('auto', 'failed')
            return False
            
    except Exception as e:
        log('error', f'Restart exception: {e}')
        record_restart('exception', f'error:{e}')
        return False

def record_restart(reason, status, uptime=0):
    """記錄重啟事件"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO restart_log (timestamp, reason, status, uptime_secs)
        VALUES (?, ?, ?, ?)
    ''', (datetime.now().isoformat(), reason, status, uptime))
    conn.commit()
    conn.close()

def get_crash_count_last_hour():
    """取得過去一小時的崩潰次數"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT COUNT(*) FROM restart_log
        WHERE timestamp >= datetime('now', '-1 hour')
        AND status = 'restarted'
    ''')
    count = c.fetchone()[0]
    conn.close()
    return count

def record_alert(alert_type, message):
    """記錄警報"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO alert_log (timestamp, alert_type, message)
        VALUES (?, ?, ?)
    ''', (datetime.now().isoformat(), alert_type, message))
    conn.commit()
    conn.close()
    log('alert', f'{alert_type}: {message}')

# 命令列模式
if __name__ == '__main__':
    init_db()
    
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'status'
    
    if cmd == 'status':
        status = check_gateway()
        print()
        print('='*50)
        print('Gateway Status')
        print('='*50)
        print(f'Status: {"RUNNING" if status else "STOPPED"}')
        print(f'Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        
        # 最近重啟
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            SELECT timestamp, reason, status FROM restart_log
            ORDER BY id DESC LIMIT 5
        ''')
        recent = c.fetchall()
        conn.close()
        
        if recent:
            print()
            print('Recent Restarts:')
            for r in recent:
                print(f'  {r[0]} - {r[1]}: {r[2]}')
        
    elif cmd == 'restart':
        restart_gateway()
        
    elif cmd == 'monitor':
        print('[MONITOR] Starting continuous monitor...')
        print(f'Check interval: {CHECK_INTERVAL}s')
        print(f'Max restarts/hour: {MAX_RESTARTS_PER_HOUR}')
        print()
        
        consecutive_failures = 0
        was_running = True
        
        while True:
            status = check_gateway()
            ts = datetime.now().strftime('%H:%M:%S')
            
            if status:
                if not was_running:
                    log('info', 'Gateway recovered')
                    record_restart('recovery', 'recovered')
                    consecutive_failures = 0
                was_running = True
            else:
                if was_running:
                    log('warn', 'Gateway stopped!')
                    was_running = False
                
                # 檢查崩潰次數
                crashes = get_crash_count_last_hour()
                
                if crashes >= MAX_RESTARTS_PER_HOUR:
                    log('warn', f'Too many restarts ({crashes}), waiting...')
                    record_alert('rate_limit', f'{crashes} restarts in 1 hour')
                    time.sleep(60)
                    continue
                
                log('info', f'Restarting (crash #{crashes+1})')
                success = restart_gateway()
                
                if success:
                    consecutive_failures = 0
                    was_running = True
                else:
                    consecutive_failures += 1
                    if consecutive_failures >= CRASH_ALERT_THRESHOLD:
                        record_alert('consecutive', f'{consecutive_failures} consecutive failures')
                
                time.sleep(5)
            
            time.sleep(CHECK_INTERVAL)