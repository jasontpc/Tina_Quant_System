import sys
sys.path.insert(0, r'C:\Users\USER\.openclaw\agents\ray')

# Debug fetch_tavily_articles step by step
import logging
_log = logging.getLogger("ray_econ_learner")
_log.setLevel(logging.INFO)
if not _log.handlers:
    import pathlib
    log_dir = pathlib.Path("logs")
    log_dir.mkdir(exist_ok=True)
    h = logging.FileHandler(str(log_dir / "ray_econ_learner.log"), encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    _log.addHandler(h)

TAVILY_KEY = "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"

QUANT_KEYWORDS = [
    "sharpe", "kelly", "fat-tail", "volatility", "drawdown", "momentum",
    "rsi", "macd", "mean reversion", "portfolio", "risk management",
    "position sizing", "stop loss", "tail risk", "asymmetric", "convexity",
    "black swan", "quantitative", "trading strategy", "backtest"
]

REJECT_PATTERNS = [
    "sharpe < 0", "no stop loss", "all in", "leverage > 10x",
    "guaranteed", "100% win", "always win"
]

def is_relevant(text):
    text_lower = text.lower()
    has_keyword = any(kw in text_lower for kw in QUANT_KEYWORDS)
    has_reject = any(pat in text_lower for pat in REJECT_PATTERNS)
    return has_keyword and not has_reject

def fetch_tavily_articles(queries, max_results=5):
    """用 Tavily 搜尋取代 Jina Reader（更穩定）"""
    articles = []
    for q in queries:
        try:
            import requests
            resp = requests.post(
                "https://api.tavily.com/search",
                json={"query": q, "api_key": TAVILY_KEY, "max_results": max_results, "topic": "finance"},
                timeout=15
            )
            _log.info(f"Tavily query '{q}' status={resp.status_code}")
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                _log.info(f"  results count: {len(results)}")
                for r in results[:3]:
                    content = r.get("content", "")[:500]
                    rel = is_relevant(content)
                    _log.info(f"  title={r.get('title','')[:40]} relevant={rel}")
                    if rel:
                        articles.append({
                            "title": r.get("title", "")[:100],
                            "summary": content,
                            "url": r.get("url", "")
                        })
        except Exception as e:
            _log.warning(f"Tavily query failed: {e}")
    return articles

queries = [
    "quantitative trading strategy Sharpe ratio",
    "momentum RSI mean reversion trading",
    "risk management position sizing drawdown",
]

_log.info("=== Direct test ===")
result = fetch_tavily_articles(queries, max_results=3)
_log.info(f"Total articles: {len(result)}")
for a in result:
    _log.info(f"  - {a['title'][:60]}")