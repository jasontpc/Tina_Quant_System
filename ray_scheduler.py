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

import os, time, subprocess, logging
from datetime import datetime
from pathlib import Path

_log = logging.getLogger("ray_scheduler")
_log.setLevel(logging.INFO)

MODELS_4B = ["ray-v3.5", "qwen3.5-4b-iq4xs"]
MODELS_7B = ["ray-commander", "ray-deep-v1", "qwen2.5:7b"]

TRADING_TW  = (9, 0,  13, 30)   # 09:00 - 13:30
TRADING_US  = (21, 30, 4, 0)    # 21:30 - 04:00 (跨日凌晨)
TRAINING    = (14, 0, 20, 0)    # 14:00 - 20:00

def is_trading_hours():
    now = datetime.now()
    h, m = now.hour, now.minute
    # TW
    if (9 <= h < 13) or (h == 13 and m == 0):
        return True
    # US (跨日)
    if h >= 21 or h < 4:
        return True
    return False

def is_training_hours():
    now = datetime.now()
    h = now.hour
    return 14 <= h < 20

def ollama_stop(model):
    """停止指定的 Ollama 模型（釋放 VRAM）"""
    try:
        subprocess.run(["ollama", "stop", model],
                      capture_output=True, timeout=30, check=False)
        _log.info(f"[VRAM] Stopped: {model}")
    except Exception as e:
        _log.warning(f"[VRAM] Stop {model} failed: {e}")

def ollama_list_running():
    """返回當前加載的模型列表"""
    try:
        result = subprocess.run(["ollama", "list"],
                               capture_output=True, text=True, timeout=10, check=True)
        lines = result.stdout.strip().split('\n')[1:]
        return [l.split()[0] for l in lines if l.strip()]
    except:
        return []

def enforce():
    """根據時間段強制執行 VRAM 調度"""
    now = datetime.now().strftime("%H:%M")
    running = ollama_list_running()
    _log.info(f"[{now}] Running models: {running}")

    if is_trading_hours():
        # 交易時段：只留 4B，停掉 7B
        for m in MODELS_7B:
            if m in running:
                ollama_stop(m)
                _log.info(f"[TRADING] Stopped 7B {m} to protect VRAM")
        # 確保 4B 可用（延遲加載）
        for m in MODELS_4B:
            if m not in running:
                _log.info(f"[TRADING] {m} not loaded (will load on demand)")

    elif is_training_hours():
        # 訓練時段：停掉所有 4B
        for m in MODELS_4B:
            if m in running:
                ollama_stop(m)
                _log.info(f"[TRAINING] Stopped 4B {m} for 7B training")
        # 7B 在需要時由外部腳本啟動

    else:
        # 閒置時段（05:00-08:00）：低功耗
        for m in MODELS_7B + MODELS_4B:
            if m in running:
                ollama_stop(m)
        _log.info(f"[IDLE] All models stopped")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )
    print(f"[{datetime.now().strftime('%H:%M')}] ray_scheduler started")
    enforce()
