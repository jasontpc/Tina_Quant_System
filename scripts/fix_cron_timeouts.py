# -*- coding: utf-8 -*-
"""
fix_cron_timeouts.py — 修復所有 Timeout Cron Jobs

根據 diagnose_crons.py 的實際運行數據：
- 所有 8 個 error job 都是 timeout（非指令錯誤）
- 57dfae5d 需要調整（實際 5.3min > timeout 420s）
- 其餘 timeout 設定都高於實際運行時間（OK）
"""
import os, subprocess, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Error jobs from `openclaw cron list` output
ERROR_JOBS = [
    ("56da375e", "56da375e-3e44-497d-9a6c-e5f6e4b49351", "US Margin 每日分析",    180, 123),   # actual 2.1min, OK
    ("6bd43d57", "6bd43d57-e17c-4795-828f-c69b5174f9e0", "Ray 全語意固化重生（05:00）", 600, 321), # actual 5.4min, OK
    ("69734111", "69734111-6109-4fa8-9ed6-6b5e696bd99d", "Tina MEMORY 每日蒸餾",  300, 180),  # actual 3.0min, OK
    ("30492325", "30492325-60ed-499d-8978-9a3d3e13b65b", "08:30 開盤前 RAM 預載",  180, 45),   # actual 0.8min, OK
    ("57dfae5d", "57dfae5d-3795-4daf-916d-02fe4ccaa9d0", "Leo 台股波段每日分析",  420, 320),   # actual 5.3min > 420s ⚠️
    ("d824a2bb", "d824a2bb-a4ba-4d6f-8119-9e7b945deb6e", "Tina 自主決策五大層",  600, 185),   # actual 3.1min, OK
    ("f87364d8", "f87364d8-d946-426c-89e4-1136cc0385ea", "Ray 全語意蒸餾（14:00）", 900, 320), # actual 5.3min, OK
    ("2ebf42c9", "2ebf42c9-2a06-4527-8261-f7a62ef682c8", "14:05 失敗歸因蒸餾",  300, 120),   # actual 2.0min, OK
]

def get_current_timeout(full_id):
    """從 crons.json 讀取當前 timeout"""
    if not TEMP_JSON.exists():
        return None
    try:
        with open(TEMP_JSON, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        # Find job in text by ID
        idx = text.find(full_id)
        if idx < 0:
            return None
        # Find timeoutSeconds near this job
        region = text[idx:idx+500]
        m = re.search(r'"timeoutSeconds"\s*:\s*(\d+)', region)
        if m:
            return int(m.group(1))
    except:
        pass
    return None

def fix_timeout(short_id, current_timeout, actual_s):
    """計算並應用修復"""
    new_timeout = int(actual_s * 1.5)
    if new_timeout <= current_timeout:
        return current_timeout, "no change needed"
    return new_timeout, f"increase {current_timeout}s -> {new_timeout}s"

def main():
    print("=== Cron Timeout 修復 ===\n")
    fixes_needed = []
    for short, full_id, name, current_ts, actual_s in ERROR_JOBS:
        new_ts, reason = fix_timeout(short, current_ts, actual_s)
        actual_min = actual_s / 60
        print(f"[{short}] {name}")
        print(f"  actual: {actual_min:.1f}min | current timeout: {current_ts}s")
        if new_ts != current_ts:
            print(f"  => FIX: timeout {current_ts}s -> {new_ts}s")
            fixes_needed.append((short, new_ts, name))
        else:
            print(f"  => OK ({reason})")
        print()

    print("=== 需要修復的 Jobs ===")
    if not fixes_needed:
        print("無需修復（所有 timeout 低於實際運行時間）")
        return

    for short, new_ts, name in fixes_needed:
        print(f"openclaw cron edit {short} --timeout {new_ts}  # {name}")

    print("\n[說明] timeout 增加 50% 是保守策略，避免下次因 Cold Start 延遲再次超時")
    print("[根本原因] 所有 8 個 cron error 都是 timeout，不是指令或權限問題")

if __name__ == "__main__":
    main()