# -*- coding: utf-8 -*-
"""
Tina 自主進化引擎 — 每日盤後自動修正循環
美股收盤後（21:30 UTC+8）自動執行

流程：
1. 讀取今日失敗的 wisdom_logs
2. Layer 1: ray-v1 快速分類（走 Router Layer 1 → ray-v1 本地）
3. Layer 2: MiniMax 深度分析（走 Router Layer 2 → MiniMax雲端）
4. 寫入 wisdom_corrections + 調整 weight
5. 蒸餾精華 → distill_temp.jsonl

2026-05-12: All LLM calls go through llm_router.py (no direct Ollama)
"""

import json, sqlite3, time, sys, os
from datetime import datetime, timedelta

DB_PATH = "ray_wisdom.db"

# ── Router 導入 ──────────────────────────────────────────────
try:
    from llm_router import get_router
    ROUTER = get_router()
    HAS_ROUTER = True
except ImportError:
    ROUTER = None
    HAS_ROUTER = False

BASE_URL = "http://localhost:11434/api/chat"
MODEL_1B = "ray-deep-v1"       # Jo 指定全本地走 ray-deep-v1
MODEL_7B = "ray-deep-v1"  # Jo 指定統一走 ray-deep

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# ════════════════════════════════════════════════════════════
# STEP 1: 找出失敗的 wisdoms
# ════════════════════════════════════════════════════════════
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

# ════════════════════════════════════════════════════════════
# STEP 2: Layer 1 — ray-v1 快速分類（走 Router Layer 1）
# ════════════════════════════════════════════════════════════
print(f"\n[2/5] Layer 1: ray-v1 fast classification...")

def _ollama_fallback(model, prompt, timeout=30):
    """降級：直接走 Ollama（當 Router 不可用時）"""
    import requests
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "temperature": 0.1,
    }
    try:
        resp = requests.post(BASE_URL, json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "")
    except Exception as e:
        return ""

def fast_classify(axiom_json, reflection):
    """用 ray-v1 快速判斷：需要深度分析嗎？"""
    d = json.loads(axiom_json)
    prompt = (
        f"Classify this failed strategy.\n"
        f"Strategy: {d.get('strategy_name')}\n"
        f"Indicator: {d.get('indicator')}\n"
        f"Reflection: {reflection[:100]}\n\n"
        'Output ONLY JSON: {"needs_deep":true/false,"quick_fix":"...","confidence":0.0}'
    )

    if ROUTER and HAS_ROUTER:
        try:
            return ROUTER.fast(prompt=prompt)
        except Exception as e:
            print(f"    [Router.fast failed: {e}], falling back to Ollama")
            raw = _ollama_fallback(MODEL_1B, prompt, timeout=15)
    else:
        raw = _ollama_fallback(MODEL_1B, prompt, timeout=15)

    # 解析 JSON
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(raw[start:end])
        except:
            pass
    return {"needs_deep": False, "quick_fix": reflection[:50], "confidence": 0.5}

needs_deep = []
for axiom_id, axiom_json, reflection, weight in failed:
    result = fast_classify(axiom_json, reflection)
    if isinstance(result, str):
        # Router 回傳字串，嘗試解析
        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            result = json.loads(result[start:end]) if start >= 0 else {"needs_deep": False}
        except:
            result = {"needs_deep": False}

    if result.get("needs_deep") or result.get("confidence", 1) < 0.5:
        needs_deep.append((axiom_id, axiom_json, result))
    elif result.get("quick_fix"):
        c.execute('''INSERT INTO wisdom_corrections 
            (axiom_id, symbol, diagnosis, corrected_json, confidence, meta_label, created_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime("now"))''',
            (axiom_id, "AUTO", result.get("quick_fix", "")[:200],
             axiom_json, result.get("confidence", 0.5), "fast_fix"))
        conn.commit()

print(f"  Fast fixed: {len(failed) - len(needs_deep)}")
print(f"  Needs deep analysis: {len(needs_deep)}")

# ════════════════════════════════════════════════════════════
# STEP 3: Layer 2 — MiniMax 深度分析（走 Router Layer 2）
# ════════════════════════════════════════════════════════════
print(f"\n[3/5] Layer 2: MiniMax deep analysis ({len(needs_deep)} cases)...")

def deep_analyze(axiom_id, axiom_json, context):
    d = json.loads(axiom_json)
    prompt = (
        f"Diagnose why this strategy failed.\n\n"
        f"Strategy: {d.get('strategy_name')}\n"
        f"Indicator: {d.get('indicator')}\n"
        f"Params: {d.get('params', {})}\n"
        f"Entry: {d.get('entry_condition', {})}\n"
        f"Stop loss: {d.get('stop_loss', 0.08)}\n"
        f"Context: {context}\n\n"
        'Output ONLY JSON: {"diagnosis":"...","corrected_json":{...},"confidence":0.0}'
    )

    t0 = time.time()

    if ROUTER and HAS_ROUTER:
        try:
            raw = ROUTER.deep(prompt=prompt)
            elapsed = time.time() - t0
            print(f"    [MiniMax] {elapsed:.1f}s")
        except Exception as e:
            print(f"    [Router.deep failed: {e}], falling back to Ollama 7B")
            raw = _ollama_fallback(MODEL_7B, prompt, timeout=180)
    else:
        raw = _ollama_fallback(MODEL_7B, prompt, timeout=180)

    # 解析 JSON
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            item = json.loads(raw[start:end])
            item["_elapsed"] = time.time() - t0
            return item
        except:
            pass
    return {"diagnosis": "parse_failed", "confidence": 0, "_elapsed": 0}

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

# ════════════════════════════════════════════════════════════
# STEP 4: Weight 調整
# ════════════════════════════════════════════════════════════
print(f"\n[4/5] Adjusting wisdom weights...")

c.execute('''UPDATE wisdom_logs 
              SET weight = weight * 0.8 
              WHERE passed=0 AND weight IS NOT NULL AND weight > 0.1''')
conn.commit()
decayed = c.rowcount

c.execute('''UPDATE wisdom_logs 
              SET weight = MIN(weight * 1.05, 3.0) 
              WHERE passed=1 AND weight IS NOT NULL''')
conn.commit()
boosted = c.rowcount

print(f"  Decayed (failed): {decayed}")
print(f"  Boosted (passed): {boosted}")

# ════════════════════════════════════════════════════════════
# STEP 5: 每週蒸餾精華 → distill_temp.jsonl
# ════════════════════════════════════════════════════════════
print(f"\n[5/5] Generating distillation samples...")

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

# ════════════════════════════════════════════════════════════
# 完成
# ════════════════════════════════════════════════════════════
c.execute('SELECT COUNT(*) FROM wisdom_corrections')
total_corr = c.fetchone()[0]

print(f"\n{'='*50}")
print(f"=== Daily Self-Correction Done ===")
print(f"Date: {today}")
print(f"Failed processed: {len(failed)}")
print(f"Fast fixed: {len(failed) - len(needs_deep)}")
print(f"Deep corrected: {deep_done}")
print(f"Weight decayed: {decayed}")
print(f"Weight boosted: {boosted}")
print(f"wisdom_corrections total: {total_corr}")
print(f"Distillation samples: {existing + new_samples}")
print(f"Router: {'ACTIVE' if (ROUTER and HAS_ROUTER) else 'NOT AVAILABLE (using Ollama fallback)'}")
print(f"{'='*50}")

conn.close()