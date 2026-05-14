# -*- coding: utf-8 -*-
"""
cleanup_dirty_files.py — 清理 Tina_Quant_System 根目錄髒數據

執行前請確認所有路徑。
"""

import os
from pathlib import Path

BASE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")

def delete(path):
    p = BASE / path
    if p.exists():
        size = p.stat().st_size
        p.unlink()
        print(f"  DEL: {path} ({size//1024}KB)")
        return size
    else:
        print(f"  MISS: {path}")
        return 0

def mkdir(path):
    p = BASE / path
    p.mkdir(parents=True, exist_ok=True)
    print(f"  MKDIR: {path}/")

def move(src, dst):
    s = BASE / src
    d = BASE / dst
    if s.exists():
        d.parent.mkdir(parents=True, exist_ok=True)
        s.rename(d)
        print(f"  MOVE: {src} -> {dst}")
        return True
    else:
        print(f"  MISS: {src}")
        return False

total_freed = 0

print("=== Phase 1: 創建目錄結構 ===")
mkdir("scripts/checks")
mkdir("scripts/db")
mkdir("configs")
mkdir("scripts/analysis")

print()
print("=== Phase 2: 刪除一次性修補 ===")
delete_files = [
    "fix_confidence.py",
    "fix_logic_distiller.py",
    "fix_logic_distiller2.py",
    "p3_fix_token.py",
    "patch_daily_review.py",
    "patch_score_display.py",
    "gemini_embedding_demo.py",
    "lang_analysis.py",
    "check_keys.py",
    "check_gemini_usage.py",
    "sig_range.py",
    "verify_pos.py",
    "cleanup_old_sessions.py",
]
for f in delete_files:
    total_freed += delete(f)

print()
print("=== Phase 3: 移動腳本到 scripts/ ===")
move("check_00713.py", "scripts/checks/check_00713.py")
move("check_schema.py", "scripts/checks/check_schema.py")
move("db_audit.py", "scripts/db/db_audit.py")
move("db_audit2.py", "scripts/db/db_audit2.py")
move("rsi_audit.py", "scripts/checks/rsi_audit.py")
move("analyze_2454.py", "scripts/analysis/analyze_2454.py")
move("analyze_2458.py", "scripts/analysis/analyze_2458.py")
move("analyze_2492.py", "scripts/analysis/analyze_2492.py")

print()
print("=== Phase 4: 刪除根目錄過時檔案 ===")
delete_files2 = [
    "gap_fix_report_20260502.md",
    "cron_audit_report.md",
    "ai_image_classifier_README.md",
    "P3_FIX_STATUS.md",
]
for f in delete_files2:
    total_freed += delete(f)

print()
print(f"=== 總計釋放: {total_freed//1024}KB ===")