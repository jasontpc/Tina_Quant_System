# -*- coding: utf-8 -*-
"""
db_add_audit_tables.py — 新增 system_fault_logs / logic_corrections / vram_audit 三表
"""
import sqlite3, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB = r"C:\Users\USER\.openclaw\agents\ray\ray_wisdom.db"
conn = sqlite3.connect(DB)
c = conn.cursor()

print("=== DB Schema 升級：系統錯誤追蹤 + 邏輯修正 + VRAM 審計 ===\n")

# ── 1. system_fault_logs ─────────────────────────────────────
c.execute("""CREATE TABLE IF NOT EXISTS system_fault_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    script_name TEXT,
    error_type TEXT,
    traceback TEXT,
    fixed INTEGER DEFAULT 0,
    fix_script TEXT,
    resolved_at TEXT
)""")
print("✅ system_fault_logs 已建立")

# ── 2. logic_corrections ──────────────────────────────────────
c.execute("""CREATE TABLE IF NOT EXISTS logic_corrections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    failed_logic TEXT,
    fixed_logic TEXT,
    master_tag TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    applied_at TEXT,
    confidence REAL DEFAULT 0.5
)""")
print("✅ logic_corrections 已建立")

# ── 3. vram_audit ─────────────────────────────────────────────
c.execute("""CREATE TABLE IF NOT EXISTS vram_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    model_active TEXT,
    peak_vram_mb INTEGER,
    oom_event INTEGER DEFAULT 0,
    violation_text TEXT,
    action_taken TEXT
)""")
print("✅ vram_audit 已建立")

# ── 寫入示範數據 ─────────────────────────────────────────────
import time as _time

# 過往 RSI bug 記錄（示範）
c.execute("""INSERT OR IGNORE INTO system_fault_logs (script_name, error_type, traceback, fixed)
    VALUES ('tina_cron_v2.py', 'RSI_ALL_SAME_BUG',
            'Layer3 每個 position RSI 都相同，pos_rsis list 在迴圈中被錯誤累加',
            1)""")

# 示範 logic_correction
c.execute("""INSERT OR IGNORE INTO logic_corrections (failed_logic, fixed_logic, master_tag, confidence)
    VALUES ('Layer3 positions JSON comprehension 使用外部迴圈變量 current_rsi',
            '使用 explicit layer3_positions list，確保每檔 RSI 正確對應',
            'ray-deep-v1:20260513',
            0.85)""")

# 示範 vram_audit
c.execute("""INSERT OR IGNORE INTO vram_audit (model_active, peak_vram_mb, violation_text, action_taken)
    VALUES ('ray-v3.5 + qwen2.5:7b', 0,
            '雙模型同時運行但 VRAM=0（懷疑使用 CPU 推理）',
            '需確認 Ollama GPU offload 設定')""")

conn.commit()
conn.close()

print("\n✅ Schema 升級完成")
print("  system_fault_logs — 腳本錯誤記錄")
print("  logic_corrections  — 修正後的新天條")
print("  vram_audit        — VRAM 違規審計")