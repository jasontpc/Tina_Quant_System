# -*- coding: utf-8 -*-
"""
ray_us_premarket_macro.py — 21:00 美股盤前宏觀分析
接管 MiniMax Layer 3 任務，節省雲端配額
"""
import sys, json, time, sqlite3, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

AGENTS_DIR = r"C:\Users\USER\.openclaw\agents\ray"
DB = os.path.join(AGENTS_DIR, "ray_wisdom.db")
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:7b"
RAM_CACHE = os.path.join(AGENTS_DIR, "master_insights_ram.json")

# ── VRAM 單模型清理 ────────────────────────────────────────
def clear_all_vram():
    """強制清理所有模型（單模型協議前置）"""
    import subprocess, time
    try:
        subprocess.run(["ollama", "stop", "--all"],
                       capture_output=True, timeout=60, check=False)
        print("[VRAM] ███ 清理中，60s 冷卻... ███")
        time.sleep(60)
        print("[VRAM] ✅ VRAM 清空")
    except Exception as e:
        print(f"[VRAM] 清理失敗: {e}")

def stop_model(model):
    """任務結束後卸載模型"""
    import subprocess
    try:
        subprocess.run(["ollama", "stop", model],
                       capture_output=True, timeout=30, check=False)
    except:
        pass

# ── Helper ──────────────────────────────────────────────────
def ollama_raw(model, prompt, temperature=0.15, num_predict=350, timeout=90):
    try:
        import requests
        resp = requests.post(OLLAMA_URL, json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": temperature, "top_p": 0.8, "num_predict": num_predict}
        }, timeout=timeout)
        return resp.json().get("message", {}).get("content", "")
    except Exception as e:
        return f"ERROR: {e}"

def load_web_auto():
    """讀取 ray_web_collector 產出的 web_auto 規則"""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''SELECT diagnosis, corrected_json FROM wisdom_corrections
                 WHERE web_auto IS NOT NULL ORDER BY created_at DESC LIMIT 5''')
    rows = c.fetchall()
    conn.close()
    return "\n".join([f"- {r[0]}: {r[1][:80]}" for r in rows]) if rows else "（尚無 web_auto 規則）"

def get_macro_data():
    try:
        import yfinance as yf
        symbols = {"SPX": "^GSPC", "NDX": "^IXIC", "VIX": "^VIX", "WTI": "CL=F", "TNX": "^TNX", "DXY": "DXY"}
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
        (f"us_prem_{time.strftime('%Y%m%d%H%M')}", tag, "US_PREMARKET", content, 0.80, MODEL, now))
    conn.commit()
    conn.close()

def update_ram_cache(data):
    """更新 master_insights_ram.json（32GB RAM 快取）"""
    try:
        existing = {}
        if os.path.exists(RAM_CACHE):
            existing = json.load(open(RAM_CACHE, encoding='utf-8'))

        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "type": "premarket_sentiment",
            "data": data
        }
        existing["premarket"] = entry

        with open(RAM_CACHE, 'w', encoding='utf-8') as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
        print(f"[+] RAM 快取已更新: premarket sentiment")
    except Exception as e:
        print(f"[-] RAM 快取更新失敗: {e}")

# ── Main ──────────────────────────────────────────────────
def main():
    print(f"[*] {time.strftime('%H:%M:%S')} 接管 MiniMax — 執行盤前宏觀分析 (qwen2.5:7b)")
    print("=" * 60)

    # 前置清理：確保 VRAM 乾淨（單模型協議）
    print("[VRAM] 執行任務前清理...")
    clear_all_vram()

    web_auto_rules = load_web_auto()
    macro = get_macro_data()
    macro_str = json.dumps(macro, indent=2, ensure_ascii=False)

    prompt = f"""### ROLE: MASTER ALIGNMENT ANALYST ###
[Master Insights]: 參考 Dalio 的多樣化與 Simons 的模式識別。
[Input]: 當日宏觀數據
{macro_str}

[Web Auto Rules]:
{web_auto_rules}

[Mission]: 將這些數據轉化為 4B 指揮官可理解的「權重修正因子」。

請產出（JSON）：
{{
  "sentiment": "+0.1|0|-0.1",
  "inflation_risk": "low|medium|high",
  "recession_signal": true|false,
  "tomorrow_strategy": "aggressive|neutral|defensive",
  "position_adjustment": "描述",
  "confidence": 0.0-1.0
}}

只輸出 JSON，嚴禁其他文字。"""

    result = ollama_raw(MODEL, prompt)

    if result and "ERROR" not in result:
        print(result)
        save_to_db(result, tag="US_Premarket")
        update_ram_cache(result)
        print("[+] 盤前分析完成，MiniMax 配額節省成功")
    else:
        print(f"[-] 分析失敗: {result}")

    # 任務結束：卸載模型釋放 VRAM
    print("[VRAM] 任務結束，卸載 qwen2.5:7b...")
    stop_model(MODEL)

    print("=" * 60)

if __name__ == "__main__":
    main()