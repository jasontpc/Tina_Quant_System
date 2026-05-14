# -*- coding: utf-8 -*-
"""
ray_guard.py — VRAM 守護者（RTX 4050 6GB 排隊系統）
功能：
  - 檔案鎖排隊機制（File Lock）
  - @ray_singleton 裝飾器，確保單模型執行
  - 自動清理 VRAM（ollama stop --all）
  - 防死鎖：持有超過 1 小時自動強制釋放

用法：
  from utils.ray_guard import ray_singleton

  @ray_singleton
  def my_model_task():
      # ... 你的任務邏輯
      pass
"""

import os
import sys
import time
import functools
import subprocess
import threading
from datetime import datetime
from pathlib import Path

# ── 設定 ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
LOCK_DIR = BASE_DIR / "locks"
LOCK_FILE = LOCK_DIR / "ray_vram.lock"
MODELS_DIR = BASE_DIR / "models"

LOCK_DIR.mkdir(parents=True, exist_ok=True)

# 防死鎖超時（秒）
DEADLOCK_TIMEOUT = 3600  # 1 小時

# ── 工具函式 ────────────────────────────────────────────────────────────────

def get_lock_holder():
    """讀取目前持有鎖的腳本名稱"""
    if not LOCK_FILE.exists():
        return None
    try:
        with open(LOCK_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if not content:
            return None
        # 格式：script_name|timestamp
        parts = content.split("|")
        return parts[0] if parts else None
    except Exception:
        return None


def get_lock_age_seconds():
    """取得鎖的存活時間（秒）"""
    if not LOCK_FILE.exists():
        return 0
    try:
        mtime = LOCK_FILE.stat().st_mtime
        return time.time() - mtime
    except Exception:
        return 0


def is_lock_stale():
    """判斷鎖是否已死鎖（超時）"""
    age = get_lock_age_seconds()
    return age > DEADLOCK_TIMEOUT


def clear_stale_lock():
    """強制清除死鎖"""
    if is_lock_stale():
        holder = get_lock_holder()
        print(f"[DEADLOCK CLEAR] Lock held for {get_lock_age_seconds():.0f}s, force releasing...")
        try:
            os.remove(LOCK_FILE)
            print(f"[UNLOCK] Force deleted stale lock (previous holder: {holder})")
        except FileNotFoundError:
            pass


def clear_vram():
    """物理清理 VRAM：停止所有 Ollama 模型"""
    try:
        subprocess.run(["ollama", "stop", "--all"],
                       capture_output=True, timeout=30)
        time.sleep(3)
        print("[VRAM] ollama stop --all executed")
    except Exception as e:
        print(f"[VRAM] Cleanup failed: {e}")


def wait_for_lock(script_name, poll_interval=10, max_wait=3600):
    """等待鎖釋放，超時拋異常"""
    start = time.time()
    while LOCK_FILE.exists():
        holder = get_lock_holder() or "未知任務"
        elapsed = time.time() - start
        if elapsed > max_wait:
            raise TimeoutError(f"等待鎖逾時（{elapsed:.0f}s），持有者：{holder}")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {script_name} waiting... holder: {holder} (elapsed: {elapsed:.0f}s)")
        time.sleep(poll_interval)


# ── 裝飾器 ──────────────────────────────────────────────────────────────────

def ray_singleton(func):
    """
    @ray_singleton — 單模型守護裝飾器

    行為：
      1. 檢查並等待 ray_vram.lock（最多 1 小時）
      2. 自動清理 VRAM（ollama stop --all）
      3. 取得鎖後執行任務
      4. 任務結束自動釋放鎖

    使用：
      @ray_singleton
      def my_task():
          ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        script_name = os.path.basename(sys.argv[0]) or func.__name__

        # 前置：嘗試清除死鎖
        clear_stale_lock()

        # 等待鎖
        wait_for_lock(script_name)

        # 取得鎖
        try:
            lock_content = f"{script_name}|{time.time()}"
            with open(LOCK_FILE, "w", encoding="utf-8") as f:
                f.write(lock_content)
            print(f"[LOCK] {script_name}")

            # 物理清理 VRAM
            clear_vram()

            # 執行任務
            result = func(*args, **kwargs)

            return result

        finally:
            # 釋放鎖
            try:
                if LOCK_FILE.exists():
                    os.remove(LOCK_FILE)
                    print(f"[UNLOCK] {script_name}")
            except FileNotFoundError:
                pass

    return wrapper


def ray_guard_clear():
    """手動強制清除鎖（緊急用）"""
    clear_stale_lock()
    clear_vram()


# ── I/O 寫入鎖（守護 MEMORY.md / 寫入安全）─────────────────────────────────────
IO_LOCK_FILE = LOCK_DIR / "ray_io.lock"
IO_DEADLOCK_TIMEOUT = 300  # 5 分鐘超時（I/O 操作通常很快）

def get_io_lock_holder():
    """讀取目前持有 I/O 鎖的腳本名稱"""
    if not IO_LOCK_FILE.exists():
        return None
    try:
        with open(IO_LOCK_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if not content:
            return None
        parts = content.split("|")
        return parts[0] if parts else None
    except Exception:
        return None


def get_io_lock_age_seconds():
    """取得 I/O 鎖的存活時間（秒）"""
    if not IO_LOCK_FILE.exists():
        return 0
    try:
        return time.time() - IO_LOCK_FILE.stat().st_mtime
    except Exception:
        return 0


def is_io_lock_stale():
    """判斷 I/O 鎖是否已死鎖（超時）"""
    return get_io_lock_age_seconds() > IO_DEADLOCK_TIMEOUT


def clear_stale_io_lock():
    """強制清除 I/O 死鎖"""
    if is_io_lock_stale():
        holder = get_io_lock_holder()
        print(f"[DEADLOCK CLEAR IO] Lock held {get_io_lock_age_seconds():.0f}s, force releasing...")
        try:
            os.remove(IO_LOCK_FILE)
            print(f"[IO UNLOCK] Force deleted stale lock (holder: {holder})")
        except FileNotFoundError:
            pass


def wait_for_io_lock(script_name, poll_interval=1, max_wait=300):
    """等待 I/O 鎖釋放（輪詢頻率更高：1秒）"""
    start = time.time()
    while IO_LOCK_FILE.exists():
        holder = get_io_lock_holder() or "未知任務"
        elapsed = time.time() - start
        if elapsed > max_wait:
            raise TimeoutError(f"等待 I/O 鎖逾時（{elapsed:.0f}s），持有者：{holder}")
        if int(elapsed) % 10 == 0:  # 每 10 秒報告一次，避免過度輸出
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [IO] {script_name} waiting... holder: {holder}")
        time.sleep(poll_interval)


def io_singleton(func):
    """
    @io_singleton — I/O 寫入守護裝飾器

    行為：
      1. 檢查並等待 ray_io.lock（最多 5 分鐘）
      2. 取得鎖後執行任務
      3. 任務結束自動釋放鎖

    用途：
      - 寫入 MEMORY.md / axioms_v3.5.json / ray_forbidden_rules.json
      - 防止多個腳本同時寫入導致 Edit failed
      - 輪詢頻率 1s（比 VRAM 鎖更密集）

    使用：
      @io_singleton
      def write_log():
          ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        script_name = os.path.basename(sys.argv[0]) or func.__name__

        # 前置：清除 I/O 死鎖
        clear_stale_io_lock()

        # 等待 I/O 鎖
        wait_for_io_lock(script_name)

        # 取得鎖
        try:
            lock_content = f"{script_name}|{time.time()}"
            with open(IO_LOCK_FILE, "w", encoding="utf-8") as f:
                f.write(lock_content)

            # 執行任務
            result = func(*args, **kwargs)
            return result

        finally:
            # 釋放鎖
            try:
                if IO_LOCK_FILE.exists():
                    os.remove(IO_LOCK_FILE)
            except FileNotFoundError:
                pass

    return wrapper


def io_guard_clear():
    """手動強制清除 I/O 鎖（緊急用）"""
    clear_stale_io_lock()


# ── 快速測試 ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Ray Guard 測試 ===")
    print(f"VRAM_LOCK: {LOCK_FILE}")
    print(f"IO_LOCK:   {IO_LOCK_FILE}")
    print(f"VRAM Lock holder: {get_lock_holder()}")
    print(f"IO Lock holder:   {get_io_lock_holder()}")
    print(f"VRAM stale: {is_lock_stale()}")
    print(f"IO stale:   {is_io_lock_stale()}")
    print("=====================")

    # 測試 VRAM 計時器
    @ray_singleton
    def test_vram_task():
        print("✅ VRAM 任務執行中...")
        time.sleep(1)
        print("✅ VRAM 任務完成")

    # 測試 I/O 計時器
    @io_singleton
    def test_io_task():
        print("✅ I/O 任務執行中...")
        time.sleep(1)
        print("✅ I/O 任務完成")

    test_vram_task()
    test_io_task()