# -*- coding: utf-8 -*-
"""
ray_semantic_distiller.py — 全語意標籤蒸餾（14:00執行）

功能：
1. 讀取歷史失敗日誌 + 當日市場數據
2. 將數值轉化為純語意標籤（禁止具體數字）
3. 蒸餾輸出 semantic_logic_v2.json
4. 供隔日 05:00 ray_distiller_auto.py 燒入 ray-v3.5

語意標籤池：
- [OVERHEATED]     技術過熱（RSI>70 或 BB>90%）
- [OVERSOLD]       技術超賣（RSI<35 或 BB<15%）
- [VOL_PRICE_DIVERGENCE] 量價背離
- [LEADER_CATCH_UP]  龍頭補漲
- [BLACK_SWAN_RISK] 宏觀崩潰風險
- [TRAP]           陷阱（假突破/假跌破）
- [ANTIFRAGILE]    反脆弱（勝率高/波動低）
- [MOMENTUM_DRY]   動能枯竭
- [REGIME_SHIFT]   市場結構轉變
- [TREND_INTACT]   趨勢完整
- [HIGH_CONF]     高信心標籤組合
- [LOW_CONF]       低信心標籤組合
"""

import sys, os, json, time
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
FAULT_REPORT = BASE_DIR / "stores" / "system_defect_report_20260513.md"
OUTPUT_FILE  = BASE_DIR / "stores" / "long_term" / "semantic_logic_v2.json"
LOG_FILE     = BASE_DIR / "stores" / "distillation_log.json"
OLLAMA_URL   = "http://localhost:11434/api/chat"

def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ── 語意標籤池 ──────────────────────────────────────────────
SEMANTIC_TAGS = [
    "[OVERHEATED]", "[OVERSOLD]", "[VOL_PRICE_DIVERGENCE]",
    "[LEADER_CATCH_UP]", "[BLACK_SWAN_RISK]", "[TRAP]",
    "[ANTIFRAGILE]", "[MOMENTUM_DRY]", "[REGIME_SHIFT]",
    "[TREND_INTACT]", "[HIGH_CONF]", "[LOW_CONF]",
    "[RSI_EXTREME]", "[BB_BREAK]", "[KDJ_CROSS]",
    "[TREND_BROKEN]", "[PULLBACK]", "[BREAKOUT_CONFIRMED]"
]

# ── MiniMax 蒸餾（已停用，改用本地 7B）──────────────────────
def distill_semantic(fault_text: str) -> list:
    tags_pool = """  - [OVERHEATED]
  - [OVERSOLD]
  - [VOL_PRICE_DIVERGENCE]
  - [LEADER_CATCH_UP]
  - [BLACK_SWAN_RISK]
  - [TRAP]
  - [ANTIFRAGILE]
  - [MOMENTUM_DRY]
  - [REGIME_SHIFT]
  - [TREND_INTACT]
  - [HIGH_CONF]
  - [LOW_CONF]
  - [RSI_EXTREME]
  - [BB_BREAK]
  - [KDJ_CROSS]
  - [TREND_BROKEN]
  - [PULLBACK]
  - [BREAKOUT_CONFIRMED]"""
    prompt = f"""你是 Ray 全語意蒸餾師。

目標：將以下失敗案例轉化為「語意標籤規則」（純邏輯，無數字）。

[語意標籤池]：
{tags_pool}

[失敗日誌]：
{fault_text}

[蒸餾規則]：
- IF 標籤組合 → THEN 行動（只有 ACT 或 SKIP）
- 禁止任何具體數值（15, 80%, $226...）
- 每條規則必須有邏輯ID（如 SEM_001）

輸出 JSON 陣列：
[
  {{
    "if_tags": ["[TAG_A]", "[TAG_B]"],
    "then_action": "ACT|SKIP",
    "logic_id": "SEM_XXX",
    "master_align": "Taleb|Thorp|Simons|Dalio",
    "priority": 1
  }}
]

只輸出 JSON，無其他文字。"""

    # 直接用本地 7B（已移除 MiniMax API call，避免 key 問題）
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
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
        content = raw.get("message", {}).get("content", "").strip()
        import re
        m = re.search(r'\[[\s\S]*\]', content)
        if m:
            return json.loads(m.group())
    except Exception as e:
        print(f"[Local 7B] ERROR: {e}")

    return []

# ── 主蒸餾流程 ─────────────────────────────────────────────
def main():
    print("=== Ray Semantic Distiller 啟動（14:00）===")
    log = {"started": time.strftime("%Y-%m-%d %H:%M:%S"), "steps": [], "new_rules": 0}

    # Step 1: 讀取失敗日誌
    if FAULT_REPORT.exists():
        with open(FAULT_REPORT, "r", encoding="utf-8") as f:
            fault_text = f.read()[-3000:]
        print(f"[Step 1] 失敗日誌：{len(fault_text)} 字")
        log["steps"].append({"step": "load_faults", "chars": len(fault_text)})
    else:
        fault_text = "[NO_FAULT_DATA]"
        log["steps"].append({"step": "load_faults", "note": "none"})

    # Step 2: LLM 蒸餾語意規則
    print("[Step 2] LLM 語意蒸餾...")
    rules = distill_semantic(fault_text)
    print(f"  蒸餾出 {len(rules)} 條語意規則")
    log["steps"].append({"step": "distill", "rules": len(rules)})

    # Step 3: 寫入 semantic_logic_v2.json
    if rules:
        output = {
            "schema": "semantic_logic_v2",
            "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "version": "2.0",
            "count": len(rules),
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
    print(f"\n供隔日 05:00 ray_distiller_auto.py 燒入 ray-v3.5 ✅")