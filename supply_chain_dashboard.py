# -*- coding: utf-8 -*-
"""
supply_chain_dashboard.py — 產業鏈族群連動性儀表板
可獨立運行或嵌入 streamlit

功能：
  1. 族群連動性：上游大漲 → 亮燈提示下游「補漲」標的
  2. 財報預警：上下游營收分歧（Divergence）警示
  3. 集中度風險：單一客戶佔比過高警示（Taleb 反脆弱）
"""
import sys, json, os, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import yfinance as yf
import numpy as np
import streamlit as st

AGENTS_DIR = r"C:\Users\USER\.openclaw\agents\ray"
RAM_CACHE = os.path.join(AGENTS_DIR, "supply_chain_ram.json")

# ── 讀取產業鏈 ──────────────────────────────────────────────
def load_chain():
    if os.path.exists(RAM_CACHE):
        with open(RAM_CACHE, 'r', encoding='utf-8', errors='replace') as f:
            return json.load(f)
    return {}

def get_rsi(c, p=14):
    if len(c) < p + 1:
        return 50.0
    d = np.diff(c)
    g = np.where(d > 0, d, 0)
    l = np.where(d < 0, -d, 0)
    ag = np.mean(g[-p:])
    al = np.mean(l[-p:])
    return 100 - (100 / (1 + ag / al)) if al != 0 else 50.0

def get_price_change(symbol):
    """抓取單一股票日漲幅"""
    try:
        h = yf.Ticker(symbol).history(period="5d")
        if h is None or h.empty or len(h) < 2:
            return None, None
        close = h['Close'].values
        pct = (close[-1] - close[-2]) / close[-2] * 100
        rsi = get_rsi(close)
        return round(pct, 2), round(rsi, 1)
    except:
        return None, None

# ── 評估函式 ──────────────────────────────────────────────
def eval_upstream_glow(chain):
    """評估上游是否大漲→下游補漲機會"""
    results = []
    for sym, data in chain.items():
        up_pct = []
        for upstream in data.get("upstream", []):
            # 嘗試解析上游代碼（简单关键字匹配）
            tick = upstream.split("(")[-1].split(")")[0] if "(" in upstream else None
            if tick:
                pct, rsi = get_price_change(tick)
                if pct:
                    up_pct.append(pct)

        if up_pct:
            avg_up_pct = sum(up_pct) / len(up_pct)
            my_pct, my_rsi = get_price_change(sym)
            if my_pct is not None:
                gap = avg_up_pct - my_pct
                results.append({
                    "symbol": sym,
                    "avg_upstream_pct": round(avg_up_pct, 2),
                    "my_pct": my_pct,
                    "gap": round(gap, 2),
                    "upstream": data.get("upstream", []),
                    "downstream": data.get("downstream", []),
                    "status": "🔴 補漲機會" if gap > 2 else "🟡 落後" if gap > 0 else "🟢 連動正常"
                })
    return sorted(results, key=lambda x: x["gap"], reverse=True)

def eval_divergence(chain):
    """上下游營收分歧警示（示範：簡單價格分歧）"""
    alerts = []
    for sym, data in chain.items():
        my_pct, _ = get_price_change(sym)
        if my_pct is None:
            continue

        up_alert = False
        for upstream in data.get("upstream", [])[:1]:
            tick = upstream.split("(")[-1].split(")")[0] if "(" in upstream else None
            if tick:
                up_pct, _ = get_price_change(tick)
                if up_pct and my_pct > 2 and up_pct < -1:
                    alerts.append({
                        "symbol": sym,
                        "issue": "價格分歧",
                        "detail": f"{sym}漲{my_pct}%但上游{tick}跌{up_pct}%",
                        "risk": "⚠️ 上游拖累"
                    })
        if not up_alert and len(alerts) < 5:
            pass  # 正常
    return alerts

def eval_concentration(sym, downstream_list):
    """單一客戶集中度風險（Taleb 反脆弱）"""
    if not downstream_list:
        return None
    risks = []
    if len(downstream_list) == 1:
        risks.append(f"⚠️ {sym} 完全依賴單一客戶 {downstream_list[0]}")
    if len(downstream_list) <= 2:
        risks.append(f"⚠️ 客戶基礎過窄（僅{len(downstream_list)}個）")
    return risks if risks else None

# ── Streamlit UI ──────────────────────────────────────────
def run_dashboard():
    st.set_page_config(page_title="產業鏈連動儀表板", layout="wide")
    st.title("🔗 產業鏈族群連動性")

    chain = load_chain()
    if not chain:
        st.warning("尚無產業鏈資料，請先執行 supply_chain_scanner.py")
        return

    # 讀取今日資料
    with st.spinner("抓取最新報價..."):
        analysis = eval_upstream_glow(chain)

    # ── Tab 1：族群連動 ─────────────────────────────────
    st.header("📊 族群連動性 — 上游 vs 下游")
    if analysis:
        for item in analysis:
            with st.container():
                col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
                with col1:
                    st.metric(item["symbol"], f"{item['my_pct']:+.2f}%")
                with col2:
                    st.metric("上淤平均", f"{item['avg_upstream_pct']:+.2f}%")
                with col3:
                    st.metric("落差", f"{item['gap']:+.2f}%")
                with col4:
                    st.write(item["status"])
                    st.caption(f"上游: {item['upstream']}")
    else:
        st.info("暫無連動資料")

    # ── Tab 2：風險警報 ──────────────────────────────────
    st.header("🚨 風險警報")
    divs = eval_divergence(chain)

    # 集中度檢查
    concentration_risks = []
    for sym, data in list(chain.items())[:5]:
        risks = eval_concentration(sym, data.get("downstream", []))
        if risks:
            concentration_risks.append({"symbol": sym, "risks": risks})

    if divs or concentration_risks:
        for d in divs:
            st.error(f"{d['symbol']}: {d['detail']} | {d['risk']}")
        for cr in concentration_risks:
            for r in cr["risks"]:
                st.warning(f"{cr['symbol']}: {r}")
    else:
        st.success("✅ 無風險警報")

    # ── Tab 3：產業鏈總覽 ──────────────────────────────
    st.header("🗺️ 產業鏈總覽")
    rows = []
    for sym, data in chain.items():
        my_pct, my_rsi = get_price_change(sym)
        rows.append({
            "symbol": sym,
            "price": data.get("price", my_pct or 0),
            "day_pct": my_pct or 0,
            "rsi": my_rsi or 0,
            "upstream": ", ".join(data.get("upstream", [])[:2]),
            "downstream": ", ".join(data.get("downstream", [])[:2]),
            "last_scan": data.get("last_scan", "N/A")
        })
    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("尚無資料")

def run_standalone():
    """非 streamlit 環境：直接輸出文字報告"""
    print("=" * 60)
    print(" 產業鏈連動性儀表板")
    print(f" Time: {time.strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    chain = load_chain()
    if not chain:
        print("[-] 無產業鏈資料，執行 supply_chain_scanner.py")
        return

    analysis = eval_upstream_glow(chain)

    print(f"\n📊 族群連動性（{len(analysis)} 檔）")
    print(f"{'Symbol':<8} {'本身':>8} {'上淤均':>8} {'落差':>8} {'狀態'}")
    for item in analysis:
        print(f"{item['symbol']:<8} {item['my_pct']:>+7.2f}% {item['avg_upstream_pct']:>+7.2f}% {item['gap']:>+7.2f}% {item['status']}")

    divs = eval_divergence(chain)
    if divs:
        print(f"\n🚨 風險警報")
        for d in divs:
            print(f"  {d['symbol']}: {d['detail']} | {d['risk']}")
    else:
        print(f"\n✅ 無風險警報")

    print("=" * 60)

if __name__ == "__main__":
    try:
        import streamlit as st
        run_dashboard()
    except:
        run_standalone()