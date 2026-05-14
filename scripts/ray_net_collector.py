# -*- coding: utf-8 -*-
"""
ray_net_collector.py — 連網學習與跨市場標籤化系統

功能：
  1. 美股連動標籤（SOX / NVDA）
  2. 產業鏈動態（新聞抓取）
  3. 情緒指標（PTT Stock）
  4. 多頻率學習（05:30 / 14:30 / 每120分鐘 / 週末）

標籤池：
  [MACRO_BEAR_PRESSURE]  SOX跌>2%
  [AI_LEADERSHIP]        NVDA創高
  [FUNDAMENTAL_FRAGILE] 新聞提及訂單下修
  [RETAIL_OVERHEATED]   PTT散戶情緒過熱
  [FUNDAMENTAL_WARNING] 連網顯示產業景氣下行

用法：
  python scripts/ray_net_collector.py --mode full     # 完整學習（05:30 / 14:30）
  python scripts/ray_net_collector.py --mode fast    # 快閃監控（每120分鐘）
  python scripts/ray_net_collector.py --mode weekend # 週末全局回測
"""

import sys, os, json, time, re
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.utils.ray_guard import ray_singleton, io_singleton, market_safe_guard

# ── 設定 ─────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
NEWS_POOL = BASE_DIR / "news_pool.txt"
MACRO_TAGS_FILE = BASE_DIR / "stores" / "short_term" / "macro_tags.json"
LESSONS_FILE = BASE_DIR / "stores" / "long_term" / "lessons.json"
LEDGER_FILE = BASE_DIR / "stores" / "long_term" / "experience_ledger.json"

# ── 工具函式 ─────────────────────────────────────────────────
def load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default if default is not None else {}

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def fetch_url(url: str, headers: dict = None) -> str:
    """發送 HTTP 請求，返回內容（超時 10s）"""
    try:
        req = Request(url, headers=headers or {})
        with urlopen(req, timeout=10) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.read().decode(charset, errors="replace")
    except (URLError, HTTPError, TimeoutError) as e:
        print(f"  [fetch_url] ERROR {url}: {e}")
        return ""

def fetch_news_pool():
    """讀取今日快閃新聞池"""
    if not NEWS_POOL.exists():
        return []
    with open(NEWS_POOL, "r", encoding="utf-8", errors="replace") as f:
        return [l.strip() for l in f if l.strip()]

# ── 1. 美股連動標籤 ──────────────────────────────────────────
@io_singleton
def get_macro_tags() -> dict:
    """
    抓取 SOX 和 NVDA 數據，產出宏觀標籤。
    結果寫入 stores/short_term/macro_tags.json
    """
    tags = []
    signals = {}

    # SOX 半導體指數
    try:
        import yfinance as yf
        sox = yf.Ticker("^SOX").history(period="1d")
        if len(sox) >= 2:
            sox_chg = (sox["Close"].iloc[-1] / sox["Close"].iloc[-2] - 1) * 100
            signals["SOX_chg"] = round(sox_chg, 2)
            if sox_chg < -2:
                tags.append("[MACRO_BEAR_PRESSURE]")
            elif sox_chg > 1.5:
                tags.append("[MACRO_BULL]")
    except Exception as e:
        print(f"  [SOX] ERROR: {e}")

    # NVDA
    try:
        nvda = yf.Ticker("NVDA").history(period="5d")
        if len(nvda) >= 2:
            nvda_chg = (nvda["Close"].iloc[-1] / nvda["Close"].iloc[-2] - 1) * 100
            nvda_high_52w = nvda["Close"].max()
            signals["NVDA_chg"] = round(nvda_chg, 2)
            if nvda["Close"].iloc[-1] >= nvda_high_52w * 0.98:
                tags.append("[AI_LEADERSHIP]")
    except Exception as e:
        print(f"  [NVDA] ERROR: {e}")

    # VIX
    try:
        vix = yf.Ticker("^VIX").history(period="1d")
        if len(vix) >= 1:
            vix_val = float(vix["Close"].iloc[-1])
            signals["VIX"] = round(vix_val, 2)
            if vix_val > 25:
                tags.append("[HIGH_VIX]")
            elif vix_val > 30:
                tags.append("[BLACK_SWAN_RISK]")
    except:
        pass

    result = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tags": tags,
        "signals": signals,
    }

    # 寫入
    save_json(MACRO_TAGS_FILE, result)
    return result

# ── 2. 產業鏈動態（新聞）─────────────────────────────────────
def fetch_supply_chain_news(symbols: list) -> list:
    """
    抓取台股相關新聞（已移除 yfinance.news，避免hang）。
    結果寫入 news_pool.txt，fast 模式讀取 pool。
    """
    return []

def tag_news(news_items: list) -> list:
    """
    將新聞標題轉化為語意標籤。
    """
    negative_keywords = ["下修", "砍單", "衰退", "警告", "裁員", "庫存過高", "需求放緩", "loss", "cut", "warn", "downgrade"]
    positive_keywords = ["訂單", "擴產", "創高", "突破", "成長", "超標", "boom", "upgrade", "record"]

    tagged = []
    for item in news_items:
        title = item.get("title", "").lower()
        neg = any(k in title for k in negative_keywords)
        pos = any(k in title for k in positive_keywords)

        if neg:
            item["tag"] = "[FUNDAMENTAL_FRAGILE]"
        elif pos:
            item["tag"] = "[FUNDAMENTAL_STRONG]"
        else:
            item["tag"] = "[NEUTRAL]"

        tagged.append(item)
    return tagged

# ── 3. 情緒指標（PTT Stock）────────────────────────────────
def fetch_ptt_sentiment() -> dict:
    """
    抓取 PTT Stock 版情緒（模擬）。
    實際需串接 PTT API 或 web crawler。
    這裡用關鍵字模擬情緒。
    """
    # 模擬：讀取 news_pool 中最近 10 條新聞的關鍵字
    pool = fetch_news_pool()
    hot_keywords = ["噴", "涨停", "暴漲", "賺錢", "梭哈", "all in"]
    cold_keywords = ["崩", "跌停", "套牢", "止损", "止损"]

    hot_count = sum(1 for t in pool for k in hot_keywords if k in t)
    cold_count = sum(1 for t in pool for k in cold_keywords if k in t)

    if hot_count > 5:
        sentiment_tag = "[RETAIL_OVERHEATED]"
    elif cold_count > 3:
        sentiment_tag = "[RETAIL_PANIC]"
    else:
        sentiment_tag = "[RETAIL_CAUTIOUS]"

    return {
        "sentiment_tag": sentiment_tag,
        "hot_count": hot_count,
        "cold_count": cold_count,
        "pool_size": len(pool),
    }

# ── 4. 全局學習（蒸餾）───────────────────────────────────
def perform_global_learning(news_items: list, macro_data: dict, sentiment: dict):
    """
    收集連網資訊，寫入 lessons.json。
    實際 Ollama 蒸餾由 Cron Job（14:00 / 17:00）執行。
    """
    # 組合上下文
    context = {
        "macro": macro_data,
        "sentiment": sentiment,
        "news_count": len(news_items),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    print(f"  全局學習上下文：{json.dumps(context, ensure_ascii=False)[:200]}")

    # 寫入 lessons
    lessons = load_json(LESSONS_FILE, {"lessons": [], "metadata": {}, "last_updated": ""})
    new_lessons = []
    for tag in macro_data.get("tags", []):
        new_lessons.append({
            "id": len(lessons.get("lessons", [])) + 1,
            "type": "macro",
            "tag": tag,
            "context": context,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "confidence": 0.75,
        })

    if new_lessons:
        lessons["lessons"].extend(new_lessons)
        lessons["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_json(LESSONS_FILE, lessons)
        print(f"  + 新增 {len(new_lessons)} 條 lessons（共 {len(lessons['lessons'])} 條）")
    else:
        print("  無新增 lessons")

    return {"new_lessons": len(new_lessons), "total": len(lessons.get("lessons", []))}

# ── 5. 快閃新聞監控 ───────────────────────────────────────
@io_singleton
def fast_news_fetch():
    """
    輕量級新聞抓取，存入 news_pool.txt。
    不佔顯存，純文字。
    """
    pool = fetch_news_pool()
    new_count = 0

    # 抓取 Yahoo Finance 台股相關新聞
    try:
        import yfinance as yf
        tickers = ["2330.TW", "2454.TW", "2317.TW", "3034.TW", "2379.TW"]
        for sym in tickers:
            try:
                t = yf.Ticker(sym)
                news = t.news or []
                for n in news[:1]:
                    title = n.get("title", "")
                    if title and title not in pool:
                        pool.append(title)
                        new_count += 1
            except:
                pass
    except Exception as e:
        print(f"  [fast_news] ERROR: {e}")

    if new_count > 0:
        with open(NEWS_POOL, "w", encoding="utf-8") as f:
            f.write("\n".join(pool[-100:]))  # 只保留最近100條
        print(f"  [fast_news] 新增 {new_count} 條（pool: {len(pool)}）")

    return {"pool_size": len(pool), "new": new_count}

# ── 主學習流程 ─────────────────────────────────────────────
def full_learning_cycle():
    """
    完整學習週期：macro → supply chain → sentiment → distillation
    """
    print("=== Ray 連網學習 — 完整週期 ===")
    print(f"時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Step 1: Macro tags
    print("\n[Step 1] Macro 連動標籤...")
    macro = get_macro_tags()
    print(f"  標籤：{' '.join(macro['tags']) if macro['tags'] else '無'}")
    print(f"  信號：{macro.get('signals', {})}")

    # Step 2: Supply chain news
    print("\n[Step 2] 產業鏈動態...")
    news = fetch_supply_chain_news(["2330.TW", "2454.TW", "3034.TW", "3665.TW"])
    tagged_news = tag_news(news)
    fragile = [n for n in tagged_news if n["tag"] == "[FUNDAMENTAL_FRAGILE]"]
    print(f"  新聞總數：{len(news)}，負面：{len(fragile)}")
    for n in fragile[:3]:
        print(f"    {n['tag']}: {n['title'][:40]}")

    # Step 3: Sentiment
    print("\n[Step 3] 情緒指標...")
    sentiment = fetch_ptt_sentiment()
    print(f"  情緒：{sentiment['sentiment_tag']}（hot={sentiment['hot_count']}, cold={sentiment['cold_count']}）")

    # Step 4: Global distillation
    print("\n[Step 4] 跨市場蒸餾...")
    result = perform_global_learning(tagged_news, macro, sentiment)
    print(f"  蒸餾結果：新增 {result['new_lessons']} 條 lessons（共 {result['total']} 條）")

    print("\n=== 完成 ===")
    return {"macro": macro, "news": len(news), "sentiment": sentiment, "distill": result}

def fast_learning_cycle():
    """
    快閃學習（每120分鐘）：只抓新聞，不蒸餾
    """
    print("=== Ray 快閃監控 ===")
    result = fast_news_fetch()
    print(f"  Pool: {result['pool_size']} 條，新增: {result['new']}")
    return result

def weekend_learning_cycle():
    """
    週末全局回測：移除所有 [STALE_LOGIC]，重新蒸餾
    """
    print("=== Ray 週末全局回測 ===")

    # 清理 stale lessons
    lessons = load_json(LESSONS_FILE, {"lessons": [], "metadata": {}, "last_updated": ""})
    before = len(lessons.get("lessons", []))
    stale = [l for l in lessons.get("lessons", []) if "[STALE_LOGIC]" in str(l)]
    lessons["lessons"] = [l for l in lessons["lessons"] if l not in stale]
    save_json(LESSONS_FILE, lessons)
    print(f"  移除 {len(stale)} 條 STALE lessons（{before} → {len(lessons['lessons'])}）")

    # 全局宏觀學習
    macro = get_macro_tags()
    print(f"  Macro 標籤：{' '.join(macro['tags']) if macro['tags'] else '無'}")

    print("=== 週末回測完成 ===")
    return {"stale_removed": len(stale), "macro": macro}

# ── CLI ─────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="fast", choices=["full", "fast", "weekend"])
    args = parser.parse_args()

    if args.mode == "full":
        full_learning_cycle()
    elif args.mode == "fast":
        fast_learning_cycle()
    elif args.mode == "weekend":
        weekend_learning_cycle()