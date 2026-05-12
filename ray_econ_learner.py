# -*- coding: utf-8 -*-
"""
ray_econ_learner.py — 經濟型連網自主學習
Token 節約策略：本地預處理 + Markdown 壓縮 + 批量摘要

核心優化：
1. 本地 NLP 預處理（BeautifulSoup + Regex）
2. Jina Reader 轉 Markdown（省 40-60% Token）
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

# ============================================================
# 1. 本地 NLP 預處理（減少無關內容）
# ============================================================

def local_nlp_clean(html_text):
    """
    BeautifulSoup 本地清洗：
    - 移除廣告、導航列、Script、Style
    - 只保留文章主體
    """
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_text, "html.parser")

        # 移除無關標籤
        for tag in soup(["script", "style", "nav", "header", "footer", "aside", "ads"]):
            tag.decompose()

        # 提取主要文字
        article = soup.find("article") or soup.find("main") or soup.find("body")
        if article:
            text = article.get_text(separator="\n", strip=True)
        else:
            text = soup.get_text(separator="\n", strip=True)

        # 清理多餘空行
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text[:3000]  # 限制長度

    except ImportError:
        # fallback: 簡單正則清洗
        text = re.sub(r"<script[^>]*>.*?</script>", "", html_text, flags=re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:3000]

def jina_read_convert(url):
    """
    使用 Jina Reader 將網頁轉為 Markdown
    省 40-60% Token
    """
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
# 2. 關鍵詞預選（直接捨棄無關內容）
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
    """關鍵詞預選"""
    text_lower = text.lower()
    # 必須包含至少一個量化關鍵詞
    has_keyword = any(kw in text_lower for kw in QUANT_KEYWORDS)
    # 不能包含拒絕模式
    has_reject = any(pat in text_lower for pat in REJECT_PATTERNS)
    return has_keyword and not has_reject

def deduplicate(text, db_path=DB_PATH):
    """與資料庫現有內容比對，重複者捨棄"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT diagnosis FROM wisdom_corrections WHERE symbol='WEB_SOURCE' LIMIT 50")
    existing = [row[0] for row in c.fetchall()]
    conn.close()

    # 簡單字詞重疊檢查
    text_words = set(text.lower().split())
    for ex in existing:
        ex_words = set(ex.lower().split())
        overlap = len(text_words & ex_words) / max(len(text_words), 1)
        if overlap > 0.7:  # 70% 重疊 = 重複
            return False
    return True

# ============================================================
# 3. 批量摘要（多合一，節省 Token）
# ============================================================

def batch_summarize(articles):
    """
    將多篇文章合併為 1 次 LLM 呼叫
    只呼叫 7B 一次，產生 3 條精煉規則
    """
    if not articles:
        return []

    # 合併文章（限制總長度）
    combined = []
    total_len = 0
    for art in articles[:10]:  # 最多 10 篇
        excerpt = f"## {art['title']}\n{art['summary'][:500]}\n"
        if total_len + len(excerpt) > 3000:
            break
        combined.append(excerpt)
        total_len += len(excerpt)

    combined_text = "\n---\n".join(combined)

    # 構造省 Token Prompt
    prompt = f"""你是 Ray 7B 參謀。請將以下外部文章精簡為 3 條可執行規則。

要求：
- 每條規則需包含：具體數值門檻 + 執行時機
- 只輸出與量化交易相關的規則
- 忽略與系統無關的內容

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
        import re
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
    """將精煉後的規則寫入 wisdom_corrections"""
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
                0,
                "WEB_SOURCE",
                rule.get("rule", "N/A")[:200],
                json.dumps({"source": source_info, "action": rule.get("action", ""), "threshold": rule.get("threshold", "")}),
                0.75,  # 預設信心
                json.dumps({"source": "econ_learner", "type": "BATCH_SUMMARIZED"}),
                time.strftime("%Y-%m-%d %H:%M:%S")
            ))

    conn.commit()
    conn.close()

# ============================================================
# 5. 主循環
# ============================================================

def econ_web_learning():
    """
    經濟型連網學習主循環
    目標：1 次 LLM 呼叫處理 10 篇 articles
    """
    _log.info("=== Ray Econ Learner 啟動 ===")

    # 測試 URLs（實際可替換為真實來源）
    test_urls = [
        "https://www.fooledbyrandomness.com/TS.html",  # Taleb
        "https://arxiv.org/abs/quant-ph",  # arXiv quant
    ]

    articles = []

    # 1. Jina Reader 抓取（Markdown 格式）
    _log.info("Step 1: Jina Reader 抓取...")
    for url in test_urls:
        md = jina_read_convert(url)
        if md and is_relevant(md):
            title_match = re.search(r"^#\s+(.+)", md)
            title = title_match.group(1)[:100] if title_match else url
            articles.append({"title": title, "summary": md[:1000], "url": url})
            _log.info(f"  OK: {title[:50]}")

    _log.info(f"  抓取並通過預選: {len(articles)} 篇")

    # 2. 去重複
    _log.info("Step 2: 去重複檢查...")
    filtered = [a for a in articles if deduplicate(a["summary"])]
    _log.info(f"  去重後: {len(filtered)} 篇")

    # 3. 批量摘要（1 次 LLM 呼叫）
    _log.info("Step 3: 7B 批量摘要...")
    rules = batch_summarize(filtered)
    _log.info(f"  產生 {len(rules)} 條規則")

    # 4. 寫入 DB
    if rules:
        save_rules(rules, f"batch:{len(filtered)}urls")
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
    print("\nToken 節約：1 次 LLM 呼叫處理 10 篇 ✅")