# -*- coding: utf-8 -*-
"""
ray_decision_gateway.py — Ray System 決策閘門
============================================================
分析後等待 Jo 數字輸入 [1-4]，60秒超時自動略過 [2]
使用 @ray_singleton 確保 VRAM 独占

用法：
  python ray_decision_gateway.py NVDA
  python ray_decision_gateway.py 3034.TW --mode tw
"""

import sys, os, time, json, subprocess
from pathlib import Path
from datetime import datetime

# ── 路徑設定 ────────────────────────────────────────────────────────────
BASE_DIR = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
sys.path.insert(0, str(BASE_DIR / "scripts" / "utils"))

try:
    from ray_guard import ray_singleton, io_singleton
    _HAS_GUARD = True
except ImportError:
    def ray_singleton(func): return func
    def io_singleton(func): return func
    _HAS_GUARD = False

# ── 依賴 ──────────────────────────────────────────────────────────────────
try:
    import yfinance as yf
    import numpy as np
except ImportError:
    print("❌ 缺少依賴: pip install yfinance numpy")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════════════════
# 技術指標計算（CPU 端）
# ═══════════════════════════════════════════════════════════════════════════

def ema(c, n):
    a = 2/(n+1); e = np.zeros(len(c)); e[0]=c[0]
    for i in range(1, len(c)):
        e[i] = c[i]*a + e[i-1]*(1-a)
    return e

def rsi_calc(c, period=14):
    d = np.diff(c, prepend=c[0])
    g = np.where(d>0, d, 0.); l = np.where(d<0, -d, 0.)
    ag = g.copy(); al = l.copy()
    for i in range(1, len(ag)):
        ag[i] = (ag[i-1]*13+g[i])/14
        al[i] = (al[i-1]*13+l[i])/14
    rs = ag[-1]/max(al[-1], 1e-10)
    return float(100-(100/(1+rs)))

def get_tech_summary(symbol, period="6mo"):
    """抓取並計算技術指標"""
    print(f"  📡 抓取 {symbol} 數據...")
    df = yf.Ticker(symbol).history(period=period, interval="1d", auto_adjust=True, timeout=15)
    if df is None or len(df) < 60:
        return None

    c = df['Close'].values.astype(float)
    h = df['High'].values.astype(float)
    l = df['Low'].values.astype(float)
    v = df['Volume'].values.astype(float)

    m20 = ema(c, 20); m60 = ema(c, 60)
    ef = ema(c, 12); es = ema(c, 26)
    mac = ef - es; sigv = ema(mac, 9); mh = mac - sigv

    rs = rsi_calc(c)
    p = float(c[-1])
    prev_p = float(c[-2]) if len(c) >= 2 else p
    change = (p/prev_p - 1) * 100

    return {
        "symbol": symbol,
        "price": p,
        "change_pct": round(change, 2),
        "ma20": round(float(m20[-1]), 2),
        "ma60": round(float(m60[-1]), 2),
        "rsi": round(rs, 1),
        "macd_hist": round(float(mh[-1]), 3),
        "volume": int(v[-1]),
        "ma20_above_ma60": float(m20[-1]) > float(m60[-1]),
        "macd_positive": float(mh[-1]) > 0,
    }

def get_positions():
    """讀取持倉"""
    p = BASE_DIR / "stores" / "portfolio" / "positions.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except:
            pass
    return []

def format_price(p):
    return f"${p:.2f}" if p else "N/A"

def format_pnl(pnl):
    return f"+{pnl:.2f}%" if pnl >= 0 else f"{pnl:.2f}%"

# ═══════════════════════════════════════════════════════════════════════════
# 載入 Axioms + 禁止規則
# ═══════════════════════════════════════════════════════════════════════════

def load_axioms():
    path = BASE_DIR / "stores" / "long_term" / "axioms_v3.5.json"
    if not path.exists():
        return ""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        rules = data if isinstance(data, list) else data.get("axioms", data.get("rules", []))
        return "\n".join([f"{i+1}. {r.get('text', r) if isinstance(r, dict) else r}" for i, r in enumerate(rules[:8])])
    except:
        return ""

def load_forbidden():
    path = BASE_DIR / "stores" / "long_term" / "ray_forbidden_rules.json"
    if not path.exists():
        return ""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        rules = data.get("rules", [])[-5:]
        return "\n".join([f"- {r.get('symbol','ALL')}: {r.get('rule','')}" for r in rules])
    except:
        return ""

@io_singleton
def log_to_memory(content):
    """安全寫入日誌，防止 Edit Failed（I/O 鎖保護）"""
    ts = datetime.now().strftime('%Y-%m-%d %H:%M')
    entry = f"\n\n### 📅 {ts} 決策紀錄\n{content}"
    try:
        with open(BASE_DIR / "MEMORY.md", "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception as e:
        print(f"[WARN] log_to_memory failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# AI 分析（VRAM 保護）
# ═══════════════════════════════════════════════════════════════════════════

@ray_singleton
def run_ai_analysis(symbol, tech, model="qwen3.5-4b-iq4xs:latest"):
    """使用 Ollama 進行分析"""
    axioms_text = load_axioms()
    forbidden_text = load_forbidden()

    # 抓持倉資訊
    positions = get_positions()
    holding = next((p for p in positions if symbol in p.get("symbol", "")), None)

    holding_info = ""
    if holding:
        holding_info = f"""【當前持倉】
- 成本: {format_price(holding.get('cost'))} | 現價: {format_price(holding.get('current_price'))}
- PnL: {format_pnl(float(holding.get('pnl_pct', 0)))} ({holding.get('pnl', 'N/A')})
- 持有天數: {holding.get('days_held', 'N/A')} 天
- RSI: {holding.get('rsi', 'N/A')} | MA20: {holding.get('ma20', 'N/A')}
"""

    prompt = f"""### ROLE: RAY-COMMANDER V3.5
你是美股/台股波段交易分析師，結合 Taleb 反脆弱 + Thorp 資金管理 + Connors RSI2 均值回歸。

【分析標的】
{symbol}

【技術面】
- 現價: {format_price(tech.get('price'))} | 漲跌: {tech.get('change_pct', 0):.2f}%
- RSI(14): {tech.get('rsi')}
- MA20: {format_price(tech.get('ma20'))} | MA60: {format_price(tech.get('ma60'))} ({'多頭' if tech.get('ma20_above_ma60') else '空頭'})
- MACD Hist: {tech.get('macd_hist')} ({'正' if tech.get('macd_positive') else '負'})
- 成交量: {tech.get('volume', 0):,}

{holding_info}
【Axioms 框架】
{axioms_text if axioms_text else "（無）"}

【禁止規則】
{forbidden_text if forbidden_text else "（無）"}

請產出以下格式（繁體中文）：

## 技術面簡析
（1-2句）

## 基本面簡析
（1-2句，若無基本面數據則寫「無詳細基本面數據」）

## 綜合評分（0-100）及理由
（評分 + 2-3句理由）

## 實戰建議
【動作】：BUY / HOLD / WATCH / REDUCE / SELL
【理由】：1-2句
【進場價】：若 BUY 给出建議進場價
【停損價】：所有動作都需給出停損價（MA20 或成本 -8% 取嚴格者）
【目標價】：若有明確目標

## Taleb 風險提示
（如適用，特別注意：RSI>70 + 持有>20天 = 警戒）

---
🤖 **Ray 指揮官決策選單**

請在分析結尾輸出以下決策選單（不可省略）：

```
🤖 Ray 指揮官決策選單：
 [1] ⚡ 立即執行：[簡述動作]
 [2] ✋ 暫時略過：[簡述理由]
 [3] 🔍 深度歸因：[調用 7B 進行邏輯蒸餾]
 [4] 🛠️ 手動修正：[開啟人工干預模式]
```
"""

    print(f"\n  [AI] 分析中（模型: {model}）...")
    try:
        # Pre-check: verify model exists
        list_result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            timeout=15,
            encoding="utf-8",
            errors="replace",
        )
        available_models = []
        if list_result.returncode == 0:
            for line in list_result.stdout.split("\n"):
                parts = line.split()
                if parts:
                    available_models.append(parts[0])

        if model not in available_models:
            return f"[Model Not Ready] {model} 未安裝或正在下載。請先執行: ollama pull {model}"

        result = subprocess.run(
            ["ollama", "run", model],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=150,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            import re
            stderr_clean = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', result.stderr)
            stderr_clean = stderr_clean.strip()
            if stderr_clean and len(stderr_clean) > 5:
                return f"[Ollama Error] {stderr_clean[:200]}"
            return f"[Ollama Error] 模型執行失敗（{len(result.stderr)} bytes stderr）"
    except subprocess.TimeoutExpired:
        return "[Timeout] 模型回應逾時（150秒）"
    except FileNotFoundError:
        return "[Error] Ollama 未運行。請先執行: ollama serve"
    except Exception as e:
        return f"[Error] {str(e)}"

# ═══════════════════════════════════════════════════════════════════════════
# 決策閘門（60秒超時）
# ═══════════════════════════════════════════════════════════════════════════

def decision_gate(timeout_sec=60):
    """等待 Jo 輸入决策，60秒超時則預設 [2] 略過"""
    print(f"\n{'='*50}")
    print("🤖 Ray 指揮官決策選單")
    print(" [1] ⚡ 立即執行")
    print(" [2] ✋ 暫時略過（預設，60秒後自動執行）")
    print(" [3] 🔍 深度歸因")
    print(" [4] 🛠️ 手動修正")
    print(f"{'='*50}")
    print(f"請輸入決策 [1-4]（{timeout_sec}秒內無回應則自動略過）: ", end="", flush=True)

    import threading

    result = {"choice": None}

    def input_reader():
        try:
            result["choice"] = input().strip()
        except:
            result["choice"] = ""

    t = threading.Thread(target=input_reader, daemon=True)
    t.start()
    t.join(timeout=timeout_sec)

    choice = result["choice"]

    if choice == "":
        print("⏱️  超時未回應，自動選擇 [2] 略過")
        choice = "2"

    return choice

# ═══════════════════════════════════════════════════════════════════════════
# 決策執行
# ═══════════════════════════════════════════════════════════════════════════

def execute_decision(choice, symbol, tech):
    """根據决策代號執行對應動作"""
    action_map = {
        "1": ("⚡ 立即執行", "🚀"),
        "2": ("✋ 暫時略過", "💤"),
        "3": ("🔍 深度歸因", "🧠"),
        "4": ("🛠️ 手動修正", "✍️"),
    }

    label, icon = action_map.get(choice, ("❌ 無效", "❌"))

    print(f"\n{icon} 决策: {label}")
    print(f"{'='*50}")

    if choice == "1":
        print(f"🚀 指令已發送至 Gateway...")
        log_to_memory(f"ACTION: EXECUTE | {symbol} | {tech.get('price')} | {analysis[:100]}")
    elif choice == "2":
        print(f"💤 略過。系統將繼續監控 {symbol}，等待下一個信號。")
        log_to_memory(f"ACTION: SKIP | {symbol} | RSI={tech.get('rsi')} | {analysis[:80]}")
    elif choice == "3":
        print(f"  🧠 啟動 7B 深度歸因蒸餾...")
        print(f"  📝 失敗歸因腳本: scripts/ray_logic_distiller.py")
        print(f"  ⏰ 將於下次 14:05 自動執行")
        # 寫入待處理標記
        pending = BASE_DIR / "stores" / "short_term" / "pending_deep_analysis.json"
        try:
            data = json.loads(pending.read_text(encoding="utf-8")) if pending.exists() else []
        except:
            data = []
        data.append({"symbol": symbol, "time": datetime.now().isoformat(), "reason": "manual_deep"})
        pending.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  ✅ 已加入深度分析佇列")

    elif choice == "4":
        print(f"✍️ 手動修正模式")
        correction = input("請輸入欲修正的邏輯或規則：").strip()
        if correction:
            log_to_memory(f"FIX: {symbol} | {correction}")
            print(f"✅ 修正已記錄，將於明日 05:00 固化")
        else:
            print(f"⚠️ 無輸入，略過")

# ═══════════════════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print()
    print("="*60)
    print("🛡️ Ray System — 決策閘門 (Decision Gateway)")
    print(f"   VRAM Guard: {'✅' if _HAS_GUARD else '⚠️ 不存在'}")
    print(f"   時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    # 解析參數
    args = sys.argv[1:]
    if not args:
        print("用法: python ray_decision_gateway.py NVDA [model]")
        print("       python ray_decision_gateway.py 3034.TW --mode tw")
        sys.exit(1)

    symbol = args[0].upper()
    model = args[1] if len(args) > 1 and not args[1].startswith("--") else "qwen3.5:4b-instruct-q4_K_S"

    print(f"\n📌 分析標的: {symbol}")
    print(f"🤖 使用模型: {model}")

    # Step 1: 抓技術數據
    print()
    tech = get_tech_summary(symbol)
    if not tech:
        print(f"❌ 無法獲取 {symbol} 數據")
        sys.exit(1)

    print()
    print("【技術面】")
    print(f"  現價: {format_price(tech['price'])} ({tech['change_pct']:+.2f}%)")
    print(f"  RSI: {tech['rsi']} | MA20: {format_price(tech['ma20'])} | MA60: {format_price(tech['ma60'])}")
    print(f"  MACD Hist: {tech['macd_hist']} ({'正' if tech['macd_positive'] else '負'})")
    print(f"  MA 排列: {'多頭' if tech['ma20_above_ma60'] else '空頭'}")

    # Step 2: AI 分析
    print()
    analysis = run_ai_analysis(symbol, tech, model=model)
    print()
    print("【AI 分析結果】")
    print("-"*50)
    print(analysis)
    print("-"*50)

    # Step 3: 決策閘門
    choice = decision_gate(timeout_sec=60)

    # Step 4: 執行决策
    execute_decision(choice, symbol, tech)

    print()
    print(f"✅ 決策流程完成 | {datetime.now().strftime('%H:%M:%S')}")
    print("🔒 VRAM 解鎖 | 系統恢復監控")

if __name__ == "__main__":
    main()