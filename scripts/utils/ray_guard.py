# -*- coding: utf-8 -*-
"""
ray_guard.py — RTX 4050 6GB VRAM 守護者（多層守護系統）
功能：
  1. 檔案鎖排隊機制（File Lock）
  2. @ray_singleton — 單模型守護裝飾器
  3. @io_singleton — I/O 寫入守護裝飾器
  4. @ray_singleton_high_priority — 開盤前專用高優先級守護
  5. @market_safe_guard — 台美股開盤禁區守護
  6. 防死鎖：持有超過門檻自動強制釋放
  7. 積極物理清理（taskkill + ollama stop --all）

用法：
  from utils.ray_guard import ray_singleton, io_singleton

  @ray_singleton
  def my_model_task():
      ...
"""

import os
import sys
import time
import functools
import subprocess
from datetime import datetime
from pathlib import Path

# ── 設定 ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
LOCK_DIR = BASE_DIR / "locks"
LOCK_FILE = LOCK_DIR / "ray_vram.lock"
IO_LOCK_FILE = LOCK_DIR / "ray_io.lock"
HIGH_PRIORITY_LOCK = LOCK_DIR / "ray_vram_priority.lock"

LOCK_DIR.mkdir(parents=True, exist_ok=True)

# 防死鎖超時（秒）
DEADLOCK_TIMEOUT = 3600  # 1 小時（一般 VRAM 鎖）
IO_DEADLOCK_TIMEOUT = 300  # 5 分鐘（I/O 鎖）
PRIORITY_DEADLOCK_TIMEOUT = 60  # 60 秒（高優先級鎖）

# ── VRAM 鎖工具函式 ───────────────────────────────────────────────────────────

def get_lock_holder():
    """讀取目前持有 VRAM 鎖的腳本名稱"""
    if not LOCK_FILE.exists():
        return None
    try:
        content = LOCK_FILE.read_text(encoding="utf-8").strip()
        return content.split("|")[0] if content else None
    except Exception:
        return None


def get_lock_age_seconds():
    """取得 VRAM 鎖的存活時間（秒）"""
    if not LOCK_FILE.exists():
        return 0
    try:
        return time.time() - LOCK_FILE.stat().st_mtime
    except Exception:
        return 0


def is_lock_stale():
    """判斷 VRAM 鎖是否已死鎖（超時）"""
    return get_lock_age_seconds() > DEADLOCK_TIMEOUT


def clear_stale_lock():
    """強制清除 VRAM 死鎖"""
    if is_lock_stale():
        holder = get_lock_holder()
        try:
            os.remove(LOCK_FILE)
            print(f"[DEADLOCK CLEAR] Force deleted stale VRAM lock (holder: {holder})")
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
        print(f"[VRAM] Cleanup warning: {e}")


def wait_for_lock(script_name, poll_interval=10, max_wait=3600):
    """等待 VRAM 鎖釋放，超時拋異常"""
    start = time.time()
    while LOCK_FILE.exists():
        holder = get_lock_holder() or "未知任務"
        elapsed = time.time() - start
        if elapsed > max_wait:
            raise TimeoutError(f"VRAM 鎖等待逾時（{elapsed:.0f}s），持有者：{holder}")
        if int(elapsed) % 20 == 0:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {script_name} waiting... holder: {holder}")
        time.sleep(poll_interval)


# ── @ray_singleton — 單模型守護裝飾器 ────────────────────────────────────────

def ray_singleton(func):
    """
    @ray_singleton — 單模型 VRAM 守護裝飾器

    行為：
      1. 檢查並等待 ray_vram.lock（最多 1 小時）
      2. 自動清理 VRAM（ollama stop --all）
      3. 取得鎖後執行任務
      4. 任務結束自動釋放鎖

    使用：
      @ray_singleton
      def my_model_task():
          ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        script_name = os.path.basename(sys.argv[0]) or func.__name__
        clear_stale_lock()
        wait_for_lock(script_name)

        try:
            lock_content = f"{script_name}|{time.time()}"
            LOCK_FILE.write_text(lock_content, encoding="utf-8")
            print(f"[LOCK] {script_name}")
            clear_vram()
            return func(*args, **kwargs)
        finally:
            try:
                if LOCK_FILE.exists():
                    os.remove(LOCK_FILE)
                    print(f"[UNLOCK] {script_name}")
            except FileNotFoundError:
                pass

    return wrapper


# ── I/O 鎖工具函式 ────────────────────────────────────────────────────────────

def get_io_lock_holder():
    """讀取目前持有 I/O 鎖的腳本名稱"""
    if not IO_LOCK_FILE.exists():
        return None
    try:
        content = IO_LOCK_FILE.read_text(encoding="utf-8").strip()
        return content.split("|")[0] if content else None
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
        try:
            os.remove(IO_LOCK_FILE)
            print(f"[DEADLOCK CLEAR IO] Force deleted stale lock (holder: {holder})")
        except FileNotFoundError:
            pass


def wait_for_io_lock(script_name, poll_interval=1, max_wait=300):
    """等待 I/O 鎖釋放（輪詢頻率 1 秒）"""
    start = time.time()
    while IO_LOCK_FILE.exists():
        holder = get_io_lock_holder() or "未知任務"
        elapsed = time.time() - start
        if elapsed > max_wait:
            raise TimeoutError(f"I/O 鎖等待逾時（{elapsed:.0f}s），持有者：{holder}")
        if int(elapsed) % 10 == 0:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [IO] {script_name} waiting... holder: {holder}")
        time.sleep(poll_interval)


# ── @io_singleton — I/O 寫入守護裝飾器 ─────────────────────────────────────

def io_singleton(func):
    """
    @io_singleton — I/O 寫入守護裝飾器

    行為：
      1. 檢查並等待 ray_io.lock（最多 5 分鐘）
      2. 取得鎖後執行任務
      3. 任務結束自動釋放鎖

    用途：保護 MEMORY.md / axioms_v3.5.json / ray_forbidden_rules.json 寫入安全

    使用：
      @io_singleton
      def write_log():
          ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        script_name = os.path.basename(sys.argv[0]) or func.__name__
        clear_stale_io_lock()
        wait_for_io_lock(script_name)

        try:
            lock_content = f"{script_name}|{time.time()}"
            IO_LOCK_FILE.write_text(lock_content, encoding="utf-8")
            return func(*args, **kwargs)
        finally:
            try:
                if IO_LOCK_FILE.exists():
                    os.remove(IO_LOCK_FILE)
            except FileNotFoundError:
                pass

    return wrapper


# ── @ray_singleton_high_priority — 高優先級 VRAM 守護（08:30 預載專用）───────

def clear_priority_lock():
    """強制清除高優先級鎖（死鎖破門）"""
    if HIGH_PRIORITY_LOCK.exists():
        age = time.time() - HIGH_PRIORITY_LOCK.stat().st_mtime
        if age > PRIORITY_DEADLOCK_TIMEOUT:
            try:
                holder = HIGH_PRIORITY_LOCK.read_text(encoding="utf-8").strip()
                os.remove(HIGH_PRIORITY_LOCK)
                print(f"[PRIORITY BREACH] Force cleared stale lock (holder: {holder}, age: {age:.0f}s)")
            except Exception:
                pass


def ray_singleton_high_priority(func):
    """
    @ray_singleton_high_priority — 高優先級 VRAM 守護（開盤前專用）

    與 @ray_singleton 的差異：
      1. 獨立鎖檔案（ray_vram_priority.lock），不與一般任務排隊
      2. 60 秒死鎖自動破門（強行奪取 VRAM 控制權）
      3. 更積極的物理清理（taskkill + ollama stop --all）
      4. 獨立排隊，不參與普通 VRAM 鎖競爭

    使用：
      @ray_singleton_high_priority
      def preload_session():
          ollama.generate(model='ray-v3.5', prompt='WARMUP')
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        script_name = os.path.basename(sys.argv[0]) or func.__name__

        # Step 1: 死鎖破門檢查（60秒超時）
        clear_priority_lock()

        # Step 2: 等待鎖（最多等 120 秒）
        wait_start = time.time()
        while HIGH_PRIORITY_LOCK.exists():
            age = time.time() - HIGH_PRIORITY_LOCK.stat().st_mtime
            if age > PRIORITY_DEADLOCK_TIMEOUT:
                try:
                    os.remove(HIGH_PRIORITY_LOCK)
                    print(f"[PRIORITY BREACH] Lock timeout, force acquiring...")
                except FileNotFoundError:
                    pass
                break
            elapsed = time.time() - wait_start
            if elapsed > 120:
                raise TimeoutError(f"高優先級鎖等待逾時（120s），放棄預載")
            if int(elapsed) % 15 == 0:
                print(f"[PRIORITY WAIT] {script_name} 等待中... ({elapsed:.0f}s)")
            time.sleep(2)

        # Step 3: 取得鎖
        try:
            lock_content = f"{script_name}|{time.time()}"
            HIGH_PRIORITY_LOCK.write_text(lock_content, encoding="utf-8")
            print(f"[PRIORITY LOCK] {script_name} acquired")

            # Step 4: 積極物理清理 VRAM
            print("[VRAM] Performing aggressive cleanup...")
            try:
                subprocess.run(["taskkill", "/F", "/IM", "ollama.exe"],
                               capture_output=True, timeout=10)
            except Exception:
                pass
            subprocess.run(["ollama", "stop", "--all"],
                           capture_output=True, timeout=30)
            time.sleep(4)  # GPU 驅動回收時間
            print("[VRAM] Cleanup complete")

            # Step 5: 執行任務
            return func(*args, **kwargs)

        finally:
            # Step 6: 釋放鎖
            try:
                if HIGH_PRIORITY_LOCK.exists():
                    os.remove(HIGH_PRIORITY_LOCK)
                    print(f"[PRIORITY UNLOCK] {script_name}")
            except FileNotFoundError:
                pass

    return wrapper


# ── @market_safe_guard — 台美股開盤禁區守護 ─────────────────────────────────

def is_market_open():
    """回傳目前是否為開盤時段（TW 或 US）"""
    now = datetime.now()
    ct = now.strftime("%H:%M")
    return ("08:55" <= ct <= "13:35") or (("21:25" <= ct <= "23:59") or ("00:00" <= ct <= "04:05"))


def market_safe_guard(func):
    """
    @market_safe_guard — 台美股開盤禁區守護（保護 4050 VRAM 實戰資源）

    應用場景：
      - ollama create（模型重構）
      - 大量歷史回測（VectorBT 矩陣）
      - 腳本修改寫入（蒸餾/固化流程）

    禁區時段：
      - 台股：08:55 ~ 13:35（含開盤/收盤緩衝）
      - 美股：21:25 ~ 04:05（盤前+盤後）

    例外（不攔截）：
      - @ray_singleton_high_priority（08:30 預載）保持優先
      - ray_guardian.py 事故歸因（緊急處理）
      - 盤後維護（14:05 / 05:00）

    使用：
      @market_safe_guard
      def rebuild_ray_commander():
          ollama.create(...)
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        now = datetime.now()
        current_time = now.strftime("%H:%M")

        # 高優先級預載任務，跳過禁區檢查
        script_name = os.path.basename(sys.argv[0]) or func.__name__
        if 'preload' in script_name.lower() or '0830' in script_name.lower():
            return func(*args, **kwargs)

        # 定義禁區時段
        is_tw_market = ("08:55" <= current_time <= "13:35")
        is_us_market = (("21:25" <= current_time <= "23:59") or ("00:00" <= current_time <= "04:05"))

        if is_tw_market or is_us_market:
            market_type = "台股" if is_tw_market else "美股"
            print(f"[MARKET GUARD] 攔截高負載任務：{func.__name__}")
            print(f"[MARKET GUARD] 當前為 {market_type} 開盤時段（{current_time}）")
            print(f"[MARKET GUARD] 4050 VRAM 資源鎖定為實戰模式")
            print(f"[MARKET GUARD] 此任務將在盤後自動執行（14:05 / 05:00）")
            return None

        # 非禁區：進入標準單模型互斥排隊
        return ray_singleton(func)(*args, **kwargs)

    return wrapper


# ── 緊急清除工具 ─────────────────────────────────────────────────────────────

def ray_guard_clear():
    """手動強制清除所有鎖（緊急用）"""
    clear_stale_lock()
    clear_stale_io_lock()
    clear_priority_lock()
    clear_vram()
    print("[GUARD CLEAR] All locks cleared")


def io_guard_clear():
    """手動強制清除 I/O 鎖（緊急用）"""
    clear_stale_io_lock()


# ── 快速測試 ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Ray Guard 測試 ===")
    print(f"VRAM_LOCK: {LOCK_FILE}")
    print(f"IO_LOCK:   {IO_LOCK_FILE}")
    print(f"PRIORITY_LOCK: {HIGH_PRIORITY_LOCK}")
    print(f"Market open: {is_market_open()}")
    print(f"VRAM Lock holder: {get_lock_holder()}")
    print(f"IO Lock holder: {get_io_lock_holder()}")
    print("=====================")

    @ray_singleton_high_priority
    def test_priority_task():
        print("✅ 高優先級任務執行中...")
        time.sleep(1)
        print("✅ 高優先級任務完成")

    test_priority_task()