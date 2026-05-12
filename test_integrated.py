import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import sqlite3, json, time
import numpy as np
import yfinance as yf

DB = 'ray_wisdom.db'
OLLAMA_URL = "http://localhost:11434/api/chat"

print("=== Ray 整合大腦測試 ===")
print()

# 1. 取得 VOO 數據
print("1. 取得 VOO 數據...")
ticker = yf.Ticker("VOO")
df = ticker.history(period="1y")
close = df['Close'].values
delta = np.diff(close)
gain = np.clip(delta, 0, None).mean()
loss = np.clip(-delta, 0, None).mean()
rs = gain / loss if loss > 0 else 0
rsi = 100 - (100 / (1 + rs)) if rs > 0 else 50
ma20 = close[-20:].mean()
returns = np.diff(close) / close[:-1]
sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
print(f"   RSI: {rsi:.1f}, MA20: {ma20:.2f}, Sharpe: {sharpe:.2f}, Price: {close[-1]:.2f}")

# 2. 查詢策略
print()
print("2. 查詢 backtest_reports...")
conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute('SELECT strategy_name, sharpe_ratio FROM backtest_reports WHERE symbol="VOO" AND sharpe_ratio > 0 ORDER BY sharpe_ratio DESC LIMIT 3')
strats = c.fetchall()
print(f"   VOO 策略: {strats}")

# 3. 查詢修正
print()
print("3. 查詢 wisdom_corrections...")
c.execute('SELECT diagnosis, confidence FROM wisdom_corrections WHERE confidence >= 0.8 ORDER BY confidence DESC LIMIT 3')
corrs = c.fetchall()
print(f"   高信心修正: {corrs}")

# 4. 詢問 LLM
print()
print("4. 詢問 ray-v1...")
import requests
prompt = f"""你是 Ray 量化大腦。分析 VOO：

指標：RSI={rsi:.1f}, MA20={ma20:.2f}, Sharpe={sharpe:.2f}
價格：{close[-1]:.2f}

輸出 JSON（只輸出 JSON，不要其他文字）：
{{"signal": "BUY/SELL/WATCH", "confidence": 0.0-1.0, "reason": "原因"}}"""

resp = requests.post(OLLAMA_URL, json={
    "model": "ray-v1",
    "messages": [{"role": "user", "content": prompt}],
    "stream": False
}, timeout=30)
result = resp.json().get("message", {}).get("content", "")
print(f"   LLM 回覆: {result[:200]}")

# 解析 JSON
import re
m = re.search(r'\{[\s\S]*\}', result)
if m:
    signal_json = json.loads(m.group())
    print(f"   信號: {signal_json}")

    # 寫入 signals_log
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    c.execute('''INSERT INTO signals_log
        (timestamp, symbol, source, score, sharpe_30d, mdd_30d, win_rate_30d, signal_tag, approved, note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (now, "VOO", "INTEGRATED_TEST", signal_json.get("confidence", 0),
         sharpe, 0, 0, signal_json.get("signal", "WATCH"), 0,
         json.dumps({"rsi": rsi, "ma20": ma20, "sharpe": sharpe})))
    conn.commit()
    print(f"   已寫入 signals_log")

conn.close()
print()
print("=== 測試完成 ===")