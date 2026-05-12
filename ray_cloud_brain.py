# -*- coding: utf-8 -*-
"""
ray_cloud_brain.py — 雲端搜尋 + 本地 LLM 整合系統
已啟用 Tavily API

分工：
- Tavily: 連網搜尋趨勢（已啟用 ✅）
- ray-v1 (1.5B): 快速策略決策
- ray-deep-v1 (7B): 深度風控審核
"""
import sys, sqlite3, json, time, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
TAVILY_KEY = "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"
DB = 'ray_wisdom.db'

# ============================================================
# 1. Tavily 搜尋（已啟用）
# ============================================================

def tavily_search(query, max_results=5):
    """Tavily 搜尋"""
    try:
        resp = requests.post(
            "https://api.tavily.com/search",
            json={
                "query": query,
                "api_key": TAVILY_KEY,
                "max_results": max_results,
                "topic": "finance"
            },
            timeout=15
        )
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            return results
    except Exception as e:
        return []
    return []

def tavily_trend(symbol):
    """搜尋趨勢"""
    results = tavily_search(f"{symbol} stock trend analysis 2024", max_results=5)
    if results:
        summary = []
        for r in results[:3]:
            summary.append(f"- {r.get('title', '')}: {r.get('content', '')[:100]}")
        return "\n".join(summary)
    return "無搜尋結果"

def tavily_sentiment(symbol):
    """搜尋情緒"""
    results = tavily_search(f"{symbol} stock market sentiment news", max_results=5)
    if results:
        summary = []
        for r in results[:3]:
            summary.append(f"- {r.get('content', '')[:100]}")
        return "\n".join(summary)
    return "無搜尋結果"

# ============================================================
# 2. 本地 LLM 決策（ray-v1）
# ============================================================

def local_decision(symbol, cloud_data, indicators, strategies):
    prompt = f"""你是 Ray 本地量化大腦（ray-v1）。

標的：{symbol}

【雲端搜尋數據】
{cloud_data}

【本地技術指標】
{indicators}

【歷史策略表現】
{strategies}

根據以上數據，給出交易建議。

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

    # Tavily 趨勢
    print("1. Tavily 趨勢搜尋...")
    trend = tavily_trend(symbol)
    print(f"   {trend[:80]}...")

    # Tavily 情緒
    print()
    print("2. Tavily 情緒搜尋...")
    sentiment = tavily_sentiment(symbol)
    print(f"   {sentiment[:80]}...")

    cloud_data = f"趨勢：\n{trend}\n\n情緒：\n{sentiment}"

    # ray-v1 決策
    print()
    print("3. ray-v1 決策...")
    decision = local_decision(symbol, cloud_data, indicators, strategies)
    print(f"   {decision[:100]}...")

    # ray-deep-v1 風控
    print()
    print("4. ray-deep-v1 風控...")
    risk = risk_review(symbol, decision, indicators)
    print(f"   {risk[:100]}...")

    # 解析寫入
    print()
    print("5. 寫入資料庫...")
    m = re.search(r'\{[\s\S]*\}', decision)
    signal_json = json.loads(m.group()) if m else None

    if signal_json:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        c.execute('''INSERT INTO signals_log
            (timestamp, symbol, source, score, sharpe_30d, mdd_30d, win_rate_30d, signal_tag, approved, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (now, symbol, "TAVILY_CLOUD", signal_json.get("confidence", 0),
             indicators.get("sharpe", 0), 0, 0,
             signal_json.get("signal", "WATCH"), 0,
             json.dumps({"trend": trend[:300], "sentiment": sentiment[:300], "decision": decision, "risk": risk})))
        conn.commit()
        conn.close()
        print(f"   ✅ {signal_json.get('signal')} (conf={signal_json.get('confidence')})")

    return {"decision": decision, "risk": risk}

# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    print("=== 雲端搜尋 + 本地 LLM 整合（Tavily 已啟用）===")
    print()

    symbol = "NVDA"
    indicators = {"rsi": 56.5, "sharpe": 2.16, "price": 219.44}
    strategies = "MOMENTUM: Sharpe=1.30, RSI2: Sharpe=0.52"

    result = analyze(symbol, indicators, strategies)

    print()
    print("=== 完成 ===")