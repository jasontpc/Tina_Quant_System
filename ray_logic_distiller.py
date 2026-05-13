# -*- coding: utf-8 -*-
"""
ray_logic_distiller.py — Phase1：失敗歸因蒸餾
每日 14:05（ray_knowledge_distiller.py 之後）

功能：
1. 讀取 wisdom_corrections（67筆）+ wisdom_corrections.web_auto
2. 呼叫 ray-deep-v1 將失敗案例蒸餾成 10 條「絕對禁止行為」
3. 產出 ray_forbidden_rules.json → 提供給 Phase2 Modelfile 寫入

產出：
- ray_forbidden_rules.json
- 同步到 stores/long_term/
"""

import json, os, sqlite3, sys, time, requests
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

AGENTS_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(AGENTS_DIR, "ray_wisdom.db")
WISDOM_STORE = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\stores\long_term"
OUTPUT_PATH = os.path.join(WISDOM_STORE, "ray_forbidden_rules.json")

MODEL_DEEP = "ray-deep-v1"
OLLAMA_URL = "http://localhost:11434/api/chat"

MASTERS = ["Taleb", "Thorp", "Simons", "Connors", "Dalio"]

def load_wisdom():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Failed cases (confidence < 0.7)
    c.execute('''SELECT axiom_id, symbol, diagnosis, corrected_json, confidence, meta_label
                 FROM wisdom_corrections WHERE confidence < 0.7
                 ORDER BY confidence ASC LIMIT 30''')
    failures = [dict(row) for row in c.fetchall()]

    # Web auto rules
    c.execute('''SELECT axiom_id, diagnosis, corrected_json, confidence, meta_label, web_auto
                 FROM wisdom_corrections WHERE web_auto IS NOT NULL LIMIT 20''')
    web_auto = [dict(row) for row in c.fetchall()]

    conn.close()
    return failures, web_auto

def distill_failure_case(failure, all_failures_text):
    """使用 ray-deep-v1 將單筆失敗蒸餾成 If-Then 禁止規則"""
    master = failure.get('master') or 'SYSTEM'
    prompt = f"""你是 {master} 交易大師的邏輯執行器。

以下是一個失敗案例：
- 標的：{failure.get('symbol','UNKNOWN')}
- 診斷：{failure.get('diagnosis','')}
- 信心：{failure.get('confidence', 0)}

請將此案例轉化為 1 條「If-Then 絕對禁止規則」，格式如下：
{{
  "rule": "If [具體條件] Then [禁止/執行動作]",
  "master": "{master}",
  "priority": 1,
  "case_id": "{failure.get('axiom_id','')}"
}}

優先級：1=最高（立即執行），2=標準，3=謹慎參考

只輸出 JSON 陣列，包含 1 個規則。"""
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": MODEL_DEEP,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.15, "top_p": 0.8, "num_predict": 200}
        }, timeout=90)
        raw = resp.json().get("message", {}).get("content", "")
        if raw:
            parsed = json.loads(raw)
            if isinstance(parsed, list) and len(parsed) > 0:
                return parsed[0]
    except Exception as e:
        print(f"    [WARN] distill failed for {failure.get('axiom_id','?')}: {e}")
    return None

def distill_batch(all_failures_text):
    """使用 ray-deep-v1 批量蒸餾 10 條禁止規則"""
    prompt = """你是 Ray 系統的 7B 總參謀長，任務是將失敗案例蒸餾成 4B 必須遵守的「絕對禁止規則」。

## 五大大師框架（你必須引用這些概念）：

【Taleb — 反脆弱 / 肥尾 / 啞鈴 / 尾部對沖】
  - 核心：系統在極端波動下反而變強；常態分布低估極端事件機率
  - 啞鈴：避開中等風險，資金压在「極安全」+「極高槓桿」兩端
  - 尾部對沖：不追求精準預測，確保極端情況不會摧毁系統

【Thorp — 凱利公式 / 二元結局 / 優勢開發 / 紀律】
  - 核心：f* = (bp - q)/b，根據勝率與盈虧比決定下注比例
  - 二元結局：結果只有贏或輸，沒有中間地帶
  - 紀律：每筆交易獨立服從統計紀律，不情緒化

【Simons — Regime Switch / 統計異常 / 趨勢追蹤】
【Connors — 均值回歸 / RSI2 / 彈簧理論】
【Dalio — 多樣化 / 相關性 / 風險分散】

## 失敗案例摘要：
""" + all_failures_text[:3000] + """

## 任務：
分析失敗案例，找出 5 個最常見的失敗模式，對應五位大師的防禦邏輯，生成 10 條「If-Then 禁止規則」。

## 輸出格式（純 JSON 陣列）：
[
  {
    "rule": "If [具體條件] Then [禁止動作]",
    "master": "大師名（必須是 Taleb/Thorp/Simons/Connors/Dalio 之一）",
    "priority": 1-3（1=最高立即執行，2=標準，3=謹慎參考）",
    "taleb_aligned": true/false,
    "taleb_reason": "（taleb_aligned=true必填）明確說明使用了肥尾/啞鈴/尾部對沖/反脆弱哪個概念",
    "thorp_aligned": true/false,
    "thorp_reason": "（thorp_aligned=true必填）明確說明使用了凱利/勝率/二元結局/紀律哪個概念"
  }
]

## 框架強制引用：
  每條規則的 rule 必須從以下 8 個關鍵詞中至少引用 1 個，否則視為框架未對齊：
  Taleb陣營：肥尾、啞鈴、尾部對沖、反脆弱
  Thorp陣營：凱利、勝率、二元結局、紀律

## 嚴格校驗：
  1. rule 必須有具體數值（不能是「波動大」而要是「RSI>75」）
  2. taleb_aligned=true 時，taleb_reason 必須提到「肥尾/啞鈴/尾部對沖/反脆弱」之一
  3. thorp_aligned=true 時，thorp_reason 必須提到「凱利/勝率/二元結局/紀律」之一
  4. 只輸出 JSON，嚴禁其他文字。
"""
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": MODEL_DEEP,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.2, "top_p": 0.85, "num_predict": 600}
        }, timeout=120)
        raw = resp.json().get("message", {}).get("content", "")
        if raw:
            try:
                return json.loads(raw)
            except:
                match = re.search(r'\[[\s\S]+\]', raw)
                if match:
                    return json.loads(match.group())
    except Exception as e:
        print(f"  [ERROR] batch distillation failed: {e}")
    return []
def main():
    print("=" * 60)
    print("Ray Logic Distiller — Phase1 失敗歸因蒸餾")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Load data
    print("\n[1/3] 讀取失敗案例...")
    failures, web_auto = load_wisdom()
    print(f"  失敗案例：{len(failures)} 筆")
    print(f"  Web自動規則：{len(web_auto)} 筆")

    # Build failure text for batch distillation
    all_failures_text = "\n".join([
        f"- [{f.get('symbol','?')}] {f.get('diagnosis','')} (conf={f.get('confidence',0):.2f})"
        for f in failures[:20]
    ])

    # Distill batch (10 rules at once)
    print("\n[2/3] ray-deep-v1 批量蒸餾 10 條禁止規則...")
    rules = distill_batch(all_failures_text)
    print(f"  取得規則：{len(rules)} 條")

    # Individual distillation for each failure case
    print("\n[3/3] 單筆失敗案例蒸餾...")
    for f in failures[:10]:
        rule = distill_failure_case(f, all_failures_text)
        if rule:
            rules.append(rule)

    # Deduplicate by rule text
    seen = set()
    unique_rules = []
    for r in rules:
        key = r.get("rule","")
        if key and key not in seen:
            seen.add(key)
            unique_rules.append(r)

    rules = unique_rules[:10]

    # Assign priority based on master
    for r in rules:
        if r.get("master") == "Taleb" and ("尾部" in r.get("rule","") or "黑天鵝" in r.get("rule","")):
            r["priority"] = 1

    # Save
    os.makedirs(WISDOM_STORE, exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump({"rules": rules, "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"), "count": len(rules)}, f, ensure_ascii=False, indent=2)

    print(f"\n=== 完成 ===")
    print(f"產出：{OUTPUT_PATH}")
    print(f"規則數：{len(rules)}")
    for r in rules[:5]:
        print(f"  [{r.get('master','?')}] P{r.get('priority','?')}: {r.get('rule','')[:70]}")

if __name__ == "__main__":
    main()