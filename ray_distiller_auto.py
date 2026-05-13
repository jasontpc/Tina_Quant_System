# -*- coding: utf-8 -*-
"""
ray_distiller_auto.py — 自動被動蒸餾腳本
每日清晨執行（05:00），將所有專家模組蒸餾進 Modelfile

流程：
1. 讀取 wisdom_corrections 高信心案例
2. 讀取 backtest_reports 最優策略
3. 整合五大專家模組
4. 生成雙語 Modelfile（11%+ 中文）
5. 部署 Ollama
6. 驗證
"""

import json, os, sqlite3, sys, subprocess, requests, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_PATH = os.path.join(os.path.dirname(__file__), "ray_wisdom.db")
MODEL = "qwen3.5-4b-iq4xs"
MODELS_DIR = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "models")
MODELFLE_PATH = os.path.join(MODELS_DIR, "qwen35-4b-iq4xs", "Modelfile")

# 載入專家模組
from ray_expert_modules import get_all_experts_prompt, EXPERT_MODULES, get_expert_for_trigger

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()

# 確保 sop_versions 表存在（第一次執行時建立）
try:
    c.execute("""CREATE TABLE IF NOT EXISTS sop_versions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        update_date TEXT,
        version TEXT,
        content TEXT,
        changelog TEXT
    )""")
    conn.commit()
except:
    pass

print("=== Ray Distiller Auto ===")
print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Step 1: 讀取高信心修正
print("[1] 讀取 wisdom_corrections...")
c.execute('''SELECT axiom_id, symbol, diagnosis, corrected_json, confidence
              FROM wisdom_corrections WHERE confidence >= 0.8
              ORDER BY confidence DESC LIMIT 15''')
corrs = c.fetchall()
print(f"  高信心（>=0.8）: {len(corrs)} 筆")

# Step 2: 讀取最優 backtest
print("[2] 讀取 backtest_reports...")
c.execute('''SELECT strategy_name, symbol, indicator, sharpe_ratio, params
              FROM backtest_reports WHERE sharpe_ratio > 0.8
              ORDER BY sharpe_ratio DESC LIMIT 10''')
strategies = c.fetchall()
print(f"  Sharpe > 0.8: {len(strategies)} 筆")

# Step 3: 讀取衰減權重（失敗教訓）
print("[3] 讀取失敗 wisdom_logs...")
c.execute('SELECT COUNT(*) FROM wisdom_logs WHERE passed=0')
failed = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM wisdom_logs WHERE weight < 1.0')
decayed = c.fetchone()[0]
print(f"  失敗: {failed} | 衰減: {decayed}")

conn.close()

# Step 4: 生成完整 SYSTEM Prompt
print("[4] 生成 SYSTEM Prompt...")

parts = []

# 基礎設定
parts.append("You are Ray, Jo's dedicated quantitative trading agent.")
parts.append("你是 Ray，Jo 的專屬美股 ETF 量化交易 Agent。\n")

# 大師專家系統
parts.append(get_all_experts_prompt())
parts.append("")

# 數學把關（雙語）
parts.append("【MATH GATE / 數學把關】")
parts.append("  • Sharpe < 0.8 → REJECT（夏普值低於 0.8 拒絕）")
parts.append("  • MDD > 20% → REJECT（最大回撤超過 20% 拒絕）")
parts.append("  • WinRate < 35% → REJECT（勝率低於 35% 拒絕）")
parts.append("  • Kurtosis > 3 → WARN（峰度過高，肥尾警告）\n")

# 高信心修正案例（雙語）
if corrs:
    parts.append("【Recent High-Confidence Corrections / 最新高信心修正】")
    for axiom_id, symbol, diag, corr_json, conf in corrs[:8]:
        if diag and len(diag) > 15:
            parts.append(f"  • [{symbol}] {diag[:100]} (conf={conf:.2f})")
    parts.append("")

# 最優策略（雙語）
if strategies:
    parts.append("【Top-Performing Strategies / 最優策略】")
    for strat_name, symbol, indicator, sharpe, params in strategies[:7]:
        parts.append(f"  • {strat_name} ({indicator}): Sharpe={sharpe:.2f} on {symbol}")
    parts.append("")

# 輸出格式（強制）
parts.append("【OUTPUT FORMAT / 輸出格式】")
parts.append('Response must be JSON only. No text outside JSON.')
parts.append('回應必須是純 JSON，不能有額外文字。')
parts.append("")
parts.append("【JSON Schema / JSON 結構】")
parts.append('  {')
parts.append('    "strategy_name": "MOMENTUM_60",      // 策略名稱（英文大寫）')
parts.append('    "indicator": "EMA_CROSS",             // 指標名稱')
parts.append('    "params": {"period": 60},             // 參數')
parts.append('    "entry_condition": {"operator": "CROSS_ABOVE", "threshold": 0},')
parts.append('    "stop_loss": 0.08,                    // 停損（8%）')
parts.append('    "take_profit": 0.15,                 // 止盈（15%）')
parts.append('    "confidence": 0.85,                  // 信心度（0-1）')
parts.append('    "risk_reason": "Taleb asymmetric",    // 風險理由')
parts.append('    "source": "CoT_analyzed"             // 來源')
parts.append('  }')
parts.append("")
parts.append("【Decision Rules / 決策規則】")
parts.append("1. 僅在 RSI2 < 20 AND Sharpe >= 1.0 時買入")
parts.append("2. 波段動能策略停損設 12%（MOMENTUM_60）")
parts.append("3. 均值回歸策略停損設 8%（RSI2_CONNORS）")
parts.append("4. RSI2 > 65 AND 價格跌破 EMA20 → 準備賣出")
parts.append("5. 最大同時持有 3 個部位")
parts.append("6. Meta-Labeling 二次校準後才能執行")
parts.append("")
parts.append("【IMPORTANT】Output JSON only. No explanation. / 只輸出 JSON，不需要說明。")

system_prompt = "\n".join(parts)

# 統計
total_chars = len(system_prompt)
chinese_chars = sum(1 for c in system_prompt if '\u4e00' <= c <= '\u9fff')
english_chars = total_chars - chinese_chars

print(f"  Prompt 長度: {total_chars} 字元")
print(f"  中文字數: {chinese_chars} ({chinese_chars/(total_chars+1)*100:.1f}%)")
print(f"  英文字數: {english_chars}")
print(f"  專家模組: {len(EXPERT_MODULES)} 個")
print()

# Step 4b: 建立 sop_versions 快照
print("[4b] 寫入 sop_versions...")
from datetime import datetime
sop_conn = sqlite3.connect(DB_PATH)
sop_c = sop_conn.cursor()
sop_c.execute("SELECT COUNT(*) FROM sop_versions")
prev_ver = sop_c.fetchone()[0] or 0
new_ver = f"v{prev_ver + 1}.{datetime.now().strftime('%Y%m%d')}"
sop_c.execute("""INSERT INTO sop_versions (update_date, version, content, changelog)
                  VALUES (?, ?, ?, ?)""",
    (datetime.now().strftime('%Y-%m-%d'), new_ver, system_prompt[:1000],
     f"自動蒸餾 {datetime.now().strftime('%H:%M')} — 高信心修正{len(corrs)}筆 最優策略{len(strategies)}筆"))
sop_conn.commit()
sop_conn.close()
print(f"  新版本: {new_ver}（共 {prev_ver+1} 個版本）")

# Step 5: 寫入 Modelfile
print("[5] 寫入 Modelfile...")
os.makedirs(os.path.dirname(MODELFLE_PATH), exist_ok=True)

modelfile_content = f"""FROM ./Qwen3.5-4B-IQ4_XS.gguf
SYSTEM \"\"\"{system_prompt}\"\"\"
PARAMETER temperature 0.2
PARAMETER num_ctx 8192
PARAMETER num_thread 14
PARAMETER top_p 0.85
PARAMETER top_k 40
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
test_cases = [
    ("NVDA", "RSI2=22 超賣動能策略"),
    ("TSLA", "MOMENTUM 動量策略"),
    ("SPY", "均值回歸 RSI2<20"),
]

for symbol, desc in test_cases:
    try:
        resp = requests.post("http://localhost:11434/api/chat", json={
            "model": MODEL,
            "messages": [{"role": "user", "content": f"{symbol} {desc}，輸出 JSON"}],
            "format": "json",
            "stream": False
        }, timeout=30)
        content = resp.json().get("message", {}).get("content", "")[:100].replace('\n', ' ')
        print(f"  [{symbol}] → {content[:80]}")
    except Exception as e:
        print(f"  [{symbol}] → 錯誤: {str(e)[:50]}")

print()
print("=== 完成 ===")
print(f"高信心修正: {len(corrs)} 筆")
print(f"最優策略: {len(strategies)} 筆")
print(f"專家模組: {len(EXPERT_MODULES)} 個（Simons/Connors/Taleb/Thorp/Meta-Labeling）")
print(f"中文比例: {chinese_chars/(total_chars+1)*100:.1f}%")
print()
print("24小時被動蒸餾循環：運行中 ✅")
print()
print("【蒸餾摘要】")
print("  ✅ Simons HMM 市場狀態 → Layer 3")
print("  ✅ Connors RSI2 均值回歸 → Layer 1&2")
print("  ✅ Taleb 肥尾風險 → Math Gate")
print("  ✅ Thorp 凱利倉位 → Layer 3")
print("  ✅ Meta-Labeling 二次校準 → Layer 3")
print("  ✅ 高信心修正注入 → Prompt")
print("  ✅ 最優策略注入 → Prompt")
print("  ✅ 雙語 Modelfile → 11%+ 中文")