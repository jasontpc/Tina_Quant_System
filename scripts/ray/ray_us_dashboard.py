# -*- coding: utf-8 -*-
"""
ray_us_dashboard.py — Ray System 2.0 美股 AI 分析中心
============================================================
Streamlit UI: 整合 ray_data_center + ray_engine + us_scan_live
i9 CPU: K線計算 / RTX 4050: Ollama 邏輯分析
VRAM 保護: @ray_singleton 排隊機制

Run: 
  streamlit run ray_us_dashboard.py                    # 一般模式
  streamlit run ray_us_dashboard.py -- --debug        # DEBUG 模式
  streamlit run ray_us_dashboard.py -- --log          # LOG 模式
  streamlit run ray_us_dashboard.py -- --debug --log  # 兩者皆開
"""

import sys, os, time, json
from pathlib import Path
from datetime import datetime
import argparse

# ── 命令列參數解析 ──────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--debug", action="store_true")
parser.add_argument("--log", action="store_true")
args, _ = parser.parse_known_args()

_DEBUG = args.debug
_LOG   = args.log

# ── 日誌設定 ───────────────────────────────────────────────────────────────
BASE_DIR = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
LOG_DIR  = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "ray_us_dashboard.log"

def _log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    if _DEBUG:
        print(line)
    if _LOG:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")

_log("=" * 60)
_log("Ray System 2.0 Dashboard")
_log(f"DEBUG={_DEBUG} LOG={_LOG}")
_log("=" * 60)

sys.path.insert(0, str(BASE_DIR))

# ── VRAM 守護 ──────────────────────────────────────────────────────────────
sys.path.insert(0, str(BASE_DIR / "scripts" / "utils"))
try:
    from ray_guard import ray_singleton
    _has_guard = True
    _log("ray_guard OK", "DEBUG")
except ImportError:
    def ray_singleton(func): return func
    _has_guard = False
    _log("ray_guard NOT FOUND", "WARN")

# ── Streamlit 設定 ──────────────────────────────────────────────────────────
import streamlit as st
st.set_page_config(
    page_title="Ray System 2.0 — US AI Analysis",
    page_icon=":arrows_counterclockwise:",
    layout="wide",
)

# ── 依賴檢查 ──────────────────────────────────────────────────────────────
try:
    import yfinance as yf
    import pandas as pd
    import numpy as np
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    _HAS_DEPS = True
except ImportError as e:
    st.error(f"依賴缺失: {e}")
    st.stop()

# ═══════════════════════════════════════════════════════════════════════════
# 工具函式
# ═══════════════════════════════════════════════════════════════════════════

SHARPE_MIN = 1.5
MDD_MAX    = 0.15
WIN_MIN    = 0.45

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

def kdj(h, l, c, n=9):
    k=np.zeros_like(c); d=np.zeros_like(c)
    for i in range(n-1, len(c)):
        lo = np.min(l[max(0,i-n+1):i+1])
        hi = np.max(h[max(0,i-n+1):i+1])
        k[i] = 50 if hi==lo else (c[i]-lo)/(hi-lo)*100
        d[i] = float(np.nanmean(k[max(n,i-n+1):i+1])) if i>=n else 50.0
    j = 3*k-2*d
    return k, d, j

def calc_rolling_stats(df, window=30):
    if len(df) < window:
        return {"sharpe": None, "mdd": None, "win_rate": None}
    c = df['Close'].values.astype(float)
    ret = np.diff(c)/c[:-1]; ret = np.insert(ret, 0, 0)
    cum = np.cumsum(ret); cummax = np.maximum.accumulate(cum)
    mdd = float(np.max(cummax - cum))
    mean_ret = float(np.mean(ret)); std_ret = float(np.std(ret))
    sharpe = (mean_ret/std_ret*np.sqrt(252)) if std_ret>1e-10 else 0.0
    win_rate = float(np.sum(ret>0)/max(len(ret),1))
    return {"sharpe": round(sharpe,3), "mdd": round(mdd,4), "win_rate": round(win_rate,4)}

def get_tech_snapshot(df):
    c = df['Close'].values.astype(float)
    h = df['High'].values.astype(float)
    l = df['Low'].values.astype(float)
    v = df['Volume'].values.astype(float)
    m20 = ema(c, 20); m60 = ema(c, 60)
    ef = ema(c, 12); es = ema(c, 26)
    mac = ef - es; sigv = ema(mac, 9); mh = mac - sigv
    k_arr, d_arr, j_arr = kdj(h, l, c)
    rs = rsi_calc(c)
    j0 = float(j_arr[-1]) if not np.isnan(j_arr[-1]) else 50.0
    j1 = float(j_arr[-2]) if len(j_arr)>=2 else j0
    k0 = float(k_arr[-1]) if not np.isnan(k_arr[-1]) else 50.0
    d0 = float(d_arr[-1]) if not np.isnan(d_arr[-1]) else 50.0
    p  = float(c[-1])
    stats = calc_rolling_stats(df, 30)
    sharpe = stats.get("sharpe") or 0
    mdd    = stats.get("mdd")    or 999
    win_r  = stats.get("win_rate") or 0
    math_passed = (sharpe >= SHARPE_MIN and mdd <= MDD_MAX and win_r >= WIN_MIN)
    bull = 0
    if p > float(m20[-1]): bull += 1
    if p > float(m60[-1]): bull += 1
    if float(mh[-1]) > 0: bull += 1
    if j0 > j1 and 10 < j0 < 85: bull += 1
    signal = "BUY" if (bull>=3 and math_passed) else ("WATCH" if math_passed else "NEUTRAL")
    return {
        "price": p,
        "change_pct": round((p/float(c[-2])-1)*100, 2) if len(c)>=2 else 0,
        "ma20": round(float(m20[-1]), 2),
        "ma60": round(float(m60[-1]), 2),
        "rsi": round(rs, 1),
        "macd_hist": round(float(mh[-1]), 3),
        "kdj_k": round(k0, 1),
        "kdj_d": round(d0, 1),
        "kdj_j": round(j0, 1),
        "volume": int(v[-1]),
        "sharpe": sharpe, "mdd": mdd, "win_rate": round(win_r*100, 1),
        "math_passed": math_passed, "bull_score": bull, "signal": signal,
    }

def get_fundamental(ticker):
    try:
        info = ticker.info
        return {
            "eps": info.get("trailingEps"),
            "pe": info.get("trailingPE"),
            "market_cap": info.get("marketCap"),
            "gross_margin": round(info.get("grossMargins",0)*100,2) if info.get("grossMargins") else None,
            "op_margin": round(info.get("operatingMargins",0)*100,2) if info.get("operatingMargins") else None,
            "profit_margin": round(info.get("profitMargins",0)*100,2) if info.get("profitMargins") else None,
            "avg_target": info.get("targetMeanPrice"),
            "recommendation": info.get("recommendationKey"),
            "sector": info.get("sector"),
        }
    except:
        return {}

def format_mc(val):
    if val is None: return "N/A"
    if val > 1e12: return f"${val/1e12:.2f}T"
    if val > 1e9:  return f"${val/1e9:.1f}B"
    return f"${val:,.0f}"

def get_watchlist():
    wl = BASE_DIR / "stores" / "long_term" / "us_watchlist.json"
    if wl.exists():
        try:
            return json.loads(wl.read_text(encoding="utf-8"))
        except: pass
    return ["NVDA","AMD","AVGO","AMAT","META","AAPL","MSFT","GOOGL","AMZN","TSLA","QCOM","MU","INTC","ASML","LRCX","KLAC","TER","SNPS","NXPI","MRVL"]

def plot_kline(df, symbol, tech=None):
    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True,
        vertical_spacing=0.05, row_heights=[0.4, 0.2, 0.2, 0.2],
        subplot_titles=(f"{symbol} K線 + MA20/60/120/200", "RSI(14)", "MACD Hist + Signal", "KDJ K/D/J"),
    )
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name="K線", increasing_line_color='#26A69A', decreasing_line_color='#EF5350',
    ), row=1, col=1)
    c = df['Close'].values.astype(float)
    m20 = ema(c, 20); m60 = ema(c, 60); m120 = ema(c, 120); m200 = ema(c, 200)
    fig.add_trace(go.Scatter(x=df.index, y=m20, line=dict(color="#FF9800", width=1.2), name="MA20"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=m60, line=dict(color="#42A5F5", width=1.2), name="MA60"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=m120, line=dict(color="#AB47BC", width=1.0), name="MA120"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=m200, line=dict(color="#78909C", width=1.0), name="MA200"), row=1, col=1)
    rsi_vals = [rsi_calc(df['Close'].values[:i+1]) for i in range(len(df))]
    fig.add_trace(go.Scatter(x=df.index, y=rsi_vals, fill='tozeroy', fillcolor='rgba(156,39,176,0.15)',
                             line=dict(color="#9C27B0", width=1.5), name="RSI"), row=2, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="#EF5350", line_width=0.8, row=2, col=1)
    fig.add_hline(y=50, line_dash="dot", line_color="#90A4AE", line_width=0.5, row=2, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="#26A69A", line_width=0.8, row=2, col=1)
    ef = ema(c, 12); es = ema(c, 26)
    mac = ef - es; sigv = ema(mac, 9); mh = mac - sigv
    colors = ["#26A69A" if x >= 0 else "#EF5350" for x in mh]
    fig.add_trace(go.Bar(x=df.index, y=mh, marker_color=colors, name="MACD Hist"), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=sigv, line=dict(color="#FFA726", width=1.2), name="Signal"), row=3, col=1)
    fig.add_hline(y=0, line_dash="dot", line_color="#90A4AE", line_width=0.5, row=3, col=1)
    k_arr, d_arr, j_arr = kdj(df['High'].values, df['Low'].values, c)
    fig.add_trace(go.Scatter(x=df.index, y=k_arr, line=dict(color="#42A5F5", width=1.2), name="K"), row=4, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=d_arr, line=dict(color="#FF9800", width=1.2), name="D"), row=4, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=j_arr, line=dict(color="#E91E63", width=1.0),
                             fill='tozeroy', fillcolor='rgba(233,30,99,0.1)', name="J"), row=4, col=1)
    fig.add_hline(y=80, line_dash="dot", line_color="#EF5350", line_width=0.8, row=4, col=1)
    fig.add_hline(y=20, line_dash="dot", line_color="#26A69A", line_width=0.8, row=4, col=1)
    fig.update_layout(
        title=f"{symbol} 實戰分析", xaxis_rangeslider_visible=False, height=750,
        template="plotly_dark",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=60, r=20, b=40, l=20),
    )
    return fig

# ═══════════════════════════════════════════════════════════════════════════
# AI 分析（VRAM 保護）
# ═══════════════════════════════════════════════════════════════════════════

@ray_singleton
def run_ai_analysis(symbol, tech_data, fund_data, model="qwen3.5-4b-iq4xs:latest"):
    import subprocess, re
    axioms_path = BASE_DIR / "stores" / "long_term" / "axioms_v3.5.json"
    forbidden_path = BASE_DIR / "stores" / "long_term" / "ray_forbidden_rules.json"

    axioms_text = ""
    if axioms_path.exists():
        try:
            axioms = json.loads(axioms_path.read_text(encoding="utf-8"))
            rules = axioms if isinstance(axioms, list) else axioms.get("axioms", axioms.get("rules", []))
            axioms_text = "\n".join([f"{i+1}. {r.get('text', r) if isinstance(r, dict) else r}" for i, r in enumerate(rules[:8])])
        except: axioms_text = "（無法讀取 axioms）"

    forbidden_text = ""
    if forbidden_path.exists():
        try:
            forbid = json.loads(forbidden_path.read_text(encoding="utf-8"))
            rules = forbid.get("rules", [])[-5:]
            forbidden_text = "\n".join([f"- {r.get('symbol','ALL')}: {r.get('rule','')}" for r in rules])
        except: forbidden_text = "（無）"

    prompt = f"""### ROLE: RAY-COMMANDER V3.5
你是美股波段交易分析師。分析 symbol={symbol}。

【技術面】
- Price: ${tech_data.get('price', 'N/A')}
- RSI(14): {tech_data.get('rsi', 'N/A')}
- MA20: ${tech_data.get('ma20', 'N/A')} | MA60: ${tech_data.get('ma60', 'N/A')}
- MACD Hist: {tech_data.get('macd_hist', 'N/A')}
- KDJ(J): {tech_data.get('kdj_j', 'N/A')}
- Sharpe(30d): {tech_data.get('sharpe', 'N/A')} | MDD: {tech_data.get('mdd', 'N/A')}%
- Signal: {tech_data.get('signal', 'N/A')} (bull={tech_data.get('bull_score', 0)}/4)

【基本面】
- EPS: {fund_data.get('eps', 'N/A')}
- P/E: {fund_data.get('pe', 'N/A')}
- Market Cap: {format_mc(fund_data.get('market_cap'))}
- 毛利率: {fund_data.get('gross_margin', 'N/A')}%
- 營益率: {fund_data.get('op_margin', 'N/A')}%
- 淨利率: {fund_data.get('profit_margin', 'N/A')}%
- Recommendation: {fund_data.get('recommendation', 'N/A')}

【Axioms 框架】
{axioms_text}

【禁止規則】
{forbidden_text}

請提供（繁體中文，Markdown格式）：
1. 技術面簡析（1-2句）
2. 基本面簡析（1-2句）
3. 綜合評分（0-100）及理由
4. 實戰建議：BUY / HOLD / WATCH / REDUCE / SELL（含進場/停損價位）
5. Taleb 風險提示

---
[1] 立即執行 | [2] 略過 | [3] 深度歸因 | [4] 手動修正
"""

    try:
        list_result = subprocess.run(
            ["ollama", "list"], capture_output=True, timeout=15, encoding="utf-8", errors="replace"
        )
        available = []
        if list_result.returncode == 0:
            for line in list_result.stdout.split("\n"):
                parts = line.split()
                if parts: available.append(parts[0])

        if model not in available:
            return f"[Model Not Ready] {model} 未安裝或正在下載。請執行: ollama pull {model}"

        result = subprocess.run(
            ["ollama", "run", model],
            input=prompt, capture_output=True, text=True, timeout=120,
            encoding="utf-8", errors="replace",
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            stderr_clean = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', result.stderr).strip()
            return f"[Ollama Error] {stderr_clean[:200]}" if stderr_clean else "[Ollama Error]"
    except subprocess.TimeoutExpired:
        return "[Timeout] 模型回應逾時（120秒）"
    except FileNotFoundError:
        return "[Error] Ollama 未運行。請執行: ollama serve"
    except Exception as e:
        return f"[Error] {str(e)}"

# ═══════════════════════════════════════════════════════════════════════════
# Session State
# ═══════════════════════════════════════════════════════════════════════════
if "analysis_log" not in st.session_state:
    st.session_state["analysis_log"] = []
if "selected_symbols" not in st.session_state:
    st.session_state["selected_symbols"] = []

# ═══════════════════════════════════════════════════════════════════════════
# 側邊欄
# ═══════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## [Shield] Ray System 2.0")
    st.divider()

    # 分析模式
    mode = st.radio("**模式**", ["單一個股", "批次分析", "全市場掃描"], index=0, horizontal=False)
    st.divider()

    # ── 單一個股 ──────────────────────────────────────────────────────────
    if mode == "單一個股":
        symbol_input = st.text_input("**美股代碼**", value="", placeholder="NVDA / AAPL / MSFT...").strip().upper()
        st.caption("輸入後按下方按鈕")
        quick = st.columns(3)
        for i, sym in enumerate(["NVDA", "AAPL", "MSFT"]):
            if quick[i].button(sym, use_container_width=True):
                symbol_input = sym
                st.rerun()
        period = st.select_slider("**時間**", options=["1mo","3mo","6mo","1y","2y","5y"], value="1y")
        col_scan, col_ai = st.columns(2)
        with col_scan:
            scan_btn = st.button("[Scan] 技術分析", use_container_width=True, type="primary")
        with col_ai:
            ai_btn = st.button("[AI] 深度分析", use_container_width=True)

    # ── 批次分析 ──────────────────────────────────────────────────────────
    elif mode == "批次分析":
        watchlist = get_watchlist()
        selected = st.multiselect("**選擇股票**", watchlist,
            default=st.session_state.get("selected_symbols", ["NVDA","AMD","AVGO"]),
            label_visibility="collapsed")
        st.session_state["selected_symbols"] = selected
        st.markdown(f"已選 **{len(selected)}** 檔")
        c1, c2 = st.columns(2)
        with c1:
            st.button("[+] 全選", use_container_width=True,
                on_click=lambda: st.session_state.update({"selected_symbols": watchlist}))
        with c2:
            st.button("[-] 清空", use_container_width=True,
                on_click=lambda: st.session_state.update({"selected_symbols": []}))
        period_b = st.select_slider("**時間**", options=["1mo","3mo","6mo","1y","2y"], value="6mo")
        scan_btn = st.button("[Scan] 批次掃描", use_container_width=True, type="primary")

    # ── 全市場掃描 ──────────────────────────────────────────────────────────
    elif mode == "全市場掃描":
        watchlist = get_watchlist()
        st.markdown(f"**全市場掃描 ({len(watchlist)} 檔)**")
        st.caption("Math Gate: Sharpe>1.5 / MDD<15% / Win>45%")
        period_s = st.select_slider("**時間**", options=["3mo","6mo","1y"], value="6mo")
        scan_btn = st.button("[Scan] 全市場掃描", use_container_width=True, type="primary")
        ai_btn = False

    st.divider()

    # VRAM 狀態
    lock_file = BASE_DIR / "locks" / "ray_vram.lock"
    if lock_file.exists():
        holder = lock_file.read_text(encoding="utf-8", errors="ignore").split("|")[0] or "?"
        age = time.time() - lock_file.stat().st_mtime
        st.warning(f"[LOCK] {holder} ({age:.0f}s)")
    else:
        st.success("[FREE] VRAM 空閒")

    # 模型選擇
    model_opts = ["qwen3.5-4b-iq4xs:latest", "qwen2.5:7b", "ray-v3.5:latest", "ray-deep-v1:latest"]
    model_lbl = {"qwen3.5-4b-iq4xs:latest":"qwen3.5:4b", "qwen2.5:7b":"qwen2.5:7b",
                 "ray-v3.5:latest":"ray-v3.5(固化)", "ray-deep-v1:latest":"ray-deep-v1"}
    selected_model = st.selectbox("**模型**", model_opts,
        format_func=lambda x: model_lbl.get(x, x), label_visibility="collapsed")

    st.divider()
    st.caption(f"VRAM Guard: {'OK' if _has_guard else 'NOT FOUND'}")
    st.caption(f"DEBUG={_DEBUG} LOG={_LOG}")

# ═══════════════════════════════════════════════════════════════════════════
# 頁面標題
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("### [Shield] Ray System 2.0 — US AI Analysis")
st.caption("i9 CPU (K線) + RTX 4050 (Ollama) | VRAM 排隊保護 | DEBUG={} LOG={}".format(_DEBUG, _LOG))
st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# 模式 1: 單一個股
# ═══════════════════════════════════════════════════════════════════════════
if mode == "單一個股":
    symbol = symbol_input.upper() if symbol_input else ""

    if not symbol:
        st.info("👈 在左側輸入美股代碼（NVDA / AAPL / MSFT）然後選擇 [Scan] 或 [AI]")
    else:
        col_chart, col_info, col_ai = st.columns([2, 1, 1], gap="medium")

        with col_chart:
            if scan_btn or ai_btn:
                try:
                    df = yf.Ticker(symbol).history(period=period, interval="1d", auto_adjust=True, timeout=15)
                    if df.empty or len(df) < 30:
                        st.warning(f"{symbol} 數據不足")
                    else:
                        tech = get_tech_snapshot(df)
                        fig = plot_kline(df, symbol, tech)
                        st.plotly_chart(fig, use_container_width=True)
                        st.caption(f"{period} | {df.index[-1].strftime('%Y-%m-%d')}")
                except Exception as e:
                    st.error(f"讀取失敗: {e}")
            else:
                st.info("👈 選擇 [Scan] 或 [AI] 開始")

        with col_info:
            if scan_btn or ai_btn:
                try:
                    df2 = yf.Ticker(symbol).history(period=period, interval="1d", auto_adjust=True, timeout=15)
                    if not df2.empty:
                        tech = get_tech_snapshot(df2)
                        fund = get_fundamental(yf.Ticker(symbol))
                        sig = tech["signal"]
                        st.metric(label="現價", value=f"${tech['price']:.2f}", delta=f"{tech['change_pct']:.2f}%")
                        st.markdown(f"**Signal: {sig}** (bull={tech['bull_score']}/4)")
                        st.progress(tech['rsi']/100, text=f"RSI: {tech['rsi']:.1f}")
                        r1, r2, r3, r4 = st.columns(4)
                        r1.metric("MA20", f"${tech['ma20']:.2f}")
                        r2.metric("MA60", f"${tech['ma60']:.2f}")
                        r3.metric("MACD", f"{tech['macd_hist']:.3f}")
                        r4.metric("KDJ(J)", f"{tech['kdj_j']:.1f}")
                        st.markdown("**風控**")
                        k1, k2, k3, k4 = st.columns(4)
                        k1.metric("Sharpe", f"{tech['sharpe']:.2f}")
                        k2.metric("MDD", f"{tech['mdd']:.2%}")
                        k3.metric("Win%", f"{tech['win_rate']:.1f}%")
                        k4.metric("K/D", f"{tech.get('kdj_k','?')}/{tech.get('kdj_d','?')}")
                        st.caption(f"Math: {'PASS' if tech['math_passed'] else 'FAIL'}")
                        st.markdown("**基本面**")
                        b1, b2 = st.columns(2)
                        b1.metric("EPS", f"${fund.get('eps', 'N/A')}")
                        b2.metric("P/E", f"{fund.get('pe', 'N/A')}")
                        gm = fund.get('gross_margin')
                        st.progress(gm/100 if gm else 0, text=f"毛利率: {gm:.1f}%" if gm else "毛利率: N/A")
                        st.caption(f"建議: {fund.get('recommendation', 'N/A')}")
                except Exception as e:
                    st.error(f"數據失敗: {e}")

        with col_ai:
            if ai_btn:
                st.markdown(f"**AI 分析: {symbol}**")
                with st.spinner("VRAM 排隊中..."):
                    df3 = yf.Ticker(symbol).history(period="2y", interval="1d", auto_adjust=True, timeout=15)
                    tech3 = get_tech_snapshot(df3)
                    fund3 = get_fundamental(yf.Ticker(symbol))
                    result = run_ai_analysis(symbol, tech3, fund3, model=selected_model)
                    st.markdown(result)
                    st.caption(f"Model: {selected_model}")
                    st.session_state["analysis_log"].append({
                        "symbol": symbol, "time": datetime.now().strftime("%H:%M"), "result": result[:300]
                    })
            else:
                st.markdown("**AI 分析**")
                st.caption("選擇 [AI] 深度分析")

        # 分析記錄
        if st.session_state.get("analysis_log"):
            st.markdown("---")
            st.markdown("**📜 分析記錄**")
            for entry in reversed(st.session_state["analysis_log"][-3:]):
                with st.expander(f"{entry['symbol']} @ {entry['time']}"):
                    st.markdown(entry["result"][:500] + ("..." if len(entry["result"])>500 else ""))

# ═══════════════════════════════════════════════════════════════════════════
# 模式 2: 批次分析
# ═══════════════════════════════════════════════════════════════════════════
elif mode == "批次分析":
    selected = st.session_state.get("selected_symbols", [])
    if not selected:
        st.warning("👈 在左側選擇股票")
    elif scan_btn:
        st.markdown(f"## [Scan] 批次技術掃描 — {len(selected)} 檔")
        status = st.empty()
        rows = []
        for i, sym in enumerate(selected):
            status.text(f"掃描中: {sym} ({i+1}/{len(selected)})")
            try:
                df_s = yf.Ticker(sym).history(period=period_b, interval="1d", auto_adjust=True, timeout=10)
                if df_s is not None and len(df_s) >= 30:
                    t = get_tech_snapshot(df_s)
                    rows.append({
                        "Symbol": sym, "Price": f"${t['price']:.2f}",
                        "RSI": t['rsi'], "Sharpe": t['sharpe'],
                        "MDD": f"{t['mdd']:.2%}", "Signal": t['signal'],
                        "Bull": f"{t['bull_score']}/4", "Math": "PASS" if t['math_passed'] else "FAIL",
                    })
            except:
                pass
            time.sleep(0.15)
        status.empty()
        if rows:
            df_r = pd.DataFrame(rows)
            buy_df = df_r[df_r["Signal"]=="BUY"].sort_values("Sharpe", ascending=False)
            watch_df = df_r[df_r["Signal"]=="WATCH"].sort_values("Sharpe", ascending=False)
            if not buy_df.empty:
                st.markdown("### [Green] BUY Signals")
                st.dataframe(buy_df, use_container_width=True, hide_index=True)
            if not watch_df.empty:
                st.markdown("### [Yellow] WATCH Signals")
                st.dataframe(watch_df, use_container_width=True, hide_index=True)
            st.markdown("### 全部結果")
            st.dataframe(df_r.sort_values(["Signal","Sharpe"], ascending=[True,False]),
                        use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════════════════════════
# 模式 3: 全市場掃描
# ═══════════════════════════════════════════════════════════════════════════
elif mode == "全市場掃描":
    if scan_btn:
        watchlist = get_watchlist()
        st.markdown(f"## [Scan] 全市場技術掃描 — {len(watchlist)} 檔")
        status = st.empty()
        progress = st.progress(0)
        rows = []
        for i, sym in enumerate(watchlist):
            status.text(f"掃描中: {sym} ({i+1}/{len(watchlist)})")
            progress.progress((i+1)/len(watchlist))
            try:
                df_s = yf.Ticker(sym).history(period=period_s, interval="1d", auto_adjust=True, timeout=8)
                if df_s is None or len(df_s) < 60:
                    continue
                t = get_tech_snapshot(df_s)
                rows.append({
                    "Symbol": sym, "Price": f"${t['price']:.2f}",
                    "RSI": t['rsi'], "Sharpe": t['sharpe'],
                    "MDD": f"{t['mdd']:.2%}", "Signal": t['signal'],
                    "Bull": f"{t['bull_score']}/4", "Math": "PASS" if t['math_passed'] else "FAIL",
                })
            except:
                pass
            time.sleep(0.12)
        progress.empty(); status.empty()
        if rows:
            df_a = pd.DataFrame(rows)
            buy_a = df_a[df_a["Signal"]=="BUY"].sort_values("Sharpe", ascending=False)
            watch_a = df_a[df_a["Signal"]=="WATCH"].sort_values("Sharpe", ascending=False)
            if not buy_a.empty:
                st.markdown("### [Green] BUY Signals")
                st.dataframe(buy_a, use_container_width=True, hide_index=True)
            if not watch_a.empty:
                st.markdown("### [Yellow] WATCH Signals")
                st.dataframe(watch_a, use_container_width=True, hide_index=True)
            st.markdown("### 全部結果")
            st.dataframe(df_a.sort_values(["Signal","Sharpe"], ascending=[True,False]),
                        use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════════════════════════
# 底部資訊
# ═══════════════════════════════════════════════════════════════════════════
st.divider()
c1, c2, c3, c4 = st.columns(4)
c1.caption(f"VRAM Guard: {'OK' if _has_guard else 'NOT FOUND'}")
c2.caption(f"Model: {selected_model if 'selected_model' in dir() else 'qwen3.5-4b-iq4xs:latest'}")
c3.caption(f"Streamlit: {st.__version__}")
c4.caption(f"{datetime.now().strftime('%H:%M:%S')}")