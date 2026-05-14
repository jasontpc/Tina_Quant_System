# -*- coding: utf-8 -*-
"""
ray_logic_distiller.py — 失敗歸因蒸餾（每日 14:05）
職責：讀取昨日/今日失敗交易，分析失敗根因，更新禁止規則

使用 @ray_singleton 裝飾器，確保 VRAM 独占
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# ── 路徑設定 ────────────────────────────────────────────────────────────────
BASE_DIR = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
STORES_DIR = BASE_DIR / "stores"
LONG_TERM = STORES_DIR / "long_term"
SHORT_TERM = STORES_DIR / "short_term"
WISDOM_FILE = LONG_TERM / "wisdom_corrections.json"
AXIOMS_FILE = LONG_TERM / "axioms_v3.5.json"
FORBIDDEN_FILE = LONG_TERM / "ray_forbidden_rules.json"
PORTFOLIO_DIR = STORES_DIR / "portfolio"
POSITIONS_FILE = PORTFOLIO_DIR / "positions.json"
TRADES_LOG = PORTFOLIO_DIR / "trades.log"

# 引用 VRAM 守護
sys.path.insert(0, str(BASE_DIR / "scripts" / "utils"))
from ray_guard import ray_singleton

# ── 時間設定 ────────────────────────────────────────────────────────────────
NOW = datetime.now()
TODAY_STR = NOW.strftime("%Y-%m-%d")
YESTERDAY_STR = (NOW - timedelta(days=1)).strftime("%Y-%m-%d")

# ── 工具函式 ───────────────────────────────────────────────────────────────

def load_json(path, default=None):
    """安全讀取 JSON"""
    if path is None:
        return default or {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default or {}


def save_json(path, data):
    """安全寫入 JSON"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def ollama_run(model, prompt, timeout=60):
    """呼叫 Ollama，回傳純文字"""
    try:
        result = subprocess.run(
            ["ollama", "run", model],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8"
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None


def extract_json_block(text):
    """從文字中取出 ```json ... ``` 區塊"""
    try:
        start = text.find("```json") + 7
        end = text.find("```", start)
        if start > 6 and end > start:
            return json.loads(text[start:end].strip())
    except Exception:
        pass
    return None


def get_recent_trades(days=3):
    """讀取近 N 天失敗交易記錄"""
    trades = []
    if not TRADES_LOG.exists():
        return trades
    try:
        with open(TRADES_LOG, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # 格式：DATE|SYMBOL|ACTION|PRICE|PNL|PNL_PCT|RSI|DAYS|HOLD
                parts = line.split("|")
                if len(parts) >= 6:
                    date_str = parts[0]
                    try:
                        pnl_pct = float(parts[5].replace("%", ""))
                        if date_str >= YESTERDAY_STR and pnl_pct < 0:
                            trades.append({
                                "date": date_str,
                                "symbol": parts[1],
                                "action": parts[2],
                                "price": parts[3],
                                "pnl": parts[4],
                                "pnl_pct": pnl_pct,
                                "rsi": parts[6] if len(parts) > 6 else "N/A",
                                "days": parts[7] if len(parts) > 7 else "N/A",
                            })
                    except ValueError:
                        continue
    except Exception:
        pass
    return trades


def get_positions():
    """讀取目前持倉"""
    return load_json(POSITIONS_FILE, [])


def get_axioms():
    """讀取當前 Axioms"""
    return load_json(AXIOMS_FILE, [])


def get_wisdom():
    """讀取 wisdom_corrections"""
    return load_json(WISDOM_FILE, {"rules": [], "insights": []})


def get_forbidden():
    """讀取禁止規則"""
    return load_json(FORBIDDEN_FILE, {"rules": [], "metadata": {}})


# ── 核心邏輯 ────────────────────────────────────────────────────────────────

@ray_singleton
def run_failure_attribution():
    """
    失敗歸因蒸餾 — 14:05 任務
    流程：
      1. 讀取近3天失敗交易
      2. 讀取持倉現況
      3. 呼叫 4B 模型分析失敗根因
      4. 輸出新的禁止規則到 ray_forbidden_rules.json
      5. 更新 wisdom_corrections
    """
    print(f"\n{'='*50}")
    print(f"🔍 [失敗歸因] {TODAY_STR} 14:05 蒸餾開始")
    print(f"{'='*50}\n")

    # Step 1: 收集失敗交易
    failed_trades = get_recent_trades(days=3)
    positions = get_positions()
    axioms = get_axioms()
    forbidden = get_forbidden()

    # Step 2: 讀取昨日收盤數據（用 positions 的 cost/現價）
    open_positions = [p for p in positions if p.get("status") in ("HOLD", "MONITOR")]
    loss_positions = [p for p in open_positions if float(p.get("pnl_pct", 0)) < 0]

    # Step 3: 建構失敗交易摘要
    failed_summary = []
    for t in failed_trades:
        failed_summary.append(
            f"- {t['date']} {t['symbol']} {t['action']}@{t['price']} "
            f"PNL:{t['pnl']}({t['pnl_pct']}%) RSI:{t['rsi']} 持有:{t['days']}天"
        )

    loss_summary = []
    for p in loss_positions:
        loss_summary.append(
            f"- {p['symbol']} 成本:{p['cost']} 現價:{p['price']} "
            f"PNL:{p['pnl']}({p['pnl_pct']}%) RSI:{p.get('rsi','N/A')}"
        )

    # Step 4: 讀取近5條禁止規則（避免重複）
    recent_forbidden = forbidden.get("rules", [])[-5:]
    forbidden_symbols = {r.get("symbol") for r in recent_forbidden if r.get("symbol")}

    # Step 5: 呼叫 Ollama 失敗歸因
    axiom_list = "\n".join([f"{i+1}. {a['text']}" for i, a in enumerate(axioms)]) or "（空）"

    prompt = f"""你是一個交易失敗歸因分析師。請分析以下失敗案例，找出根本原因。

【當前 Axioms 框架】
{axiom_list}

【近3天失敗交易】
{failed_summary[:10] if failed_summary else "（無失敗交易）"}

【目前虧損持倉】
{loss_summary if loss_summary else "（無虧損持倉）"}

【近期禁止規則（避免重複）】
{recent_forbidden[:5] if recent_forbidden else "（無）"}

請產出 JSON：
```json
{{
  "analysis": "失敗模式描述（1-2句）",
  "root_causes": ["原因1", "原因2"],
  "new_rules": [
    {{
      "symbol": "代碼或ALL",
      "rule": "具體新規則",
      "reason": "理由",
      "severity": "high/medium/low"
    }}
  ],
  "wisdom_update": "給操作者的 insight（1句）"
}}
```"""

    raw = ollama_run("qwen3.5:4b-instruct-q4_K_S", prompt, timeout=90)
    result = extract_json_block(raw) if raw else None

    if not result:
        print("⚠️ [歸因] Ollama 無回應，跳過本次更新")
        return

    # Step 6: 更新禁止規則
    new_rules = result.get("new_rules", [])
    for nr in new_rules:
        # 避免重複
        if nr.get("symbol") in forbidden_symbols:
            continue
        nr["created_at"] = TODAY_STR
        nr["source"] = "logic_distiller"
        forbidden["rules"].append(nr)

    # 保留最多 20 條
    forbidden["rules"] = forbidden["rules"][-20:]
    forbidden["metadata"]["last_update"] = TODAY_STR
    save_json(FORBIDDEN_FILE, forbidden)

    # Step 7: 更新 wisdom_corrections
    wisdom = get_wisdom()
    insight = {
        "type": "failure_attribution",
        "text": result.get("wisdom_update", result.get("analysis", "")),
        "created_at": TODAY_STR,
        "meta_label": "qwen3.5:4b",
        "root_causes": result.get("root_causes", [])
    }
    wisdom["insights"].append(insight)
    wisdom["insights"] = wisdom["insights"][-50:]  # 保留最近50條
    save_json(WISDOM_FILE, wisdom)

    # Step 8: 產出摘要
    print(f"📊 [歸因結果]")
    print(f"   分析：{result.get('analysis', 'N/A')}")
    print(f"   根因：{result.get('root_causes', [])}")
    print(f"   新增規則：{len(new_rules)} 條")
    for nr in new_rules:
        print(f"     • {nr.get('symbol')}: {nr.get('rule')} ({nr.get('severity')})")
    print(f"\n✅ [失敗歸因] 完成，共 {len(new_rules)} 條新規則")

    return {
        "analysis": result.get("analysis"),
        "new_rules_count": len(new_rules),
        "root_causes": result.get("root_causes", [])
    }


# ── 入口 ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        result = run_failure_attribution()
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"❌ [失敗歸因] 執行例外：{e}")
        sys.exit(1)
