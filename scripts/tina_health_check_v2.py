# -*- coding: utf-8 -*-
"""
tina_health_check_v2.py — 全系統健檢橫向整合版

垂直整合（單一系統）：
  ├── 智力資產（Lessons/Patterns/Ledger/Axioms/Semantic）
  ├── 資源狀態（VRAM_lock / IO_lock / locks/）
  ├── Cron Job 健康度（失敗次數 / Timeout 統計）
  ├── Commit 一致性（be11eda 以後）
  └── 五大師人格同步狀態（Modelfile / Axioms / Semantic）

横向整合（跨團隊）：
  ├── Leo Team（6檔：2330/2454/2379/2376/2382/3665）
  ├── Nana Team（ETF/個股波段）
  ├── Ray Team（DCA / 決策閘）
  └── Tina System（蒸餾/固化/Cron）
"""
import json, os, sys
from pathlib import Path
from datetime import datetime
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.utils.ray_guard import io_singleton

BASE = Path(__file__).parent.parent

def load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default or {}

# ── Vertical Checks ────────────────────────────────
def check_intellectual_assets():
    """智力資產完整性"""
    lessons  = load_json(BASE / "stores/long_term/lessons.json", {"lessons": []})
    patterns = load_json(BASE / "stores/long_term/patterns.json", {"patterns": []})
    ledger   = load_json(BASE / "stores/long_term/experience_ledger.json", {"records": []})
    axioms   = load_json(BASE / "stores/long_term/axioms_v4.0.json", [])
    semantic = load_json(BASE / "stores/long_term/semantic_logic_v2.json", {"rules": []})
    macro    = load_json(BASE / "stores/short_term/macro_tags.json", {})

    n_lessons = len(lessons.get("lessons", []))
    n_patterns = len(patterns.get("patterns", []))
    n_ledger  = len(ledger.get("records", []))
    n_axioms  = len(axioms)
    n_semantic= len(semantic.get("rules", []))

    thorp_aligned = sum(1 for a in axioms if a.get("thorp_aligned"))
    avg_conf = sum(a["confidence"] for a in axioms) / n_axioms if n_axioms else 0

    # Status
    status = []
    if n_lessons >= 20:  status.append("lessons_ok")
    if n_patterns >= 20: status.append("patterns_ok")
    if n_axioms == 8 and thorp_aligned == 8: status.append("thorp_ok")
    if n_semantic >= 20: status.append("semantic_ok")

    return {
        "lessons": n_lessons, "patterns": n_patterns,
        "ledger": n_ledger, "axioms": n_axioms,
        "thorp_aligned": thorp_aligned, "avg_conf": round(avg_conf, 3),
        "semantic": n_semantic,
        "tags": macro.get("tags", []),
        "vix": macro.get("signals", {}).get("VIX", "N/A"),
        "status": status
    }

def check_resources():
    """資源狀態"""
    vram_lock = os.path.exists(BASE / "locks/ray_vram.lock")
    io_lock   = os.path.exists(BASE / "locks/ray_io.lock")
    return {"vram_lock": vram_lock, "io_lock": io_lock}

def check_blueprint_script():
    """system_blueprint.py 存在性"""
    exists = (BASE / "system_blueprint.py").exists()
    return {"blueprint_exists": exists}

# ── Cross-team Checks ─────────────────────────────
def check_leo_universe():
    """Leo Team 持股宇宙"""
    summary = load_json(BASE / "teams/leo/matrix_results/leo_backtest_summary.json", {})
    syms = summary.get("symbols", {})
    retained = ["2330", "2379", "3665", "2454", "2382", "2376"]
    removed  = ["2317", "3034"]
    status = "ok" if all(s in syms for s in retained) and all(s not in syms for s in removed) else "warn"
    return {"universe": retained, "removed": removed, "status": status, "avg_wr": summary.get("overall", {}).get("avg_val_wr", 0)}

def check_nana_system():
    """Nana Team 狀態"""
    nana_dir = BASE / "teams/nana"
    reports = list((nana_dir / "reports").glob("*.json")) if (nana_dir / "reports").exists() else []
    return {"nana_reports": len(reports), "status": "ok" if reports else "empty"}

def check_ray_system():
    """Ray Team 狀態"""
    ray_dir = BASE / "teams/ray"
    ray_scripts = list((ray_dir / "scripts").glob("*.py")) if (ray_dir / "scripts").exists() else []
    return {"ray_scripts": len(ray_scripts), "status": "ok"}

def check_tina_crons():
    """Tina Cron Job 健康度"""
    try:
        import subprocess
        result = subprocess.run(
            ["openclaw", "cron", "list", "--json"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            jobs = json.loads(result.stdout)
            errors = [j for j in jobs if j.get("lastRunStatus") == "error"]
            return {"total": len(jobs), "errors": len(errors), "error_jobs": [j.get("name","?") for j in errors[:5]]}
    except:
        pass
    return {"total": -1, "errors": -1, "error_jobs": []}

def check_news_pool():
    """news_pool.txt 狀態"""
    path = BASE / "news_pool.txt"
    if not path.exists():
        return {"exists": False, "count": 0}
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = [l.strip() for l in f if l.strip()]
    return {"exists": True, "count": len(lines)}

def check_master_burn():
    """ray_master_burn.py 狀態"""
    path = BASE / "scripts/ray_master_burn.py"
    exists = path.exists()
    size = path.stat().st_size if exists else 0
    return {"exists": exists, "size": size}

def check_modelfile():
    """Ray-v3.5.Modelfile 狀態"""
    path = BASE / "Ray-v3.5.Modelfile"
    if not path.exists():
        return {"exists": False, "size": 0}
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    has_thorp = "thorp" in content.lower() or "f*" in content
    has_loupe = "loupe" in content.lower()
    return {"exists": True, "size": len(content), "has_thorp": has_thorp, "has_loupe": has_loupe}

# ── Main ────────────────────────────────────────
@io_singleton
def run_health_check():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"=== Tina 全系統健檢 v2 — {now} ===")
    print()

    # Vertical
    ia = check_intellectual_assets()
    rs = check_resources()
    bp = check_blueprint_script()
    nb = check_news_pool()
    mb = check_master_burn()
    mf = check_modelfile()

    # Cross-team
    leo = check_leo_universe()
    nana = check_nana_system()
    ray = check_ray_system()
    crons = check_tina_crons()

    # Score
    score = 0
    total = 0

    def score_item(cond, weight=1):
        nonlocal score, total
        total += weight
        if cond: score += weight

    score_item(ia["lessons"] >= 20, 2)
    score_item(ia["patterns"] >= 20, 2)
    score_item(ia["thorp_aligned"] == 8, 2)
    score_item(ia["semantic"] >= 20, 1)
    score_item(rs["vram_lock"], 1)
    score_item(bp["blueprint_exists"], 1)
    score_item(nb["count"] >= 3, 1)
    score_item(mb["exists"], 1)
    score_item(mf["has_thorp"] and mf["has_loupe"], 1)
    score_item(leo["status"] == "ok", 2)
    score_item(crons["errors"] == 0, 2)
    score_item(ia["ledger"] >= 10, 1)  # ledger target

    health_pct = round(score / total * 100) if total > 0 else 0

    # Report
    print("─── 智力資產（垂直）───")
    print(f"  Lessons:    {ia['lessons']} 筆  {'[OK]' if ia['lessons']>=20 else '[WARN]'}")
    print(f"  Patterns:   {ia['patterns']} 筆  {'[OK]' if ia['patterns']>=20 else '[WARN]'}")
    print(f"  Ledger:     {ia['ledger']} 筆   {'[WARN]' if ia['ledger']<10 else '[OK]'}")
    print(f"  Axioms:     {ia['axioms']} 條（thorp_aligned={ia['thorp_aligned']}/8, conf={ia['avg_conf']})")
    print(f"  Semantic:  {ia['semantic']} 條")
    print(f"  VIX:        {ia['vix']}  | Tags: {ia['tags']}")
    print()

    print("─── 資源狀態（垂直）───")
    print(f"  VRAM_lock: {'LOCKED [OK]' if rs['vram_lock'] else 'FREE [WARN]'}")
    print(f"  Blueprint: {'exists [OK]' if bp['blueprint_exists'] else 'MISSING [WARN]'}")
    print(f"  news_pool: {nb['count']} 條  {'[OK]' if nb['count']>=3 else '[WARN]'}")
    print()

    print("─── 五大師固化（垂直）───")
    print(f"  master_burn.py: {mb['size']} bytes  {'[OK]' if mb['exists'] else '[MISSING]'}")
    print(f"  Modelfile: {mf['size']} bytes")
    print(f"    Thorp f*: {'[OK]' if mf['has_thorp'] else '[MISSING]'}")
    print(f"    LOUPE:    {'[OK]' if mf['has_loupe'] else '[MISSING]'}")
    print()

    print("─── 跨團隊整合（橫向）───")
    print(f"  Leo Universe: {leo['universe']}  avg_wr={leo['avg_wr']:.1f}%  {'[OK]' if leo['status']=='ok' else '[WARN]'}")
    print(f"  Removed: {leo['removed']}")
    print(f"  Nana: {nana['nana_reports']} reports  {nana['status']}")
    print(f"  Ray:  {ray['ray_scripts']} scripts  {ray['status']}")
    print()

    print("─── Cron Job 健康度 ───")
    print(f"  Total: {crons['total']}  jobs")
    print(f"  Errors: {crons['errors']}  {'[OK]' if crons['errors']==0 else '[WARN]'}")
    if crons.get("error_jobs"):
        for j in crons["error_jobs"]:
            print(f"    FAIL: {j}")
    print()

    print(f"─── 總健康度：{health_pct}% ───")
    print(f"  Score: {score}/{total}")

    return {
        "timestamp": now,
        "health_pct": health_pct,
        "score": score,
        "total": total,
        "intellectual_assets": ia,
        "resources": rs,
        "cron": crons,
        "cross_team": {"leo": leo, "nana": nana, "ray": ray}
    }

if __name__ == "__main__":
    result = run_health_check()
    print("\n[JSON]", json.dumps(result, ensure_ascii=False, indent=2))