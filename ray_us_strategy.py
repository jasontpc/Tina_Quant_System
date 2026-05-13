# -*- coding: utf-8 -*-
"""
ray_us_strategy.py — 15:00 美股策略分析
使用 ray-deep-v1 分析當日美股行情，產出策略建議
"""
import sys, json, time, requests
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

AGENTS_DIR = r"C:\Users\USER\.openclaw\agents\ray"
DB = f"{AGENTS_DIR}\\ray_wisdom.db"
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "ray-deep-v1"

def ollama_call(model, messages, timeout=90):
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.2, "top_p": 0.85, "num_predict": 400}
        }, timeout=timeout)
        return resp.json().get("message", {}).get("content", "")
    except Exception as e:
        return f"ERROR: {e}"

def get_market_data():
    try:
        import yfinance as yf
        symbols = ["^GSPC", "^IXIC", "^DJI", "^VIX", "CL=F"]
        data = {}
        for sym in symbols:
            try:
                h = yf.Ticker(sym).history(period="5d")
                if len(h) >= 2:
                    cur = h['Close'].iloc[-1]
                    prev = h['Close'].iloc[-2]
                    chg = (cur - prev) / prev * 100
                    data[sym] = {"price": cur, "change": chg}
            except:
                pass
        return data
    except Exception as e:
        return {}

def main():
    print(f"[{time.strftime('%H:%M')}] Ray US Strategy Analysis (ray-deep-v1)")
    print("=" * 60)

    market = get_market_data()
    if not market:
        print("No market data, using general analysis")
        market_context = "Unable to fetch market data"
    else:
        spx = market.get("^GSPC", {})
        ndx = market.get("^IXIC", {})
        vix = market.get("^VIX", {})
        oil = market.get("CL=F", {})
        market_context = json.dumps(market, indent=2)

    prompt = f"""你是 Ray-US 美股策略分析師（ray-deep-v1）。

當日市場數據：
{market_context}

任務：
1. 根據 VIX、原油、S&P500 判斷當前市場狀態（多頭/空頭/震盪）
2. 找出 RS | MDD 最佳的 3 個標的
3. 產出 3 個 WATCH 和 3 個 BUY 信號
4. 警示可能的黑天鵝風險

輸出格式（JSON）：
{{
  "market_status": "bullish|bearish|volatile",
  "vix_level": "low|medium|high",
  "signals": {{
    "watch": ["標的1", "標的2", "標的3"],
    "buy": ["標的1", "標的2", "標的3"]
  }},
  "risk_alert": "風險描述",
  "confidence": 0.0-1.0
}}

只輸出 JSON，嚴禁其他文字。"""

    result = ollama_call(MODEL, [{"role": "user", "content": prompt}])
    print(result if result else "No response")

    # Save to DB
    try:
        import sqlite3
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS wisdom_corrections
            (id INTEGER PRIMARY KEY, axiom_id TEXT, symbol TEXT, diagnosis TEXT,
             corrected_json TEXT, confidence REAL, meta_label TEXT, created_at TEXT, web_auto TEXT)''')
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO wisdom_corrections (axiom_id, symbol, diagnosis, corrected_json, confidence, meta_label, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (f"us_strat_{time.strftime('%Y%m%d%H%M')}", "US_MARKET", "美股策略分析", result, 0.75, "ray-deep-v1", now))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB save error: {e}")

    print("\n=== 完成 ===")

if __name__ == "__main__":
    main()