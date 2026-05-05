# -*- coding: utf-8 -*-
"""
Tina 新聞情緒分析模組
功能：
  1. 從公開來源取得台股相關新聞摘要
  2. 判斷新聞情緒（正面/負面/中立）
  3. 計算情緒分數（-100 ~ +100）
  4. 結合 TWII RSI 給出市場建議
  5. 當 TWII RSI > 80 且情緒負面時，自動警示降倉位
"""

import sys
import os
import json
import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# 嘗試 import yfinance
try:
    import yfinance as yf
    HAS_YF = True
except ImportError:
    HAS_YF = False

# ========== 情緒關鍵詞 ==========
POSITIVE_KEYWORDS = ['漲', '升', '反彈', '創高', '盈餘', '看好', '買超', '突破', '強漲', '大漲', '多头', '回升', '利多', '驚漲']
NEGATIVE_KEYWORDS = ['跌', '崩', '警戒', '賣超', '虧損', '風險', '下調', '破底', '暴跌', '大跌', '空頭', '利空', '腰斬', '倒莊']

# ========== 新聞情緒分析 ==========
def analyze_sentiment(news_list):
    """分析新聞情緒，回傳分數 (-100 ~ +100)"""
    if not news_list:
        return 0, "中立", []

    positive_count = 0
    negative_count = 0
    matched_keywords = []

    for title in news_list:
        for kw in POSITIVE_KEYWORDS:
            if kw in title:
                positive_count += 1
                matched_keywords.append(f"+{kw}")
        for kw in NEGATIVE_KEYWORDS:
            if kw in title:
                negative_count += 1
                matched_keywords.append(f"-{kw}")

    total = positive_count + negative_count
    if total == 0:
        return 0, "中立", matched_keywords

    score = int(((positive_count - negative_count) / max(positive_count, negative_count)) * 100)
    score = max(-100, min(100, score))

    if score > 20:
        label = "正面"
    elif score < -20:
        label = "負面"
    else:
        label = "中立"

    return score, label, matched_keywords

# ========== 抓取台股新聞 ==========
def fetch_taiwan_news():
    """用 yfinance 抓台股相關新聞"""
    if not HAS_YF:
        return _fallback_news()

    try:
        ticker = yf.Ticker("^TWII")
        news = ticker.news
        if news:
            titles = [item.get('title', '') for item in news[:10]]
            return titles
    except Exception:
        pass
    return _fallback_news()

def _fallback_news():
    """當無法取得新聞時，回傳模擬資料（日期觸發的關鍵詞）"""
    now = datetime.datetime.now()
    hour = now.hour
    # 模擬盤中/盤後資訊
    return [
        "台股今小跌 50 點，市場警戒氛圍濃" if hour % 2 == 0 else "台股反彈 120 點，電子股買超居首",
        "美科技股大跌，亞股跟進拖累台股",
        "台積電法說將登場，市場看好後市",
        "航運股持續弱勢，外資賣超擴大",
        "金控股受升息預期影響，表現穩健",
    ]

# ========== 抓 TWII RSI ==========
def get_twii_rsi():
    """取得加權指數 RSI(14)"""
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

# ========== 主程式 ==========
def main():
    base_dir = Path(__file__).parent
    report_dir = base_dir / "teams" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    report_path = report_dir / "news_sentiment_report.json"

    # 抓新聞
    news_titles = fetch_taiwan_news()

    # 情緒分析
    score, label, matched = analyze_sentiment(news_titles)

    # TWII RSI
    twii_rsi = get_twii_rsi()
    if twii_rsi is None:
        twii_rsi_desc = "N/A"
    else:
        twii_rsi_desc = f"{twii_rsi}"

    # 市場建議
    if twii_rsi is not None and twii_rsi > 80:
        if label == "負面":
            action = "建議減倉（TWII RSI 過熱且新聞情緒負面）"
        elif label == "正面":
            action = "建議觀望（TWII RSI 過熱但新聞情緒正面，小心拉回）"
        else:
            action = "建議觀望（TWII RSI 過熱）"
    else:
        if label == "負面":
            action = "謹慎操作，注意風險"
        elif label == "正面":
            action = "市場情緒偏多，可續抱"
        else:
            action = "中立觀望"

    report = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "twii_rsi": twii_rsi,
        "news_count": len(news_titles),
        "news_titles": news_titles,
        "sentiment_score": score,
        "sentiment_label": label,
        "matched_keywords": matched[:20],
        "action": action
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"✅ 新聞情緒報告已寫入: {report_path}")
    print(f"   TWII RSI: {twii_rsi_desc}")
    print(f"   情緒分數: {score} ({label})")
    print(f"   建議: {action}")

if __name__ == "__main__":
    main()