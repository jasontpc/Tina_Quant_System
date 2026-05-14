# -*- coding: utf-8 -*-
"""
ray_knowledge_distiller.py — 每日失敗模式蒸餾（14:00執行）

功能：
1. 讀取今日失敗日誌（system_fault_report）
2. 分析失敗模式（使用 MiniMax 或本地 7B）
3. 蒸餾新禁止規則寫入 ray_forbidden_rules.json
4. 供隔日 05:00 ray_distiller_auto.py 燒入模型

排程：每日 14:00（Asia/Taipei）
依賴：axioms_v3.5.json, ray_forbidden_rules.json, system_defect_report
"""

import sys, os, json, time
from pathlib import Path

# ── 路徑設定 ──────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
FAULT_REPORT = BASE_DIR / "stores" / "system_defect_report_20260513.md"
AXIOMS_FILE  = BASE_DIR / "stores" / "long_term" / "axioms_v3.5.json"
FORBIDDEN_FILE = BASE_DIR / "stores" / "long_term" / "ray_forbidden_rules.json"
LOG_FILE   = BASE_DIR / "stores" / "distillation_log.json"

# ── Ollama / MiniMax ──────────────────────────────────────
OLLAMA_URL = "http://localhost:11434/api/chat"

def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ── LLM 蒸餾（MiniMax 優先，本地 7B 備用）──────────────────
def distill_with_llm(fault_text: str, context: str) -> list:
    """使用 MiniMax 蒸餾失敗模式為禁止規則"""
    prompt = f"""你是 Ray 系統的失敗模式分析師。

目標：從以下失敗日誌中，蒸餾出 2-4 條「禁止規則」（ray_forbidden_rules）。
禁止規則格式：IF <條件> THEN DO NOT <行動>

大師對齊：Taleb（肥尾/反脆弱）、Thorp（凱利/纪律）、Simons（模型穩定性）、Dalio（風險平衡）

失敗日誌：
{fault_text}

現有禁止規則（避免重複）：
{context}

輸出 JSON 陣列（每個物件包含 rule / master / priority / taleb_aligned / thorp_aligned）：
[
  {{"rule": "IF <condition> THEN DO NOT <action>", "master": "大師名", "priority": 1, "taleb_aligned": true/false, "thorp_aligned": true/false}}
]

只輸出 JSON，無其他文字。"""

    # 嘗試 MiniMax
    try:
        import urllib.request, urllib.error
        api_key = os.getenv("MINIMAX_API_KEY") or os.getenv("api-key") or ""
        if api_key:
            payload = {
                "model": "minimax/MiniMax-M2.7",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 2000
            }
            req = urllib.request.Request(
                "https://api.minimax.chat/v1/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
            result = raw["choices"][0]["message"]["content"].strip()
            import re
            m = re.search(r'\[[\s\S]*\]', result)
            if m:
                rules = json.loads(m.group())
                return rules if isinstance(rules, list) else []
    except Exception as e:
        print(f"[MiniMax fallback] {e}")

    # 備用：本地 7B
    try:
        import urllib.request
        payload = {
            "model": "qwen2.5:7b",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 400}
        }
        req = urllib.request.Request(
            OLLAMA_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=90) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
        content = raw.get("message", {}).get("content", "").strip()
        import re
        m = re.search(r'\[[\s\S]*\]', content)
        if m:
            return json.loads(m.group())
    except Exception as e:
        print(f"[Local 7B fallback] {e}")

    return []

# ── 主蒸餾流程 ─────────────────────────────────────────────
def main():
    print("=== Ray Knowledge Distiller 啟動（14:00）===")
    log = {"started": time.strftime("%Y-%m-%d %H:%M:%S"), "steps": [], "new_rules": 0}

    # Step 1: 讀取失敗報告
    if FAULT_REPORT.exists():
        with open(FAULT_REPORT, "r", encoding="utf-8") as f:
            fault_text = f.read()[-3000:]  # 取最後 3000 字（最新失敗）
        print(f"[Step 1] 讀取失敗報告：{len(fault_text)} 字")
        log["steps"].append({"step": "load_faults", "chars": len(fault_text)})
    else:
        fault_text = "無失敗報告（系統正常）"
        print(f"[Step 1] 無失敗報告")
        log["steps"].append({"step": "load_faults", "note": "no_report"})

    # Step 2: 讀取現有禁止規則（避免重複）
    existing = load_json(FORBIDDEN_FILE, {"rules": []})
    existing_rules = [r.get("rule","") for r in existing.get("rules", [])]
    context = "\n".join(existing_rules)
    print(f"[Step 2] 現有禁止規則：{len(existing_rules)} 條")
    log["steps"].append({"step": "load_existing", "count": len(existing_rules)})

    # Step 3: LLM 蒸餾
    print("[Step 3] LLM 蒸餾失敗模式...")
    new_rules = distill_with_llm(fault_text, context)
    print(f"  蒸餾出 {len(new_rules)} 條新規則")
    log["steps"].append({"step": "distill", "rules_count": len(new_rules), "model": "minimax_or_7b"})

    # Step 4: 過濾重複規則
    unique_rules = []
    for r in new_rules:
        rule_text = r.get("rule", "")
        if rule_text and rule_text not in existing_rules:
            # 簡單相似度檢查（關鍵詞重疊）
            overlap = sum(1 for kw in ["EMA", "RSI", "stop_loss", "distance"] if kw in rule_text)
            if overlap >= 1:
                unique_rules.append(r)
                existing_rules.append(rule_text)

    print(f"[Step 4] 去重後：{len(unique_rules)} 條新規則（總計 {len(existing_rules)} 條）")
    log["steps"].append({"step": "dedup", "unique": len(unique_rules)})

    # Step 5: 寫入禁止規則檔案
    if unique_rules:
        updated = {
            "schema": "ray_forbidden_rules_v1",
            "version": "1.2",
            "generated": time.strftime("%Y-%m-%d"),
            "count": len(existing_rules),
            "rules": existing.get("rules", []) + unique_rules
        }
        save_json(FORBIDDEN_FILE, updated)
        print(f"[Step 5] 已寫入 {len(unique_rules)} 條新規到 {FORBIDDEN_FILE.name}")
        log["steps"].append({"step": "write", "written": len(unique_rules)})
    else:
        print("[Step 5] 無新規則，跳過寫入")

    # Step 6: 更新日誌
    log["completed"] = time.strftime("%Y-%m-%d %H:%M:%S")
    log["new_rules"] = len(unique_rules)
    log_entries = load_json(LOG_FILE, [])
    log_entries.append(log)
    save_json(LOG_FILE, log_entries[-10:])  # 保留最近 10 次

    print(f"\n=== 完成。蒸餾 {len(unique_rules)} 條新規則 ===")
    for r in unique_rules:
        print(f"  [{r.get('master','?')}] {r.get('rule','')[:70]}")

    return {"new_rules": len(unique_rules), "total_rules": len(existing_rules)}

if __name__ == "__main__":
    result = main()
    print(f"\n本次蒸餾：{result['new_rules']} 條新規則（總計：{result['total_rules']} 條）")
    print("供隔日 05:00 ray_distiller_auto.py 燒入模型 ✅")