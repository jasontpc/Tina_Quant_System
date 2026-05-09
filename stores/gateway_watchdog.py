# -*- coding: utf-8 -*-
"""
Gateway Watchdog — 系統崩潰後自動重啟
=====================================
職責：
1. 每30秒檢查 Gateway 健康狀態（port 18789）
2. 若無回應，視為崩潰，自動重啟
3. 記錄所有事件到 watchdog_log.json
4. 防止重複重啟（cooldown 保護）

Windows 重啟方式：
- 用 taskkill 停止 node.exe
- 用 schtasks /run 啟動 Gateway（排程任務名：OpenClaw Gateway）
- 或直接重啟 node.exe（後台運行）
"""

import sys, json, time, socket, subprocess, os, shutil
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

sys.stdout.reconfigure(encoding='utf-8')

# ─── Config ────────────────────────────────────────────────────────────────
GATEWAY_HOST = '127.0.0.1'
GATEWAY_PORT = 18789
CHECK_INTERVAL = 30      # 每30秒檢查一次
COOLDOWN_SEC = 60         # 重啟後60秒冷卻，防止迴圈
MAX_RESTART_PER_HOUR = 5  # 每小時最多重啟5次，超過則報警
LOG_FILE = Path(__file__).parent / 'watchdog_log.json'
STATE_FILE = Path(__file__).parent / 'watchdog_state.json'

# ─── helpers ───────────────────────────────────────────────────────────────

def load_json(filepath, default=None):
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default if default is not None else {}

def save_json(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_gateway_alive():
    """檢查 Gateway 是否活著"""
    # Method 1: TCP socket check
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((GATEWAY_HOST, GATEWAY_PORT))
        sock.close()
        if result == 0:
            return True
    except Exception as e:
        pass

    # Method 2: HTTP probe
    try:
        req = Request(f'http://{GATEWAY_HOST}:{GATEWAY_PORT}/', timeout=5)
        with urlopen(req, timeout=5) as resp:
            return resp.status < 400
    except:
        pass

    return False

def get_node_processes():
    """取得所有 node.exe 行程"""
    try:
        output = subprocess.check_output(
            ['tasklist', '/FI', 'IMAGENAME eq node.exe', '/FO', 'CSV', '/NH'],
            shell=True, stderr=subprocess.DEVNULL
        )
        lines = output.decode('utf-8', errors='ignore').strip().split('\n')
        pids = []
        for line in lines:
            if 'node.exe' in line.lower():
                parts = line.split(',')
                if len(parts) >= 2:
                    pids.append(int(parts[1].strip('"')))
        return pids
    except:
        return []

def stop_gateway():
    """停止 Gateway node 程序"""
    killed = []
    for pid in get_node_processes():
        try:
            subprocess.run(['taskkill', '/PID', str(pid), '/F', '/T'],
                          shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            killed.append(pid)
        except:
            pass
    return killed

def start_gateway():
    """啟動 Gateway（透過排程任務）"""
    try:
        # 嘗試用 schtasks 啟動排程任務
        subprocess.run(
            ['schtasks', '/Run', '/TN', 'OpenClaw Gateway'],
            shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return True
    except:
        pass

    # fallback: 直接啟動 node
    try:
        node_path = r'C:\Program Files\nodejs\node.exe'
        openclaw_path = r'C:\Users\USER\AppData\Roaming\npm\node_modules\openclaw\dist\index.js'
        subprocess.Popen(
            [node_path, openclaw_path, 'gateway', '--port', str(GATEWAY_PORT)],
            cwd=r'C:\Users\USER',
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            creationflags=subprocess.DETACHED_PROCESS if hasattr(subprocess, 'DETACHED_PROCESS') else 0
        )
        return True
    except:
        return False

def log_event(state, event_type, detail=''):
    """寫入事件日誌"""
    log = load_json(LOG_FILE, [])
    entry = {
        'timestamp': datetime.now().isoformat(),
        'event': event_type,
        'detail': detail,
        'gateway_alive': is_gateway_alive(),
    }
    log.append(entry)
    # Keep last 200 entries
    if len(log) > 200:
        log = log[-200:]
    save_json(LOG_FILE, log)

    # Update state
    state['last_event'] = event_type
    state['last_event_time'] = datetime.now().isoformat()
    state['gateway_alive'] = entry['gateway_alive']
    save_json(STATE_FILE, state)

# ─── main watchdog ─────────────────────────────────────────────────────────

def watchdog_cycle(state):
    """單次檢查循環"""
    now = datetime.now()
    alive = is_gateway_alive()

    # Update state with current status
    state['last_check'] = now.isoformat()
    state['gateway_alive'] = alive

    if alive:
        # Gateway 正常運行
        state['consecutive_failures'] = 0
        state['restart_cooldown'] = False
        save_json(STATE_FILE, state)
        return True

    # Gateway 掛了
    state['consecutive_failures'] = state.get('consecutive_failures', 0) + 1
    failures = state['consecutive_failures']

    print(f'[!] Gateway dead (consecutive_failures={failures})')

    # Cooldown protection — don't restart too soon
    if state.get('restart_cooldown'):
        remaining = state.get('cooldown_until', 0) - time.time()
        if remaining > 0:
            print(f'    Cooldown active, {remaining:.0f}s remaining')
            save_json(STATE_FILE, state)
            return False

    # Count restarts in last hour
    restart_count = 0
    log = load_json(LOG_FILE, [])
    one_hour_ago = time.time() - 3600
    for entry in log:
        if entry.get('event') == 'restart' and entry.get('timestamp'):
            try:
                ts = datetime.fromisoformat(entry['timestamp']).timestamp()
                if ts > one_hour_ago:
                    restart_count += 1
            except:
                pass

    if restart_count >= MAX_RESTART_PER_HOUR:
        print(f'[!] Max restarts per hour reached ({MAX_RESTART_PER_HOUR}), skipping restart')
        log_event(state, 'max_restarts_reached', f'count={restart_count}')
        return False

    # Attempt restart
    print(f'[!] Attempting restart (attempt #{restart_count+1})')
    log_event(state, 'crash_detected', f'failures={failures}')

    # Stop
    killed = stop_gateway()
    print(f'    Killed {len(killed)} node processes: {killed}')
    time.sleep(2)

    # Start
    success = start_gateway()
    print(f'    Start {'succeeded' if success else 'FAILED'}')
    log_event(state, 'restart_attempt', f'success={success} killed={killed}')

    # Set cooldown
    state['restart_cooldown'] = True
    state['cooldown_until'] = time.time() + COOLDOWN_SEC
    state['last_restart'] = now.isoformat()
    state['restart_count'] = restart_count + 1

    save_json(STATE_FILE, state)

    # Wait and verify
    if success:
        time.sleep(5)  # 等待啟動
        verified = is_gateway_alive()
        print(f'    Gateway alive after restart: {verified}')
        log_event(state, 'restart_verified' if verified else 'restart_failed', '')
        state['gateway_alive'] = verified

    return success

def main():
    print(f'=== Gateway Watchdog | {datetime.now().strftime("%Y-%m-%d %H:%M")} ===')
    print(f'Check interval: {CHECK_INTERVAL}s | Cooldown: {COOLDOWN_SEC}s | Max restarts/hr: {MAX_RESTART_PER_HOUR}')

    state = load_json(STATE_FILE, {
        'consecutive_failures': 0,
        'restart_cooldown': False,
        'cooldown_until': 0,
        'last_restart': None,
        'restart_count': 0,
        'gateway_alive': False,
        'started_at': datetime.now().isoformat(),
    })

    # Initial check
    if is_gateway_alive():
        print(f'[OK] Gateway is alive')
        state['gateway_alive'] = True
        save_json(STATE_FILE, state)
    else:
        print(f'[!] Gateway appears dead, attempting restart...')
        watchdog_cycle(state)

    # Main loop
    print(f'\nWatchdog running... (Ctrl+C to stop)')
    while True:
        try:
            time.sleep(CHECK_INTERVAL)
            watchdog_cycle(state)
        except KeyboardInterrupt:
            print('\nWatchdog stopped.')
            break
        except Exception as e:
            print(f'[!] Watchdog error: {e}')
            time.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    main()