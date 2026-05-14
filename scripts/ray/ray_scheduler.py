# -*- coding: utf-8 -*-
"""
ray_scheduler.py — VRAM 單模型調度器 v2
單模型運行協議：物理清理 + 互斥鎖 + 冷卻期

核心原則：在啟動任何模型前，先執行物理清理，並在切換間加入冷卻期。

| 時段 (台北)      | 運行模型  | 互斥機制                    |
|----------------|-----------|---------------------------|
| 05:00-08:00   | 4B        | 固化重構                   |
| 09:00-13:30   | 4B        | 禁7B，走MiniMax            |
| 14:00-21:00   | 7B        | 蒸餾/歸因/策略/宏觀接管     |
| 21:30-04:00   | 4B        | 美股實戰                   |
"""

import os, sys, subprocess, logging, time
from datetime import datetime

_log = logging.getLogger("ray_scheduler")
_log.setLevel(logging.INFO)

RAY_AGENT_DIR = r"C:\Users\USER\.openclaw\agents\ray"
MODELS_4B = ["ray-v3.5", "qwen3.5-4b-iq4xs"]
MODELS_7B = ["ray-commander", "ray-deep-v1", "qwen2.5:7b"]
ALL_MODELS = MODELS_4B + MODELS_7B + ["qwen3.5-4b-instruct-q4_K_S"]

VRAM_SAFETY_GB = 5.5
COOLDOWN_SECONDS = 5   # clear_vram() 的物理冷卻

# ─── 核心清理函數 ────────────────────────────────────────────
def clear_vram():
    """強制卸載所有模型，釋放 VRAM（物理清理）"""
    _log.info("[VRAM] ███ 執行 VRAM 物理清理 ███")
    for model in ALL_MODELS:
        try:
            r = subprocess.run(["ollama", "stop", model],
                               capture_output=True, text=True, timeout=30, check=False)
            if r.returncode == 0:
                _log.info(f"  ✓ stopped {model}")
        except Exception as e:
            pass
    _log.info(f"[VRAM] 冷卻期 {COOLDOWN_SECONDS}s（讓驅動回收）...")
    time.sleep(COOLDOWN_SECONDS)

def clear_vram_full():
    """完整清理：ollama stop --all + 60s 冷卻（切換模型前用）"""
    _log.info("[VRAM] ███ 執行完整 VRAM 清理 + 60s 冷卻 ███")
    try:
        subprocess.run(["ollama", "stop", "--all"],
                       capture_output=True, timeout=60, check=False)
    except:
        pass
    _log.info("[VRAM] 60s 冷卻中...")
    time.sleep(60)
    _log.info("[VRAM] ✅ VRAM 已清空")

# ─── 查詢 ────────────────────────────────────────────────────
def get_vram_usage_gb():
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return int(result.stdout.strip().split('\n')[0]) / 1024
    except:
        pass
    return None

def get_running_models():
    try:
        result = subprocess.run(["ollama", "list"],
                                capture_output=True, text=True, timeout=10, check=True)
        lines = result.stdout.strip().split('\n')[1:]
        return [l.split()[0] for l in lines if l.strip() and not l.startswith("NAME")]
    except:
        return []

# ─── 單模型調度 ─────────────────────────────────────────────
def schedule_vram():
    now = datetime.now()
    h, m = now.hour, now.minute
    now_str = now.strftime("%H:%M")
    running = get_running_models()

    vram_gb = get_vram_usage_gb()
    vram_info = f"VRAM={vram_gb:.1f}GB" if vram_gb else "VRAM=?"
    _log.info(f"[{now_str}] {vram_info} | Running: {running}")

    # ─── 09:00-13:30 台股實戰：只允許 4B ────────────────────
    if (9 <= h < 13) or (h == 13 and m == 0):
        blocked = [m for m in MODELS_7B if m in running]
        if blocked:
            _log.warning(f"[TRADING] 禁止 7B 運行中: {blocked} → 執行清理")
            clear_vram_full()
        elif vram_gb and vram_gb > VRAM_SAFETY_GB:
            _log.warning(f"[TRADING] VRAM {vram_gb:.1f}GB > {VRAM_SAFETY_GB}GB → 清理")
            clear_vram_full()
        else:
            _log.info(f"[TRADING] ✅ 單模型 4B 環境正常")
        return

    # ─── 14:00-21:00 邏輯進化：只允許 7B ───────────────────
    if 14 <= h < 21:
        blocked = [m for m in MODELS_4B if m in running]
        if blocked:
            _log.warning(f"[TRAINING] 禁止 4B 運行中: {blocked} → 執行清理")
            clear_vram_full()
        elif vram_gb and vram_gb > VRAM_SAFETY_GB:
            _log.warning(f"[TRAINING] VRAM {vram_gb:.1f}GB > {VRAM_SAFETY_GB}GB → 清理")
            clear_vram_full()
        else:
            _log.info(f"[TRAINING] ✅ 單模型 7B 環境正常")
        return

    # ─── 21:30-04:00 美股實戰：只允許 4B ──────────────────
    if h >= 21 or h < 4:
        blocked = [m for m in MODELS_7B if m in running]
        if blocked:
            _log.warning(f"[US_MARKET] 禁止 7B 運行中: {blocked} → 執行清理")
            clear_vram_full()
        elif vram_gb and vram_gb > VRAM_SAFETY_GB:
            _log.warning(f"[US_MARKET] VRAM {vram_gb:.1f}GB > {VRAM_SAFETY_GB}GB → 清理")
            clear_vram_full()
        else:
            _log.info(f"[US_MARKET] ✅ 單模型 4B 環境正常")
        return

    # ─── 其他時段：完全停止 ─────────────────────────────────
    if running:
        _log.info(f"[IDLE] 閒置時段 → 執行完整清理")
        clear_vram_full()
    else:
        _log.info(f"[IDLE] ✅ 無模型運行，VRAM 空閒")

# ─── 入口 ────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )
    now_str = datetime.now().strftime("%H:%M")
    print(f"[{now_str}] ray_scheduler v2 started — 單模型協議")
    schedule_vram()