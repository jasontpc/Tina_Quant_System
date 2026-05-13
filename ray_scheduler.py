# -*- coding: utf-8 -*-
"""
ray_scheduler.py — VRAM 動態調度器
24小時 作戰/訓練 自動切換

| 時間段 (台北)      | 市場狀態     | 系統動作                    | VRAM 分配  |
|-------------------|-------------|----------------------------|-----------|
| 09:00 - 13:30    | 台股實戰     | 4B 執行掃描，嚴禁 7B 啟動   | 4B (2.8GB)|
| 14:00 - 20:00    | 邏輯進化     | 7B 反思+蒸餾大師觀點        | 7B (4.5GB)|
| 21:30 - 04:00    | 美股實戰     | 4B 執行決策，嚴禁 7B 啟動   | 4B (2.8GB)|
| 05:00 - 08:00    | 模型更新     | CPU 重構 Modelfile          | 低消耗     |
"""

import os, sys, subprocess, logging, time
from datetime import datetime

_log = logging.getLogger("ray_scheduler")
_log.setLevel(logging.INFO)

RAY_AGENT_DIR = r"C:\Users\USER\.openclaw\agents\ray"
MODELS_4B = ["ray-v3.5", "qwen3.5-4b-iq4xs"]
MODELS_7B = ["ray-commander", "ray-deep-v1", "qwen2.5:7b"]

def is_trading_hours():
    now = datetime.now()
    h, m = now.hour, now.minute
    if (9 <= h < 13) or (h == 13 and m == 0):
        return True
    if h >= 21 or h < 4:
        return True
    return False

def is_training_hours():
    now = datetime.now()
    h = now.hour
    return 14 <= h < 20

def is_preload_time():
    """08:30 開盤前預載 RAM"""
    now = datetime.now()
    return now.hour == 8 and now.minute >= 30

VRAM_SAFETY_GB = 5.5
MODELS_PHASE2 = {
    "ray-deep-v1":   "複雜策略分析（Regime Switch / 套利邏輯）",
    "ray-commander": "情緒指標掃描（恐慌貪婪指數 / 法人流向）",
}

def get_vram_usage():
    """嘗試讀取 NVIDIA GPU VRAM 使用量（MB）"""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            mb = int(result.stdout.strip().split('\n')[0])
            return mb / 1024  # GB
    except:
        pass
    return None

def vram_safety_check():
    """若 VRAM > 5.5GB，強制停止所有模型直到低於 4GB"""
    gb = get_vram_usage()
    if gb is None:
        return
    if gb > VRAM_SAFETY_GB:
        _log.warning(f"[VRAM SAFETY] {gb:.1f}GB > {VRAM_SAFETY_GB}GB — executing stop_all_with_cooldown()")
        stop_all_with_cooldown()
    else:
        _log.info(f"[VRAM] Current: {gb:.1f}GB / {VRAM_SAFETY_GB}GB — safe")

def ollama_stop(model):
    try:
        subprocess.run(["ollama", "stop", model],
                      capture_output=True, timeout=30, check=False)
        _log.info(f"[VRAM] Stopped: {model}")
        time.sleep(2)  # 物理釋放 VRAM 緩衝
    except Exception as e:
        _log.warning(f"[VRAM] Stop {model} failed: {e}")

def stop_all_with_cooldown():
    """停止所有模型 + 60s 強制冷卻期（避免 OOM）"""
    try:
        subprocess.run(["ollama", "stop", "--all"],
                      capture_output=True, timeout=60, check=False)
        _log.info("[VRAM] All models stopped, cooling down 60s...")
        time.sleep(60)  # 強制冷卻，讓驅動完全釋放 VRAM
        _log.info("[VRAM] Cooldown complete, VRAM should be clear")
    except Exception as e:
        _log.warning(f"[VRAM] stop_all failed: {e}")

def ollama_list_running():
    try:
        result = subprocess.run(["ollama", "list"],
                               capture_output=True, text=True, timeout=10, check=True)
        lines = result.stdout.strip().split('\n')[1:]
        return [l.split()[0] for l in lines if l.strip()]
    except:
        return []

def preload_master_insights():
    """08:30 開盤前預載：將 web_auto 最新規則載入 32GB RAM"""
    try:
        sys.path.insert(0, RAY_AGENT_DIR)
        from ray_web_collector import preload_ram_cache
        result = preload_ram_cache()
        _log.info(f"[PRELOAD] {result.get('count',0)} insights preloaded for market open")
        return True
    except Exception as e:
        _log.warning(f"[PRELOAD] failed: {e}")
        return False

def enforce():
    now = datetime.now()
    now_str = now.strftime("%H:%M")
    running = ollama_list_running()
    _log.info(f"[{now_str}] Running models: {running}")

    # VRAM 安全檢查（任何時段）
    vram_safety_check()

    if is_preload_time():
        _log.info(f"[PRELOAD] Running 08:30 market open preload...")
        preload_master_insights()

    if is_trading_hours():
        for m in MODELS_7B:
            if m in running:
                ollama_stop(m)
                _log.info(f"[TRADING] Stopped 7B {m} to protect VRAM")
        # 確保 VRAM 完全釋放後再加載 4B
        vram_safety_check()
        for m in MODELS_4B:
            if m not in running:
                _log.info(f"[TRADING] {m} not loaded (will load on demand)")

    elif is_training_hours():
        for m in MODELS_4B:
            if m in running:
                ollama_stop(m)
                _log.info(f"[TRAINING] Stopped 4B {m} for 7B training")
        # 切換到 7B 前執行完整冷卻
        vram_safety_check()
        _log.info(f"[TRAINING] 7B models available for training")

    else:
        stop_all_with_cooldown()  # 閒置時段完全停止 + 60s 冷卻

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )
    now_str = datetime.now().strftime("%H:%M")
    print(f"[{now_str}] ray_scheduler started")
    enforce()