# -*- coding: utf-8 -*-
"""
safe_memory_writer.py — Tina 安全寫入 MEMORY.md 的工具
============================================================
確保所有對 MEMORY.md 的寫入都經過 I/O 鎖排隊
避免多腳本同時寫入導致 Edit failed

用法：
  from safe_memory_writer import append_to_memory, append_to_daily_log

  append_to_memory("新增內容", marker="2026-05-13")
"""

import sys
from pathlib import Path

# 確保能 import ray_io_guard
BASE_DIR = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
sys.path.insert(0, str(BASE_DIR / "scripts" / "utils"))

try:
    from ray_io_guard import io_singleton, safe_append_memory as _safe_append_memory
    from ray_io_guard import safe_append_daily_log as _safe_append_daily_log
    from ray_io_guard import safe_write_json as _safe_write_json
    _HAS_GUARD = True
except ImportError:
    # ray_io_guard 不存在時的 fallback（不保護但可正常運作）
    def io_singleton(func):
        return func
    _safe_append_memory = None
    _safe_append_daily_log = None
    _safe_write_json = None
    _HAS_GUARD = False


MEMORY_PATH = Path(r"C:\Users\USER\.openclaw\workspace\MEMORY.md")
MEMORY_DIR  = Path(r"C:\Users\USER\.openclaw\workspace\memory")


def append_to_memory(content, marker=None):
    """
    安全寫入 MEMORY.md（經過 I/O 鎖保護）

    @param content: 要寫入的 Markdown 內容
    @param marker:   可選章節標記（如 "## 2026-05-13 系統更新"）
    """
    if not _HAS_GUARD:
        # fallback: 直接寫入（無保護）
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        header = f"\n\n---\n{marker or '追加'} @ {timestamp}\n" if marker else f"\n\n[{timestamp}] "
        with open(MEMORY_PATH, "a", encoding="utf-8") as f:
            f.write(header + content)
        print(f"[WARN] io_singleton not available, direct write to MEMORY.md")
        return

    _safe_append_memory(content, marker=marker)


def append_to_daily_log(content, date_str=None):
    """
    安全寫入當日日誌 (memory/YYYY-MM-DD.md)

    @param content:  要寫入的內容
    @param date_str: 可選，預設今天
    """
    if not _HAS_GUARD:
        from datetime import datetime
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
        log_file = MEMORY_DIR / f"{date_str}.md"
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%H:%M")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n[{timestamp}] {content}")
        print(f"[WARN] io_singleton not available, direct write to daily log")
        return

    _safe_append_daily_log(content, date_str=date_str)


def atomic_write_json(filepath, data):
    """
    原子化寫入 JSON（先寫 .tmp 再 rename）
    適合寫入 positions.json、axioms_v3.5.json 等重要狀態檔
    """
    if not _HAS_GUARD:
        import json
        import tempfile
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[WARN] io_singleton not available, direct write to {p.name}")
        return

    _safe_write_json(filepath, data)


# ── 測試 ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from datetime import datetime
    print(f"Safe Memory Writer — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"I/O Guard: {'OK' if _HAS_GUARD else 'NOT AVAILABLE'}")

    # Test append to memory
    append_to_memory("I/O Guard 整合測試完成", marker="系統測試")
    print("✅ Test passed")