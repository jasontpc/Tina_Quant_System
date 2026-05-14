# -*- coding: utf-8 -*-
"""
ray_web_collector.py — 大師人格增強版 (v2)
每日 17:00 全球休市期執行

功能：
1. i9 CPU 關鍵字過濾（經濟型 Token）
2. 抓取五位大師最新文章
3. 7B 蒸餾成 4B 專用「天條」
4. 存入 wisdom_corrections.web_auto
5. RAM 預載：開盤前 30 分鐘將 web_auto 內容載入記憶體
"""

import json, os, re, sqlite3, sys, time, requests
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

AGENTS_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(AGENTS_DIR, "ray_wisdom.db")
RAM_CACHE = os.path.join(AGENTS_DIR, "master_insights_ram.json")
MODEL_7B = "qwen2.5:7b"
OLLAMA_URL = "http://localhost:11434/api/chat"
TAVILY_KEY = os.environ.get("TAVEL_API_KEY", "") or os.environ.get("TAVILY_API_KEY", "")

# ── 五位大師關鍵字（i9 CPU 正則預過濾）─────────────────────────
MASTER_FILTERS = {
    "Taleb":  ["tail risk","black swan","fat tail","volatility","fragile","antifragile","肥尾","黑天鵝","尾部風險"],
    "Thorp":  ["kelly criterion","expected value","bet sizing","probability","凱利","凱利公式","勝率","部位的置"],
    "Simons": ["regime switch","hmm","momentum","trend","趨勢","狀態切換","統計優勢","alpha"],
    "Connors":["mean reversion","rsi2","oversold","均值回歸","超賣","彈簧","均值收斂"],
    "Dalio":  ["correlation","diversification","portfolio","多樣化","相關性","風險分散","組合"],
}

def cpu_filter(text):
    """i9 CPU cheap keyword scan - no LLM token cost."""
    text_lower = text.lower()
    hits = {}
    for master, keywords in MASTER_FILTERS.items():
        matched = [kw for kw in keywords if kw.lower() in text_lower]
        if matched:
            hits[master] = matched
    return hits

def fetch_tavily(query, max_results=5):
    if not TAVILY_KEY:
        return None
    try:
        resp = requests.post(
            "https://api.tavily.com/search",
            json={"query": query, "max_results": max_results, "api_key": TAVILY_KEY},
            timeout=20
        )
        if resp.status_code == 200:
            return resp.json().get("results", [])
    except:
        pass
    return None

# ── RayIntelligenceEnhancer: 7B → 4B 蒸餾 ──────────────────
class RayIntelligenceEnhancer:
    def __init__(self):
        self.ollama_url = OLLAMA_URL
        self.model_7b = MODEL_7B

    def distill_for_4b(self, raw_text, master):
        """7B 蒸餾成 4B 的『天條』（If-Then 格式）"""
        prompt = f"""你是 {master} 交易哲學蒸餾專家，同時是 Qwen3.5-4B 的教官。

請將以下文章內容蒸餾成 3 條「If-Then 規則」——這是 4B 必須無歧義執行的作戰指令。

{master} 文章內容：
{raw_text[:2000]}

輸出格式（只輸出 JSON陣列）：
[
  {{"if": "條件描述", "then": "禁止/執行動作", "master": "{master}", "priority": 1-3}}
]

優先級：1=最高（立即執行），2=標準，3=謹慎參考
"""
        try:
            resp = requests.post(self.ollama_url, json={
                "model": self.model_7b,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": 0.2, "top_p": 0.85, "num_predict": 300}
            }, timeout=90)
            return resp.json().get("message", {}).get("content", "")
        except Exception as e:
            return f"ERROR: {e}"

def parse_if_then(raw):
    """解析 7B 的 If-Then JSON 回應"""
    if not raw or raw.startswith('ERROR:'):
        return []
    try:
        return json.loads(raw)
    except:
        match = re.search(r'\[[\s\S]+\]', raw)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
    return []

# ── RAM 預載功能（32GB RAM 暴力掃描）────────────────────────
def preload_ram_cache():
    """開盤前 30 分鐘：將所有 web_auto 載入 32GB RAM"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT web_auto FROM wisdom_corrections WHERE web_auto IS NOT NULL")
    records = [json.loads(row[0]) for row in c.fetchall() if row[0]]
    conn.close()

    cache = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "insights": records,
        "count": len(records)
    }
    with open(RAM_CACHE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    print(f"  [RAM PRELOAD] {len(records)} insights cached for market open")
    return cache

def get_cached_insights(symbol=None):
    """瞬檢索：回傳與 symbol 相關的大師錦囊（<100ms）"""
    try:
        with open(RAM_CACHE, 'r', encoding='utf-8') as f:
            cache = json.load(f)
    except:
        return []

    insights = cache.get("insights", [])
    if not symbol:
        return insights

    # 符號相關性過濾（簡單關鍵字匹配）
    filtered = [
        i for i in insights
        if symbol.upper() in str(i).upper()
        or "GLOBAL" in str(i).get("symbol", "GLOBAL")
        or "AUTO" in str(i).get("symbol", "")
    ]
    return filtered

# ── 主程式 ──────────────────────────────────────────────────
print("=" * 60)
print("Ray 大師人格增強版 (v2) — 17:00 全球休市期")
print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

warnings = []
enhancer = RayIntelligenceEnhancer()

# Step 1: 抓取五位大師文章
masters_queries = {
    "Taleb":   "Nassim Taleb finance risk volatility 2026",
    "Thorp":   "Edward Thorp kelly criterion investing 2026",
    "Simons":  "Jim Simons Renaissance regime switch momentum 2026",
    "Connors": "Larry Connors mean reversion RSI2 strategy 2026",
    "Dalio":   "Ray Dalio diversification portfolio correlation 2026",
}

print("\n[1/4] i9 CPU 抓取大師文章（關鍵字預過濾）...")
fetch_results = {}
for master, query in masters_queries.items():
    results = fetch_tavily(query, max_results=3)
    if not results:
        results = fetch_tavily(query.replace(" 2026", ""), max_results=3)
    fetch_results[master] = results or []
    print(f"  [{master}] {len(fetch_results[master])} 篇")

# Step 2: CPU 過濾 + 7B 蒸餾
print("\n[2/4] 7B 蒸餾成 If-Then 天條...")
for master, results in fetch_results.items():
    if not results:
        # Fallback：建立通用大師警示
        warnings.append({
            "rule": f"If [市場異動] Then 遵循 {master} 核心原則",
            "master": master,
            "priority": 2,
            "risk_level": "MEDIUM",
            "source": "fallback_generic"
        })
        continue

    for r in results[:1]:  # 每位大師只蒸餾最重要的 1 篇
        snippet = f"{r.get('title','')}. {r.get('content','')}"
        hits = cpu_filter(snippet)
        print(f"  [{master}] keywords: {list(hits.get(master, []))[:3]}")

        raw = enhancer.distill_for_4b(snippet[:1500], master)
        rules = parse_if_then(raw)
        for rule in rules:
            rule["source"] = r.get('url', 'tavily')
            rule["risk_level"] = "HIGH" if rule.get("priority", 2) == 1 else "MEDIUM"
            warnings.append(rule)

        if not rules:
            warnings.append({
                "rule": f"If [異常] Then 謹慎 {master} 原則",
                "master": master,
                "priority": 2,
                "risk_level": "MEDIUM",
                "source": "no_rule_generated"
            })

print(f"\n  取得 {len(warnings)} 條天條")

# Step 3: 更新 DB
print("\n[3/4] 更新 wisdom_corrections.web_auto...")
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
for w in warnings:
    try:
        c.execute('''INSERT INTO wisdom_corrections
                     (axiom_id, symbol, diagnosis, corrected_json, confidence, meta_label, web_auto)
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (f"auto_{int(time.time())}",
             "AUTO",
             w.get("rule", ""),
             json.dumps(w, ensure_ascii=False),
             0.85 if w.get("priority", 2) == 1 else 0.75,
             f"web_auto_{w.get('master','unknown')}",
             json.dumps(w, ensure_ascii=False)))
    except:
        pass
conn.commit()
conn.close()
print(f"  Updated {len(warnings)} web_auto records")

# Step 4: RAM 預載
print("\n[4/4] 32GB RAM 預載大師錦囊...")
cache = preload_ram_cache()

print("\n=== 完成 ===")
print(f"Insights cached: {cache['count']}")
print(f"RAM cache: {RAM_CACHE}")

# Print top rules
for w in sorted(warnings, key=lambda x: x.get("priority", 3))[:5]:
    print(f"  [{w['master']}] P{w.get('priority','?')}: {w.get('rule','?')[:60]}")