# -*- coding: utf-8 -*-
"""
ray_minimax_cloud.py — MiniMax 負責連網抓大數據 + 趨勢分析
本地 LLM (ray-v1) 負責策略決策

分工設計：
- MiniMax: 連網搜尋、趨勢分析、情緒分析、新聞摘要
- 本地 LLM: RAG 檢索、策略提案、風險決策
"""
import sys, os, sqlite3, json, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
MINIMAX_API = "sk-cp-d1DZZxzGpsijgC4bJaTl6_mrDJp376z9iwXyRnXRq8wYZOXBKRqFL2YVSE6nVwJ0yi14yjhh6fPCwvtLT5J53KNdfLMSJgLIjfcCqTHpja08L58oTe0wztg"
MINIMAX_BASE = "https://api.minimax.chat"

DB = 'ray_wisdom.db'

# ============================================================
# 1. MiniMax 連網功能
# ============================================================

def minimax_search(query, num_results=5):
    """MiniMax 搜尋引擎（Web Search）"""
    try:
        resp = requests.post(
            f"{MINIMAX_BASE}/v1/text/chatcompletion_pro",
            headers={"Authorization": f"Bearer {MINIMAX_API}"},
            json={
                "model": "MiniMax-Text-01",
                "messages": [{
                    "role": "user",
                    "content": f"搜尋以下主題並回傳要點：{query}"
                }],
                "max_tokens": 1000,
                "temperature": 0.3
            },
            timeout=30
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception as e:
        return f"搜尋失敗: {str(e)}"
    return None

def minimax_news_summary(news_text):
    """MiniMax 新聞摘要"""
    try:
        resp = requests.post(
            f"{MINIMAX_BASE}/v1/text/chatcompletion_pro",
            headers={"Authorization": f"Bearer {MINIMAX_API}"},
            json={
                "model": "MiniMax-Text-01",
                "messages": [{
                    "role": "user",
                    "content": f"摘要以下新聞並提取關鍵數據和趨勢：\n\n{news_text[:3000]}"
                }],
                "max_tokens": 500,
                "temperature": 0.2
            },
            timeout=30
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception as e:
        return f"摘要失敗: {str(e)}"
    return None

def minimax_trend_analysis(symbol, price_data, market_context):
    """MiniMax 趨勢分析"""
    try:
        prompt = f"""分析 {symbol} 的趨勢：

市場背景：
{market_context}

價格數據：
{price_data}

輸出 JSON：
{{"trend": "UP/DOWN/SIDEWAYS", "strength": 0.0-1.0, "key_levels": ["支撐", "壓力"], "outlook": "分析"}}
"""
        resp = requests.post(
            f"{MINIMAX_BASE}/v1/text/chatcompletion_pro",
            headers={"Authorization": f"Bearer {MINIMAX_API}"},
            json={
                "model": "MiniMax-Text-01",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 800,
                "temperature": 0.3
            },
            timeout=30
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception as e:
        return f"趨勢分析失敗: {str(e)}"
    return None

def minimax_sentiment(symbol):
    """MiniMax 情緒分析"""
    try:
        # 先搜尋相關新聞
        search_results = minimax_search(f"{symbol} 股票 市場 情緒")
        if not search_results:
            return None

        resp = requests.post(
            f"{MINIMAX_BASE}/v1/text/chatcompletion_pro",
            headers={"Authorization": f"Bearer {MINIMAX_API}"},
            json={
                "model": "MiniMax-Text-01",
                "messages": [{
                    "role": "user",
                    "content": f"分析以下關於 {symbol} 的市場情緒（多/空/中立）：\n\n{search_results[:2000]}"
                }],
                "max_tokens": 300,
                "temperature": 0.2
            },
            timeout=30
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception as e:
        return f"情緒分析失敗: {str(e)}"
    return None

# ============================================================
# 2. 本地 LLM 功能（ray-v1）
# ============================================================

def local_llm_decision(symbol, minimax_data, local_indicators, strategies):
    """本地 LLM 綜合決策"""
    prompt = f"""你是 Ray 本地量化大脑（ray-v1 1.5B）。

標的：{symbol}

【MiniMax 雲端分析】
{minimax_data}

【本地技術指標】
{local_indicators}

【歷史策略表現】
{strategies}

根據以上數據，輸出交易決策：

輸出 JSON：
{{"signal": "BUY/SELL/WATCH", "confidence": 0.0-1.0, "position_size": 0-100%, "stop_loss": "價位", "take_profit": "價位", "reason": "決策原因"}}
"""
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": "ray-v1",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }, timeout=60)
        return resp.json().get("message", {}).get("content", "")
    except Exception as e:
        return f"本地 LLM 決策失敗: {str(e)}"

def local_llm_risk_check(decision, indicators):
    """本地 LLM 風險審核（ray-deep-v1）"""
    prompt = f"""你是 Ray 風控官（ray-deep-v1 7B）。

交易決策：
{decision}

技術指標：
{indicators}

審核這個決策是否通過 Math Gate（Sharpe >= 1.5, MDD <= 20%）：

輸出 JSON：
{{"approved": true/false, "risk_score": 0.0-1.0, "warnings": ["風險警告"], "adjustments": "調整建議"}}
"""
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": "ray-deep-v1",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }, timeout=120)
        return resp.json().get("message", {}).get("content", "")
    except Exception as e:
        return f"風控審核失敗: {str(e)}"

# ============================================================
# 3. 整合分析流程
# ============================================================

def analyze_with_cloud(symbol, local_indicators, strategies):
    """雲端 + 本地整合分析"""

    print(f"=== 分析 {symbol} ===")
    print()

    # Step 1: MiniMax 趨勢分析
    print("1. MiniMax 趨勢分析...")
    trend = minimax_trend_analysis(
        symbol,
        f"RSI: {local_indicators.get('rsi')}, Sharpe: {local_indicators.get('sharpe')}",
        "市場高檔，AI 概念股強勢"
    )
    print(f"   趨勢: {trend[:100] if trend else '失敗'}...")

    # Step 2: MiniMax 情緒分析
    print()
    print("2. MiniMax 情緒分析...")
    sentiment = minimax_sentiment(symbol)
    print(f"   情緒: {sentiment[:100] if sentiment else '失敗'}...")

    # Step 3: 組合雲端數據
    minimax_data = f"趨勢分析：{trend}\n\n情緒分析：{sentiment}"

    # Step 4: 本地 LLM 決策
    print()
    print("3. 本地 LLM 決策（ray-v1）...")
    decision = local_llm_decision(symbol, minimax_data, local_indicators, strategies)
    print(f"   決策: {decision[:200] if decision else '失敗'}...")

    # Step 5: 本地 LLM 風控審核
    print()
    print("4. 風控審核（ray-deep-v1）...")
    risk_check = local_llm_risk_check(decision, local_indicators)
    print(f"   審核: {risk_check[:200] if risk_check else '失敗'}...")

    # Step 6: 寫入 DB
    print()
    print("5. 寫入資料庫...")
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    now = time.strftime("%Y-%m-%d %H:%M:%S")

    # 解析決策 JSON
    import re
    signal_json = None
    m = re.search(r'\{[\s\S]*\}', decision)
    if m:
        try:
            signal_json = json.loads(m.group())
        except:
            pass

    if signal_json:
        c.execute('''INSERT INTO signals_log
            (timestamp, symbol, source, score, sharpe_30d, mdd_30d, win_rate_30d, signal_tag, approved, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (now, symbol, "MINIMAX_CLOUD", signal_json.get("confidence", 0),
             local_indicators.get("sharpe", 0), 0, 0,
             signal_json.get("signal", "WATCH"), 0,
             json.dumps({"trend": trend, "sentiment": sentiment, "decision": decision, "risk_check": risk_check})))
        conn.commit()
        print(f"   已寫入: {signal_json.get('signal')} (conf={signal_json.get('confidence')})")

    conn.close()

    return {
        "symbol": symbol,
        "trend": trend,
        "sentiment": sentiment,
        "decision": decision,
        "risk_check": risk_check
    }

# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    print("=== MiniMax 雲端 + 本地 LLM 整合分析 ===")
    print()

    # 測試符號
    symbol = "NVDA"

    # 模擬本地指標
    local_indicators = {
        "rsi": 58.3,
        "sharpe": 2.16,
        "price": 219.44,
        "ma20": 204.69
    }

    # 模擬策略
    strategies = "MOMENTUM_5: Sharpe=1.18, RSI2: Sharpe=0.52"

    result = analyze_with_cloud(symbol, local_indicators, strategies)

    print()
    print("=== 完成 ===")