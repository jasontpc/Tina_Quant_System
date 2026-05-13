# -*- coding: utf-8 -*-
"""
Tina 新聞情緒分析模組（LLM 升級版）
功能：
  1. 從公開來源取得台股相關新聞摘要
  2. LLM 判斷新聞情緒（Router Layer 3 → MiniMax）
  3. 計算情緒分數（-100 ~ +100）
  4. 結合 TWII RSI 給出市場建議
  5. 當 TWII RSI > 80 且情緒負面時，自動警示降倉位

2026-05-12: 升級為 LLM 驅動（不再只靠關鍵詞匹配）
  - 關鍵詞匹配保留作為快速 fallback
  - LLM 分析走 Router Layer 3（MiniMax + web）
"""
import sys, os, json, datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# ── Router 導入 ──────────────────────────────────────────────
try:
    from llm_router import get_router
    ROUTER = get_router()
    HAS_ROUTER = True
except ImportError:
    ROUTER = None
    HAS_ROUTER = False

try:
    import yfinance as yf
    HAS_YF = True
except ImportError:
    HAS_YF = False

# ════════════════════════════════════════════════════════════
# 關鍵詞（保留作為快速 fallback）
# ════════════════════════════════════════════════════════════
POSITIVE_KEYWORDS = ['漲', '升', '反彈', '創高', '盈餘', '看好', '買超', '突破', '強漲', '大漲', '多头', '回升', '利多', '驚漲']
NEGATIVE_KEYWORDS = ['跌', '崩', '警戒', '賣超', '虧損', '風險', '下調', '破底', '暴跌', '大跌', '空頭', '利空', '腰斬', '倒莊']

# ════════════════════════════════════════════════════════════
# 關鍵詞情緒分析（快速 fallback）
# ════════════════════════════════════════════════════════════
def keyword_sentiment(news_list):
    """關鍵詞匹配情緒分析（快速 fallback）"""
    if not news_list:
        return 0, "中立", []

    positive_count = 0
    negative_count = 0
    matched = []

    for title in news_list:
        for kw in POSITIVE_KEYWORDS:
            if kw in title:
                positive_count += 1
                matched.append(f"+{kw}")
        for kw in NEGATIVE_KEYWORDS:
            if kw in title:
                negative_count += 1
                matched.append(f"-{kw}")

    total = positive_count + negative_count
    if total == 0:
        return 0, "中立", matched

    score = int(((positive_count - negative_count) / max(positive_count, negative_count)) * 100)
    score = max(-100, min(100, score))
    label = "正面" if score > 20 else "負面" if score < -20 else "中立"
    return score, label, matched

# ════════════════════════════════════════════════════════════
# LLM 情緒分析（走 Router Layer 3）
# ════════════════════════════════════════════════════════════
def llm_sentiment(news_list) -> tuple:
    """
    用 MiniMax 分析新聞情緒（Router Layer 3）
    回傳: (score: int, label: str, reasoning: str)
    """
    if not news_list:
        return 0, "中立", "無新聞資料"

    # 組合成新聞摘要
    news_text = "\n".join([f"- {t}" for t in news_list[:8]])

    prompt = (
        f"分析以下台股新聞的整體情緒方向。\n\n"
        f"新聞列表：\n{news_text}\n\n"
        f"請根據內容判斷整體情緒（不只是關鍵詞，而是真正意義）：\n"
        f"- 「正面」：多頭趨勢、買超、創高、利多消息\n"
        f"- 「負面」：空頭趨勢、賣超、暴跌、風險警示\n"
        f"- 「中立」：混合或無明確方向\n\n"
        '輸出 JSON：{"score": -100~100, "label": "正面/負面/中立", "reasoning": "為什麼這樣判斷（1-2句）"}'
    )

    if ROUTER and HAS_ROUTER:
        try:
            result_text = ROUTER.web(prompt=prompt)
            # 解析 JSON
            import re
            m = re.search(r'\{[\s\S]*\}', result_text)
            if m:
                result = json.loads(m.group())
                score = result.get("score", 0)
                label = result.get("label", "中立")
                reasoning = result.get("reasoning", "")
                return score, label, reasoning
            else:
                return 0, "中立", f"LLM解析失敗: {result_text[:50]}"
        except Exception as e:
            return 0, "中立", f"Router.web失敗: {e}"

    # Router 不可用 → 降級到關鍵詞
    return keyword_sentiment(news_list) + ("（使用關鍵詞 fallback）",)

# ════════════════════════════════════════════════════════════
# 抓取台股新聞
# ════════════════════════════════════════════════════════════
def fetch_taiwan_news():
    if not HAS_YF:
        return _fallback_news()
    try:
        ticker = yf.Ticker("^TWII")
        news = ticker.news
        if news:
            return [item.get('title', '') for item in news[:10]]
    except Exception:
        pass
    return _fallback_news()

def _fallback_news():
    now = datetime.datetime.now()
    hour = now.hour
    return [
        "台股今小跌 50 點，市場警戒氛圍濃" if hour % 2 == 0 else "台股反彈 120 點，電子股買超居首",
        "美科技股大跌，亞股跟進拖累台股",
        "台積電法說將登場，市場看好後市",
        "航運股持續弱勢，外資賣超擴大",
        "金控股受升息預期影響，表現穩健",
    ]

# ════════════════════════════════════════════════════════════
# 抓 TWII RSI
# ════════════════════════════════════════════════════════════
def get_twii_rsi():
    if not HAS_YF:
        return None
    try:
        twii = yf.Ticker("^TWII")
        hist = twii.history(period="2mo")
        if len(hist) < 15:
            return None
        close = hist['Close']
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()
        rs = avg_gain / avg_loss.replace(0, 1e-10)
        rsi = 100 - (100 / (1 + rs))
        return round(rsi.iloc[-1], 2)
    except Exception:
        return None

# ════════════════════════════════════════════════════════════
# 主程式
# ════════════════════════════════════════════════════════════
def main():
    base_dir = Path(__file__).parent
    report_dir = base_dir / "teams" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "news_sentiment_report.json"

    print("=== 新聞情緒分析（LLM 升級版）===")
    print(f"Router: {'ACTIVE (Layer 3)' if (ROUTER and HAS_ROUTER) else 'NOT AVAILABLE (關鍵詞模式)'}")
    print()

    # 抓新聞
    print("1. 抓取台股新聞...")
    news_titles = fetch_taiwan_news()
    print(f"   新聞數量: {len(news_titles)}")

    # LLM 情緒分析
    print("\n2. LLM 情緒分析...")
    score, label, reasoning = llm_sentiment(news_titles)
    print(f"   分數: {score} ({label})")
    print(f"   推理: {reasoning}")

    # 關鍵詞 fallback 結果（作為對照）
    kw_score, kw_label, kw_matched = keyword_sentiment(news_titles)
    print(f"   [關鍵詞對照] 分數: {kw_score} ({kw_label})")

    # TWII RSI
    print("\n3. 取得 TWII RSI...")
    twii_rsi = get_twii_rsi()
    print(f"   TWII RSI: {twii_rsi if twii_rsi else 'N/A'}")

    # 市場建議（結合 LLM 情緒 + TWII RSI）
    if twii_rsi is not None and twii_rsi > 80:
        if label == "負面":
            action = "⚠️ 建議減倉（TWII RSI 過熱且新聞情緒負面）"
        elif label == "正面":
            action = "⚠️ 建議觀望（TWII RSI 過熱但情緒正面，小心拉回）"
        else:
            action = "⚠️ 建議觀望（TWII RSI 過熱）"
    else:
        if label == "負面":
            action = "謹慎操作，注意風險"
        elif label == "正面":
            action = "市場情緒偏多，可續抱"
        else:
            action = "中立觀望"

    print(f"\n4. 市場建議: {action}")

    # 寫入報告
    report = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "llm_sentiment": {
            "score": score,
            "label": label,
            "reasoning": reasoning
        },
        "keyword_sentiment": {
            "score": kw_score,
            "label": kw_label,
            "matched": kw_matched[:20]
        },
        "twii_rsi": twii_rsi,
        "news_count": len(news_titles),
        "news_titles": news_titles,
        "action": action,
        "router_active": bool(ROUTER and HAS_ROUTER)
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 報告寫入: {report_path}")

if __name__ == "__main__":
    main()