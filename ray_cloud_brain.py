# -*- coding: utf-8 -*-
"""
ray_cloud_brain.py — 雲端搜尋 + 本地 LLM 整合系統
已啟用 Tavily API

分工（2026-05-12 重構）：
- Tavily: 連網搜尋趨勢 ✅
- Router Layer 3 (MiniMax + web): 處理 Tavily 數據（帶 web fetch 能力）
- Router Layer 2 (MiniMax): 深度風控審核
- Router Layer 1 (ray-v1): 備用快速決策

所有 LLM 調用走 llm_router.py
"""
import sys, sqlite3, json, time, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests

TAVILY_KEY = "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"
DB = 'ray_wisdom.db'

# ── Router 導入 ──────────────────────────────────────────────
try:
    from llm_router import get_router
    ROUTER = get_router()
    HAS_ROUTER = True
except ImportError:
    ROUTER = None
    HAS_ROUTER = False

OLLAMA_URL = "http://localhost:11434/api/chat"
LOCAL_FAST = "ray-deep-v1"  # Jo 指定全本地分析走 ray-deep

# ════════════════════════════════════════════════════════════
# 1. Tavily 搜尋（保持不變）
# ════════════════════════════════════════════════════════════

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
            return resp.json().get("results", [])
    except Exception as e:
        pass
    return []

def tavily_trend(symbol):
    results = tavily_search(f"{symbol} stock trend analysis 2024", max_results=5)
    if results:
        return "\n".join([f"- {r.get('title', '')}: {r.get('content', '')[:100]}" for r in results[:3]])
    return "無搜尋結果"

def tavily_sentiment(symbol):
    results = tavily_search(f"{symbol} stock market sentiment news", max_results=5)
    if results:
        return "\n".join([f"- {r.get('content', '')[:100]}" for r in results[:3]])
    return "無搜尋結果"

# ════════════════════════════════════════════════════════════
# 2. 決策（走 Router Layer 3 → MiniMax）
#    因為 Tavily 數據是 web-sourced，屬於 Layer 3
# ════════════════════════════════════════════════════════════

def _ollama_fallback(model, prompt, timeout=60):
    import requests
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "temperature": 0.2,
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "")
    except Exception as e:
        return f"Error: {e}"

def local_decision(symbol, cloud_data, indicators, strategies):
    prompt = (
        f"你是 Ray 本地量化大腦。\n\n"
        f"標的：{symbol}\n\n"
        f"【雲端搜尋數據】\n{cloud_data}\n\n"
        f"【本地技術指標】\n{indicators}\n\n"
        f"【歷史策略表現】\n{strategies}\n\n"
        f"根據以上數據，給出交易建議。\n\n"
        '輸出 JSON（只輸出JSON）：{"signal": "BUY/SELL/WATCH", "confidence": 0.0-1.0, "reason": "原因"}'
    )

    # ── 走 Router Layer 3（Tavily 數據 = web-sourced）──────────
    if ROUTER and HAS_ROUTER:
        try:
            result = ROUTER.web(prompt=prompt)
            print(f"    [Router.web/L3] response: {result[:80]}...")
            return result
        except Exception as e:
            print(f"    [Router.web failed: {e}], falling back to Ollama")

    # 降級：直接走 Ollama ray-v1
    return _ollama_fallback(LOCAL_FAST, prompt, timeout=60)

# ════════════════════════════════════════════════════════════
# 3. 風控審核（走 Router Layer 2 → MiniMax）
# ════════════════════════════════════════════════════════════

def risk_review(symbol, decision, indicators):
    prompt = (
        f"你是 Ray 風控官。\n\n"
        f"標的：{symbol}\n"
        f"決策：{decision}\n"
        f"指標：{indicators}\n\n"
        f"Math Gate: Sharpe >= 1.5, MDD <= 20%\n\n"
        '輸出 JSON（只輸出JSON）：{"approved": true/false, "risk_score": 0.0-1.0, "warnings": ["警告"], "adjustments": "建議"}'
    )

    # ── 走 Router Layer 2（深度風控）─────────────────────────
    if ROUTER and HAS_ROUTER:
        try:
            result = ROUTER.deep(prompt=prompt)
            print(f"    [Router.deep/L2] response: {result[:80]}...")
            return result
        except Exception as e:
            print(f"    [Router.deep failed: {e}], falling back to Ollama")

    # 降級：直接走 Ollama ray-deep-v1
    return _ollama_fallback("ray-deep-v1", prompt, timeout=120)

# ════════════════════════════════════════════════════════════
# 4. 整合分析
# ════════════════════════════════════════════════════════════

def analyze(symbol, indicators, strategies):
    print(f"=== 分析 {symbol} (Cloud Brain + Router) ===")
    print(f"Router: {'ACTIVE' if (ROUTER and HAS_ROUTER) else 'NOT AVAILABLE'}")
    print()

    # Tavily 趨勢
    print("1. Tavily 趨勢搜尋...")
    trend = tavily_trend(symbol)
    print(f"   {trend[:80]}...")

    # Tavily 情緒
    print("\n2. Tavily 情緒搜尋...")
    sentiment = tavily_sentiment(symbol)
    print(f"   {sentiment[:80]}...")

    cloud_data = f"趨勢：\n{trend}\n\n情緒：\n{sentiment}"

    # Layer 3 決策
    print("\n3. Router.web (L3) — Tavily 數據分析...")
    decision = local_decision(symbol, cloud_data, indicators, strategies)

    # Layer 2 風控
    print("\n4. Router.deep (L2) — 風控審核...")
    risk = risk_review(symbol, decision, indicators)

    # 解析寫入
    print("\n5. 寫入資料庫...")
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
    else:
        print(f"   ⚠️ 無法解析 decision: {decision[:100]}")

    return {"decision": decision, "risk": risk}

# ════════════════════════════════════════════════════════════
# CLI
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=== 雲端搜尋 + Router L3/L2 整合 ===")
    print()

    symbol = "NVDA"
    indicators = {"rsi": 56.5, "sharpe": 2.16, "price": 219.44}
    strategies = "MOMENTUM: Sharpe=1.30, RSI2: Sharpe=0.52"

    result = analyze(symbol, indicators, strategies)

    print("\n=== 完成 ===")