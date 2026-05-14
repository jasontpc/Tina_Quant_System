# -*- coding: utf-8 -*-
"""
system_blueprint.py — 全系統戰情室藍圖匯報
"""
import json, os
from pathlib import Path
from datetime import datetime

BASE = Path(".")

def load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default or {}

# ── Load all assets ────────────────────────────────
lessons  = load_json("stores/long_term/lessons.json", {"lessons": []})
patterns = load_json("stores/long_term/patterns.json", {"patterns": []})
ledger  = load_json("stores/long_term/experience_ledger.json", {"records": []})
axioms  = load_json("stores/long_term/axioms_v4.0.json", [])
semantic= load_json("stores/long_term/semantic_logic_v2.json", {"rules": []})
macro   = load_json("stores/short_term/macro_tags.json", {})
news_pool = []
if os.path.exists("news_pool.txt"):
    with open("news_pool.txt", "r", encoding="utf-8", errors="replace") as f:
        news_pool = [l.strip() for l in f if l.strip()]

# ── Counts ──────────────────────────────────────
n_lessons = len(lessons.get("lessons", []))
n_patterns = len(patterns.get("patterns", []))
n_ledger  = len(ledger.get("records", []))
n_axioms  = len(axioms)
n_semantic= len(semantic.get("rules", []))
n_news   = len(news_pool)
n_cross  = sum(1 for p in patterns.get("patterns", []) if p.get("type") == "cross_pattern")
n_thorp_pass = sum(1 for p in patterns.get("patterns", []) if p.get("thorp_pass") == True)

# ── Thorp stats ─────────────────────────────────
thorp_aligned = sum(1 for a in axioms if a.get("thorp_aligned"))
avg_conf = sum(a["confidence"] for a in axioms) / n_axioms if n_axioms else 0

# ── Scripts list ─────────────────────────────────
scripts = {}
scripts_dir = BASE / "scripts"
if scripts_dir.exists():
    for s in scripts_dir.glob("*.py"):
        scripts[s.name] = s.stat().st_size

# ── Cron jobs (manual check) ────────────────────
vram_lock = os.path.exists("locks/ray_vram.lock")
io_lock   = os.path.exists("locks/ray_io.lock")

# ── Print ───────────────────────────────────────
now = datetime.now().strftime("%Y-%m-%d %H:%M")
print(f"=== 全系統戰情室 — {now} ===")
print()
print("─── 智力資產 ───")
print(f"  Lessons:     {n_lessons} 筆")
print(f"  Patterns:    {n_patterns} 筆 (cross={n_cross}, thorp_pass={n_thorp_pass})")
print(f"  Ledger:      {n_ledger} 筆")
print(f"  Axioms v4.0:{n_axioms} 條 (thorp_aligned={thorp_aligned}/8, avg_conf={avg_conf:.3f})")
print(f"  Semantic:    {n_semantic} 條規則")
print(f"  news_pool:   {n_news} 條新聞")
print()
print("─── Macro ───")
for tag in macro.get("tags", []):
    print(f"  {tag}")
sig = macro.get("signals", {})
print(f"  VIX={sig.get('VIX','N/A')}, NVDA={sig.get('NVDA_chg','N/A')}")
print()
print("─── 資源狀態 ───")
print(f"  VRAM_lock: {'LOCKED' if vram_lock else 'free'}")
print(f"  IO_lock:   {'LOCKED' if io_lock else 'free'}")
print()
print("─── 核心腳本 ───")
priority_scripts = [
    "ray_master_burn.py", "ray_semantic_distiller.py",
    "ray_net_collector.py", "expand_lessons.py",
    "pattern_cross_logic.py", "backtest_to_lessons.py",
    "tw_stock_tagger.py", "ray_decision_gate.py",
    "analyze_and_fix_crash.py"
]
for name in priority_scripts:
    if name in scripts:
        print(f"  {name}: {scripts[name]} bytes")
print()
print("─── 腳本總數 ───")
py_scripts = [s for s in scripts if s.endswith(".py")]
bat_scripts = list(scripts_dir.glob("*.bat")) if scripts_dir.exists() else []
ps_scripts = list(scripts_dir.glob("*.ps1")) if scripts_dir.exists() else []
print(f"  .py: {len(py_scripts)}")
print(f"  .bat: {len(bat_scripts)}")
print(f"  .ps1: {len(ps_scripts)}")
