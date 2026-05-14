# -*- coding: utf-8 -*-
"""
Cron Governor — 系統活動感知智能排程器
=====================================
職責：
1. 每5分鐘評估系統活動分數（0-100）
2. 低活動時段自動喚醒 cron jobs
3. 高負載時抑制非緊急 jobs
4. 保護 Gateway 資源，防止連鎖崩潰

活動分數計算：
- eventLoopDelayMaxMs: <500ms = 100分, >3000ms = 0分
- CPU: <30% = 100分, >80% = 0分
- Memory: <50% = 100分, >85% = 0分
- cronQueueDepth: 0 = 100分, >5 = 0分
- activeJobs: 0 = 100分, >3 = 0分

Threshold:
- <30分：進入「清醒時段」，允許高優先級 jobs
- 30-60分：普通模式，按原排程
- >60分：進入「節能模式」，只允許必要 jobs
"""

import sys, json, time, psutil, os
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import urlopen, Request

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
STORES_DIR = BASE_DIR / 'stores'
STATE_FILE = STORES_DIR / 'cron_governor_state.json'
LOG_FILE = STORES_DIR / 'cron_governor_log.json'

# ─── Config ────────────────────────────────────────────────────────────────
GATEWAY_URL = 'http://127.0.0.1:18789'
ACTIVITY_THRESHOLD_LOW = 30      # 分數 < 30 → 清醒時段
ACTIVITY_THRESHOLD_HIGH = 60     # 分數 > 60 → 節能模式
CHECK_INTERVAL_SEC = 1200       # 每20分鐘檢查一次
WINDOW_START = 2   # 凌晨2:00（系統最空）
WINDOW_END = 6     # 凌晨6:00（系統最空）
MARKET_OPEN_HOUR = 9
MARKET_CLOSE_HOUR = 16

# ─── Helpers ────────────────────────────────────────────────────────────────

def load_json(filepath, default=None):
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default if default is not None else {}

def save_json(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_system_metrics():
    """抓取系統指標"""
    metrics = {
        'cpu_percent': 0,
        'memory_percent': 0,
        'event_loop_delay_ms': 0,
        'cron_queue_depth': 0,
        'active_jobs': 0,
        'timestamp': datetime.now().isoformat()
    }

    # CPU / Memory via psutil
    try:
        metrics['cpu_percent'] = psutil.cpu_percent(interval=1)
        vm = psutil.virtual_memory()
        metrics['memory_percent'] = vm.percent
    except Exception as e:
        print(f'psutil error: {e}')

    # Parse gateway log for event loop delay
    try:
        log_path = Path(os.environ.get('TEMP', '/tmp')) / 'openclaw' / 'openclaw-2026-05-08.log'
        if log_path.exists():
            lines = log_path.read_text(encoding='utf-8', errors='ignore').splitlines()
            for line in reversed(lines[-200:]):
                try:
                    entry = json.loads(line)
                    msg = entry.get('message', '')
                    if 'eventLoopDelayMaxMs' in msg or 'eventLoop' in msg:
                        # Try to extract number
                        import re
                        m = re.search(r'eventLoopDelayMaxMs[":\s]+(\d+)', msg)
                        if m:
                            metrics['event_loop_delay_ms'] = int(m.group(1))
                            break
                except:
                    pass
    except Exception as e:
        print(f'log parse error: {e}')

    # Gateway API health check (as proxy for active jobs)
    try:
        req = Request(f'{GATEWAY_URL}/api/health', timeout=3)
        # Just check if gateway is responsive
        with urlopen(req, timeout=3) as resp:
            pass
        metrics['gateway_ok'] = True
    except:
        metrics['gateway_ok'] = False

    return metrics

def calc_activity_score(metrics):
    """
    計算系統活動分數（0-100）
    100 = 完全空閒，0 = 完全過載
    """
    scores = []

    # CPU: 30% 以下 = 100分, 80% 以上 = 0分
    cpu = metrics.get('cpu_percent', 0)
    cpu_score = max(0, min(100, 100 - (cpu - 30) * (100/50))) if cpu >= 30 else 100
    scores.append(('cpu', cpu_score, 0.25))

    # Memory: 50% 以下 = 100分, 85% 以上 = 0分
    mem = metrics.get('memory_percent', 0)
    mem_score = max(0, min(100, 100 - (mem - 50) * (100/35))) if mem >= 50 else 100
    scores.append(('memory', mem_score, 0.20))

    # Event Loop Delay: <500ms = 100分, >3000ms = 0分
    eld = metrics.get('event_loop_delay_ms', 0)
    eld_score = max(0, min(100, 100 - (eld - 500) * (100/2500))) if eld >= 500 else 100
    scores.append(('event_loop', eld_score, 0.35))

    # Gateway responsiveness: OK = 100, Down = 0
    gw_ok = metrics.get('gateway_ok', True)
    scores.append(('gateway', 100 if gw_ok else 0, 0.20))

    # Weighted average
    total_score = sum(s[1] * s[2] for s in scores)
    return int(total_score)

def get_window_mode():
    """判断當前是否在低活動時段窗口"""
    now = datetime.now()
    hour = now.hour
    
    # 凌晨低活動窗口
    if WINDOW_START <= hour < WINDOW_END:
        return 'deep_sleep'  # 深夜窗口，最寬鬆
    
    # 市場關閉後（16:00-02:00）
    if hour >= MARKET_CLOSE_HOUR or hour < WINDOW_START:
        return 'evening'     # 晚間窗口，中等寬鬆
    
    # 市場開放時間（09:00-16:00）
    if MARKET_OPEN_HOUR <= hour < MARKET_CLOSE_HOUR:
        return 'market_hours'  # 市場時間，最嚴格
    
    # 早盤或午餐時間
    return 'normal'

def decide_action(score, window_mode, pending_jobs):
    """
    根據分數和窗口模式決定允許動作
    返回: (allow_new_jobs, max_concurrent, suppress_low_priority)
    """
    # 清廉政（深夜）: 寬鬆
    if window_mode == 'deep_sleep':
        return True, 5, False
    
    # 晚間：適中
    if window_mode == 'evening':
        if score < 30:
            return True, 3, False
        elif score < 50:
            return True, 2, True   # 抑制低優先級
        else:
            return False, 1, True   # 只允許風控
    
    # 市場時間：嚴格
    if window_mode == 'market_hours':
        if score < 20:
            return True, 2, True
        else:
            return False, 1, True   # 只允許風控
    
    # 正常時間
    if score < 30:
        return True, 2, False
    elif score < 50:
        return True, 1, True
    else:
        return False, 1, True

def log_decision(score, window_mode, action, pending):
    """寫入決策日誌"""
    log = load_json(LOG_FILE, [])
    log.append({
        'timestamp': datetime.now().isoformat(),
        'activity_score': score,
        'window_mode': window_mode,
        'action': action,
        'pending_jobs': pending,
        'cpu': psutil.cpu_percent(interval=0.5),
        'memory_percent': psutil.virtual_memory().percent
    })
    # Keep last 100 entries
    if len(log) > 100:
        log = log[-100:]
    save_json(LOG_FILE, log)

def log_fault_to_db(script, error_type, traceback):
    """寫入 system_fault_logs（供 ray_self_fixer.py 讀取）"""
    DB_PATH = r'C:\Users\USER\.openclaw\agents\ray\ray_wisdom.db'
    if not os.path.exists(DB_PATH):
        return
    try:
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""INSERT INTO system_fault_logs (script_name, error_type, traceback, fixed)
                      VALUES (?, ?, ?, 0)""", (script, error_type, traceback[:500]))
        conn.commit()
        conn.close()
        print(f"[FAULT] {script}: {error_type}")
    except Exception as e:
        print(f"[FAULT-LOG-ERROR] {e}")

def scan_gateway_logs_for_errors():
    """掃描 Gateway 日誌，發現錯誤時寫入 system_fault_logs"""
    try:
        log_path = Path(os.environ.get('LOCALAPPDATA', '')) / 'Temp' / 'openclaw' / 'openclaw-2026-05-13.log'
        if not log_path.exists():
            log_path = Path(os.environ.get('TEMP', '/tmp')) / 'openclaw' / 'openclaw-2026-05-13.log'
        if not log_path.exists():
            return []
        lines = log_path.read_text(encoding='utf-8', errors='ignore').splitlines()
        errors = []
        for line in reversed(lines[-500:]):
            try:
                entry = json.loads(line)
                msg = str(entry.get('message', ''))
                lvl = entry.get('level', '')
                if lvl in ('error', 'warn') and 'cron' in msg.lower():
                    errors.append(msg[:200])
            except:
                pass
        return errors
    except Exception as e:
        print(f"[SCAN-ERROR] {e}")
        return []

# ─── Main ──────────────────────────────────────────────────────────────────

def main():
    print(f'=== Cron Governor | {datetime.now().strftime("%Y-%m-%d %H:%M")} ===')
    
    # 1. 抓取指標
    metrics = get_system_metrics()
    print(f'Metrics: CPU={metrics["cpu_percent"]:.1f}% MEM={metrics["memory_percent"]:.1f}% EL={metrics["event_loop_delay_ms"]}ms GW={metrics["gateway_ok"]}')
    
    # 1b. 掃描錯誤並寫入 system_fault_logs
    print('[FAULT] 掃描 Gateway 日誌錯誤...')
    errors = scan_gateway_logs_for_errors()
    for err in errors[:3]:
        log_fault_to_db('cron_governor', 'gateway_cron_error', err)
    if not errors:
        print('[FAULT] 無新錯誤')
    
    # 2. 計算分數
    score = calc_activity_score(metrics)
    window = get_window_mode()
    print(f'Score: {score}/100 | Window: {window}')
    
    # 3. 載入狀態
    state = load_json(STATE_FILE, {'last_action': None, 'last_score': 50})
    
    # 4. 決策
    allow_jobs, max_concurrent, suppress_low = decide_action(score, window, state.get('pending_jobs', 0))
    
    print(f'Action: allow={allow_jobs} max_concurrent={max_concurrent} suppress_low={suppress_low}')
    
    # 5. 更新狀態
    state['activity_score'] = score
    state['window_mode'] = window
    state['last_check'] = datetime.now().isoformat()
    state['allow_new_jobs'] = allow_jobs
    state['max_concurrent'] = max_concurrent
    state['suppress_low_priority'] = suppress_low
    state['metrics'] = metrics
    save_json(STATE_FILE, state)
    
    # 6. 日誌
    action_str = f'allow={allow_jobs}|max={max_concurrent}|suppress={suppress_low}'
    log_decision(score, window, action_str, state.get('pending_jobs', 0))
    
    print(f'State saved: {STATE_FILE}')
    print(f'GOVERNOR DONE')

if __name__ == '__main__':
    main()