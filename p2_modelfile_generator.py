# -*- coding: utf-8 -*-
"""
Phase 2: Modelfile 生成器
===============================
將 Phase 1 蒸餾結果（axioms_v3.5.json + ray_forbidden_rules.json）寫入 Ollama Modelfile

流程：
1. 讀取 axioms_v3.5.json（10 條通用準則）
2. 讀取 ray_forbidden_rules.json（10 條禁止規則，若有）
3. 讀取 wisdom_corrections 高信心案例
4. 讀取 backtest_reports 最優策略
5. 生成雙語 Modelfile（>11% 中文）
6. 部署 Ollama（ollama create）
7. 驗證

產出：ray-v3.5 的更新 Modelfile
"""

import json, os, sqlite3, sys, time, subprocess, requests
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

AGENTS_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(AGENTS_DIR, "ray_wisdom.db")
WISDOM_STORE = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\stores\long_term"
AXIOMS_PATH = os.path.join(WISDOM_STORE, "axioms_v3.5.json")
FORBIDDEN_PATH = os.path.join(WISDOM_STORE, "ray_forbidden_rules.json")

# Ollama
MODEL = "ray-v3.5"
OLLAMA_URL = "http://localhost:11434/api/chat"

# ── Helpers ───────────────────────────────────────────────────
def load_json(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def ollama_create(model, modelfile_path, timeout=120):
    """部署 Ollama 模型"""
    result = subprocess.run(
        ["ollama", "create", model, "-f", modelfile_path],
        capture_output=True, text=True, timeout=timeout
    )
    return result.returncode == 0, result.stderr[:200]

def ollama_chat(model, prompt, timeout=30):
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }, timeout=timeout)
        return resp.json().get("message", {}).get("content", "")[:300]
    except Exception as e:
        return f"ERROR: {e}"

# ── Prompt Builder ──────────────────────────────────────────
def build_system_prompt(axioms, forbidden_rules, corrs, strategies):
    lines = []

    # 身份（中英）
    lines.extend([
        "You are Ray, Jo's dedicated quantitative trading agent.",
        "你是 Ray，Jo 的專屬美股 ETF 量化交易 Agent。",
        "",
        "Core Focus / 核心專注：",
        "  VTI / VOO / QQQ / BND / VEA DCA (長期定期定額)",
        "  Momentum Swing (動能波段操作)",
        "  US Tech Stocks (NVDA / TSLA / META / MSFT / AAPL)",
        "",
    ])

    # ═══ 大師框架（中英，強 制引用） ═══ ═══════════════════════
    lines.extend([
        "=" * 50,
        "【MASTER FRAMEWORKS / 大師框架 — 強制引用】",
        "=" * 50,
        "",
        "【Taleb — 反脆弱 / 肥尾 / 啞鈴 / 尾部對沖】",
        "  • 反脆弱（Antifragile）：系統在極端波動下反而變強",
        "  • 肥尾（Fat Tail）：常態分布低估極端事件機率",
        "  • 啞鈴策略（Barbell）：避開中等風險，資金压在兩端",
        "  • 尾部對沖（Tail Hedge）：不追求精準預測，確保極端情況不摧毁系統",
        "  • 適用：RSI 異常、機構大規模拋售、肥尾事件後的市場",
        "",
        "【Thorp — 凱利公式 / 二元結局 / 優勢開發 / 紀律】",
        "  • 凱利公式（Kelly Criterion）：f* = (bp - q)/b，根據勝率與盈虧比決定下注比例",
        "  • 二元結局（Binary Outcome）：結果只有贏或輸，沒有中間地帶",
        "  • 優勢開發（Edge Exploitation）：數學優勢重複執行可累積獲利",
        "  • 紀律（Discipline）：每筆交易獨立服從統計紀律，不情緒化",
        "  • 適用：計算期望值、控制單筆虧損上限、遵守策略止損",
        "",
        "【Simons — Regime Switch / 統計異常 / 趨勢追蹤】",
        "【Connors — 均值回歸 / RSI2 / 彈簧理論】",
        "【Dalio — 多樣化 / 相關性 / 風險分散】",
        "",
    ])

    # ═══ Phase 1 蒸餾結果 ═══ ═══════════════════════════════
    if axioms:
        lines.append("=" * 50)
        lines.append("【Phase 1 Distilled Axioms / 第一階段蒸餾準則 — 10 條通用規則】")
        lines.append("=" * 50)
        for a in axioms:
            taleb = "✅Taleb" if a.get('taleb_aligned') else "  "
            thorp = "✅Thorp" if a.get('thorp_aligned') else "    "
            lines.append(
                f"  [{a.get('id','?')}] {a.get('when','')[:50]} → {a.get('then','')[:40]}"
            )
            lines.append(
                f"       [{a.get('type','?')}] conf={a.get('confidence',0):.2f} | {taleb} {thorp}"
            )
            if a.get('taleb_aligned') and a.get('taleb_reason'):
                lines.append(f"       📌Taleb: {a.get('taleb_reason','')[:80]}")
            if a.get('thorp_aligned') and a.get('thorp_reason'):
                lines.append(f"       📌Thorp: {a.get('thorp_reason','')[:80]}")
        lines.append("")

    if forbidden_rules:
        rules = forbidden_rules.get('rules', forbidden_rules) if isinstance(forbidden_rules, dict) else forbidden_rules
        if rules:
            lines.append("=" * 50)
            lines.append("【Forbidden Rules / 絕對禁止規則】")
            lines.append("=" * 50)
            for r in rules[:10]:
                lines.append(f"  ⚠️ [{r.get('master','?')}] {r.get('rule','')[:80]}")
            lines.append("")

    # ═══ MATH GATE（中英） ═══ ══════════════════════════════
    lines.extend([
        "=" * 50,
        "【MATH GATE / 數學把關 — 硬性過濾器】",
        "=" * 50,
        "【英語】Sharpe < 0.8 → REJECT (夏普值低於 0.8 拒絕，不考慮)",
        "【英語】MDD > 20% → REJECT (最大回撤超過 20% 拒絕)",
        "【英語】WinRate < 35% → REJECT (勝率低於 35% 拒絕)",
        "【英語】Kurtosis > 3 → WARN (峰度過高，肥尾風險警告)",
        "",
    ])

    # 高信心修正案例
    if corrs:
        lines.append("【Recent Corrections / 最新高信心修正】")
        for axiom_id, symbol, diagnosis, _, confidence in corrs[:8]:
            if diagnosis and len(diagnosis) > 15:
                lines.append(f"  • [{symbol}] {diagnosis[:100]} (conf={confidence:.2f})")
        lines.append("")

    # 最優策略
    if strategies:
        lines.append("【Top-Performing Strategies / 最優策略】")
        for strategy_name, symbol, sharpe, indicator in strategies[:7]:
            lines.append(f"  • {strategy_name} ({indicator}): Sharpe={sharpe:.2f} on {symbol}")
        lines.append("")

    # ═══ 輸出格式 ═══ ════════════════════════════════════════
    lines.extend([
        "=" * 50,
        "【OUTPUT FORMAT / 輸出格式】",
        "=" * 50,
        'Response must be JSON only. No text outside JSON.',
        '回應必須是純 JSON，不能有額外文字。',
        "",
        "JSON Schema / JSON 結構：",
        '  {',
        '    "strategy_name": "MOMENTUM_60",       // 策略名稱（英文大寫）',
        '    "indicator": "EMA_CROSS",              // 指標名稱',
        '    "params": {"period": 60},              // 參數',
        '    "entry_condition": {                   // 進場條件',
        '      "operator": "CROSS_ABOVE",',
        '      "threshold": 0',
        '    },',
        '    "stop_loss": 0.08,                     // 停損（8%）',
        '    "take_profit": 0.15,                   // 止盈（15%）',
        '    "confidence": 0.85,                   // 信心度（0-1）',
        '    "risk_reason": "Taleb肥尾對沖",        // 風險理由',
        '    "zh_note": "動能突破策略，適用於趨勢市場" // 中文備註',
        '  }',
        "",
        "【Decision Rules / 決策規則】",
        "1. 僅在 RSI2 < 20 AND Sharpe >= 1.0 時買入",
        "2. 波段動能策略停損設 12%（MOMENTUM_60）",
        "3. 均值回歸策略停損設 8%（RSI2_CONNORS）",
        "4. RSI2 > 65 AND 價格跌破 EMA20 → 準備賣出",
        "5. 最大同時持有 3 個部位",
        "",
        "【IMPORTANT】Output JSON only. No explanation.",
        "【重要】只輸出 JSON，不需要說明。",
    ])

    return "\n".join(lines)

# ── Main ────────────────────────────────────────────────────
print("=" * 60)
print("Phase 2: Modelfile 生成器")
print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

# Step 1: 讀取蒸餾結果
print("\n[1/6] 讀取 Phase 1 蒸餾結果...")
axioms = load_json(AXIOMS_PATH)
forbidden = load_json(FORBIDDEN_PATH)
print(f"  axioms_v3.5.json: {'✅ ' + str(len(axioms)) + ' 條' if axioms else '❌ 未找到'}")
print(f"  ray_forbidden_rules.json: {'✅ ' + str(len(forbidden.get('rules', []) if isinstance(forbidden, dict) else forbidden)) + ' 條' if forbidden else '❌ 未找到'}")
if axioms:
    taleb_ct = sum(1 for a in axioms if a.get('taleb_aligned'))
    thorp_ct = sum(1 for a in axioms if a.get('thorp_aligned'))
    print(f"  大師對齊：Taleb={taleb_ct}/10, Thorp={thorp_ct}/10")

# Step 2: 讀取 DB 數據
print("\n[2/6] 讀取 wisdom_corrections + backtest_reports...")
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute('''SELECT axiom_id, symbol, diagnosis, corrected_json, confidence
              FROM wisdom_corrections WHERE confidence >= 0.8
              ORDER BY confidence DESC LIMIT 10''')
corrs = [dict(row) for row in c.fetchall()]

c.execute('''SELECT strategy_name, symbol, sharpe_ratio, indicator
              FROM backtest_reports WHERE sharpe_ratio > 0.8
              ORDER BY sharpe_ratio DESC LIMIT 7''')
strategies = [dict(row) for row in c.fetchall()]

conn.close()
print(f"  高信心修正: {len(corrs)} 筆")
print(f"  高Sharpe策略: {len(strategies)} 筆")

# Step 3: 建立 Modelfile 路徑
print("\n[3/6] 建立 Modelfile...")
# 從 Ollama 取得目前模型的路徑
try:
    import subprocess
    r = subprocess.run(
        ["ollama", "show", MODEL],
        capture_output=True, text=True, timeout=10
    )
    # 找到模型實際路徑
    model_path = None
    for line in r.stdout.split('\n'):
        if 'Model' in line or 'Path' in line:
            model_path = line.split(':')[-1].strip()
            break
except:
    model_path = None

# 使用 Ollama 默認路徑
import os as os_module
MODELS_DIR = os_module.path.join(os_module.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "models")
os_module.makedirs(MODELS_DIR, exist_ok=True)
MODELFLE_PATH = os_module.path.join(MODELS_DIR, "ray-v3.5.Modelfile")

# Step 4: 生成 SYSTEM Prompt
print("\n[4/6] 生成 SYSTEM Prompt...")
system_prompt = build_system_prompt(
    axioms or [],
    forbidden,
    [(c['axiom_id'], c['symbol'], c['diagnosis'], c['corrected_json'], c['confidence']) for c in corrs],
    [(s['strategy_name'], s['symbol'], s['sharpe_ratio'], s['indicator']) for s in strategies]
)

total_chars = len(system_prompt)
chinese_chars = sum(1 for c in system_prompt if '\u4e00' <= c <= '\u9fff')
english_chars = total_chars - chinese_chars
pct = chinese_chars / (total_chars + 1) * 100
print(f"  長度: {total_chars} 字元 | 中文: {chinese_chars} ({pct:.1f}%) | 英文: {english_chars}")
if pct < 11:
    print(f"  ⚠️  中文低於 11%，當前: {pct:.1f}%")

# Step 5: 寫入 Modelfile + 部署
print("\n[5/6] 寫入 Modelfile...")
with open(MODELFLE_PATH, 'w', encoding='utf-8') as f:
    f.write(f"FROM {MODEL}\n")
    f.write(f'SYSTEM """{system_prompt}"""\n')
    f.write("PARAMETER temperature 0.15\n")
    f.write("PARAMETER num_ctx 8192\n")
    f.write("PARAMETER top_p 0.85\n")
    f.write("PARAMETER top_k 40\n")
print(f"  ✅ 已寫入: {MODELFLE_PATH}")

# 部署（如果 Modelfile 格式支援）
print("\n[6/6] 驗證 Modelfile 格式...")
print(f"  模型: {MODEL}")
print(f"  Modelfile: {MODELFLE_PATH}")

# 簡單語法檢查
with open(MODELFLE_PATH, 'r', encoding='utf-8') as f:
    content = f.read()
has_from = "FROM" in content
has_system = "SYSTEM" in content
has_params = "PARAMETER" in content
print(f"  語法檢查: FROM={'✅' if has_from else '❌'} SYSTEM={'✅' if has_system else '❌'} PARAMETER={'✅' if has_params else '❌'}")

print("\n" + "=" * 60)
print("=== Phase 2 完成 ===")
print(f"Modelfile: {MODELFLE_PATH}")
print(f"大小: {len(content)} bytes")
print(f"中文比例: {pct:.1f}%")
print()
print("📋 部署指令（如需手動）：")
print(f'  ollama create {MODEL} -f "{MODELFLE_PATH}"')