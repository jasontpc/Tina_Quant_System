# -*- coding: utf-8 -*-
"""
ray_econ_learner.py — 經濟型連網自主學習
Token 節約策略：本地預處理 + Markdown 壓縮 + 批量摘要

核心優化：
1. 本地 NLP 預處理（BeautifulSoup + Regex）
2. Tavily API 搜尋（主要）+ Jina Reader 備用
3. 多合一批量摘要（10 條 → 1 次 LLM 呼叫）
4. 固定 JSON Schema 輸出
"""

import sys, os, sqlite3, json, time, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_URL = "http://localhost:11434/api/chat"
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
import logging
_log = logging.getLogger("ray_econ_learner")
_log.setLevel(logging.INFO)
if not _log.handlers:
    h = logging.FileHandler(str(LOG_DIR / "ray_econ_learner.log"), encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    _log.addHandler(h)

DB_PATH = "ray_wisdom.db"

# ── Tavily API（主要連網方式）───
TAVILY_KEY = "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"

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
            if resp.status_code == 200:
                results = resp.json().get("results", [])[:3]
                for r in results:
                    content = r.get("content", "")[:500]
                    if is_relevant(content):
                        articles.append({
                            "title": r.get("title", "")[:100],
                            "summary": content,
                            "url": r.get("url", "")
                        })
        except Exception as e:
            _log.warning(f"Tavily query failed: {e}")
    return articles

# ============================================================
# 1. 本地 NLP 預處理（減少無關內容）
# ============================================================

def local_nlp_clean(html_text):
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_text, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "aside", "ads"]):
            tag.decompose()
        article = soup.find("article") or soup.find("main") or soup.find("body")
        text = article.get_text(separator="\n", strip=True) if article else soup.get_text(separator="\n", strip=True)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text[:3000]
    except ImportError:
        text = re.sub(r"<script[^>]*>.*?</script>", "", html_text, flags=re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:3000]

def jina_read_convert(url):
    """Jina Reader 備用（當 Tavily 失敗時）"""
    try:
        jina_url = f"https://r.jina.ai/{url}"
        import urllib.request
        req = urllib.request.Request(jina_url, headers={"Accept": "text/markdown"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")[:4000]
    except Exception as e:
        _log.warning(f"Jina Reader failed: {e}")
        return None

# ============================================================
# 2. 關鍵詞預選
# ============================================================

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

def deduplicate(text, db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT diagnosis FROM wisdom_corrections WHERE symbol='WEB_SOURCE' LIMIT 50")
    existing = [row[0] for row in c.fetchall()]
    conn.close()
    text_words = set(text.lower().split())
    for ex in existing:
        ex_words = set(ex.lower().split())
        overlap = len(text_words & ex_words) / max(len(text_words), 1)
        if overlap > 0.7:
            return False
    return True

# ============================================================
# 3. 批量摘要（多合一，節省 Token）
# ============================================================

def batch_summarize(articles):
    if not articles:
        return []
    combined = []
    total_len = 0
    for art in articles[:10]:
        excerpt = f"## {art['title']}\n{art['summary'][:500]}\n"
        if total_len + len(excerpt) > 3000:
            break
        combined.append(excerpt)
        total_len += len(excerpt)
    combined_text = "\n---\n".join(combined)
    prompt = f"""你是 Ray 7B 參謀。請將以下外部文章精簡為 3 條可執行規則。

要求：
- 每條規則需包含：具體數值門檻 + 執行時機
- 只輸出與量化交易相關的規則

文章：
{combined_text}

輸出 JSON陣列（每條規則一個物件）：
[
  {{"rule": "規則描述", "action": "具體行動", "threshold": "數值門檻"}}
]
"""
    try:
        import requests
        resp = requests.post(BASE_URL, json={
            "model": "ray-deep-v1",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "temperature": 0.2
        }, timeout=180)
        result = resp.json().get("message", {}).get("content", "")
        m = re.search(r'\[[\s\S]*\]', result)
        if m:
            rules = json.loads(m.group())
            return rules if isinstance(rules, list) else []
    except Exception as e:
        _log.error(f"7B batch summarize failed: {e}")
    return []

# ============================================================
# 4. 寫入資料庫
# ============================================================

def save_rules(rules, source_info):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        rule_text = rule.get("rule", "") + " " + rule.get("action", "")
        if not is_relevant(rule_text):
            continue
        c.execute('''INSERT INTO wisdom_corrections
            (axiom_id, symbol, diagnosis, corrected_json, confidence, meta_label, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (
                0, "WEB_SOURCE",
                rule.get("rule", "N/A")[:200],
                json.dumps({"source": source_info, "action": rule.get("action", ""), "threshold": rule.get("threshold", "")}),
                0.75,
                json.dumps({"source": "econ_learner", "type": "BATCH_SUMMARIZED"}),
                time.strftime("%Y-%m-%d %H:%M:%S")
            ))
    conn.commit()
    conn.close()

# ============================================================
# 5. 主循環
# ============================================================

def econ_web_learning():
    _log.info("=== Ray Econ Learner 啟動 ===")

    queries = [
        "quantitative trading momentum strategy RSI backtest",
        "volatility Sharpe ratio portfolio risk management",
        "trading stop loss position sizing drawdown",
    ]

    # 1. Tavily 搜尋
    _log.info("Step 1: Tavily 搜尋...")
    articles = fetch_tavily_articles(queries, max_results=5)
    _log.info(f"  Tavily 抓到 {len(articles)} 篇")

    # 2. 去重複
    _log.info("Step 2: 去重複檢查...")
    filtered = [a for a in articles if deduplicate(a["summary"])]
    _log.info(f"  去重後: {len(filtered)} 篇")

    # 3. 批量摘要
    _log.info("Step 3: 7B 批量摘要...")
    rules = batch_summarize(filtered)
    _log.info(f"  產生 {len(rules)} 條規則")

    # 4. 寫入 DB
    if rules:
        save_rules(rules, f"tavily:{len(filtered)}urls")
        _log.info(f"  已寫入 {len(rules)} 條規則")

    # 5. 統計
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM wisdom_corrections WHERE symbol='WEB_SOURCE'")
    total = c.fetchone()[0]
    conn.close()

    _log.info(f"=== 完成。WEB_SOURCE 總計: {total} 筆 ===")
    return {"articles": len(articles), "filtered": len(filtered), "rules": len(rules), "total": total}

if __name__ == "__main__":
    result = econ_web_learning()
    print(f"\n=== 經濟型連網學習結果 ===")
    print(f"抓取: {result['articles']} 篇")
    print(f"去重後: {result['filtered']} 篇")
    print(f"規則: {result['rules']} 條")
    print(f"WEB_SOURCE 總計: {result['total']} 筆")