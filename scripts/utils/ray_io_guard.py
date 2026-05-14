# -*- coding: utf-8 -*-
"""
ray_io_guard.py -- I/O Mutex Guard (MEMORY.md write protection)
===============================================================
Features:
  - File lock queue mechanism to prevent multi-script conflicts
  - @io_singleton decorator for atomic writes
  - Lock timeout auto-release (120s) to prevent deadlocks

Usage:
  from utils.ray_io_guard import io_singleton

  @io_singleton
  def safe_write_memory(content):
      with open(MEMORY_PATH, "a", encoding="utf-8") as f:
          f.write(content)
"""

import os
import time
import functools
import sys
from datetime import datetime
from pathlib import Path

# -- I/O lock path (separate from VRAM lock) ------------------------------
BASE_DIR = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
IO_LOCK_DIR = BASE_DIR / "locks"
IO_LOCK_DIR.mkdir(parents=True, exist_ok=True)
IO_LOCK_FILE = IO_LOCK_DIR / "ray_io_memory.lock"

# Deadlock timeout (seconds)
IO_DEADLOCK_TIMEOUT = 120  # 2 minutes

# -- Utility Functions -------------------------------------------------------

def get_io_lock_holder():
    """Read current I/O lock holder name"""
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
    """Get I/O lock age in seconds"""
    if not IO_LOCK_FILE.exists():
        return 0
    try:
        return time.time() - IO_LOCK_FILE.stat().st_mtime
    except Exception:
        return 0


def is_io_lock_stale():
    """Check if I/O lock has deadlocked (exceeded timeout)"""
    return get_io_lock_age_seconds() > IO_DEADLOCK_TIMEOUT


def clear_stale_io_lock():
    """Force clear stale I/O lock"""
    if is_io_lock_stale():
        holder = get_io_lock_holder()
        print(f"[!] [IO-STALE] Lock held {get_io_lock_age_seconds():.0f}s, force releasing...")
        try:
            os.remove(IO_LOCK_FILE)
            print(f"[OK] [IO-UNLOCK] Stale lock removed (was held by: {holder})")
        except FileNotFoundError:
            pass


def wait_for_io_lock(script_name, poll_interval=1, max_wait=300):
    """Wait for I/O lock to be released, raise TimeoutError if exceeded"""
    start = time.time()
    first_wait = True

    while IO_LOCK_FILE.exists():
        holder = get_io_lock_holder() or "unknown"
        elapsed = time.time() - start

        if elapsed > max_wait:
            raise TimeoutError(f"I/O wait timeout ({elapsed:.0f}s), holder: {holder}")

        if first_wait:
            print(f"\n[!] [IO-CONFLICT] {datetime.now().strftime('%H:%M:%S')}")
            print(f"    Write attempt: {script_name}")
            print(f"    Blocked by: {holder} (waited {elapsed:.0f}s)")
            print(f"    Queueing for lock release...")
            first_wait = False
        else:
            if int(elapsed) % 5 == 0 and int(elapsed) > 0:
                print(f"    [WAIT] {elapsed:.0f}s... (holder: {holder})")

        time.sleep(poll_interval)


# -- Decorator --------------------------------------------------------------

def io_singleton(func):
    """
    @io_singleton -- I/O single-write guard decorator

    Behavior:
      1. Wait for ray_io_memory.lock (max 5 min)
      2. Auto-clear stale locks (>120s)
      3. Acquire lock, execute task
      4. Auto-release lock on completion

    Usage:
      @io_singleton
      def safe_write_log(content):
          ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        script_name = os.path.basename(sys.argv[0]) or func.__name__

        # Pre-check: clear stale locks
        clear_stale_io_lock()

        # Wait for lock
        wait_for_io_lock(script_name)

        # Acquire lock
        try:
            lock_content = f"{script_name}|{time.time()}"
            with open(IO_LOCK_FILE, "w", encoding="utf-8") as f:
                f.write(lock_content)
            print(f"[LOCK] {script_name}")

            # Execute task
            result = func(*args, **kwargs)
            return result

        finally:
            # Release lock
            try:
                if IO_LOCK_FILE.exists():
                    os.remove(IO_LOCK_FILE)
                    print(f"[UNLOCK] {script_name}")
            except FileNotFoundError:
                pass

    return wrapper


# -- Safe Write Utilities ---------------------------------------------------

MEMORY_PATH = Path(r"C:\Users\USER\.openclaw\workspace\MEMORY.md")
MEMORY_DIR  = Path(r"C:\Users\USER\.openclaw\workspace\memory")


@io_singleton
def safe_append_memory(content, marker=None):
    """
    Safely append content to MEMORY.md

    Args:
        content: Markdown content to write
        marker:  Optional section marker (e.g. "## 2026-05-13")
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    header = f"\n\n---\n{marker or 'Entry'} @ {timestamp}\n" if marker else f"\n\n[{timestamp}] "
    with open(MEMORY_PATH, "a", encoding="utf-8") as f:
        f.write(header + content)
    print(f"[OK] Wrote to MEMORY.md @ {timestamp}")


@io_singleton
def safe_append_daily_log(content, date_str=None):
    """
    Safely append content to daily log file

    Args:
        content:  Content to write
        date_str: Optional, defaults to today (YYYY-MM-DD)
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    log_file = MEMORY_DIR / f"{date_str}.md"
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%H:%M")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"\n[{timestamp}] {content}")
    print(f"[OK] Wrote to {log_file.name}")


@io_singleton
def safe_write_json(filepath, data):
    """
    Safely write JSON file (atomic write via .tmp rename)

    Args:
        filepath: Path or str to JSON file
        data:     Serializable object
    """
    import json
    p = Path(filepath) if isinstance(filepath, str) else filepath
    p.parent.mkdir(parents=True, exist_ok=True)

    tmp_file = p.with_suffix(p.suffix + ".tmp")
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp_file.replace(p)  # atomic rename
    print(f"[OK] Atomic wrote {p.name}")


@io_singleton
def safe_append_log(filepath, content):
    """
    Safely append text to any log file

    Args:
        filepath: Path or str
        content:  String content
    """
    p = Path(filepath) if isinstance(filepath, str) else filepath
    p.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(p, "a", encoding="utf-8") as f:
        f.write(f"\n[{timestamp}] {content}")
    print(f"[OK] Appended to {p.name}")


# -- Quick Test -------------------------------------------------------------

if __name__ == "__main__":
    print("=== Ray I/O Guard Test ===")
    print(f"IO_LOCK_FILE: {IO_LOCK_FILE}")
    print(f"Lock holder: {get_io_lock_holder()}")
    print(f"Lock age: {get_io_lock_age_seconds():.0f}s")
    print(f"Is stale: {is_io_lock_stale()}")
    print("==========================")

    print("\n[Test] safe_append_daily_log:")
    safe_append_daily_log("I/O Guard test OK")

    print("\n[Test] safe_append_memory:")
    safe_append_memory("Ray I/O Guard integration test complete", marker="System Test")

    print("\nAll tests passed!")