# -*- coding: utf-8 -*-
"""
ray_semantic_distiller.py — 純規則引擎蒸餾（無需 Ollama）

功能：
1. 從 axioms_v4.0 讀取 Thorp 約束（8條凱利公式規則）
2. 從 lessons.json 讀取高勝率 lesson（WR≥65%）
3. 從 patterns.json 讀取高信心 pattern（hit_rate≥60%）
4. 直接產出 semantic_logic_v2.json

對比舊版：完全移除 Ollama 7B 呼叫，不再有 VRAM 搶奪問題
"""

import sys, os, json, time, re
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
FAULT_REPORT = BASE_DIR / "stores/system_defect_report_20260513.md"
OUTPUT_FILE  = BASE_DIR / "stores/long_term/semantic_logic_v2.json"
LOG_FILE     = BASE_DIR / "stores/distillation_log.json"
OLLAMA_URL   = "http://localhost:11434/api/chat"  # 保留但不使用

def load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default if default is not None else {}

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ── 語意蒸餾（純規則引擎，無需 7B）───────────────────────────
def distill_semantic(fault_text: str) -> list:
    """
    純規則引擎蒸餾：
    - 從 axioms_v4.0 讀取 Thorp 約束
    - 從 lessons/patterns 讀取語意標籤組合
    - 直接產出 semantic_logic_v2.json，無需 Ollama
    """
    rules = []
    rule_id = 1

    # ── Step 1: 從 axioms_v4.0 讀取 Thorp 約束 ───────────────
    axioms = load_json(BASE_DIR / "stores/long_term/axioms_v4.0.json", [])
    thorp_axioms = [a for a in axioms if a.get("thorp_aligned")]

    for axiom in thorp_axioms:
        when = axiom.get("when", "")
        then = axiom.get("then", "")
        tag = axiom.get("tag", "")
        calc = axiom.get("thorp_calculus", {})
        conf = axiom.get("confidence", 0.85)

        # 提取 [TAG] 格式的標籤
        tags = re.findall(r'\[([A-Z_]+)\]', when)
        tag_list = [f"[{t}]" for t in tags] if tags else ([tag] if tag else ["[UNKNOWN]"])

        # 判斷 ACT 或 SKIP（包含 f* 或 example 含 0 → SKIP）
        then_upper = then.upper()
        is_reject = ("f*" in then_upper or "SKIP" in then_upper or
                     "負" in then or "全數離場" in then)

        rules.append({
            "if_tags": tag_list,
            "then_action": "SKIP" if is_reject else "ACT",
            "logic_id": f"SEM_{rule_id:03d}",
            "master_align": "Thorp",
            "priority": int(conf * 10),
            "thorp_calculus": calc
        })
        rule_id += 1

    # ── Step 2: 從 lessons 產生額外 ACT 規則 ───────────────
    lessons_data = load_json(BASE_DIR / "stores/long_term/lessons.json", {"lessons": []})
    for lesson in lessons_data.get("lessons", [])[-10:]:
        tag = lesson.get("tag", "")
        sym = lesson.get("symbol", "")
        wr = lesson.get("win_rate", 0) or 0
        conf_lesson = lesson.get("confidence", 0.8)

        if wr >= 65 or conf_lesson >= 0.85:
            if tag:
                tag_clean = tag.strip("[]")
                tag_fmt = f"[{tag_clean}]" if not tag.startswith("[") else tag
                rules.append({
                    "if_tags": [tag_fmt],
                    "then_action": "ACT",
                    "logic_id": f"SEM_{rule_id:03d}",
                    "master_align": "Thorp",
                    "priority": int((wr / 100) * 10) if wr else int(conf_lesson * 10),
                    "source": f"lesson:{sym}"
                })
            rule_id += 1

    # ── Step 3: 從 patterns 產生 ACT 規則 ─────────────────
    patterns_data = load_json(BASE_DIR / "stores/long_term/patterns.json", {"patterns": []})
    for pat in patterns_data.get("patterns", []):
        pname = pat.get("pattern_name", "")
        hit = pat.get("hit_rate") or 0
        conf_pat = pat.get("confidence", 0.8)
        if hit >= 0.6 or conf_pat >= 0.8:
            rules.append({
                "if_tags": [f"[{pname}]"],
                "then_action": "ACT",
                "logic_id": f"SEM_{rule_id:03d}",
                "master_align": "Taleb",
                "priority": int(conf_pat * 10),
                "source": f"pattern:{pname}"
            })
            rule_id += 1

    print(f"[distill] 蒸餾出 {len(rules)} 條規則（純規則引擎，無 Ollama）")
    return rules

# ── 主蒸餾流程 ─────────────────────────────────────────────
def main():
    print("=== Ray Semantic Distiller 啟動（純規則引擎）===")
    log = {"started": time.strftime("%Y-%m-%d %H:%M:%S"), "steps": [], "new_rules": 0, "engine": "rule-based"}

    # Step 1: 讀取失敗日誌（用於日誌記錄，規則引擎不依賴）
    if FAULT_REPORT.exists():
        with open(FAULT_REPORT, "r", encoding="utf-8") as f:
            fault_text = f.read()[-3000:]
        print(f"[Step 1] 失敗日誌：{len(fault_text)} 字")
        log["steps"].append({"step": "load_faults", "chars": len(fault_text)})
    else:
        fault_text = "[NO_FAULT_DATA]"
        log["steps"].append({"step": "load_faults", "note": "none"})

    # Step 2: 純規則引擎蒸餾（無 Ollama）
    print("[Step 2] 純規則引擎蒸餾...")
    rules = distill_semantic(fault_text)
    print(f"  蒸餾出 {len(rules)} 條語意規則")
    log["steps"].append({"step": "distill", "rules": len(rules), "engine": "rule-based"})

    # Step 3: 寫入 semantic_logic_v2.json
    if rules:
        output = {
            "schema": "semantic_logic_v2",
            "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "version": "2.1",
            "count": len(rules),
            "engine": "rule-based",
            "rules": rules
        }
        save_json(OUTPUT_FILE, output)
        print(f"[Step 3] 已寫入 {OUTPUT_FILE.name}（{len(rules)} 條）")
        log["steps"].append({"step": "write", "file": str(OUTPUT_FILE), "count": len(rules)})
    else:
        print("[Step 3] 無新規則，跳過")

    # Step 4: 更新日誌
    log["completed"] = time.strftime("%Y-%m-%d %H:%M:%S")
    log["new_rules"] = len(rules)
    log_entries = load_json(LOG_FILE, [])
    log_entries.append(log)
    save_json(LOG_FILE, log_entries[-10:])

    print(f"\n=== 完成。蒸餾 {len(rules)} 條語意規則 ===")
    for r in rules:
        tags = r.get("if_tags", [])
        act = r.get("then_action", "?")
        lid = r.get("logic_id", "???")
        print(f"  [{lid}] {' + '.join(tags)} → {act}")

    return {"rules": len(rules)}

if __name__ == "__main__":
    result = main()
    print(f"\nPure rule engine, no Ollama. Relying on axioms_v4.0 + lessons + patterns [OK]")