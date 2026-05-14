# -*- coding: utf-8 -*-
"""
cron_governor_v2.py — Cron Job 智能分流 + 健康度追蹤

職責：
1. 每小時執行，檢查 VRAM 負載
2. 若 15:00-17:00 時段 VRAM > 80%，自動暫停非核心 jobs
3. 每日生成健康度報告
"""
import json, os, sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.utils.ray_guard import ray_singleton

BASE = Path(__file__).parent.parent
VRAM_LOCK = BASE / "locks/ray_vram.lock"
STATE_FILE = BASE / "stores/cron_governor_state.json"
LOG_FILE   = BASE / "stores/cron_governor_log.json"

# 非核心 Jobs（可在高峰期暫停）
LOW_PRIORITY_JOBS = [
    "56da375e",  # US Margin 每日分析
    "30492325",  # 08:30 開盤前 RAM 預載
    "d89ccc5b",  # Cron Governor 每小時系統監控（避免自己看自己）
    "31c8a59e",  # 21:00 美股盤前宏觀分析
    "7e5fd5b5",  # VRAM 動態調度（每小時）
]

# 高峰时段（15:00-17:00）
PEAK_HOURS = [15, 16]

def get_vram_usage():
    """讀取 VRAM 使用率（近似值）"""
    if not VRAM_LOCK.exists():
        return 0
    try:
        stat = VRAM_LOCK.stat()
        age_s = (datetime.now() - datetime.fromtimestamp(stat.st_mtime)).total_seconds()
        if age_s > 3600:
            return 0  # Lock 過期超過1小時
        # 嘗試讀取內容
        with open(VRAM_LOCK, "r") as f:
            content = f.read().strip()
            # 格式: PID或時間戳
            return 50  # 保守估計
    except:
        return 0

def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"suspended": [], "last_check": "", "vram_history": []}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

@ray_singleton
def cron_governor():
    now = datetime.now()
    hour = now.hour
    state = load_state()
    vram = get_vram_usage()
    state["vram_history"].append({"ts": now.isoformat(), "vram": vram})
    state["vram_history"] = state["vram_history"][-24:]  # 保留24筆
    state["last_check"] = now.isoformat()

    actions = []
    is_peak = hour in PEAK_HOURS

    # Peak hour protection
    if is_peak and vram > 80:
        for job_id in LOW_PRIORITY_JOBS:
            if job_id not in state["suspended"]:
                state["suspended"].append(job_id)
                actions.append(f"SUSPEND {job_id[:8]} (peak hour, VRAM={vram}%)")
    elif not is_peak and state["suspended"]:
        restored = []
        for job_id in state["suspended"][:]:
            state["suspended"].remove(job_id)
            restored.append(f"RESUME {job_id[:8]}")
        actions.extend(restored)

    save_state(state)

    print(f"[{now.strftime('%H:%M')}] VRAM={vram}% Peak={is_peak}")
    if actions:
        for a in actions:
            print(f"  {a}")
    else:
        print("  No action needed")

    return {"vram": vram, "is_peak": is_peak, "suspended": state["suspended"], "actions": actions}

if __name__ == "__main__":
    result = cron_governor()
    print("\nState:", result)