# -*- coding: utf-8 -*-
"""
Ray Self-Correction Engine - Dual-Layer LLM Integration
Layer 1: 1.5B (ray-v1) fast classification + weight decay
Layer 2: 7B (ray-deep-v1) only for complex cases (confidence < 0.5)

Strategy: Most failures handled by fast 1.5B, only 20% need expensive 7B.
"""

import json, sqlite3, requests, re, time
from datetime import datetime

BASE_URL  = "http://localhost:11434/api/chat"
FAST_MODEL = "ray-v1"
DEEP_MODEL = "ray-deep-v1"
DB_PATH   = "ray_wisdom.db"


def call_llm(model: str, system: str, user: str, timeout: int = 60) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user}
        ],
        "temperature": 0.3 if model == FAST_MODEL else 0.2,
        "stream": False,
        "options": {"num_predict": 300 if model == FAST_MODEL else 600}
    }
    try:
        resp = requests.post(BASE_URL, json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json()["message"]["content"]
    except Exception as e:
        return f"ERROR: {e}"


def extract_json(text: str) -> dict:
    text = text.strip()
    m = re.search(r"```(?:\w+)?\s*([\s\S]*?)```", text)
    if m:
        try: return json.loads(m.group(1).strip())
        except: pass
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        try: return json.loads(text[start:end])
        except: pass
    return {}


def ensure_schema():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("PRAGMA table_info(wisdom_logs)")
    cols = [col[1] for col in c.fetchall()]
    if "weight" not in cols:
        c.execute("ALTER TABLE wisdom_logs ADD COLUMN weight REAL DEFAULT 1.0")
    c.execute("""
        CREATE TABLE IF NOT EXISTS wisdom_corrections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            axiom_id INTEGER, symbol TEXT, diagnosis TEXT,
            corrected_json TEXT, confidence REAL, meta_label TEXT,
            model_used TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)
    """)
    conn.commit()
    conn.close()


def get_failed_wisdoms(limit=50):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT w.id, w.axiom_json, w.reflection, COALESCE(r.symbol, 'UNKNOWN') as symbol, COALESCE(w.weight, 1.0) as weight
          FROM wisdom_logs w
     LEFT JOIN backtest_reports r ON w.backtest_id = r.id
         WHERE w.passed = 0
         ORDER BY w.weight DESC, w.timestamp DESC
         LIMIT ?
    """, (limit,))
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "axiom_json": r[1], "reflection": r[2], "symbol": r[3], "weight": r[4]} for r in rows]


def layer1_fast_classification(fw: dict) -> dict:
    """Layer 1: 1.5B 快速分類失敗原因 + 決定 weight 衰減"""
    axiom = json.loads(fw["axiom_json"]) if isinstance(fw["axiom_json"], str) else fw["axiom_json"]

    system_prompt = (
        "You are Ray-Fast (1.5B). Analyze this failed strategy.\n"
        'Output ONLY JSON: {"diagnosis":"string","decay_factor":float,"needs_deep_analysis":bool,"confidence":float}\n'
        'diagnosis: Why did it fail? (short)\n'
        'decay_factor: weight multiplier (0.5=strong sell, 0.8=mild fail, 1.0=no change)\n'
        'needs_deep_analysis: true only if logic is fundamentally broken (rare)\n'
        'confidence: how confident are you (0.0-1.0)'
    )

    user_prompt = (
        f"Failed axiom: {json.dumps(axiom, ensure_ascii=False)}\n"
        f"Reflection: {fw['reflection']}\n"
        f"Symbol: {fw['symbol']}\n\n"
        "Quick diagnosis + decay decision."
    )

    t0 = time.time()
    response = call_llm(FAST_MODEL, system_prompt, user_prompt, timeout=30)
    elapsed = time.time() - t0
    print(f"    [1.5B] {elapsed:.1f}s: {response[:100]}...")

    result = extract_json(response)
    if not result:
        return {"needs_deep_analysis": False, "diagnosis": fw["reflection"][:80], "decay_factor": 0.7, "confidence": 0.5}

    return {
        "diagnosis": result.get("diagnosis", fw["reflection"][:80]),
        "decay_factor": result.get("decay_factor", 0.7),
        "needs_deep_analysis": result.get("needs_deep_analysis", False),
        "confidence": result.get("confidence", 0.5),
    }


def layer2_deep_analysis(fw: dict, diagnosis: str) -> dict:
    """Layer 2: 7B 只處理需要深度重建的複雜案例"""
    axiom = json.loads(fw["axiom_json"]) if isinstance(fw["axiom_json"], str) else fw["axiom_json"]

    system_prompt = (
        'You are Ray-Deep (Qwen 7B), the Chief Strategist of the Tina Quant System.\n'
        'Output ONLY valid JSON with this exact schema:\n'
        '{"diagnosis":"string","corrected_strategy":{"strategy_name":"string","indicator":"string",'
        '"params":{},"entry_condition":{},"stop_loss":float},"confidence":float,"meta_label":{}}'
    )

    user_prompt = (
        f"Analyze this failed strategy and produce a corrected version.\n\n"
        f"Original axiom: {json.dumps(axiom, ensure_ascii=False)}\n"
        f"Previous diagnosis: {diagnosis}\n"
        f"Failure reflection: {fw['reflection']}\n"
        f"Symbol: {fw['symbol']}\n\n"
        'Diagnosis: Why did it fail?\n'
        'Corrected Strategy: Fixed version with better parameters.\n'
        'Confidence: 0.0-1.0\n'
        'Meta-Label: What should change in next backtest?'
    )

    t0 = time.time()
    response = call_llm(DEEP_MODEL, system_prompt, user_prompt, timeout=180)
    elapsed = time.time() - t0
    print(f"    [7B] {elapsed:.1f}s: {response[:100]}...")

    result = extract_json(response)
    if not result:
        return {"diagnosis": diagnosis, "corrected_strategy": None, "confidence": 0, "meta_label": {}}

    return result


def main():
    print("=" * 60)
    print("Ray Self-Correction — Dual-Layer (1.5B + 7B)")
    print("=" * 60)

    ensure_schema()
    failed = get_failed_wisdoms(50)
    print(f"[*] Found {len(failed)} failed wisdoms (sorted by weight)")

    if not failed:
        print("[!] No failed wisdoms. Run --mode learn first.")
        return

    corrections = []
    fast_count = 0
    deep_count = 0

    for fw in failed:
        print(f"\n[*] axiom_id={fw['id']} ({fw['symbol']}) weight={fw['weight']:.2f}")

        # Layer 1: 1.5B fast classification
        layer1 = layer1_fast_classification(fw)
        new_weight = fw['weight'] * layer1['decay_factor']

        # Update weight in DB
        conn = sqlite3.connect(DB_PATH, isolation_level='IMMEDIATE')
        c = conn.cursor()
        c.execute("UPDATE wisdom_logs SET weight = ? WHERE id = ?", (new_weight, fw['id']))
        conn.commit()
        conn.close()
        print(f"    [Weight] {fw['weight']:.2f} -> {new_weight:.2f}")

        if layer1['needs_deep_analysis'] and layer1['confidence'] < 0.5:
            # Layer 2: Only for complex cases
            deep_result = layer2_deep_analysis(fw, layer1['diagnosis'])
            corrections.append({
                "axiom_id": fw['id'],
                "symbol": fw['symbol'],
                "diagnosis": layer1['diagnosis'] + " | " + deep_result.get("diagnosis", ""),
                "corrected_strategy": deep_result.get("corrected_strategy"),
                "confidence": deep_result.get("confidence", 0),
                "meta_label": deep_result.get("meta_label", {}),
                "model_used": "7B"
            })
            deep_count += 1
        else:
            corrections.append({
                "axiom_id": fw['id'],
                "symbol": fw['symbol'],
                "diagnosis": layer1['diagnosis'],
                "corrected_strategy": None,
                "confidence": layer1['confidence'],
                "meta_label": {},
                "model_used": "1.5B"
            })
            fast_count += 1

    # Save all corrections
    conn = sqlite3.connect(DB_PATH, isolation_level='IMMEDIATE')
    c = conn.cursor()
    for corr in corrections:
        c.execute("""
            INSERT INTO wisdom_corrections
                (axiom_id, symbol, diagnosis, corrected_json, confidence, meta_label, model_used)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (corr["axiom_id"], corr["symbol"], corr["diagnosis"],
             json.dumps(corr["corrected_strategy"], ensure_ascii=False) if corr["corrected_strategy"] else "{}",
             corr["confidence"], json.dumps(corr["meta_label"], ensure_ascii=False),
             corr["model_used"]))
    conn.commit()
    conn.close()

    print(f"\n{'='*60}")
    print(f"[*] Self-correction complete!")
    print(f"    1.5B (fast):   {fast_count}")
    print(f"    7B (deep):     {deep_count}")
    print(f"    Total processed: {len(corrections)}")
    print(f"[*] Corrections saved to wisdom_corrections table")

    return {"fast": fast_count, "deep": deep_count, "total": len(corrections)}


if __name__ == "__main__":
    result = main()
    print(f"Result: {result}")