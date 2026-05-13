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

TALEB_FRAMEWORK = """
大師：Nassim Taleb（你需要熟悉這個框架，因為它決定了哪些規則算「對齊」）
核心概念（你必須使用這些詞，不能自己發明）：
  - 反脆弱（Antifragile）：系統在極端波動下反而變強
  - 肥尾（Fat Tail）：常態分布低估極端事件機率
  - 啞鈴策略（Barbell）：避開中等風險，資金压在「極安全」+「極高槓桿」兩端
  - 尾部對沖（Tail Hedge）：不追求精準預測，確保極端情況不會摧毁系統
  - 適用場景：RSI 異常、機構大規模拋售、肥尾事件後的市場恢復
"""

THORP_FRAMEWORK = """
大師：Edward Thorp（你需要熟悉這個框架，因為它決定了哪些規則算「對齊」）
核心概念（你必須使用這些詞，不能自己發明）：
  - 凱利公式（Kelly Criterion）：f* = (bp - q)/b，根據勝率與盈虧比決定下注比例
  - 二元結局（Binary Outcome）：結果只有贏或輸，沒有中間地帶
  - 優勢開發（Edge Exploitation）：數學優勢重複執行可累積獲利
  - 紀律（Discipline）：每筆交易獨立服從統計紀律，不情緒化
  - 適用場景：計算期望值、控制單筆虧損上限、遵守策略止損
"""


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

    # Format failures
    fail_text = []
    for f in failures[:8]:
        fail_text.append(f"  失敗模式：{f['diagnosis'][:60]}（出現 {f['cnt']} 次）")

    prompt = f"""你是交易策略蒸餾專家。請將以下歷史數據歸納成 10 條通用交易準則。

【失敗模式】（這些教訓不可重犯）：
{chr(10).join(fail_text)}

【高信心度智慧】（已確認的判斷錯誤）：
{chr(10).join(wisdom_text[:8])}


【最優策略】（Sharpe > 0.5，歷史驗證有效）：
{chr(10).join(strat_text)}

{TALEB_FRAMEWORK}

{THORP_FRAMEWORK}

請輸出一個 JSON陣列，包含 10 條準則，格式如下：
[
  {{
    "id": 1,
    "when": "觸發條件（具體數值：RSI>70、持有>20天等）",
    "then": "具體行動（止損/降倉/觀望）",
    "axiom": "一句話總結（15-30字）",
    "type": "entry|exit|risk|position|filter",
    "source": "wisdom|backtest|both",
    "confidence": 0.0-1.0（依據下方數據質量公式計算，禁止主觀猜測）,    
    "reasoning": "為什麼這條規則存在？依據哪些數據？",
    "taleb_aligned": true/false（此規則是否呼應 Taleb 框架？）,
    "taleb_reason": "（taleb_aligned=true時必填）明確說出使用了「肥尾/啞鈴/尾部對沖/反脆弱」哪個概念及其原因，若沒有明確引用則 taleb_aligned 只能為 false",
    "thorp_aligned": true/false（此規則是否呼應 Thorp 框架？）,
    "thorp_reason": "（thorp_aligned=true時必填）明確說出使用了「凱利/勝率/二元結局/紀律」哪個概念及其原因，若沒有明確引用則 thorp_aligned 只能為 false"
  }}
]

【信心度計算公式】（你必須嚴格執行，不得自己發明數字）：
  confidence = 0.50 （固定 base）
  + 0.08（wisdoms來源 ≥ 15筆） 或 +0.04（8-14筆） 或 +0.00（<8筆）
  + 0.08（backtest來源 ≥ 10筆） 或 +0.04（5-9筆） 或 +0.00（<5筆）
  + 0.10（avg_sharpe > 1.5）或 +0.06（1.0-1.5）或 +0.03（0.5-1.0）或 +0.00（<0.5）
  + 0.05（失敗模式 ≥ 5次）
  最終上限 0.90，下限 0.50
  若數據完全不足以支持一條規則，請回傳 confidence: 0.30 而非亂填

【嚴格校驗規則】（不通過以下任一條件，規則無效）：
  1. when 必須包含具體數值或明確條件（如 RSI>70, 持有>20天, 跌幅>15%）
  2. taleb_aligned=true 時，taleb_reason 必須明確提到「肥尾」「啞鈴」「尾部對沖」「反脆弱」之一
  3. thorp_aligned=true 時，thorp_reason 必須明確提到「凱利」「勝率」「二元結局」「紀律」之一
  4. 不得使用模糊形容詞：當「波動大」必須具體成「RSI>75」；當「长期持倉」必須具體成「持有>60交易日」

【框架強制引用】：每條規則的 when 條件，必須從以下 8 個關鍵詞中至少引用 1 個，否則視為框架未對齊：
  Taleb陣營：肥尾、啞鈴、尾部對沖、反脆弱
  Thorp陣營：凱利、勝率、二元結局、紀律

  只輸出 JSON，不要任何其他文字。
"""
    return prompt

def call_7b(prompt, timeout=150):
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": MODEL_7B,
            "messages": [{"role": "system", "content": "你是頂級量化交易專家，擅长从历史数据中提炼交易准则。输出必须严格遵循WHEN/THEN格式，否则视为无效。"}, {"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.3, "top_p": 0.8}
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

def recalculate_confidence(axiom, n_wisdoms, n_backtests, n_failures_count, avg_sharpe):
    """"依據數據質量重新計算信心度，防止模型給出整齊數字"""
    base = 0.50
    if n_wisdoms >= 15: base += 0.08
    elif n_wisdoms >= 8: base += 0.04
    if n_backtests >= 10: base += 0.08
    elif n_backtests >= 5: base += 0.04
    if avg_sharpe > 1.5: base += 0.10
    elif avg_sharpe > 1.0: base += 0.06
    elif avg_sharpe > 0.5: base += 0.03
    if n_failures_count >= 5: base += 0.05
    return min(max(base, 0.50), 0.90)

def save_axioms(axioms, n_wisdoms=0, n_backtests=0, n_failures_count=0, avg_sharpe=0.0):
    os.makedirs(WISDOM_STORE, exist_ok=True)
    # Recalculate confidence for each axiom
    for a in axioms:
        a['confidence'] = recalculate_confidence(a, n_wisdoms, n_backtests, n_failures_count, avg_sharpe)
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
    avg_sharpe = sum(s['sharpe_ratio'] for s in strategies) / len(strategies) if strategies else 0
    n_failures_count = sum(f['cnt'] for f in failures) if failures else 0
    save_axioms(axioms, n_wisdoms=len(wisdoms), n_backtests=len(strategies), n_failures_count=n_failures_count, avg_sharpe=avg_sharpe)

    # Print detailed summary
    print("\n【蒸餾結果摘要】")
    taleb_count = sum(1 for a in axioms if a.get('taleb_aligned', False))
    thorp_count = sum(1 for a in axioms if a.get('thorp_aligned', False))
    for a in axioms:
        print(f"  [{a['id']}] {a.get('when','')[:40]} → {a.get('then','')[:40]}")
        print(f"       [{a['type']}] conf={a.get('confidence',0):.2f} | Taleb={a.get('taleb_aligned',False)} Thorp={a.get('thorp_aligned',False)}")
    print(f"\n  📊 大師對齊統計：Taleb={taleb_count}/10, Thorp={thorp_count}/10")
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
