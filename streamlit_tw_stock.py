# -*- coding: utf-8 -*-
"""
Tina Stock Scanner - Streamlit Version 2.0
TW + US Stock Analysis with Telegram Push
"""

import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
import time
import urllib.request
import json
from datetime import datetime

# ── Telegram ───────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = '8614615741:AAHEMV6daIzF6J_MFUAm8KkhJYtOGVOM14Q'
TELEGRAM_CHAT_ID = '1616824689'

def push_telegram(message):
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    data = json.dumps({'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}).encode()
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=10):
            return True, 'OK'
    except Exception as e:
        return False, str(e)

def format_telegram(results, title):
    if not results:
        return ["No results"]
    all_lines = [
        f"📊 *{title}* | {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "`" + "="*48 + "`"
    ]
    for r in results:
        tier_icon = {"A": "🥇", "B": "🥈", "C": "🥉", "D": "❌"}.get(r.get('tier','?'), '?')
        ma_icon = "✅" if r.get('ma20_above_ma60') else "❌"
        macd_icon = "✅" if r.get('macd_hist', 0) > 0 else "❌"
        bull = r.get('bullish', '❌')
        kd = "💎" if r.get('kd_golden') else ""
        all_lines.append(
            f"[{tier_icon}] {r['code']} {r['name'][:8]}"
            f" ${r['price']:.2f} ({r['chg']:+.2f}%)"
            f" R={r['rsi']:.0f} K={r['k']:.0f} D={r['d']:.0f}"
            f" BB%={r['bb_pct']:.0f} BIAS={r['bias5']:+.1f}% Vol={r['vol_ratio']:.1f}x"
            f" M={macd_icon} MA={ma_icon} {bull} {kd}"
        )
    a = sum(1 for r in results if r.get('tier') == 'A')
    b = sum(1 for r in results if r.get('tier') == 'B')
    c = sum(1 for r in results if r.get('tier') == 'C')
    all_lines.append("`" + "="*48 + "`")
    all_lines.append(f"🥇A={a} 🥈B={b} 🥉C={c} | Total={len(results)}")
    chunks = []
    chunk = []
    chunk_len = 0
    for line in all_lines:
        if chunk_len + len(line) + 1 > 4000 and chunk:
            chunks.append("\n".join(chunk))
            chunk = []
            chunk_len = 0
        chunk.append(line)
        chunk_len += len(line) + 1
    if chunk:
        chunks.append("\n".join(chunk))
    return chunks

# ── Session Cache ──────────────────────────────────────────────────────────────
SESSION_CACHE = {}
CACHE_TTL = 3600

# ── TW Categories ────────────────────────────────────────────────────────────
TW_CATS = {
    "熱門台股": ["2330","2454","2317","2382","3034","3665","2881","2603","2303","1216"],
    "AI 科技": ["2317","2324","2330","2345","2353","2381","2382","2454","3034","3095","3163","3211","3231","3306","3323","3325","3349","3432","3479","3483","3491","3534","3653","3665","3702","5515"],
    "半導體": ["2303","2311","2325","2363","2379","2473","3035","3041","3063","3105","3122","3141","3169","3178","3227","3228","3257","3259","3260","3264","3265","3268","3317","3372","3374","3438","3443","3467","3474","3519","3527","3529","3534","3536","3555","3556","3567","3579","3581","3598","3675","3680","3686","3707","4749","4923","4925","4945","4951","4966","4971","4973","4991","5236","5246","5262","5272","5274","5280","5297","5299","5302","5305","5344","5347","5351","5425","5443","5468","5483","5487","6103","6104","6129","6138","6147","6182","6187","6208","6223","6229","6233","6237","6239","6261","6271","6287","6291","6411","6415","6423","6435","6451","6457","6462","6485","6488","6494","6510","6515","6525","6526","6531","6532","6548","6552","6563","6568","6594","6640","6643","6651","6679","6683","6684","6693","6695","6699","6708","6716","6719","6720","6732","6756","6770","6786","6788","6819","6823","6829","6842","6895","6907","6920","6927","6953","6996","7530","7556","7669","7704","7707","7712","7734","7751","7768","7769","7770","7772","7796","7810","7815","7828","7843","7853","7856","7866","7872","7880","7886","7887","7899","7909","8024","8040","8054","8081","8086","8088","8091","8098","8102","8131","8150","8227","8261","8271","8277","8299","8383"],
    "光通訊/CPO": ["2345","3053","3432","3491","3534","3599","3627","4944","5233","5281","6255","6409","2444","3047","3053","3432","3491","3534","3558","3564","4903","4905","4906","4908","4909","5233","5353","6109","6409","3081","2455","3363","3163","6442","6715","4979","6451","4977","4908","3450","2489","3711","3265","6830","6223","6515","2360","2499","6706","2345","3665","3533","2455","3105","6488","2303","2330","3711"],
    "儲存/記憶體": ["2330","2382","2401","2454","3034","3044","3217","3356","3592","4924","4939","6208","6488","3711"],
    "ETF": ["0050","0056","00646","00662","00713","00757","00927","00878","00900","00902","00906"],
    "金融": ["2801","2807","2809","2812","2816","2820","2823","2827","2831","2832","2833","2833A","2834","2836","2836A","2837","2838","2838A","2845","2847","2849","2850","2851","2852","2854","2855","2856","2867","2880","2881","2881A","2881B","2881C","2882","2882A","2882B","2883","2883A","2883B","2884","2885","2886","2887","2887C","2887E","2887F","2887G","2887H","2887I","2887Z1","2888","2888A","2888B","2889","2890","2891","2891A","2891B","2891C","2892","2897","2897A","2897B","5820","5854","5859","5863","5864","5876","5878","5880","6004","6005","6012","6015","6016","6020","6021","6023","6024","6026","6027","6028","6035","6878"],
    "全部": [],
}

# ── US Categories ──────────────────────────────────────────────────────────────
US_CATS = {
    "AI Tech": ["NVDA","AMD","INTC","QCOM","AVGO","MRVL","TSM","MU","AMZN","MSFT","GOOGL","META","ANET","VRT","DELL","HPE","SMCI","AI","PATH","DT"],
    "Cloud": ["AMZN","MSFT","GOOGL","CRM","NOW","WDAY","TEAM","DDOG","SNOW","NET","AKAM","FFIV","PATH","VEEV"],
    "5G": ["QCOM","NOK","ERIC","AMAT","LRCX","AMAT","MU","SWKS","RF","VZ","T","TMUS"],
    "Semiconductors": ["NVDA","AMD","INTC","QCOM","AVGO","MRVL","TSM","MU","AMAT","LRCX","KLAC","SNPS","CDNS","NXPI","AMAT","MU"],
    "FinTech": ["PYPL","SQ","AFRM","COIN","HOOD","DB","BAC","GS","V","MA","PYPL","SQ","AFRM","COIN","HOOD"],
    "ETF": ["QQQ","SOXX","SMH","XLF","ARKK","FXI","GDX","XLE","IYF"],
    "全部": [],
}

# Build "全部"
def build_all(cats_dict):
    all_codes = []
    seen = set()
    for cat_codes in cats_dict.values():
        for c in cat_codes:
            if c not in seen:
                seen.add(c)
                all_codes.append(c)
    return sorted(all_codes, key=lambda x: (0, int(x)) if x.isdigit() else (1, x))[:500]

TW_CATS["全部"] = build_all({k: v for k, v in TW_CATS.items() if k != "全部"})
US_CATS["全部"] = build_all({k: v for k, v in US_CATS.items() if k != "全部"})

# ── Stock Names ───────────────────────────────────────────────────────────────
TW_NAMES = {
    "2330": "台積電", "2454": "聯發科", "2317": "鴻海", "2382": "廣達",
    "3034": "緯穎", "3665": "穎崴", "2881": "富邦金", "2603": "長榮",
    "2303": "聯電", "1216": "統一", "0050": "元大台灣50", "0056": "元大高股息",
    "00646": "富邦S&P500", "00662": "富邦NASDAQ", "00713": "元大高息低波",
    "3217": "3217", "2401": "2401", "3527": "3527", "4749": "美時",
    "6819": "6819", "6229": "6229", "6786": "6786", "6563": "6563",
    "5351": "5351", "4923": "4923", "3265": "3265",
}

US_NAMES = {
    "NVDA": "NVIDIA", "AMD": "AMD", "INTC": "Intel", "QCOM": "Qualcomm",
    "AVGO": "Broadcom", "MRVL": "Marvell", "TSM": "TSMC", "MU": "Micron",
    "AMZN": "Amazon", "MSFT": "Microsoft", "GOOGL": "Google", "META": "Meta",
    "ANET": "Arista", "VRT": "Vertiv", "DELL": "Dell", "HPE": "HPE",
    "SMCI": "SuperMicro", "AI": "C3.ai", "PATH": "UiPath", "DT": "Dynatrace",
    "CRM": "Salesforce", "NOW": "ServiceNow", "WDAY": "Workday", "TEAM": "Atlassian",
    "DDOG": "Datadog", "SNOW": "Snowflake", "NET": "Cloudflare", "AKAM": "Akamai",
    "FFIV": "F5", "VEEV": "Veeva", "NOK": "Nokia", "ERIC": "Ericsson",
    "SWKS": "Skyworks", "RF": "RF Micro", "VZ": "Verizon", "T": "AT&T",
    "TMUS": "T-Mobile", "PYPL": "PayPal", "SQ": "Block", "AFRM": "Affirm",
    "COIN": "Coinbase", "HOOD": "Robinhood", "DB": "Deutsche Bank",
    "BAC": "Bank of America", "GS": "Goldman", "V": "Visa", "MA": "Mastercard",
    "QQQ": "Nasdaq-100 ETF", "SOXX": "SOX ETF", "SMH": "SMH ETF",
    "XLF": "Financial ETF", "ARKK": "ARK ETF", "FXI": "China ETF",
    "GDX": "Gold ETF", "XLE": "Energy ETF", "IYF": "US Financial ETF",
}

# ── Indicators ────────────────────────────────────────────────────────────────
def calc_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def get_tier(rsi):
    if rsi < 35: return "A"
    if rsi < 50: return "B"
    if rsi < 70: return "C"
    return "D"

def calc_macd(close):
    ema_fast = close.ewm(span=12, adjust=False).mean()
    ema_slow = close.ewm(span=26, adjust=False).mean()
    macd = ema_fast - ema_slow
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    return float(macd.iloc[-1]), float(macd_signal.iloc[-1]), float((macd - macd_signal).iloc[-1])

# ── Fetch Price ────────────────────────────────────────────────────────────────
def fetch_price(code, market='TW'):
    cache_key = f"{market}:{code}"
    now = time.time()
    if cache_key in SESSION_CACHE:
        ts, cached_h = SESSION_CACHE[cache_key]
        if now - ts < CACHE_TTL:
            return cached_h
    try:
        if market == 'TW':
            for suffix in ['.TW', '.TWO']:
                sym = str(code).zfill(4) + suffix
                h = yf.Ticker(sym).history(period='6mo')
                if h is not None and len(h) >= 30:
                    SESSION_CACHE[cache_key] = (now, h)
                    return h
        else:
            h = yf.Ticker(code).history(period='6mo')
            if h is not None and len(h) >= 30:
                SESSION_CACHE[cache_key] = (now, h)
                return h
    except:
        pass
    return None

# ── Analyze ──────────────────────────────────────────────────────────────────
def analyze(code, market='TW'):
    name = (TW_NAMES if market == 'TW' else US_NAMES).get(code, code)
    price_hist = fetch_price(code, market)
    if price_hist is None:
        return None
    try:
        close = price_hist['Close'].astype(float)
        price = float(close.iloc[-1])
        prev = float(close.iloc[-2]) if len(close) >= 2 else price
        chg = (price - prev) / prev * 100
        rsi = float(calc_rsi(close).iloc[-1])
        if np.isnan(rsi): rsi = 50.0
        ma20 = float(close.rolling(20).mean().iloc[-1])
        ma60_val = float(close.rolling(60).mean().iloc[-1])
        ma60 = ma60_val if not np.isnan(ma60_val) else None
        ma_bull = bool(ma60 and ma20 > ma60)
        macd_val, macd_sig, macd_hist = calc_macd(close)
        macd_bull = macd_hist > 0
        low9 = close.rolling(9).min()
        high9 = close.rolling(9).max()
        rsv = (close - low9) / (high9 - low9 + 1e-9) * 100
        k_series = rsv.ewm(alpha=1/3).mean()
        d_series = k_series.ewm(alpha=1/3).mean()
        k_val = float(k_series.iloc[-1])
        d_val = float(d_series.iloc[-1])
        kd_golden = bool(k_val > d_val and k_val < 30)
        bb_ma20 = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        bb_upper = float((bb_ma20 + 2 * bb_std).iloc[-1])
        bb_lower = float((bb_ma20 - 2 * bb_std).iloc[-1])
        bb_pct = (price - bb_lower) / (bb_upper - bb_lower + 1e-9) * 100
        ma5 = close.rolling(5).mean()
        bias5 = float((close.iloc[-1] - ma5.iloc[-1]) / ma5.iloc[-1] * 100)
        vol = price_hist['Volume'] if 'Volume' in price_hist.columns else close * 0
        vol_ma5 = float(vol.rolling(5).mean().iloc[-1])
        vol_ratio = float(vol.iloc[-1] / vol_ma5) if vol_ma5 > 0 else 1.0
        bullish = "✅" if (ma_bull and macd_bull) else ("⚠️" if macd_bull else "❌")
        rsi_score = (100 - rsi) / 100 * 30 if rsi <= 100 else 0
        macd_score = (macd_hist / 5 + 2) * 20 if macd_hist > 0 else max(macd_hist + 2, 0) * 10
        ma_score = 20 if ma_bull else 0
        kd_bonus = 15 if kd_golden else 0
        bb_score = (100 - bb_pct) / 100 * 15 if bb_pct <= 100 else 0
        score = rsi_score + macd_score + ma_score + kd_bonus + bb_score
        return {
            'code': code, 'name': name,
            'price': price, 'chg': chg, 'rsi': rsi,
            'macd': macd_val, 'macd_sig': macd_sig, 'macd_hist': macd_hist,
            'ma20': ma20, 'ma60': ma60, 'ma20_above_ma60': ma_bull,
            'k': k_val, 'd': d_val, 'kd_golden': kd_golden,
            'bb_upper': bb_upper, 'bb_lower': bb_lower, 'bb_pct': bb_pct,
            'bias5': bias5, 'vol_ratio': vol_ratio,
            'bullish': bullish,
            'score': score, 'tier': get_tier(rsi),
        }
    except:
        return None

# ── Streamlit UI ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="Tina Scanner", page_icon="📈", layout="wide")
st.title("📈 Tina Scanner v2.0")

# Init session state
for key in ['tw_results', 'us_results', 'tw_filtered', 'us_filtered', 'tw_last_cat', 'us_last_cat']:
    if key not in st.session_state:
        st.session_state[key] = None

# ── Tab Layout ──────────────────────────────────────────────────────────────
tab_tw, tab_us = st.tabs(["🇹🇼 台股", "🇺🇸 美股"])

# ── TW Tab ───────────────────────────────────────────────────────────────────
with tab_tw:
    st.sidebar.header("🇹🇼 台股篩選")
    tw_cat = st.sidebar.selectbox("分類", list(TW_CATS.keys()), key="tw_cat")
    tw_rsi_max = st.sidebar.slider("RSI 上限", 30, 100, 100, key="tw_rsi")

    target_codes = TW_CATS.get(tw_cat, [])
    st.info(f"📊 **{tw_cat}** | 共 {len(target_codes)} 檔")

    if st.button("🔍 分析台股", type="primary", use_container_width=True, key="tw_analyze"):
        if not target_codes:
            st.error("此分類無股票")
        else:
            progress = st.progress(0)
            status = st.empty()
            results = []
            for i, code in enumerate(target_codes):
                r = analyze(code, 'TW')
                if r:
                    results.append(r)
                progress.progress((i+1) / len(target_codes))
                status.text(f"分析中... {i+1}/{len(target_codes)}")
                time.sleep(0.12)
            progress.empty()
            status.empty()
            filtered = [r for r in results if r['rsi'] <= tw_rsi_max]
            filtered.sort(key=lambda x: x['score'], reverse=True)
            st.session_state.tw_results = results
            st.session_state.tw_filtered = filtered
            st.session_state.tw_last_cat = tw_cat
            a = sum(1 for r in filtered if r['tier'] == 'A')
            b = sum(1 for r in filtered if r['tier'] == 'B')
            c = sum(1 for r in filtered if r['tier'] == 'C')
            d = sum(1 for r in filtered if r['tier'] == 'D')
            bull = sum(1 for r in filtered if r['bullish'] == '✅')
            kd = sum(1 for r in filtered if r['kd_golden'])
            cols = st.columns(6)
            cols[0].metric("🥇 A", a)
            cols[1].metric("🥈 B", b)
            cols[2].metric("🥉 C", c)
            cols[3].metric("❌ D", d)
            cols[4].metric("✅ 多頭", bull)
            cols[5].metric("💎 KD黃金", kd)
            st.success(f"✅ {len(results)} 檔可用 | 篩選後 {len(filtered)} 檔")

    # Display TW results from session_state
    filtered = st.session_state.tw_filtered
    results = st.session_state.tw_results
    cat = st.session_state.tw_last_cat or tw_cat

    if filtered:
        code_options = [(r['code'], f"{r['code']} {r['name'][:8]} ${r['price']:.2f} R={r['rsi']:.0f}") for r in filtered]
        code_labels = [label for _, label in code_options]
        st.markdown("**✅ 選擇股票：**")
        selected_labels = st.multiselect("勾選股票", options=code_labels, default=[], label_visibility="collapsed", key="tw_sel")
        selected_rows = [r for r in filtered if f"{r['code']} {r['name'][:8]} ${r['price']:.2f} R={r['rsi']:.0f}" in selected_labels]
        sel_count = len(selected_rows)
        st.markdown(f"已選擇 **{sel_count}** 檔 | 共 **{len(filtered)}** 檔")
        c1, c2 = st.columns(2)
        with c1:
            if st.button(f"📤 傳送已選擇 ({sel_count})", use_container_width=True, disabled=(sel_count==0), key="tw_send_sel"):
                with st.spinner("傳送中..."):
                    chunks = format_telegram(selected_rows, f"TW-{cat}")
                    ok_all = True
                    err_msg = ""
                    for chunk in chunks:
                        ok, err = push_telegram(chunk)
                        if not ok:
                            ok_all = False
                            err_msg = err
                    if ok_all:
                        st.success(f"✅ 已發送 {sel_count} 檔 ({len(chunks)}則)")
                    else:
                        st.error(f"❌ 失敗：{err_msg}")
        with c2:
            if st.button(f"📤 傳送全部 ({len(filtered)})", use_container_width=True, key="tw_send_all"):
                with st.spinner("傳送中..."):
                    chunks = format_telegram(filtered, f"TW-{cat}")
                    ok_all = True
                    err_msg = ""
                    for chunk in chunks:
                        ok, err = push_telegram(chunk)
                        if not ok:
                            ok_all = False
                            err_msg = err
                    if ok_all:
                        st.success(f"✅ 已發送 {len(filtered)} 檔 ({len(chunks)}則)")
                    else:
                        st.error(f"❌ 失敗：{err_msg}")
        csv = pd.DataFrame(results).to_csv(index=False).encode('utf-8-sig') if results else b""
        st.download_button("📥 CSV", csv, f"tw_{cat}_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", key="tw_csv")

# ── US Tab ───────────────────────────────────────────────────────────────────
with tab_us:
    st.sidebar.header("🇺🇸 美股篩選")
    us_cat = st.sidebar.selectbox("分類", list(US_CATS.keys()), key="us_cat")
    us_rsi_max = st.sidebar.slider("RSI 上限", 30, 100, 100, key="us_rsi")

    target_codes = US_CATS.get(us_cat, [])
    st.info(f"📊 **{us_cat}** | 共 {len(target_codes)} 檔")

    if st.button("🔍 分析美股", type="primary", use_container_width=True, key="us_analyze"):
        if not target_codes:
            st.error("此分類無股票")
        else:
            progress = st.progress(0)
            status = st.empty()
            results = []
            for i, code in enumerate(target_codes):
                r = analyze(code, 'US')
                if r:
                    results.append(r)
                progress.progress((i+1) / len(target_codes))
                status.text(f"Analyzing... {i+1}/{len(target_codes)}")
                time.sleep(0.12)
            progress.empty()
            status.empty()
            filtered = [r for r in results if r['rsi'] <= us_rsi_max]
            filtered.sort(key=lambda x: x['score'], reverse=True)
            st.session_state.us_results = results
            st.session_state.us_filtered = filtered
            st.session_state.us_last_cat = us_cat
            a = sum(1 for r in filtered if r['tier'] == 'A')
            b = sum(1 for r in filtered if r['tier'] == 'B')
            c = sum(1 for r in filtered if r['tier'] == 'C')
            d = sum(1 for r in filtered if r['tier'] == 'D')
            bull = sum(1 for r in filtered if r['bullish'] == '✅')
            kd = sum(1 for r in filtered if r['kd_golden'])
            cols = st.columns(6)
            cols[0].metric("🥇 A", a)
            cols[1].metric("🥈 B", b)
            cols[2].metric("🥉 C", c)
            cols[3].metric("❌ D", d)
            cols[4].metric("✅ 多頭", bull)
            cols[5].metric("💎 KD Golden", kd)
            st.success(f"✅ {len(results)} stocks | Filtered {len(filtered)}")

    filtered = st.session_state.us_filtered
    results = st.session_state.us_results
    cat = st.session_state.us_last_cat or us_cat

    if filtered:
        code_options = [(r['code'], f"{r['code']} {r['name'][:8]} ${r['price']:.2f} R={r['rsi']:.0f}") for r in filtered]
        code_labels = [label for _, label in code_options]
        st.markdown("**✅ Select stocks:**")
        selected_labels = st.multiselect("勾選股票", options=code_labels, default=[], label_visibility="collapsed", key="us_sel")
        selected_rows = [r for r in filtered if f"{r['code']} {r['name'][:8]} ${r['price']:.2f} R={r['rsi']:.0f}" in selected_labels]
        sel_count = len(selected_rows)
        st.markdown(f"Selected **{sel_count}** / **{len(filtered)}** stocks")
        c1, c2 = st.columns(2)
        with c1:
            if st.button(f"📤 Send Selected ({sel_count})", use_container_width=True, disabled=(sel_count==0), key="us_send_sel"):
                with st.spinner("Sending..."):
                    chunks = format_telegram(selected_rows, f"US-{cat}")
                    ok_all = True
                    err_msg = ""
                    for chunk in chunks:
                        ok, err = push_telegram(chunk)
                        if not ok:
                            ok_all = False
                            err_msg = err
                    if ok_all:
                        st.success(f"✅ Sent {sel_count} stocks ({len(chunks)} msgs)")
                    else:
                        st.error(f"❌ Error: {err_msg}")
        with c2:
            if st.button(f"📤 Send All ({len(filtered)})", use_container_width=True, key="us_send_all"):
                with st.spinner("Sending..."):
                    chunks = format_telegram(filtered, f"US-{cat}")
                    ok_all = True
                    err_msg = ""
                    for chunk in chunks:
                        ok, err = push_telegram(chunk)
                        if not ok:
                            ok_all = False
                            err_msg = err
                    if ok_all:
                        st.success(f"✅ Sent {len(filtered)} stocks ({len(chunks)} msgs)")
                    else:
                        st.error(f"❌ Error: {err_msg}")
        csv = pd.DataFrame(results).to_csv(index=False).encode('utf-8-sig') if results else b""
        st.download_button("📥 CSV", csv, f"us_{cat}_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", key="us_csv")

st.divider()
st.caption("📌 Data: yfinance | MACD Bull = MACDHistogram>0 | MA Bull = MA20>MA60 | For reference only | Tina Scanner v2.0")