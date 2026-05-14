# -*- coding: utf-8 -*-
"""
ray_master_burn.py — 大師人格物理燒錄（每日 05:00 執行）

職責：
1. 讀取 semantic_logic_v2.json（20條語意規則）
2. 整合 axioms_v4.0 Thorp 約束
3. 生成完整 Modelfile（包含 SYSTEM prompt）
4. 執行 ollama create ray-v3.5 物理燒錄

裝飾器：
  @market_safe_guard — 台美股開盤禁區（確保 05:00 執行）
  @ray_singleton     — VRAM 資源鎖

排程：每日 05:00（ray_cron job）
"""

import sys, os, json, time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.utils.ray_guard import ray_singleton, market_safe_guard

BASE_DIR = Path(__file__).parent.parent
SEMANTIC_FILE = BASE_DIR / "stores/long_term/semantic_logic_v2.json"
AXIOMS_FILE   = BASE_DIR / "stores/long_term/axioms_v4.0.json"
LESSONS_FILE  = BASE_DIR / "stores/long_term/lessons.json"
OUTPUT_MODelfILE = BASE_DIR / "Ray-v3.5.Modelfile"
OLLAMA_MODEL   = "ray-v3.5"
BLOB_PATH      = r"C:\Users\USER\.ollama\models\blobs\sha256-2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730"

def load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default if default is not None else {}

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ── 5 大師核心約束（硬編碼）──────────────────────────────
MASTERS_CONSTRAINTS = """
═══════════════════════════════════════════
[THORP — 數學博弈與倉位控管]
═══════════════════════════════════════════
Core: f* = (b×p - q) / b
  p = 勝率（最近20筆滾動）
  q = 1 - p
  b = avg_win / avg_loss
法則：
  f* < 0  → [SKIP] 負期望，絕對禁止
  f* > 0  → min(f*, 0.15) [Hard Cap 15%]
  p < 0.5 → f*≤0 → [SKIP]

═══════════════════════════════════════════
[TALEB — 反脆弱與黑天鵝避險]
═══════════════════════════════════════════
Core: 生存 > 獲利
法則：
  VIX > 30 → [SURVIVAL_MODE] f*=0 全數離場
  [BLACK_SWAN_RISK] → 忽略所有正面信號
  [ANTIFRAGILE] → 允許有限暴露，嚴守停損

═══════════════════════════════════════════
[DALIO — 機器化原則與極度透明]
═══════════════════════════════════════════
Core: 若 LOUPE 無匹配 → [WATCH] 模式
法則：
  進場前：查詢 experience_ledger
  無歷史 → 預設50%部位或 [WATCH]
  勝率>70% → [HIGH_CONF] + APPROVE
  勝率<50% → [STALE_LOGIC] + REJECT

═══════════════════════════════════════════
[SIMONS — 統計套利與體制切換]
═══════════════════════════════════════════
Core: Regime Switch 偵測
法則：
  [REGIME_SHIFT] → 需≥20筆新數據重算 p
  p < 0.05 → 統計顯著，放棄該模式

═══════════════════════════════════════════
[MANDELBROT — 分形幾何與極端風險]
═══════════════════════════════════════════
Core: 厚尾效應修正
法則：
  [FAT_TAIL_ALARM] → Sharpe 打折 20%
  回測勝率 → 需用真實分佈驗證
"""

# ── 產出 Modelfile SYSTEM 區塊 ──────────────────────────
def build_system_block(semantic_rules: list, axioms: list, master_constraints: str) -> str:
    """建構完整的 SYSTEM prompt"""

    # 蒸餾語意規則
    rules_text = []
    for r in semantic_rules[:10]:
        tags = " + ".join(r.get("if_tags", []))
        action = r.get("then_action", "ACT")
        logic_id = r.get("logic_id", "???")
        rules_text.append(f"  [{logic_id}] {tags} → {action}")

    # Thorp Axioms
    axioms_text = []
    for a in axioms[:8]:
        when = a.get("when", "")
        then = a.get("then", "")
        calc = a.get("thorp_calculus", {})
        example = calc.get("example", "")
        axioms_text.append(f"  • {when} → {then} {example}")

    system = f"""[RAY — Thorp Hardcore Quant System v4.0]
你是 Ray，Jo 的專屬量化 Agent。內建 5 位大師靈魂共振。

{master_constraints}

═══════════════════════════════════════════
[SEMANTIC RULES — 語意標籤組合（Top 10）]
═══════════════════════════════════════════
{chr(10).join(rules_text)}

═══════════════════════════════════════════
[THORP AXIOMS — 8條凱利約束]
═══════════════════════════════════════════
{chr(10).join(axioms_text)}

═══════════════════════════════════════════
[LOUPE — 強制查詢]
═══════════════════════════════════════════
進場前必須查詢 experience_ledger.json：
  • 勝率<50%（≥5筆）→ [STALE_LOGIC] + REJECT
  • 勝率>70%（≥5筆）→ [HIGH_CONF] + APPROVE
  • 中間 → CAUTION，部位50%或WATCH

═══════════════════════════════════════════
[決策閘輸出格式]
═══════════════════════════════════════════
## Ray 研判: [標籤組合]
Thorp f* = (b×p-q)/b = XXX → 部位 XX%
LOUPE: [命中 lesson/pattern]
[1] 執行 | [2] 略過 | [3] 深度分析
"""

    return system

# ── 燒錄主流程 ─────────────────────────────────────────
@market_safe_guard
@ray_singleton
def burn_master_genetics():
    """執行大師人格物理燒錄"""
    print("=== Ray 大師人格燒錄啟動（05:00）===")
    print(f"時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    start = time.time()

    # Step 1: 讀取數據
    print("\n[Step 1] 讀取智力資產...")
    semantic = load_json(SEMANTIC_FILE, {})
    axioms   = load_json(AXIOMS_FILE, [])
    lessons  = load_json(LESSONS_FILE, {"lessons": []})

    rules  = semantic.get("rules", [])
    lesson_count = len(lessons.get("lessons", []))
    print(f"  semantic: {len(rules)} 條規則")
    print(f"  axioms: {len(axioms)} 條 Thorp 約束")
    print(f"  lessons: {lesson_count} 筆")

    # Step 2: 建構 SYSTEM prompt
    print("\n[Step 2] 建構 SYSTEM prompt...")
    system_block = build_system_block(rules, axioms, MASTERS_CONSTRAINTS)
    print(f"  SYSTEM 區塊: {len(system_block)} 字")

    # Step 3: 產出 Modelfile
    print("\n[Step 3] 產出 Modelfile...")
    modelfile_content = (
        f"# Ray-v3.5 Modelfile \u2014 Thorp Hardcore v4.0\n"
        f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"# Lessons: {lesson_count} | Rules: {len(rules)} | Axioms: {len(axioms)}\n\n"
        f"FROM {BLOB_PATH}\n\n"
        "TEMPLATE \"\"\"\n"
        "\x3c|im_start|>system\n"
        "{{ .System }}\x3c|im_end|>\n"
        "\x3c|im_start|>user\n"
        "{{ .Prompt }}\x3c|im_end|>\n"
        "\x3c|im_start|>assistant\n\"\"\"\n\n"
        "SYSTEM \"\"\"\n"
        + system_block + "\n\"\"\"\n\n"
        "PARAMETER temperature 0.1\n"
        "PARAMETER num_predict 400\n"
        "PARAMETER top_p 0.8\n"
    )

    with open(OUTPUT_MODelfILE, "w", encoding="utf-8") as f:
        f.write(modelfile_content)
    print(f"  寫入: {OUTPUT_MODelfILE.name} ({len(modelfile_content)} bytes)")

    # Step 4: 執行燒錄
    print("\n[Step 4] 執行 ollama create...")
    import subprocess
    try:
        result = subprocess.run(
            ["ollama", "create", OLLAMA_MODEL, "-f", str(OUTPUT_MODelfILE)],
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode == 0:
            print("  [OK] ollama create ray-v3.5 燒錄成功")
        else:
            print(f"  [WARN] ollama returncode: {result.returncode}")
            print(f"  stdout: {result.stdout[:200]}")
    except Exception as e:
        print(f"  [ERROR] ollama create failed: {e}")

    elapsed = time.time() - start
    print(f"\n=== 完成，耗時 {elapsed:.1f}s ===")
    return {
        "rules": len(rules),
        "axioms": len(axioms),
        "lessons": lesson_count,
        "elapsed_s": round(elapsed, 1)
    }

if __name__ == "__main__":
    result = burn_master_genetics()
    print(f"\n燒錄完成: {result}")