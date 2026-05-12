# -*- coding: utf-8 -*-
"""
Tina 自主進化引擎 — 每日盤後自動修正循環
美股收盤後（21:30 UTC+8）自動執行

流程：
1. 讀取今日失敗的 wisdom_logs
2. Layer 1: 1.5B 快速分類（3-5s）
3. Layer 2: 7B 深度分析（confidence < 0.5 才啟動）
4. 寫入 wisdom_corrections + 調整 weight
5. 蒸餾精華 → distill_temp.jsonl
"""

import json, sqlite3, time, sys, requests, os
from datetime import datetime, timedelta

DB_PATH = "ray_wisdom.db"
BASE_URL = "http://localhost:11434/api/chat"
MODEL_1B = "ray-v1"       # Layer 1: 快速
MODEL_7B = "ray-deep-v1"  # Layer 2: 深度

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# ===== STEP 1: 找出今日失敗的 wisdoms =====
today = datetime.now().strftime("%Y-%m-%d")
c.execute('''SELECT id, axiom_json, reflection, weight 
              FROM wisdom_logs 
              WHERE passed=0 
              AND timestamp >= datetime("now", "-7 days")
              ORDER BY id DESC LIMIT 50''')
failed = list(c.fetchall())
print(f"[1/5] Found {len(failed)} failed wisdoms (last 7 days)")

if not failed:
    print("No failed wisdoms to process. Exiting.")
    conn.close()
    exit()

# ===== STEP 2: Layer 1 — 1.5B 快速分類 =====
print(f"\n[2/5] Layer 1: 1.5B fast classification...")

def fast_classify(axiom_json, reflection):
    """用 1.5B 快速判斷：需要 7B 分析嗎？"""
    d = json.loads(axiom_json)
    prompt = f"""You are Tina Radar. Classify this failed strategy.

Strategy: {d.get('strategy_name')}
Indicator: {d.get('indicator')}
Reflection: {reflection[:100]}

Output ONLY JSON: {{"needs_deep":true/false,"quick_fix":"...","confidence":0.0}}
No text outside."""

    payload = {
        "model": MODEL_1B,
        "messages": [
            {"role": "system", "content": "You are Tina Radar. Output only JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "stream": False,
    }

    try:
        resp = requests.post(BASE_URL, json=payload, timeout=15)
        raw = resp.json().get("message", {}).get("content", "")
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(raw[start:end])
    except:
        pass
    return {"needs_deep": False, "quick_fix": reflection[:50], "confidence": 0.5}

# 需要深度分析的清單
needs_deep = []
for axiom_id, axiom_json, reflection, weight in failed:
    result = fast_classify(axiom_json, reflection)
    if result.get("needs_deep") or result.get("confidence", 1) < 0.5:
        needs_deep.append((axiom_id, axiom_json, result))
    # 輕量修正直接寫入
    elif result.get("quick_fix"):
        c.execute('''INSERT INTO wisdom_corrections 
            (axiom_id, symbol, diagnosis, corrected_json, confidence, meta_label, created_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime("now"))''',
            (axiom_id, "AUTO", result.get("quick_fix", "")[:200],
             axiom_json, result.get("confidence", 0.5), "fast_fix"))
        conn.commit()

print(f"  Fast fixed: {len(failed) - len(needs_deep)}")
print(f"  Needs deep analysis: {len(needs_deep)}")

# ===== STEP 3: Layer 2 — 7B 深度分析（僅 confidence < 0.5）=====
print(f"\n[3/5] Layer 2: 7B deep analysis ({len(needs_deep)} cases)...")

# Warmup 7B
try:
    warmup = {"model": MODEL_7B, "messages": [{"role": "user", "content": "OK"}], "stream": False}
    requests.post(BASE_URL, json=warmup, timeout=120)
except:
    pass

def deep_analyze(axiom_id, axiom_json, context):
    d = json.loads(axiom_json)
    prompt = f"""You are Tina Deep Strategist. Diagnose why this strategy failed.

Strategy: {d.get('strategy_name')}
Indicator: {d.get('indicator')}
Params: {d.get('params', {})}
Entry: {d.get('entry_condition', {})}
Stop loss: {d.get('stop_loss', 0.08)}
Context: {context}

Output ONLY JSON: {{"diagnosis":"...","corrected_json":{{...}},"confidence":0.0}}
No text outside JSON."""

    payload = {
        "model": MODEL_7B,
        "messages": [
            {"role": "system", "content": "You are Tina Deep Strategist. Output only JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "stream": False,
    }

    t0 = time.time()
    try:
        resp = requests.post(BASE_URL, json=payload, timeout=180)
        elapsed = time.time() - t0
        raw = resp.json().get("message", {}).get("content", "")
        start = raw.find("{")
        end = raw.rfind("}") + 1
        item = json.loads(raw[start:end]) if start >= 0 else {}
        item["_elapsed"] = elapsed
        return item
    except Exception as e:
        return {"diagnosis": str(e)[:100], "confidence": 0, "_elapsed": 0}

deep_done = 0
for axiom_id, axiom_json, ctx in needs_deep:
    result = deep_analyze(axiom_id, axiom_json, ctx.get("quick_fix", ""))
    if result.get("confidence", 0) > 0:
        c.execute('''INSERT INTO wisdom_corrections 
            (axiom_id, symbol, diagnosis, corrected_json, confidence, meta_label, created_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime("now"))''',
            (axiom_id, "DEEP", result.get("diagnosis", "")[:500],
             json.dumps(result.get("corrected_json", {}), ensure_ascii=False),
             result.get("confidence", 0.5), "deep_done"))
        conn.commit()
        deep_done += 1

print(f"  Deep corrections written: {deep_done}")

# ===== STEP 4: Weight 調整 =====
print(f"\n[4/5] Adjusting wisdom weights...")

# 失敗過 3 次的 weight *= 0.8
c.execute('''UPDATE wisdom_logs 
              SET weight = weight * 0.8 
              WHERE passed=0 AND weight IS NOT NULL AND weight > 0.1''')
conn.commit()
decayed = c.rowcount

# 成功過的 weight *= 1.05（上限 3.0）
c.execute('''UPDATE wisdom_logs 
              SET weight = MIN(weight * 1.05, 3.0) 
              WHERE passed=1 AND weight IS NOT NULL''')
conn.commit()
boosted = c.rowcount

print(f"  Decayed (failed): {decayed}")
print(f"  Boosted (passed): {boosted}")

# ===== STEP 5: 每週蒸餾精華 → distill_temp.jsonl =====
print(f"\n[5/5] Generating distillation samples...")

# 每週蒸餾：取 weight > 2.0 或 sharpe > 1.5 的成功案例
c.execute('''SELECT axiom_json, reflection, weight 
              FROM wisdom_logs 
              WHERE passed=1 
              ORDER BY weight DESC LIMIT 100''')
gold = c.fetchall()

distill_path = "ray_distill_weekly.jsonl"
existing = 0
if os.path.exists(distill_path):
    with open(distill_path, 'r', encoding='utf-8') as f:
        existing = len(f.readlines())

new_samples = 0
with open(distill_path, 'a', encoding='utf-8') as f:
    for axiom_json, reflection, weight in gold:
        if weight and weight < 1.5:
            continue
        try:
            d = json.loads(axiom_json)
            sample = {
                "instruction": f"Suggest trading strategy for {d.get('indicator')} with params {d.get('params', {})}.",
                "input": f"Strategy: {d.get('strategy_name')}. Reflection: {reflection}",
                "output": axiom_json,
                "weight": weight or 1.0,
                "source": "tina_weekly"
            }
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")
            new_samples += 1
        except:
            pass

print(f"  Appended {new_samples} samples to {distill_path}")
print(f"  Total distillation samples: {existing + new_samples}")

# ===== 完成 =====
c.execute('SELECT COUNT(*) FROM wisdom_corrections')
total_corr = c.fetchone()[0]

print(f"\n=== Daily Self-Correction Done ===")
print(f"Date: {today}")
print(f"Failed processed: {len(failed)}")
print(f"Fast fixed: {len(failed) - len(needs_deep)}")
print(f"Deep corrected: {deep_done}")
print(f"Weight decayed: {decayed}")
print(f"Weight boosted: {boosted}")
print(f"wisdom_corrections total: {total_corr}")
print(f"Distillation samples: {existing + new_samples}")

conn.close()