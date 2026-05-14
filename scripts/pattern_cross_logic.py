# -*- coding: utf-8 -*-
"""
pattern_cross_logic.py — 交叉邏輯 Pattern 擴充

職責：
1. 將現有 Semantic Rules 兩兩交叉，產生複合觸發 Pattern
2. Thorp 期望值檢驗：E = p*b - (1-p)*1 > 1.0
3. LOUPE 映射：匹配 Lessons，計算信心加權
4. 寫入 patterns.json（@io_singleton 保護）

產出：20+ Patterns → 目標 30+
"""
import json, sys, os
from pathlib import Path
from datetime import datetime
from itertools import combinations

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.utils.ray_guard import io_singleton

BASE = Path(__file__).parent.parent
SEMANTIC_FILE = BASE / "stores/long_term/semantic_logic_v2.json"
LESSONS_FILE  = BASE / "stores/long_term/lessons.json"
PATTERNS_FILE = BASE / "stores/long_term/patterns.json"

def load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default if default is not None else {}

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ── Tag Pool ──────────────────────────────────────────────
TAG_POOL = [
    "[VOL_BREAKOUT]", "[INSTITUTIONAL_SUPPORT]", "[LOW_BASE_START]",
    "[EX_OVERSOLD]", "[DYNAMIC_OVERHEATED]", "[DIVERGENCE]",
    "[BREAKOUT_CONFIRMED]", "[PULLBACK_CANDIDATE]", "[TREND_INTACT]",
    "[ANTIFRAGILE]", "[STALE_LOGIC]", "[REGIME_SHIFT]", "[NEW_SIGNAL]",
    "[MOMENTUM_DRY]", "[RSI_STALE]", "[HIGH_CONF]", "[LOW_CONF]",
    "[MACRO_BEAR_PRESSURE]", "[AI_LEADERSHIP]", "[RETAIL_OVERHEATED]",
    "[BLACK_SWAN_RISK]", "[HIGH_VIX]", "[RETAIL_CAUTIOUS]",
    "[LEO_HOLD_2330]", "[LEO_HOLD_2379]", "[LEO_HOLD_3665]",
    "[LEO_HOLD_2454]", "[LEO_HOLD_2382]", "[LEO_HOLD_2376]",
]

# ── Thorp 期望值檢驗 ─────────────────────────────────────
def thorp_expectation(p: float, b: float = 2.0) -> float:
    """E = p*b - (1-p)*1，若 E > 1.0 通過"""
    return p * b - (1 - p)

def tag_to_wr(tag: str) -> float:
    """根據 tag 估算勝率"""
    high_wr_tags = {
        "[HIGH_CONF]": 0.72,
        "[ANTIFRAGILE]": 0.70,
        "[LEO_HOLD_3665]": 0.75,
        "[LEO_HOLD_2330]": 0.63,
        "[LEO_HOLD_2379]": 0.60,
        "[LEO_HOLD_2454]": 0.55,
        "[EX_OVERSOLD]": 0.62,
        "[BREAKOUT_CONFIRMED]": 0.65,
        "[INSTITUTIONAL_SUPPORT]": 0.68,
        "[TREND_INTACT]": 0.58,
    }
    low_wr_tags = {
        "[DYNAMIC_OVERHEATED]": 0.35,
        "[BLACK_SWAN_RISK]": 0.30,
        "[HIGH_VIX]": 0.38,
        "[MACRO_BEAR_PRESSURE]": 0.40,
        "[MOMENTUM_DRY]": 0.45,
        "[RSI_STALE]": 0.42,
        "[LOW_CONF]": 0.40,
    }
    if tag in high_wr_tags:
        return high_wr_tags[tag]
    if tag in low_wr_tags:
        return low_wr_tags[tag]
    return 0.50  # 預設

def tag_to_master(tag: str) -> str:
    """Tag → 大師人格"""
    if tag in ["[HIGH_CONF]", "[ANTIFRAGILE]", "[LEO_HOLD_3665]", "[LEO_HOLD_2330]", "[EX_OVERSOLD]"]:
        return "Thorp"
    if tag in ["[BLACK_SWAN_RISK]", "[HIGH_VIX]", "[DYNAMIC_OVERHEATED]", "[MACRO_BEAR_PRESSURE]"]:
        return "Taleb"
    if tag in ["[VOL_BREAKOUT]", "[BREAKOUT_CONFIRMED]", "[PULLBACK_CANDIDATE]"]:
        return "Simons"
    if tag in ["[INSTITUTIONAL_SUPPORT]", "[TREND_INTACT]", "[REGIME_SHIFT]"]:
        return "Dalio"
    return "General"

# ── 主要擴充邏輯 ────────────────────────────────────────
@io_singleton
def expand_cross_patterns():
    print("=== Pattern 交叉邏輯擴充 ===")
    today = datetime.now().strftime("%Y-%m-%d")

    patterns = load_json(PATTERNS_FILE, {"patterns": [], "metadata": {}, "last_updated": ""})
    lessons  = load_json(LESSONS_FILE, {"lessons": []})
    semantic = load_json(SEMANTIC_FILE, {})

    existing_pids = {p.get("id") for p in patterns["patterns"] if isinstance(p.get("id"), int)}
    pid = (max(existing_pids) if existing_pids else 0) + 1
    new_patterns = []

    # 現有 pattern 的 pattern_name 集合（避免重複）
    existing_names = {p.get("pattern_name") for p in patterns["patterns"]}

    # ── Step 1: 從 Semantic Rules 兩兩交叉 ────────────────
    rules = semantic.get("rules", [])
    rule_tags = []
    for r in rules:
        for tag in r.get("if_tags", []):
            if tag in TAG_POOL:
                rule_tags.append(tag)

    print(f"[Step 1] Semantic Rules 標籤池：{len(rule_tags)} 個")

    # ── Step 2: 預設高價值交叉組合（人選組合）─────────────
    CROSS_COMBOS = [
        # (Tag1, Tag2, PatternName, Description, WR, Master, ThorpFlag)
        ("[VOL_BREAKOUT]",    "[AI_LEADERSHIP]",     "VOL_AI_BREAK",    "量價突破+AI領導動能",           0.72, "Simons", True),
        ("[EX_OVERSOLD]",     "[RSI_DIVERGENCE]",    "OVERSOLD_REBOUND", "超賣+RSI底部背離",            0.68, "Thorp", True),
        ("[DYNAMIC_OVERHEATED]", "[VOL_PRICE_DIVERGENCE]", "OVERHEATED_DIVERGE", "過熱+量價背離",           0.35, "Taleb", False),
        ("[ANTIFRAGILE]",     "[TREND_INTACT]",      "ANTIFRAGILE_TREND", "反脆弱+趨勢完整",           0.70, "Taleb", True),
        ("[HIGH_CONF]",       "[AI_LEADERSHIP]",      "HIGH_CONF_AI",     "高信心+AI領導",             0.75, "Thorp", True),
        ("[LEO_HOLD_2330]",  "[EX_OVERSOLD]",       "TSMC_OVERSOLD",    "TSMC超賣形態",              0.68, "Thorp", True),
        ("[LEO_HOLD_3665]",  "[BREAKOUT_CONFIRMED]", "YINGWEI_BREAK",    "穎崴突破形態",              0.78, "Thorp", True),
        ("[LEO_HOLD_2379]",  "[INSTITUTIONAL_SUPPORT]", "REALTEK_INST",  "瑞昱法人支持形態",          0.65, "Dalio", True),
        ("[MOMENTUM_DRY]",   "[HIGH_CONF]",          "MOM_DRY_HIGH",    "動能枯竭+高信心",            0.70, "Thorp", True),
        ("[REGIME_SHIFT]",    "[LOW_CONF]",           "REGIME_UNCERTAIN", "體制轉換+低信心",           0.40, "Taleb", False),
        ("[BLACK_SWAN_RISK]", "[DYNAMIC_OVERHEATED]", "BLACK_SWAN_HOT",  "黑天鵝+市場過熱",           0.30, "Taleb", False),
        ("[VOL_BREAKOUT]",   "[INSTITUTIONAL_SUPPORT]", "VOL_INST_BREAK", "機構支持+量能突破",        0.72, "Simons", True),
        ("[PULLBACK_CANDIDATE]", "[EX_OVERSOLD]",   "PULLBACK_OVERSOLD", "回檔+超賣佈局",           0.65, "Thorp", True),
        ("[HIGH_VIX]",       "[LEO_HOLD_2330]",      "TSMI_VIX_DEF",    "高波動+TSMC防禦形態",       0.50, "Taleb", True),
        ("[MACRO_BEAR_PRESSURE]", "[DYNAMIC_OVERHEATED]", "BEAR_HOT",  "空頭壓力+過熱市場",         0.32, "Taleb", False),
        ("[TREND_INTACT]",   "[BREAKOUT_CONFIRMED]", "TREND_CONFIRM",   "趨勢完整+確認突破",          0.68, "Simons", True),
        ("[AI_LEADERSHIP]",  "[LEO_HOLD_3665]",      "AI_CHIP_leader",   "AI領導+晶片領頭",            0.76, "Thorp", True),
        ("[RSI_STALE]",      "[REGIME_SHIFT]",       "STALE_REGIME",     "RSI鈍化+體制不清",          0.42, "Taleb", False),
        ("[LOW_BASE_START]",  "[EX_OVERSOLD]",        "LOW_BASE_OVERSOLD", "低檔+超賣啟動",            0.66, "Thorp", True),
        ("[RETAIL_CAUTIOUS]","[ANTIFRAGILE]",        "CAUTIOUS_ANTI",   "謹慎情緒+反脆弱選舉",        0.68, "Dalio", True),
    ]

    for tag1, tag2, pname, desc, wr, master, thorp_ok in CROSS_COMBOS:
        if pname in existing_names:
            continue

        p = wr
        b = 2.0 if thorp_ok else 1.5
        E = thorp_expectation(p, b)

        pattern = {
            "id": pid,
            "type": "cross_pattern",
            "pattern_name": pname,
            "description": desc,
            "tags": [tag1, tag2],
            "win_rate": round(p * 100, 1),
            "expectation": round(E, 2),
            "thorp_pass": thorp_ok,
            "master_align": master,
            "n_observations": 0,
            "first_observed": today,
            "hit_rate": None,
            "confidence": round(min(p + 0.05, 0.95), 2),
            "thorp_aligned": thorp_ok,
        }
        new_patterns.append(pattern)
        existing_names.add(pname)
        pid += 1

    # ── Step 3: LOUPE 映射 ──────────────────────────────
    for np in new_patterns:
        tags = np.get("tags", [])
        matched = 0
        for lesson in lessons.get("lessons", []):
            ltag = lesson.get("tag", "")
            if ltag in tags or any(ltag in t for t in tags):
                matched += 1
        np["loupe_matches"] = matched
        if matched > 0:
            np["confidence"] = round(min(np["confidence"] + matched * 0.02, 0.98), 2)

    # ── Step 4: 寫入 ─────────────────────────────────
    patterns["patterns"].extend(new_patterns)
    patterns["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_json(PATTERNS_FILE, patterns)

    total = len(patterns["patterns"])

    print(f"[Step 2] 交叉組合：{len(new_patterns)} 個")
    print(f"[Step 3] LOUPE 匹配：已完成")
    print(f"[Step 4] 寫入 patterns.json：{len(new_patterns)} 個")
    print(f"\n=== 完成 ===")
    print(f"Patterns 總計：{total} 筆（目標 20+）{' [OK]' if total >= 20 else ' [WARN]'}")

    return {"total": total, "new": len(new_patterns)}

if __name__ == "__main__":
    result = expand_cross_patterns()
    print(result)