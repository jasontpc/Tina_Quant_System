# -*- coding: utf-8 -*-
"""
ray_scheduler.py — VRAM 動態調度器
============================================================
根據台北時間自動切換 7B/4B 模型：
- 交易時段（09:00-13:30 / 21:30-04:00）：停7B，只留4B
- 訓練時段（14:00-20:00）：停4B，解放VRAM
- 固化時段（05:00-08:00）：低功耗
- 其他時段：按需調度

使用 @ray_singleton 確保排隊運行，不搶 VRAM
"""

import sys, time, subprocess, json
from pathlib import Path
from datetime import datetime

# ── 路徑設定 ────────────────────────────────────────────────────────────
BASE_DIR = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
sys.path.insert(0, str(BASE_DIR / "scripts" / "utils"))

try:
    from ray_guard import ray_singleton, clear_vram, wait_for_lock
    _HAS_GUARD = True
except ImportError:
    def ray_singleton(func):
        return func
    _HAS_GUARD = False

# ── 時間帶定義 ──────────────────────────────────────────────────────────
TRADE_MORNING  = (9, 0, 13, 30)   # 09:00-13:30
TRADE_NIGHT    = (21, 30, 4, 0)   # 21:30-04:00
TRAINING       = (14, 0, 20, 0)   # 14:00-20:00
SOLIDIFICATION = (5, 0, 8, 0)    # 05:00-08:00

# ── 模型定義 ────────────────────────────────────────────────────────────
MODELS_7B = ["qwen2.5:7b-instruct-q4_K_XS"]
MODELS_4B = ["qwen3.5:4b-instruct-q4_K_S"]

# ── 日誌路徑 ────────────────────────────────────────────────────────────
SCHEDULER_LOG = BASE_DIR / "logs" / "ray_scheduler.log"
SCHEDULER_LOG.parent.mkdir(parents=True, exist_ok=True)

# ── 工具函式 ────────────────────────────────────────────────────────────

def log(msg):
    """寫入排程日誌"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(SCHEDULER_LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def get_current_time_slot():
    """根據現在時間判斷時段"""
    now = datetime.now()
    h, m = now.hour, now.minute

    # 固化時段
    if 5 <= h < 8:
        return "SOLIDIFY"

    # 交易時段（早）
    if 9 <= h < 13 or (h == 13 and m <= 30):
        return "TRADE_MORNING"

    # 訓練時段
    if 14 <= h < 20:
        return "TRAINING"

    # 交易時段（晚）
    if h >= 21 or h < 4:
        return "TRADE_NIGHT"

    return "IDLE"


def get_ollama_models():
    """取得目前運行的模型列表"""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10,
            encoding="utf-8",
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")[1:]  # skip header
            running = []
            for line in lines:
                parts = line.split()
                if len(parts) >= 1:
                    running.append(parts[0])
            return running
    except:
        pass
    return []


def stop_models(models):
    """停止指定模型"""
    stopped = []
    for model in models:
        try:
            subprocess.run(
                ["ollama", "stop", model],
                capture_output=True,
                timeout=30,
            )
            stopped.append(model)
        except:
            pass
    return stopped


def switch_to_4b():
    """切換到僅 4B 模式（釋放 VRAM）"""
    log("切換至 4B 模式：停止所有 7B 模型")
    running = get_ollama_models()
    stopped_7b = []
    for m in running:
        for x in MODELS_7B:
            base = x.split(":")[0]
            if m.startswith(base) or base in m:
                stopped_7b.append(m)
                break
    stopped = stop_models(stopped_7b)
    log(f"已停止: {', '.join(stopped) if stopped else '（無）'}")
    log("VRAM 已釋放，4B 模型待命")


def switch_to_7b():
    """切換到 7B 模式"""
    log("切換至 7B 模式：停止所有 4B 模型，載入 7B")
    running = get_ollama_models()
    stopped_4b = []
    for m in running:
        for x in MODELS_4B:
            base = x.split(":")[0]
            if m.startswith(base) or base in m:
                stopped_4b.append(m)
                break
    stopped = stop_models(stopped_4b)
    log(f"已停止: {', '.join(stopped_4b) if stopped_4b else '（無）'}")

    # 預熱 7B 模型
    for model in MODELS_7B:
        try:
            log(f"預熱 {model}...")
            subprocess.run(
                ["ollama", "run", model],
                input="hello",
                capture_output=True,
                timeout=60,
            )
            log(f"{model} 已就緒")
        except:
            log(f"{model} 預熱失敗")


def low_power_mode():
    """低功耗模式：停止所有模型"""
    log("低功耗模式：停止所有模型")
    running = get_ollama_models()
    if running:
        stopped = stop_models(running)
        log(f"已停止: {', '.join(stopped)}")
    else:
        log("（無運行中的模型）")


def get_schedule_log_path():
    """取得調度日誌路徑"""
    return SCHEDULER_LOG


# ── 主邏輯 ────────────────────────────────────────────────────────────

@ray_singleton
def run_scheduler():
    """VRAM 動態調度主邏輯"""
    log("=" * 40)
    log("VRAM 動態調度器啟動")
    log(f"VRAM Guard: {'OK' if _HAS_GUARD else 'NOT FOUND'}")

    slot = get_current_time_slot()
    log(f"當前時段: {slot}")
    log(f"運行中的模型: {', '.join(get_ollama_models()) or '（無）'}")

    if slot == "SOLIDIFY":
        log("固化時段：低功耗模式")
        low_power_mode()

    elif slot in ("TRADE_MORNING", "TRADE_NIGHT"):
        log("交易時段：只留 4B，停止 7B")
        switch_to_4b()

    elif slot == "TRAINING":
        log("訓練時段：停止 4B，解放 VRAM 給訓練")
        running = get_ollama_models()
        stopped_4b = []
        for m in running:
            for x in MODELS_4B:
                base = x.split(":")[0]
                if m.startswith(base) or base in m:
                    stopped_4b.append(m)
                    break
        stopped = stop_models(stopped_4b)
        log(f"已停止: {', '.join(stopped) if stopped else '（無）'}")

    else:
        log("空閒時段：不做強制切換")
        running = get_ollama_models()
        log(f"運行中: {', '.join(running) or '（無）'}")

    log(f"最終模型: {', '.join(get_ollama_models()) or '（無）'}")
    log("調度完成")
    log("=" * 40)


# ── 快速測試 ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    print()
    print("=" * 50)
    print("VRAM Dynamic Scheduler")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    run_scheduler()
    print()
    print(f"Log: {SCHEDULER_LOG}")