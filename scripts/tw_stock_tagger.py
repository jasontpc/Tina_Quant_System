# -*- coding: utf-8 -*-
"""
tw_stock_tagger.py — 語意標籤化輸入層（Jo 整合藍圖核心）

將 streamlit_tw_stock.py 的數值輸出轉化為語意標籤，
餵給 Ray-v3.5 (4B) + qwen2.5:7b (7B) 進行滾動回測。

標籤體系：
  [VOL_BREAKOUT]       量能突破（量 > MA5×2）
  [LOW_BASE_START]      低基期起漲（MA200之上 + RSI<60）
  [INSTITUTIONAL_SUPPORT] 法人支撐（外资+投信同步買超）
  [EX_OVERSOLD]        極端超賣（RSI<30）
  [OVERHEATED]         技術過熱（RSI>75 或 BB%>90）
  [DIVERGENCE]         量價背離
  [BREAKOUT_CONFIRMED] 突破確認（MA20+MACD+K共振）
  [PULLBACK_CANDIDATE] 回測候選（上升趨勢中的回調）
  [ANTIFRAGILE]        反脆弱標籤（勝率>70%的標籤組合）
  [STALE_LOGIC]        歷史勝率<50%，應避開
  [REGIME_SHIFT]       市場結構轉變
  [NEW_SIGNAL]        無歷史記錄的新信號

用法：
  from scripts.tw_stock_tagger import tag_stock

  tags, tag_scores = tag_stock(
      symbol="2458.TW",
      price=149.0,
      rsi=63.4,
      vol_ratio=2.3,
      ma20=145.0,
      ma60=138.0,
      ma200=130.0,
      macd_hist=2.1,
      kdj_golden=True,
      foreign_buy=1523,   # 張
      inst_buy=856,        # 張
      twii_rsi=73.0,
      score=4,             # 三位一體評分（0-8）
      win_rate=None,       # 從 experience_ledger 帶入
      holding_days=0,
  )
"""

import json
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
LEDGER_FILE = BASE_DIR / "stores" / "long_term" / "experience_ledger.json"
TAG_WEIGHTS_FILE = BASE_DIR / "stores" / "long_term" / "semantic_logic_v2.json"
DYNAMIC_WEIGHTS = BASE_DIR / "stores" / "short_term" / "dynamic_backtest_weights.json"

def load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default if default is not None else {}

# ── 核心標籤規則 ─────────────────────────────────────────────────────
def derive_tags(
    price, rsi, vol_ratio, ma20, ma60, ma200,
    macd_hist, kdj_golden, k_val, d_val,
    foreign_buy, inst_buy,
    twii_rsi, score,
    win_rate=None, holding_days=0
) -> tuple[list[str], dict]:
    """
    從數值資料推導語意標籤。
    回傳 (tags, tag_scores) — tag_scores 是每個標籤的信心度 0-1
    """
    tags = []
    scores = {}

    # ── 1. VOL_BREAKOUT ──────────────────────────────────────────
    if vol_ratio > 2.5:
        tags.append("[VOL_BREAKOUT]")
        scores["[VOL_BREAKOUT]"] = min(vol_ratio / 4.0, 1.0)
    elif vol_ratio > 1.8:
        tags.append("[VOL_BREAKOUT]")
        scores["[VOL_BREAKOUT]"] = 0.6

    # ── 2. RSI 極端標籤 ──────────────────────────────────────────
    if rsi < 30:
        tags.append("[EX_OVERSOLD]")
        scores["[EX_OVERSOLD]"] = 1.0 if rsi < 20 else 0.8
    elif rsi > 80:
        tags.append("[OVERHEATED]")
        scores["[OVERHEATED]"] = 1.0 if rsi > 90 else 0.9
    elif rsi > 75:
        tags.append("[OVERHEATED]")
        scores["[OVERHEATED]"] = 0.7

    # ── 3. LOW_BASE_START ────────────────────────────────────────
    if (ma200 and price > ma200 and rsi < 60):
        tags.append("[LOW_BASE_START]")
        scores["[LOW_BASE_START]"] = 0.8

    # ── 4. INSTITUTIONAL_SUPPORT ───────────────────────────────
    if foreign_buy > 500 and inst_buy > 300:
        tags.append("[INSTITUTIONAL_SUPPORT]")
        scores["[INSTITUTIONAL_SUPPORT]"] = min((foreign_buy + inst_buy) / 3000, 1.0)

    # ── 5. DIVERGENCE ───────────────────────────────────────────
    if vol_ratio < 0.6 and abs(macd_hist) > 1.0:
        tags.append("[DIVERGENCE]")
        scores["[DIVERGENCE]"] = 0.75

    # ── 6. BREAKOUT_CONFIRMED ───────────────────────────────────
    if score >= 6 and kdj_golden and macd_hist > 0 and price > ma20:
        tags.append("[BREAKOUT_CONFIRMED]")
        scores["[BREAKOUT_CONFIRMED]"] = 0.9

    # ── 7. PULLBACK_CANDIDATE ──────────────────────────────────
    if (ma20 > ma60) and (rsi < 50) and (macd_hist > 0) and not kdj_golden:
        tags.append("[PULLBACK_CANDIDATE]")
        scores["[PULLBACK_CANDIDATE]"] = 0.7

    # ── 8. TREND_INTACT ─────────────────────────────────────────
    if ma20 > ma60 and macd_hist > 0 and k_val > d_val:
        tags.append("[TREND_INTACT]")
        scores["[TREND_INTACT]"] = 0.85

    # ── 9. TWII 過熱過濾 ────────────────────────────────────────
    if twii_rsi > 85:
        if "[EX_OVERSOLD]" not in tags and "[LOW_BASE_START]" not in tags:
            tags.append("[MARKET_OVERHEATED]")  # 非進場標籤，只是一個標記

    # ── 10. REGIME_SHIFT ────────────────────────────────────────
    if twii_rsi > 85 and rsi > 70:
        tags.append("[REGIME_SHIFT]")
        scores["[REGIME_SHIFT]"] = 0.8

    # ── 11. WIN_RATE Override ───────────────────────────────────
    if win_rate is not None:
        if win_rate >= 0.70:
            tags.append("[ANTIFRAGILE]")
            scores["[ANTIFRAGILE]"] = 0.9
        elif win_rate < 0.50:
            tags.append("[STALE_LOGIC]")
            scores["[STALE_LOGIC]"] = 0.85

    return tags, scores


def get_loope_verdict(symbol: str) -> dict:
    """
    查詢 experience_ledger.json，計算該股票的歷史勝率。
    回傳：{win_rate, trades, verdict, signal}
    """
    ledger = load_json(LEDGER_FILE, {"entries": []})
    entries = ledger.get("entries", [])

    sym_entries = [
        e for e in entries
        if e.get("symbol") == symbol
        and e.get("result") in ["win", "loss"]
    ]

    if not sym_entries:
        return {"win_rate": None, "trades": 0, "verdict": "APPROVE", "signal": "[NEW_SIGNAL]"}

    wins = sum(1 for e in sym_entries if e.get("result") == "win")
    win_rate = wins / len(sym_entries)

    if len(sym_entries) >= 5 and win_rate < 0.50:
        verdict = "REJECT"
        signal = "[STALE_LOGIC]"
    elif win_rate >= 0.70:
        verdict = "APPROVE"
        signal = "[ANTIFRAGILE]"
    else:
        verdict = "CAUTION"
        signal = "[NEUTRAL]"

    return {
        "win_rate": round(win_rate * 100, 1),
        "trades": len(sym_entries),
        "verdict": verdict,
        "signal": signal,
    }


def compute_entry_score(tags: list, tag_scores: dict, twii_rsi: float) -> dict:
    """
    根據標籤計算進場信心分數（0-100）。
    與 Jo 的 1000 分評分不同，這裡是 100 分制，
    用於快速排序篩選。
    """
    score = 50  # 基準線

    tag_bonus = {
        "[VOL_BREAKOUT]": 15,
        "[LOW_BASE_START]": 12,
        "[INSTITUTIONAL_SUPPORT]": 10,
        "[EX_OVERSOLD]": 18,
        "[BREAKOUT_CONFIRMED]": 20,
        "[TREND_INTACT]": 8,
        "[ANTIFRAGILE]": 15,
        "[PULLBACK_CANDIDATE]": 10,
    }

    for tag in tags:
        score += tag_bonus.get(tag, 0)

    # 減分項目
    if "[OVERHEATED]" in tags:
        score -= 15
    if "[DIVERGENCE]" in tags:
        score -= 10
    if "[STALE_LOGIC]" in tags:
        score -= 30
    if "[REGIME_SHIFT]" in tags:
        score -= 5  # TWII過熱已反映在market層

    # TWII RSI 市場環境調整
    if twii_rsi > 80:
        score = int(score * 0.7)
    elif twii_rsi > 70:
        score = int(score * 0.85)

    return {
        "total": max(0, min(100, score)),
        "tags_count": len(tags),
        "top_tags": sorted(tags, key=lambda t: tag_scores.get(t, 0), reverse=True)[:3],
    }


# ── 主標籤化函式 ─────────────────────────────────────────────────────
def tag_stock(
    symbol: str,
    price: float,
    rsi: float,
    vol_ratio: float,
    ma20: float | None,
    ma60: float | None,
    ma200: float | None,
    macd_hist: float,
    kdj_golden: bool,
    k_val: float,
    d_val: float,
    foreign_buy: float,
    inst_buy: float,
    twii_rsi: float,
    score: int,
    holding_days: int = 0,
) -> dict:
    """
    完整標籤化流程：
      1. LOUPE 查詢（歷史勝率）
      2. 數值 → 語意標籤
      3. 進場信心分數
      4. 決策建議
    """
    # Step 1: LOUPE 查詢
    loupe = get_loope_verdict(symbol)
    win_rate = loupe["win_rate"]

    # Step 2: 數值 → 標籤
    tags, tag_scores = derive_tags(
        price=price,
        rsi=rsi,
        vol_ratio=vol_ratio,
        ma20=ma20,
        ma60=ma60,
        ma200=ma200,
        macd_hist=macd_hist,
        kdj_golden=kdj_golden,
        k_val=k_val,
        d_val=d_val,
        foreign_buy=foreign_buy,
        inst_buy=inst_buy,
        twii_rsi=twii_rsi,
        score=score,
        win_rate=win_rate,
        holding_days=holding_days,
    )

    # Step 3: 進場分數
    entry = compute_entry_score(tags, tag_scores, twii_rsi)

    # Step 4: 最終裁決（結合 LOUPE + 標籤分數）
    if "[STALE_LOGIC]" in tags or loupe["verdict"] == "REJECT":
        verdict = "SKIP"
        action = "SKIP: 略過（歷史勝率不足）"
    elif "[OVERHEATED]" in tags and twii_rsi > 80:
        verdict = "SKIP"
        action = "SKIP: 略過（市場過熱）"
    elif entry["total"] >= 70:
        verdict = "BUY"
        action = "BUY: 建議進場"
    elif entry["total"] >= 50:
        verdict = "WATCH"
        action = "WATCH: 觀望等待時機"
    else:
        verdict = "SKIP"
        action = "SKIP: 信心不足"

    # 如果是新信號，調升一點信心
    if loupe["signal"] == "[NEW_SIGNAL]" and "[EX_OVERSOLD]" in tags:
        verdict = "BUY"
        action = "BUY: 新信號+超賣，建議進場"

    return {
        "symbol": symbol,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tags": tags,
        "tag_scores": tag_scores,
        "entry_score": entry,
        "loupe": loupe,
        "verdict": verdict,
        "action": action,
        "price": price,
        "rsi": rsi,
        "twii_rsi": twii_rsi,
        "score": score,
    }


# ── CLI 測試 ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== TW Stock Tagger 測試 ===\n")

    test_cases = [
        # symbol, price, rsi, vol_ratio, ma20, ma60, ma200, macd, kdj, k, d, foreign, inst, twii, score
        ("2458.TW", 149.0, 63.4, 2.3, 145.0, 138.0, 130.0, 2.1, True, 68.5, 65.2, 1523, 856, 73.0, 4),
        ("2330.TW", 2235.0, 73.1, 1.4, 2100.0, 2050.0, 1900.0, 45.2, False, 82.1, 78.3, -523, 142, 73.0, 2),
        ("3034.TW", 486.5, 42.3, 3.1, 470.0, 455.0, 420.0, 5.8, True, 48.2, 44.1, 2341, 1205, 73.0, 6),
    ]

    for (symbol, price, rsi, vol_ratio, ma20, ma60, ma200, macd, kdj, k, d, foreign, inst, twii, score) in test_cases:
        result = tag_stock(
            symbol=symbol,
            price=price,
            rsi=rsi,
            vol_ratio=vol_ratio,
            ma20=ma20,
            ma60=ma60,
            ma200=ma200,
            macd_hist=macd,
            kdj_golden=kdj,
            k_val=k,
            d_val=d,
            foreign_buy=foreign,
            inst_buy=inst,
            twii_rsi=twii,
            score=score,
        )

        print(f">> {symbol} @ {price}")
        print(f"   標籤: {' '.join(result['tags'])}")
        print(f"   LOUPE: {result['loupe']['signal']} ({result['loupe']['win_rate']}% WR, {result['loupe']['trades']}筆)")
        print(f"   進場分: {result['entry_score']['total']}/100")
        print(f"   裁決: {result['verdict']} - {result['action']}")
        print()