# -*- coding: utf-8 -*-
"""
ray_us_strategy_analysis.py — 15:00 美股策略深度分析
使用 ray-deep-v1 執行長波段歸因，存入 wisdom_corrections 供 4B 固化
"""
import sys, json, time, sqlite3, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

AGENTS_DIR = r"C:\Users\USER\.openclaw\agents\ray"
DB = os.path.join(AGENTS_DIR, "ray_wisdom.db")
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "ray-deep-v1"

# ── Helper ──────────────────────────────────────────────────
def ollama_raw(model, prompt, temperature=0.2, num_predict=400, timeout=90):
    try:
        import requests
        resp = requests.post(OLLAMA_URL, json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": temperature, "top_p": 0.85, "num_predict": num_predict}
        }, timeout=timeout)
        return resp.json().get("message", {}).get("content", "")
    except Exception as e:
        return f"ERROR: {e}"

def load_forbidden_rules():
    """從 wisdom_corrections 讀取 ray-deep-v1 產出的禁止規則"""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''SELECT diagnosis FROM wisdom_corrections
                 WHERE meta_label='ray-deep-v1' AND diagnosis LIKE 'If%'
                 ORDER BY created_at DESC LIMIT 5''')
    rules = [r[0] for r in c.fetchall()]
    conn.close()
    return "\n".join([f"- {r}" for r in rules]) if rules else "（尚無禁止規則）"

def get_market_snapshot():
    """抓取當日美股關鍵數據"""
    try:
        import yfinance as yf
        symbols = {
            "SPX": "^GSPC", "NDX": "^IXIC", "VIX": "^VIX",
            "WTI": "CL=F", "TNX": "^TNX", "NVDA": "NVDA",
            "TSLA": "TSLA", "SPY": "SPY"
        }
        data = {}
        for name, sym in symbols.items():
            h = yf.Ticker(sym).history(period="5d")
            if len(h) >= 2:
                cur = h['Close'].iloc[-1]
                prev = h['Close'].iloc[-2]
                chg = (cur - prev) / prev * 100
                data[name] = {"price": round(cur, 2), "change": round(chg, 2)}
        return data
    except:
        return {}

def save_to_db(content, tag):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS wisdom_corrections
        (id INTEGER PRIMARY KEY, axiom_id TEXT, symbol TEXT, diagnosis TEXT,
         corrected_json TEXT, confidence REAL, meta_label TEXT, created_at TEXT, web_auto TEXT)''')
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO wisdom_corrections (axiom_id, symbol, diagnosis, corrected_json, confidence, meta_label, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (f"us_strat_{time.strftime('%Y%m%d%H%M')}", tag, "US_STRATEGY", content, 0.78, MODEL, now))
    conn.commit()
    conn.close()

# ── Main ──────────────────────────────────────────────────
def main():
    print(f"[*] {time.strftime('%H:%M:%S')} 啟動美股策略深度分析 (ray-deep-v1)")
    print("=" * 60)

    # 讀取禁止規則（由 ray_logic_distiller 產出）
    forbidden_rules = load_forbidden_rules()

    # 抓市場數據
    market = get_market_snapshot()
    market_str = json.dumps(market, indent=2, ensure_ascii=False)

    # 建構大師人格 Prompt
    prompt = f"""### ROLE: RAY-DEEP STRATEGIST ###
[Context]: 結合 Taleb 的反脆弱與 Thorp 的資金管理。
[Task]: 分析目前美股主要指數與個股 (NVDA, TSLA, SPY) 的日線趨勢。
[Constraint]: 檢查是否觸發以下禁令：
{forbidden_rules}

當日市場數據：
{market_str}

請產出：
1. VIX 分析（低/中/高風險）
2. 3 條具備「統計優勢」的長線策略建議（WATCH/BUY）
3. 黑天鵝風險警示

輸出格式（JSON）：
{{
  "vix_level": "low|medium|high",
  "signals": {{
    "watch": ["標的1", "標的2"],
    "buy": ["標的1", "標的2"]
  }},
  "forbidden_check": "是否觸發禁止規則",
  "risk_alert": "風險描述",
  "confidence": 0.0-1.0
}}

只輸出 JSON，嚴禁其他文字。"""

    result = ollama_raw(MODEL, prompt)

    if result and "ERROR" not in result:
        print(result)
        save_to_db(result, tag="US_Strategy")
        print("[+] 分析完成，已存入 wisdom_corrections")
    else:
        print(f"[-] 分析失敗: {result}")

    print("=" * 60)

if __name__ == "__main__":
    main()