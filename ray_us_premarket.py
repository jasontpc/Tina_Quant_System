# -*- coding: utf-8 -*-
"""
ray_us_premarket.py — 21:00 美股盤前宏觀分析
使用 qwen2.5:7b 分析明日美股開盤策略，減少 MiniMax 用量
"""
import sys, json, time, requests
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

AGENTS_DIR = r"C:\Users\USER\.openclaw\agents\ray"
DB = f"{AGENTS_DIR}\\ray_wisdom.db"
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:7b"

def ollama_call(model, messages, timeout=90):
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.15, "top_p": 0.8, "num_predict": 500}
        }, timeout=timeout)
        return resp.json().get("message", {}).get("content", "")
    except Exception as e:
        return f"ERROR: {e}"

def get_macro_data():
    try:
        import yfinance as yf
        symbols = ["^GSPC", "^IXIC", "^VIX", "CL=F", "^TNX", "DXY"]
        data = {}
        names = {"^GSPC": "SPX", "^IXIC": "NDX", "^VIX": "VIX", "CL=F": "WTI", "^TNX": "US10Y", "DXY": "DXY"}
        for sym in symbols:
            try:
                h = yf.Ticker(sym).history(period="5d")
                if len(h) >= 2:
                    cur = h['Close'].iloc[-1]
                    prev = h['Close'].iloc[-2]
                    chg = (cur - prev) / prev * 100
                    data[names.get(sym, sym)] = {"price": round(cur, 2), "change": round(chg, 2)}
            except:
                pass
        return data
    except:
        return {}

def main():
    print(f"[{time.strftime('%H:%M')}] Ray US Pre-Market Macro (qwen2.5:7b)")
    print("=" * 60)

    macro = get_macro_data()
    context = json.dumps(macro, indent=2) if macro else "No data"

    prompt = f"""你是 Ray-US 美股盤前宏觀分析師（qwen2.5:7b）。

當日宏觀數據：
{context}

任務：
1. 分析 VIX（<20=穩定, 20-30=注意, >30=恐慌）
2. 分析 WTI 原油（<90=正常, 90-100=通膨注意, >100=危險）
3. 分析美債殖利率（倒掛=經濟衰退風險）
4. 產出明日開盤策略：

輸出格式（JSON）：
{{
  "vix_analysis": "描述",
  "inflation_risk": "low|medium|high",
  "recession_signal": true|false,
  "tomorrow_strategy": "aggressive|neutral|defensive",
  "position_adjustment": "描述",
  "confidence": 0.0-1.0
}}

只輸出 JSON，嚴禁其他文字。"""

    result = ollama_call(MODEL, [{"role": "user", "content": prompt}])
    print(result if result else "No response")

    # Save
    try:
        import sqlite3
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS wisdom_corrections
            (id INTEGER PRIMARY KEY, axiom_id TEXT, symbol TEXT, diagnosis TEXT,
             corrected_json TEXT, confidence REAL, meta_label TEXT, created_at TEXT, web_auto TEXT)''')
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO wisdom_corrections (axiom_id, symbol, diagnosis, corrected_json, confidence, meta_label, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (f"us_prem_{time.strftime('%Y%m%d%H%M')}", "US_PREMARKET", "美股盤前宏觀", result, 0.8, "qwen2.5:7b", now))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB save error: {e}")

    print("\n=== 完成 ===")

if __name__ == "__main__":
    main()