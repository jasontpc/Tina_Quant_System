# -*- coding: utf-8 -*-
"""
ray_knowledge_distiller.py — 第一階段：歷史教訓智力灌頂
每日 14:00 台股盤後執行

功能：
1. 讀取 wisdom_corrections（67筆）+ backtest_reports（1057筆）
2. 調用 7B 參謀（qwen2.5:7b）歸納成 10 條通用交易準則
3. 產出 axioms_v3.5.json 存入 32GB RAM 快取

產出：
- axioms_v3.5.json
- 同步到 C:/Users/USER/.openclaw/workspace/Tina_Quant_System/stores/long_term\\
"""

import json, os, sqlite3, sys, time, requests
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

AGENTS_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(AGENTS_DIR, "ray_wisdom.db")
WISDOM_STORE = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\stores\long_term"
AXIOMS_OUT = os.path.join(WISDOM_STORE, "axioms_v3.5.json")

MODEL_7B = "qwen2.5:7b"
OLLAMA_URL = "http://localhost:11434/api/chat"

def load_data():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # High confidence wisdom
    c.execute('''SELECT axiom_id, symbol, diagnosis, corrected_json, confidence
                 FROM wisdom_corrections ORDER BY confidence DESC LIMIT 22''')
    wisdoms = [dict(row) for row in c.fetchall()]

    # Top backtest strategies
    c.execute('''SELECT strategy_name, symbol, indicator, sharpe_ratio,
                 win_rate, max_drawdown, avg_return, params
                 FROM backtest_reports WHERE sharpe_ratio > 0.5
                 ORDER BY sharpe_ratio DESC LIMIT 15''')
    strategies = [dict(row) for row in c.fetchall()]

    # Failed patterns
    c.execute('''SELECT diagnosis, COUNT(*) as cnt
                 FROM wisdom_corrections WHERE confidence < 0.6
                 GROUP BY substr(diagnosis, 1, 50) ORDER BY cnt DESC LIMIT 10''')
    failures = [dict(row) for row in c.fetchall()]

    conn.close()
    return wisdoms, strategies, failures

def build_distillation_prompt(wisdoms, strategies, failures):
    # Format top wisdoms
    wisdom_text = []
    for w in wisdoms[:15]:
        diag = (w['diagnosis'] or '')[:120]
        conf = w['confidence']
        sym = w['symbol'] or 'N/A'
        wisdom_text.append(f"  [{sym}] conf={conf:.2f}: {diag}")

    # Format top strategies
    strat_text = []
    for s in strategies[:10]:
        strat_text.append(
            f"  {s['strategy_name']}({s['indicator']}) on {s['symbol']}: "
            f"Sharpe={s['sharpe_ratio']:.2f}, WinRate={s.get('win_rate',0):.1f}%, "
            f"MaxDD={s.get('max_drawdown',0):.1f}%"
        )

    prompt = f"""你是交易策略蒸餾專家。請將以下歷史數據歸納成 10 條通用交易準則。

【失敗模式分析】這些教訓不可重犯：
{chr(10).join(wisdom_text[:8])}

【最優策略】（Sharpe > 0.5，歷史驗證有效）：
{chr(10).join(strat_text)}

請輸出一個 JSON陣列，包含 10 條準則，格式如下：
[
  {{
    "id": 1,
    "axiom": "準則內容（中文，20-50字）",
    "type": "entry|exit|risk|position|filter",
    "source": "wisdom|backtest|both",
    "confidence": 0.0-1.0,
    "taleb_aligned": true/false,
    "thorp_aligned": true/false,
    "example": "適用的典型情境"
  }}
]

規則：
- 每條準則必須有具體數值（RSI門檻、Sharpe數字、天數限制）
- 要包含「追高陷阱」的明確警告
- 要包含「持有天數上限」的明確數值
- Taleb 對齊：涉及肥尾保護、波動率異常時的行動
- Thorp 對齊：涉及凱利公式、勝率與盈虧比
- 只輸出 JSON，不要其他文字
"""
    return prompt

def call_7b(prompt, timeout=90):
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": MODEL_7B,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.2, "top_p": 0.85}
        }, timeout=timeout)
        return resp.json().get("message", {}).get("content", "")
    except Exception as e:
        return f"ERROR: {e}"

def parse_axioms(raw):
    # Extract JSON from response
    try:
        # Try direct parse
        return json.loads(raw)
    except:
        pass
    # Try to extract from markdown
    import re
    match = re.search(r'\[[\s\S]+\]', raw)
    if match:
        try:
            return json.loads(match.group())
        except:
            pass
    return None

def save_axioms(axioms):
    os.makedirs(WISDOM_STORE, exist_ok=True)
    with open(AXIOMS_OUT, 'w', encoding='utf-8') as f:
        json.dump(axioms, f, ensure_ascii=False, indent=2)
    print(f"  Saved: {AXIOMS_OUT} ({len(axioms)} axioms)")

# ── Main ──────────────────────────────────────────────────────────────────────
print("=" * 60)
print("Ray 第一階段：歷史教訓智力灌頂")
print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

print("\n[1/4] 載入資料...")
wisdoms, strategies, failures = load_data()
print(f"  wisdom_corrections: {len(wisdoms)} 筆")
print(f"  backtest_reports:   {len(strategies)} 筆（Sharpe>0.5）")

print("\n[2/4] 建立蒸餾 Prompt...")
prompt = build_distillation_prompt(wisdoms, strategies, failures)
print(f"  Prompt 長度: {len(prompt)} 字元")

print("\n[3/4] 呼叫 7B 參謀蒸餾...")
print(f"  模型: {MODEL_7B}")
raw = call_7b(prompt, timeout=120)
axioms = parse_axioms(raw)

if axioms:
    print(f"  ✅ 成功解析 {len(axioms)} 條準則")
    save_axioms(axioms)

    # Print summary
    print("\n【蒸餾結果摘要】")
    for a in axioms:
        print(f"  [{a['id']}] {a['axiom'][:50]} ({a['type']})")
else:
    print("  ⚠️ 無法解析，直接寫入原始參考")
    # Fallback: save raw
    fallback = {
        "fallback": True, "raw_length": len(raw),
        "sample": raw[:500] if raw else "empty"
    }
    os.makedirs(WISDOM_STORE, exist_ok=True)
    with open(AXIOMS_OUT.replace('.json', '_raw.json'), 'w', encoding='utf-8') as f:
        json.dump(fallback, f, ensure_ascii=False)

print("\n[4/4] 同步到 Tina stores...")
# Also copy to RAM-accessible location
ram_cache = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\stores\long_term"
os.makedirs(ram_cache, exist_ok=True)
if axioms:
    with open(os.path.join(ram_cache, "axioms_v3.5.json"), 'w', encoding='utf-8') as f:
        json.dump(axioms, f, ensure_ascii=False, indent=2)
    print(f"  ✅ Synced to {ram_cache}")

print("\n=== 第一階段完成 ===")
print(f"Axioms: {AXIOMS_OUT}")
print(f"Model: {MODEL_7B} used for distillation")
