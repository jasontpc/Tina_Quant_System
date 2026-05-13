# -*- coding: utf-8 -*-
"""
Ray 大腦 動態 Modelfile 生成器
每日凌晨自動執行：將 top 10% wisdom_corrections 轉化為 SYSTEM Instructions

功能：
1. 檢索 confidence >= 0.8 的高信心修正
2. 提取 Sharpe > 0.8 的最優策略
3. 注入 Taleb/Thorp/Connors 大師邏輯
4. 生成並部署新 Modelfile
5. 驗證模型更新
"""

import json, sqlite3, os, sys, time, subprocess, requests
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_PATH = "ray_wisdom.db"
MODEL = "ray-v1"
MODELS_DIR = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "models")
MODELFLE_PATH = os.path.join(MODELS_DIR, "modelfiles", "ray-v1.Modelfile")
LOG_PATH = os.path.join(os.path.dirname(__file__), "modelfile_update_log.txt")

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

print("=== Ray Dynamic Modelfile Generator ===")
print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Step 1: 讀取高信心修正
print("[1] 讀取高信心 wisdom_corrections...")
c.execute('''SELECT axiom_id, symbol, diagnosis, corrected_json, confidence 
              FROM wisdom_corrections 
              WHERE confidence >= 0.8
              ORDER BY confidence DESC LIMIT 15''')
corrs = c.fetchall()
print(f"  confidence >= 0.8: {len(corrs)} 筆")

# Step 2: 讀取最優策略
print("[2] 讀取最優 backtest_reports...")
c.execute('''SELECT strategy_name, symbol, sharpe_ratio, indicator, params
              FROM backtest_reports 
              WHERE sharpe_ratio > 0.8
              ORDER BY sharpe_ratio DESC LIMIT 10''')
strategies = c.fetchall()
print(f"  Sharpe > 0.8: {len(strategies)} 筆")

# Step 3: 讀取衰減/進化狀態
print("[3] 系統狀態...")
c.execute('SELECT COUNT(*) FROM wisdom_logs WHERE weight < 1.0')
decayed = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM wisdom_logs WHERE passed=0')
failed = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM wisdom_logs WHERE passed=1')
passed = c.fetchone()[0]
print(f"  wisdom_logs: {passed} passed, {failed} failed, {decayed} decayed")

conn.close()

# Step 4: 生成 SYSTEM Prompt（帶大師邏輯）
print("[4] 生成 SYSTEM Prompt...")

lines = [
    "You are Ray, quantitative trading agent specializing in US ETFs.",
    "Core focus: VTI/VOO/QQQ/BND/VEA DCA + momentum swing.",
    "",
    "=== MATH GATE (硬性過濾器) ===",
    "• Sharpe < 0.8 → REJECT",
    "• MDD > 20% → REJECT",
    "• WinRate < 35% → REJECT",
    "",
    "=== MASTER LOGIC (from 7B Deep Analysis) ===",
]

# Connors RSI2
lines.extend([
    "【Connors RSI2 Mean Reversion】",
    "• RSI2 < 20 = oversold, prepare BUY signal",
    "• RSI2 > 70 = overbought, prepare SELL signal",
    "• Entry: RSI2 < 20 AND price > EMA20 support",
    "• Exit: RSI2 > 60 OR stop_loss triggered",
    "",
])

# Taleb 肥尾
lines.extend([
    "【Taleb Fat-Tail Defense】",
    "• Kurtosis > 3 → WARN (峰度過高)",
    "• Sharpe < 0.5 → REJECT (尾部風險)",
    "• MDD > 15% → WARN, increase stop_loss",
    "",
])

# Thorp 凱利
lines.extend([
    "【Thorp Kelly Position Sizing】",
    "• Kelly % = WinRate / (1 - WinRate) * LossRatio",
    "• Use Kelly * 0.25 for conservative (half-Kelly)",
    "• Max position = 20% of portfolio",
    "",
])

# 高信心修正案例
if corrs:
    lines.append("【Recent High-Confidence Corrections】")
    for axiom_id, symbol, diagnosis, corrected_json, confidence in corrs[:10]:
        if diagnosis and len(diagnosis) > 15:
            diag = diagnosis[:100].replace('"', "'").replace('\n', ' ')
            lines.append(f"• [{symbol}] {diag} (conf={confidence:.2f})")
    lines.append("")

# 最優策略
if strategies:
    lines.append("【Top-Performing Strategies】")
    for strategy_name, symbol, sharpe, indicator, params_str in strategies[:7]:
        lines.append(f"• {strategy_name} ({indicator}): Sharpe={sharpe:.2f} on {symbol}")
    lines.append("")

# 量化閾值
lines.extend([
    "=== Decision Rules ===",
    "1. Only BUY when RSI2 < 20 AND Sharpe >= 1.0",
    "2. Use MOMENTUM_60 for swing (stop_loss=0.12)",
    "3. Use RSI2_CONNORS for mean-reversion (stop_loss=0.08)",
    "4. Exit if RSI2 > 65 AND price > EMA20 (overbought)",
    "5. Max 3 positions simultaneously",
    "",
    "Output: JSON only with strategy_name, indicator, params, entry_condition, stop_loss.",
    "No text outside JSON.",
])

system_prompt = "\n".join(lines)
print(f"  Prompt 長度: {len(system_prompt)} 字元")
print(f"  大師邏輯: {len([l for l in lines if l.startswith(('【','•'))])} 條")

# Step 5: 寫入 Modelfile
print("[5] 寫入 Modelfile...")
os.makedirs(os.path.dirname(MODELFLE_PATH), exist_ok=True)

modelfile_content = f"""FROM qwen2.5:1.5b
SYSTEM \"\"\"{system_prompt}\"\"\"
PARAMETER temperature 0.1
PARAMETER num_ctx 4096
PARAMETER top_p 0.9
PARAMETER top_k 20
"""

with open(MODELFLE_PATH, 'w', encoding='utf-8') as f:
    f.write(modelfile_content)
print(f"  已寫入: {MODELFLE_PATH} ({len(modelfile_content)} bytes)")

# Step 6: 部署 Ollama
print("[6] 部署 Ollama...")
result = subprocess.run(
    ["cmd", "/c", "ollama", "create", MODEL, "-f", MODELFLE_PATH],
    capture_output=True, text=True, timeout=120
)
success = result.returncode == 0
if success:
    print("  ✅ 模型已更新")
else:
    print(f"  ⚠️ 錯誤: {result.stderr[:100]}")

# Step 7: 驗證
print("[7] 驗證...")
test_queries = [
    "NVDA momentum strategy",
    "RSI2 oversold on SPY",
    "Kelly position for GLD",
]

for query in test_queries:
    try:
        resp = requests.post("http://localhost:11434/api/chat", json={
            "model": MODEL,
            "messages": [{"role": "user", "content": f"Suggest strategy for {query}"}],
            "stream": False
        }, timeout=30)
        content = resp.json().get("message", {}).get("content", "")[:80]
        print(f"  [{query}] → {content[:60]}")
    except Exception as e:
        print(f"  [{query}] → 錯誤: {e}")

# Step 8: 記錄日誌
print("[8] 寫入日誌...")
timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
log_entry = f"""
=== Modelfile Update Log ===
時間: {timestamp}
高信心修正: {len(corrs)} 筆
最優策略: {len(strategies)} 筆
Prompt 長度: {len(system_prompt)} 字元
部署成功: {success}
---
"""

with open(LOG_PATH, 'a', encoding='utf-8') as f:
    f.write(log_entry)

print()
print("=== 完成 ===")
print(f"高信心修正: {len(corrs)} 筆")
print(f"最優策略: {len(strategies)} 筆")
print(f"大師邏輯: {len([l for l in lines if l.startswith(('【','•'))])} 條")
print(f"日誌: {LOG_PATH}")
print()
print("24小時被動蒸餾循環：運行中 ✅")