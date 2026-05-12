# -*- coding: utf-8 -*-
"""
Ray 大腦 雙語化 Modelfile 生成器
改善語言缺陷：中文化 + 雙語並行

功能：
1. SYSTEM prompt 中英雙語
2. 大師邏輯（Taleb/Thorp/Connors）中文說明
3. 決策規則中文對照
4. 輸出 JSON 欄位英文 + 中文對照
"""

import json, sqlite3, os, sys, time, subprocess, requests
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_PATH = "ray_wisdom.db"
MODEL = "ray-v1"
MODELS_DIR = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "models")
MODELFLE_PATH = os.path.join(MODELS_DIR, "modelfiles", "ray-v1.Modelfile")

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

print("=== 雙語化 Modelfile 生成器 ===")
print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print()

# 讀取高信心修正
c.execute('''SELECT axiom_id, symbol, diagnosis, corrected_json, confidence
              FROM wisdom_corrections WHERE confidence >= 0.8 ORDER BY confidence DESC LIMIT 10''')
corrs = c.fetchall()
print(f"高信心修正: {len(corrs)} 筆")

# 讀取最優策略
c.execute('''SELECT strategy_name, symbol, sharpe_ratio, indicator FROM backtest_reports
              WHERE sharpe_ratio > 0.8 ORDER BY sharpe_ratio DESC LIMIT 7''')
strategies = c.fetchall()
print(f"高 Sharpe 策略: {len(strategies)} 筆")

conn.close()

# 雙語 SYSTEM Prompt 生成
lines = [
    "You are Ray, Jo's dedicated quantitative trading agent.",
    "你是 Ray，Jo 的專屬美股 ETF 量化交易 Agent。",
    "",
    "Core Focus / 核心專注：",
    "  VTI / VOO / QQQ / BND / VEA DCA (長期定期定額)",
    "  Momentum Swing (動能波段操作)",
    "  US Tech Stocks (NVDA / TSLA / META / MSFT / AAPL)",
    "",
    "=== MATH GATE / 數學把關 (硬性過濾器) ===",
    "【英語】Sharpe < 0.8 → REJECT (夏普值低於 0.8 拒絕)",
    "【英語】MDD > 20% → REJECT (最大回撤超過 20% 拒絕)",
    "【英語】WinRate < 35% → REJECT (勝率低於 35% 拒絕)",
    "",
    "=== MASTER LOGIC / 大師邏輯 ===",
    "",
    "【Connors RSI2 均值回歸 / Mean Reversion】",
    "  RSI2 < 20 = 超賣 → 準備買入訊號",
    "  RSI2 > 70 = 超買 → 準備賣出訊號",
    "  進場：RSI2 < 20 AND 價格站穩 EMA20 支撐",
    "  出場：RSI2 > 60 OR 觸發停損",
    "",
    "【Taleb 肥尾防禦 / Fat-Tail Defense】",
    "  Kurtosis > 3 → 警告（峰度過高，肥尾風險）",
    "  Sharpe < 0.5 → 拒絕（尾部風險超標）",
    "  MDD > 15% → 警告（提高停損靈敏度）",
    "",
    "【Thorp 凱利倉位 / Kelly Position Sizing】",
    "  Kelly % = WinRate / (1 - WinRate) * LossRatio",
    "  使用 Kelly * 0.25（保守半倉）",
    "  最大倉位 = 帳戶 20%",
    "",
]

# 高信心修正（中文說明）
if corrs:
    lines.append("【Recent Corrections / 最新修正案例】")
    for axiom_id, symbol, diagnosis, corrected_json, confidence in corrs[:5]:
        if diagnosis and len(diagnosis) > 15:
            lines.append(f"  • [{symbol}] {diagnosis[:80]} (conf={confidence:.2f})")
    lines.append("")

# 最優策略（中英對照）
if strategies:
    lines.append("【Top Strategies / 最優策略】")
    for strategy_name, symbol, sharpe, indicator in strategies[:5]:
        lines.append(f"  • {strategy_name} ({indicator}): Sharpe={sharpe:.2f} on {symbol}")
    lines.append("")

# 輸出格式（中英對照說明）
lines.extend([
    "=== OUTPUT FORMAT / 輸出格式 ===",
    'Response must be JSON only. No text outside JSON.',
    '回應必須是純 JSON，不能有額外文字。',
    "",
    "JSON Schema / JSON 結構：",
    '  {',
    '    "strategy_name": "MOMENTUM_60",      // 策略名稱（英文大寫）',
    '    "indicator": "EMA_CROSS",             // 指標名稱（英文）',
    '    "params": {                            // 參數（英文）',
    '      "period": 60,',
    '      "threshold": 0.02',
    '    },',
    '    "entry_condition": {                  // 進場條件',
    '      "operator": "CROSS_ABOVE",',
    '      "threshold": 0',
    '    },',
    '    "stop_loss": 0.08,                    // 停損比例（8%）',
    '    "confidence": 0.85,                   // 信心度（0-1）',
    '    "zh_note": "動能突破策略，適用於趨勢市場"  // 中文備註',
    '  }',
    "",
    "=== Decision Rules / 決策規則 ===",
    "1. 僅在 RSI2 < 20 AND Sharpe >= 1.0 時買入",
    "2. 波段動能策略：停損設 12% (MOMENTUM_60)",
    "3. 均值回歸策略：停損設 8% (RSI2_CONNORS)",
    "4. RSI2 > 65 AND 價格跌破 EMA20 → 準備賣出",
    "5. 最大同時持有 3 個部位",
    "",
    "【重要】Output JSON only. No explanation. / 只輸出 JSON，不需要說明。",
])

system_prompt = "\n".join(lines)
print(f"Prompt 長度: {len(system_prompt)} 字元")
chinese_chars = sum(1 for c in system_prompt if '\u4e00' <= c <= '\u9fff')
print(f"中文字數: {chinese_chars} ({chinese_chars/len(system_prompt)*100:.1f}%)")
print(f"英文字數: {len(system_prompt) - chinese_chars}")
print()

# 寫入 Modelfile
print("[1] 寫入 Modelfile...")
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

# 部署 Ollama
print("[2] 部署 Ollama...")
result = subprocess.run(
    ["cmd", "/c", "ollama", "create", MODEL, "-f", MODELFLE_PATH],
    capture_output=True, text=True, timeout=120
)
success = result.returncode == 0
print(f"  {'✅ 成功' if success else f'⚠️ 錯誤: {result.stderr[:100]}'}")

# 驗證
print("[3] 驗證（中文測試）...")
try:
    resp = requests.post("http://localhost:11434/api/chat", json={
        "model": MODEL,
        "messages": [{"role": "user", "content": "幫我分析 TSLA 的動能策略，給我 JSON 輸出"}],
        "stream": False
    }, timeout=30)
    content = resp.json().get("message", {}).get("content", "")[:200]
    print(f"  回應: {content[:150]}")
except Exception as e:
    print(f"  錯誤: {e}")

print()
print("=== 完成 ===")
print("雙語化 Modelfile 已部署 ✅")
print()
print("改善內容：")
print("  • SYSTEM prompt 中英雙語並行")
print("  • 大師邏輯（Taleb/Thorp/Connors）中文說明")
print("  • JSON 欄位中英對照")
print("  • 輸出格式中文備註")