# -*- coding: utf-8 -*-
"""
ray_decision_gate.py — Ray 決策閘門（4B指揮官實戰版）

整合 SOUL.md v3.5 + Jo 的整合藍圖：
  1. @market_safe_guard — 確保開盤期間不被維護腳本干擾
  2. @ray_singleton — 鎖定 VRAM，絕對優先
  3. LOUPE 強制查詢 — 每次決策前必讀 experience_ledger.json
  4. 標籤化日誌寫入 — 透過 @io_singleton 確保原子化

用法：
  from scripts.utils.ray_guard import market_safe_guard, ray_singleton, io_singleton

  @market_safe_guard
  @ray_singleton
  def run_decision_gate(stock_id, tags, twii_rsi):
      ...
"""

import sys
sys.path.insert(0, r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
from scripts.utils.ray_guard import market_safe_guard, ray_singleton, io_singleton

import json
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
LEDGER_FILE = BASE_DIR / "stores" / "long_term" / "experience_ledger.json"
DECISION_LOG = BASE_DIR / "stores" / "short_term" / "decision_log.json"
GUARDIAN_RULES = BASE_DIR / "stores" / "long_term" / "ray_forbidden_rules.json"

def load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default if default is not None else {}

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ── LOUPE 專家查詢 ─────────────────────────────────────────────
def loupe_query(symbol: str) -> dict:
    """
    每次決策前必讀 experience_ledger.json
    回傳：
      - stock_win_rate: 勝率
      - stock_trades: 交易筆數
      - verdict: APPROVE / CAUTION / REJECT
      - tags: ["[STALE_LOGIC]"] if low
    """
    ledger = load_json(LEDGER_FILE, {"entries": []})
    entries = ledger.get("entries", [])

    sym_entries = [e for e in entries if e.get("symbol") == symbol and e.get("result") in ["win", "loss"]]
    if not sym_entries:
        return {"win_rate": None, "trades": 0, "verdict": "APPROVE", "signal": None}

    wins = sum(1 for e in sym_entries if e.get("result") == "win")
    win_rate = wins / len(sym_entries)

    # 判定
    if len(sym_entries) >= 5 and win_rate < 0.50:
        verdict = "REJECT"
        signal = "[STALE_LOGIC]"
    elif win_rate >= 0.70:
        verdict = "APPROVE"
        signal = "[HIGH_CONF]"
    else:
        verdict = "CAUTION"
        signal = "[NEUTRAL]"

    return {
        "win_rate": round(win_rate * 100, 1),
        "trades": len(sym_entries),
        "verdict": verdict,
        "signal": signal,
        "entries": sym_entries[-5:],  # 最近5筆
    }

# ── 禁止規則查詢 ─────────────────────────────────────────────
def check_forbidden(symbol: str, tags: list) -> str | None:
    """檢查 ray_forbidden_rules.json，若命中則 REJECT"""
    rules_data = load_json(GUARDIAN_RULES, {"rules": []})
    for rule in rules_data.get("rules", []):
        rule_text = rule.get("rule", "")
        # 簡單關鍵字匹配（TODO: 未來用 NLP 更好）
        forbidden_keywords = ["RSI>80", "RSI>85", "RSI>90", "distance<5", "stop_loss>2", "EMA distance>40"]
        for kw in forbidden_keywords:
            if kw in rule_text and any(t in str(tags) for t in ["[OVERHEATED]", "[RSI_EXTREME]"]):
                return rule.get("master", "RULE")
    return None

# ── 專家委員會打分 ─────────────────────────────────────────────
def committee_score(rsi: float, twii_rsi: float, score: int) -> dict:
    """模擬三方投票：量化35% / 開發35% / 風控30%"""
    quant = max(0, 30 - max(0, rsi - 60))  # RSI>60 開始扣分
    risk = max(0, 30 - (twii_rsi - 70))   # TWII RSI>70 開始扣分
    stability = max(0, 35 - (0 if score >= 3 else 15))  # score<3 扣分

    total = quant * 0.35 + stability * 0.35 + risk * 0.30

    if total >= 25:
        decision = "APPROVE"
    elif total >= 15:
        decision = "CAUTION"
    else:
        decision = "REJECT"

    return {
        "total": round(total, 1),
        "decision": decision,
        "quant": round(quant, 1),
        "stability": round(stability, 1),
        "risk": round(risk, 1),
    }

# ── 決策閘主程式 ─────────────────────────────────────────────
@market_safe_guard
@ray_singleton
def run_decision_gate(stock_id: str, tags: list, twii_rsi: float, score: int, price: float):
    """
    4B 指揮官決策閘
    流程：
      1. LOUPE 查詢（歷史勝率）
      2. 禁止規則檢查
      3. 專家委員會投票
      4. 顯示決策選單
      5. 等待 Jo 輸入 [1-4]
      6. 執行並寫入日誌
    """
    print()
    print("=" * 55)
    print(f"     Ray 決策閘 — 4B 指揮官實戰")
    print("=" * 55)

    # 1. LOUPE 查詢
    loupe = loupe_query(stock_id)
    print(f"\n📊 LOUPE 專家系統查詢")
    if loupe["win_rate"] is not None:
        print(f"   {stock_id} | 歷史勝率: {loupe['win_rate']}% ({loupe['trades']}筆)")
        print(f"   判定: {loupe['verdict']} {loupe['signal'] or ''}")
    else:
        print(f"   {stock_id} | 無歷史記錄")

    # 2. 禁止規則檢查
    blocked_by = check_forbidden(stock_id, tags)
    if blocked_by:
        print(f"\n🚫 [BLOCKED] 命中禁止規則（{blocked_by}）")
        print(f"   自動 REJECT，跳過決策選單")
        return {"action": "BLOCKED", "reason": f"forbidden_rule:{blocked_by}"}

    # 3. 專家委員會
    rsi_cur = float(tags[0].replace("[RSI_", "").replace("]", "")[:2]) if any("RSI" in t for t in tags) else 55.0
    comm = committee_score(rsi_cur, twii_rsi, score)
    print(f"\n👥 專家委員會投票")
    print(f"   量化分析: {comm['quant']:.1f}/30")
    print(f"   策略穩定: {comm['stability']:.1f}/35")
    print(f"   風控評估: {comm['risk']:.1f}/30")
    print(f"   ─────────────────")
    print(f"   總分: {comm['total']}/8 → {comm['decision']}")

    # 4. 觸發標籤
    tag_str = "".join(tags)
    action_map = {
        "APPROVE": "🚀 執行（建議開倉）",
        "CAUTION": "⚠️ 觀望（小倉位或略過）",
        "REJECT": "✋ 否決（不建議進場）",
    }
    print(f"\n📍 觸發標籤: {tag_str}")
    print(f"🚀 行動建議: {action_map.get(comm['decision'], '---')}")

    # 5. 決策選單
    print()
    print("-" * 55)
    print("🤖 Ray 指揮官決策選單：")
    print("[1] ⚡ 執行：立即推送交易指令並寫入 MEMORY.md")
    print("[2] ✋ 略過：不執行操作，僅紀錄本次略過邏輯")
    print("[3] 🔍 深度：卸載 4B，啟動 7B 進行失敗歸因與蒸餾")
    print("[4] 🛠️ 修正：手動輸入邏輯，將其標籤化存入明日固化庫")
    print("-" * 55)

    # 6. 寫入決策日誌
    decision_record = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "stock": stock_id,
        "tags": tags,
        "twii_rsi": twii_rsi,
        "score": score,
        "price": price,
        "loupe": {"verdict": loupe["verdict"], "win_rate": loupe["win_rate"]},
        "committee": comm,
        "verdict": comm["decision"],
    }

    # I/O 安全寫入
    @io_singleton
    def write_decision_log():
        log_entries = load_json(DECISION_LOG, [])
        log_entries.append(decision_record)
        # 只保留最近100筆
        save_json(DECISION_LOG, log_entries[-100:])

    write_decision_log()
    print(f"\n📝 決策日誌已寫入（{len(tags)} 標籤）")

    return {
        "verdict": comm["decision"],
        "loupe": loupe,
        "committee": comm,
        "record": decision_record,
    }

# ── CLI 測試 ─────────────────────────────────────────────
if __name__ == "__main__":
    test_cases = [
        ("2458", ["[VOL_BREAKOUT]", "[RSI_63]"], 73.0, 3, 149.0),
        ("3034", ["[OVERHEATED]", "[RSI_68]"], 73.0, 1, 486.5),
        ("2330", ["[RSI_59]"], 73.0, 2, 2235.0),
    ]

    for stock_id, tags, twii_rsi, score, price in test_cases:
        print()
        result = run_decision_gate(stock_id, tags, twii_rsi, score, price)
        print(f"結果: {result['verdict']}")
        print()

    print("=== 測試完成 ===")