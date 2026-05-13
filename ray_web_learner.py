# -*- coding: utf-8 -*-
"""
ray_web_learner.py — 連網自主學習模組
"""

import sys, os, sqlite3, json, time, logging, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

BASE_URL = "http://localhost:11434/api/chat"

# ── Router 導入 ──────────────────────────────────────────────
try:
    from llm_router import get_router
    ROUTER = get_router()
    HAS_ROUTER = True
except ImportError:
    ROUTER = None
    HAS_ROUTER = False

from pathlib import Path

LOG_DIR_PATH = Path("logs")
LOG_DIR_PATH.mkdir(exist_ok=True)

_log = logging.getLogger("ray_web_learner")
_log.setLevel(logging.INFO)
if not _log.handlers:
    h = logging.FileHandler(str(LOG_DIR_PATH / "ray_web_learner.log"), encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    _log.addHandler(h)

DB_PATH = "ray_wisdom.db"

# ── Tavily API（主要連網搜尋）───
TAVILY_KEY = "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"

# ── RSS Feeds（備用，已不穩，建議保留過渡）───
RSS_FEEDS = {
    "taleb": "https://www.fooledbyrandomness.com/rss.xml",
    "yahoo_spy": "https://feeds.finance.yahoo.com/rss/headline?s=SPY",
}

def fetch_tavily_news(query, max_results=5):
    """Tavily 搜尋（主要資料源）"""
    try:
        import requests
        resp = requests.post(
            "https://api.tavily.com/search",
            json={"query": query, "api_key": TAVILY_KEY, "max_results": max_results, "topic": "finance"},
            timeout=15
        )
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            return [{"title": r.get("title", ""), "summary": r.get("content", "")[:200], "source": f"Tavily_{query}"} for r in results]
    except Exception as e:
        _log.warning(f"Tavily failed: {e}")
    return []

def fetch_taleb_rss():
    """Taleb RSS（備用）"""
    try:
        import feedparser
        insights = []
        try:
            f = feedparser.parse(RSS_FEEDS["taleb"])
            for entry in f.entries[:3]:
                insights.append({"title": entry.title, "summary": entry.summary[:200], "source": "Taleb_RSS"})
        except Exception as e:
            _log.warning(f"Taleb RSS failed: {e}")
        return insights
    except ImportError:
        return []

def fetch_financial_news():
    """Yahoo Finance RSS（備用，已不穩）"""
    try:
        import feedparser
        insights = []
        try:
            f = feedparser.parse(RSS_FEEDS["yahoo_spy"])
            for entry in f.entries[:5]:
                insights.append({"title": entry.title, "summary": entry.summary[:200] if hasattr(entry, 'summary') else "", "source": "Yahoo_Finance"})
        except Exception as e:
            _log.warning(f"Yahoo RSS failed: {e}")
        return insights
    except ImportError:
        return []

def filter_keywords(text):
    keywords = ["sharpe", "kelly", "fat-tail", "volatility", "drawdown", "momentum", "rsi", "macd", "mean reversion", "portfolio", "risk management", "position sizing", "stop loss", "tail risk", "asymmetric", "convexity", "black swan"]
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)

def classify_insight(text):
    text_lower = text.lower()
    if any(k in text_lower for k in ["taleb", "black swan", "fragility"]):
        return "TALEB"
    elif any(k in text_lower for k in ["thorp", "kelly", "blackjack"]):
        return "THORP"
    elif any(k in text_lower for k in ["connors", "rsi", "mean reversion"]):
        return "CONNORS"
    elif any(k in text_lower for k in ["simons", "hmm", "hidden markov"]):
        return "SIMONS"
    return "GENERAL"

def validate_with_7b(insight_text):
    """
    驗證外部觀點（走 Router Layer 2 → MiniMax）
    深度推理，不需要本地 7B
    """
    prompt = f'你是 Ray 7B 參謀。請審核以下外部觀點：\n\n"{insight_text}"\n\n輸出 JSON：{{"valid": true/false, "conflict": "none/minor/severe", "action": "具體建議"}}\n'

    if ROUTER and HAS_ROUTER:
        try:
            result_text = ROUTER.deep(prompt=prompt)
            import re
            m = re.search(r'\{[\s\S]*\}', result_text)
            if m:
                try:
                    return json.loads(m.group())
                except json.JSONDecodeError as je:
                    _log.warning(f"Router.deep JSON parse failed: {je} | raw: {result_text[:120]}")
                    return {"valid": False, "conflict": "unknown", "action": "parse_failed"}
            else:
                _log.warning(f"Router.deep no JSON found | raw: {result_text[:120]}")
                return {"valid": False, "conflict": "unknown", "action": "no_json"}
        except Exception as e:
            _log.warning(f"Router.deep failed, falling back: {e}")

    # 降級：直接走 Ollama ray-deep-v1
    try:
        import requests
        resp = requests.post(BASE_URL, json={
            "model": "ray-deep-v1",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "temperature": 0.3
        }, timeout=120)

        result = resp.json().get("message", {}).get("content", "")
        m = re.search(r'\{[\s\S]*\}', result)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                _log.warning(f"Ollama JSON parse failed | raw: {result[:120]}")
                return {"valid": False, "conflict": "unknown", "action": "parse_failed"}
        return {"valid": False, "conflict": "unknown", "action": "no_json"}
    except Exception as e:
        _log.error(f"7B validation failed: {e}")
        return {"valid": False, "conflict": "error", "action": str(e)}

def write_web_wisdom(insight, validation_result):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    insight_text = insight.get("title", "") + " " + insight.get("summary", "")
    classification = classify_insight(insight_text)
    confidence = 0.7 if validation_result.get("valid") else 0.4

    c.execute('INSERT INTO wisdom_corrections (axiom_id, symbol, diagnosis, corrected_json, confidence, meta_label, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (0, "WEB_SOURCE", f"[{classification}] {insight.get('title', 'N/A')}",
         json.dumps({"source": insight.get("source", "UNKNOWN"), "insight": insight.get("summary", ""), "validation": validation_result}),
         confidence, json.dumps({"source": "web_learner", "type": classification}),
         time.strftime("%Y-%m-%d %H:%M:%S")))

    conn.commit()
    conn.close()
    _log.info(f"Web wisdom written: {insight.get('title')[:50]} conf={confidence}")

def math_gate_check(insight):
    text = (insight.get("summary", "") + " " + insight.get("title", "")).lower()
    for pattern in ["sharpe < 0", "no stop loss", "all in", "leverage > 10x"]:
        if pattern in text:
            _log.warning(f"Math Gate rejected: {pattern}")
            return False
    return True

def daily_web_learning():
    _log.info("=== Ray Web Learner 啟動 ===")
    collected = []

    # ── 主要來源：Tavily 搜尋（取代 RSS）───
    queries = [
        "quantitative trading strategy Sharpe ratio",
        "momentum trading RSI mean reversion",
        "risk management position sizing stop loss",
        "portfolio optimization fat-tail black swan",
    ]
    for q in queries:
        results = fetch_tavily_news(q, max_results=3)
        collected.extend(results)
    _log.info(f"Tavily 抓取 {len(collected)} 筆")

    # ── 備用：RSS feeds───
    taleb = fetch_taleb_rss()
    news = fetch_financial_news()
    if taleb or news:
        collected.extend(taleb)
        collected.extend(news)
        _log.info(f"RSS 備用 {len(taleb)+len(news)} 筆（已穩定）")

    total = len(collected)
    _log.info(f"抓取 {total} 筆")

    filtered = [i for i in collected if filter_keywords(i.get("title", "") + i.get("summary", ""))]
    _log.info(f"過濾後 {len(filtered)} 筆")

    gate_passed = [i for i in filtered if math_gate_check(i)]
    _log.info(f"Gate通過 {len(gate_passed)} 筆")

    for insight in gate_passed[:5]:
        validation = validate_with_7b(insight.get("title", "") + " " + insight.get("summary", ""))
        if validation.get("valid"):
            write_web_wisdom(insight, validation)
            _log.info(f"  OK: {insight.get('title')[:50]}")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM wisdom_corrections WHERE symbol='WEB_SOURCE'")
    web_count = c.fetchone()[0]
    conn.close()
    _log.info(f"總 web_source: {web_count}")

    return {"collected": len(collected), "filtered": len(filtered), "gate_passed": len(gate_passed), "total_web_wisdom": web_count}

if __name__ == "__main__":
    result = daily_web_learning()
    print(f"\n=== 連網學習結果 ===")
    print(f"抓取: {result['collected']} 筆")
    print(f"過濾: {result['filtered']} 筆")
    print(f"Gate通過: {result['gate_passed']} 筆")
    print(f"總 web_source: {result['total_web_wisdom']} 筆")
    print("\n連網學習模組就緒")