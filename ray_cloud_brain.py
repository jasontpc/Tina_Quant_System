# -*- coding: utf-8 -*-
"""
ray_cloud_brain.py — 雲端搜尋 + 本地 LLM 整合系統

分工：
- web_search: 連網搜尋（Tavily）
- ray-v1 (1.5B): 快速策略決策
- ray-deep-v1 (7B): 深度風控審核
"""
import sys, sqlite3, json, time, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
DB = 'ray_wisdom.db'

# ============================================================
# 1. 搜尋（使用 Jina AI 抓取內容）
# ============================================================

def fetch_web_content(query):
    """使用 Jina AI 抓取網頁"""
    try:
        import urllib.parse
        encoded_query = urllib.parse.quote(query)
        jina_url = f"https://r.jina.ai/{encoded_query}"
        import urllib.request
        req = urllib.request.Request(jina_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")[:2000]
    except Exception as e:
        return f"Error: {str(e)}"

# ============================================================
# 2. 本地 LLM 決策（ray-v1）
# ============================================================

def local_decision(symbol, cloud_data, indicators, strategies):
    prompt = f"""你是 Ray 本地量化大腦（ray-v1）。

標的：{symbol}

【雲端數據】
{cloud_data}

【本地技術指標】
{indicators}

【歷史策略】
{strategies}

輸出 JSON（只輸出JSON）：
{{"signal": "BUY/SELL/WATCH", "confidence": 0.0-1.0, "reason": "原因"}}
"""
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": "ray-v1",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }, timeout=60)
        return resp.json().get("message", {}).get("content", "")
    except Exception as e:
        return f"Error: {str(e)}"

# ============================================================
# 3. 風控審核（ray-deep-v1）
# ============================================================

def risk_review(symbol, decision, indicators):
    prompt = f"""你是 Ray 風控官（ray-deep-v1）。

標的：{symbol}
決策：{decision}
指標：{indicators}

Math Gate: Sharpe >= 1.5, MDD <= 20%

輸出 JSON（只輸出JSON）：
{{"approved": true/false, "risk_score": 0.0-1.0, "warnings": ["警告"], "adjustments": "建議"}}
"""
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": "ray-deep-v1",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }, timeout=120)
        return resp.json().get("message", {}).get("content", "")
    except Exception as e:
        return f"Error: {str(e)}"

# ============================================================
# 4. 整合分析
# ============================================================

def analyze(symbol, indicators, strategies):
    print(f"=== 分析 {symbol} ===")
    print()

    # 搜尋
    print("1. 搜尋趨勢...")
    search_query = f"{symbol} stock market trend analysis"
    trend_data = fetch_web_content(search_query)
    print(f"   {trend_data[:80]}...")

    # ray-v1 決策
    print()
    print("2. ray-v1 決策...")
    decision = local_decision(symbol, trend_data, indicators, strategies)
    print(f"   {decision[:100]}...")

    # ray-deep-v1 風控
    print()
    print("3. ray-deep-v1 風控...")
    risk = risk_review(symbol, decision, indicators)
    print(f"   {risk[:100]}...")

    # 寫入
    print()
    print("4. 寫入...")
    m = re.search(r'\{[\s\S]*\}', decision)
    signal_json = json.loads(m.group()) if m else None

    if signal_json:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        c.execute('''INSERT INTO signals_log
            (timestamp, symbol, source, score, sharpe_30d, mdd_30d, win_rate_30d, signal_tag, approved, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (now, symbol, "CLOUD_BRAIN", signal_json.get("confidence", 0),
             indicators.get("sharpe", 0), 0, 0,
             signal_json.get("signal", "WATCH"), 0,
             json.dumps({"trend": trend_data[:300], "decision": decision, "risk": risk})))
        conn.commit()
        conn.close()
        print(f"   {signal_json.get('signal')} (conf={signal_json.get('confidence')})")

    return {"decision": decision, "risk": risk}

if __name__ == "__main__":
    print("=== 雲端搜尋 + 本地 LLM 整合 ===")
    print()
    symbol = "VOO"
    indicators = {"rsi": 58.6, "sharpe": 2.16, "price": 679.52}
    strategies = "MOMENTUM: Sharpe=1.18, EMA_CROSS: Sharpe=0.77"
    result = analyze(symbol, indicators, strategies)
    print()
    print("=== 完成 ===")