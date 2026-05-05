# -*- coding: utf-8 -*-
"""
Tina Scanner v2.2 - TW+US Stock Analysis with Institutional Data + Telegram
"""
import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
import time
import urllib.request
import json
from datetime import datetime

TELEGRAM_BOT_TOKEN = '8614615741:AAHEMV6daIzF6J_MFUAm8KkhJYtOGVOM14Q'
TELEGRAM_CHAT_ID = '1616824689'
FINMIND_TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSJ9.oCdQO1qNRUCYxHZSVuRQCqlF7X2DbQ77wury5ARCKzM'

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
        f"*{title}* | {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "=" * 40
    ]
    for r in results:
        tier_icon = {"A": "A", "B": "B", "C": "C", "D": "X"}.get(r.get('tier','?'), '?')
        ma_icon = "Y" if r.get('ma20_above_ma60') else "N"
        macd_icon = "+" if r.get('macd_hist', 0) > 0 else "-"
        bull = r.get('bullish', 'N')
        kd = "K+D+" if r.get('kd_golden') else ""
        inst = r.get('inst') or {}
        f_val = inst.get('foreign', 0)
        t_val = inst.get('trust', 0)
        d_val = inst.get('dealer', 0)
        inst_str = f" F:{f_val:+,} T:{t_val:+,} D:{d_val:,}" if inst else ""
        all_lines.append(
            f"[{tier_icon}] {r['code']} {r['name'][:8]}"
            f" ${r['price']:.2f} ({r['chg']:+.2f}%)"
            f" R={r['rsi']:.0f} K={r['k']:.0f} D={r['d']:.0f}"
            f" BB%={r['bb_pct']:.0f} BIAS={r['bias5']:+.1f}% Vol={r['vol_ratio']:.1f}x"
            f" M={macd_icon} MA={ma_icon} {bull} {kd}{inst_str}"
        )
    a = sum(1 for r in results if r.get('tier') == 'A')
    b = sum(1 for r in results if r.get('tier') == 'B')
    c = sum(1 for r in results if r.get('tier') == 'C')
    all_lines.append("=" * 40)
    all_lines.append(f"Grade: A={a} B={b} C={c} | Total={len(results)}")
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

SESSION_CACHE = {}
CACHE_TTL = 3600

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
US_CATS = {
    "XPU & Design": ["NVDA","AVGO","AMD","MRVL","ARM"],
    "光通訊/CPO": ["ANET","CSCO","COHR","LITE","GLW"],
    "記憶體/儲存": ["MU","WDC","STX"],
    "半導體設備": ["ASML","AMAT","LRCX","KLAC","CAMT"],
    "電力/散熱": ["VRT","ETN","AMSC","SBGSY","NVT"],
    "先進封裝/雲端": ["AMKR","EQIX","DLR","ORCL"],
    "AI 雲端": ["NVDA","AMD","AVGO","MRVL","AMZN","MSFT","GOOGL","META","ANET","VRT","DELL"],
    "5G": ["QCOM","NOK","ERIC","AMAT","LRCX","MU","SWKS","RF","VZ","T","TMUS"],
    "半導體": ["NVDA","AMD","INTC","QCOM","AVGO","MRVL","TSM","MU","AMAT","LRCX","KLAC","SNPS","CDNS","NXPI","ASML"],
    "FinTech": ["PYPL","SQ","AFRM","COIN","HOOD","DB","BAC","GS","V","MA"],
    "ETF": ["QQQ","SOXX","SMH","XLF","ARKK","FXI","GDX","XLE"],
    "全部": [],
}

all_tw = []
seen = set()
for v in TW_CATS.values():
    for c in v:
        if c not in seen:
            seen.add(c)
            all_tw.append(c)
TW_CATS["全部"] = sorted(all_tw, key=lambda x: (0, int(x)) if x.isdigit() else (1, x))[:500]

all_us = []
seen = set()
for v in US_CATS.values():
    for c in v:
        if c not in seen:
            seen.add(c)
            all_us.append(c)
US_CATS["全部"] = sorted(all_us, key=lambda x: x)[:500]

TW_NAMES = {
    "2330": "台積電", "2454": "聯發科", "2317": "鴻海", "2382": "廣達",
    "3034": "緯穎", "3665": "穎崴", "2881": "富邦金", "2603": "長榮",
    "2303": "聯電", "1216": "統一", "0050": "元大台灣50", "0056": "元大高股息",
    "00646": "富邦S&P500", "00662": "富邦NASDAQ", "00713": "元大高息低波",
    "00757": "統一大FANG+", "00927": "統一手創未來", "00878": "國泰永續高股息",
    "00900": "富邦ESG", "00902": "兆豐藍籌", "00906": "凱基優選高股息",
    "3217": "3217", "2401": "2401", "3527": "3527", "4749": "美時",
    "6819": "6819", "6229": "6229", "6786": "6786", "6563": "6563",
    "5351": "5351", "4923": "4923", "3265": "3265",
}
US_NAMES = {
    # AI 算力 / XPU & Design
    "NVDA": "NVIDIA", "AVGO": "Broadcom", "AMD": "AMD", "MRVL": "Marvell", "ARM": "ARM",
    # 光通訊 / CPO
    "ANET": "Arista", "CSCO": "Cisco", "COHR": "Coherent", "LITE": "Lumentum", "GLW": "Corning",
    # 記憶體 / 儲存
    "MU": "Micron", "WDC": "Western Digital", "STX": "Seagate",
    # 半導體設備
    "ASML": "ASML", "AMAT": "Applied Mat", "LRCX": "Lam Research", "KLAC": "KLA", "CAMT": "Camtek",
    # 電力 / 散熱
    "VRT": "Vertiv", "ETN": "Eaton", "AMSC": "AMSC", "SBGSY": "Schneider", "NVT": "nVent",
    # 先進封裝 / 雲端
    "AMKR": "Amkor", "EQIX": "Equinix", "DLR": "Digital Realty", "ORCL": "Oracle",
    # AI 雲端
    "AMZN": "Amazon", "MSFT": "Microsoft", "GOOGL": "Google", "META": "Meta", "DELL": "Dell",
    # 5G
    "QCOM": "Qualcomm", "NOK": "Nokia", "ERIC": "Ericsson", "SWKS": "Skyworks", "RF": "RF Micro",
    "VZ": "Verizon", "T": "AT&T", "TMUS": "T-Mobile",
    # 半導體
    "INTC": "Intel", "TSM": "TSM", "SNPS": "Synopsys", "CDNS": "Cadence", "NXPI": "NXP",
    # FinTech
    "PYPL": "PayPal", "SQ": "Block", "AFRM": "Affirm", "COIN": "Coinbase", "HOOD": "Robinhood",
    "DB": "Deutsche Bank", "BAC": "Bank of America", "GS": "Goldman", "V": "Visa", "MA": "Mastercard",
    # ETF
    "QQQ": "QQQ ETF", "SOXX": "SOX ETF", "SMH": "SMH ETF",
    "XLF": "Financial ETF", "ARKK": "ARK ETF", "FXI": "China ETF",
    "GDX": "Gold ETF", "XLE": "Energy ETF",
}

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

# ── Data Fetch ──────────────────────────────────────────────────────────────

def fetch_institutional(code):
    """Fetch F/T/D from FinMind TaiwanStockInstitutionalInvestorsBuySell (real-time)"""
    try:
        import urllib.request
        params = {
            'dataset': 'TaiwanStockInstitutionalInvestorsBuySell',
            'data_id': str(code).zfill(4),
            'start_date': '2026-05-04',
            'end_date': '2026-05-05',
            'token': FINMIND_TOKEN
        }
        url = 'https://api.finmindtrade.com/api/v4/data?' + '&'.join(f'{k}={v}' for k, v in params.items())
        with urllib.request.urlopen(url, timeout=8) as resp:
            data = json.loads(resp.read())
            rows = data.get('data', [])
            if not rows:
                return None
            latest_date = max(r['date'] for r in rows)
            day_rows = [r for r in rows if r['date'] == latest_date]
            result = {'foreign': 0, 'trust': 0, 'dealer': 0}
            for r in day_rows:
                name = r.get('name', '')
                net = r.get('buy', 0) - r.get('sell', 0)
                if name == 'Foreign_Investor':
                    result['foreign'] = net
                elif name == 'Investment_Trust':
                    result['trust'] = net
                elif 'Dealer' in name:
                    result['dealer'] += net
            return result if (result['foreign'] or result['trust'] or result['dealer']) else None
    except:
        return None

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

def analyze(code, market='TW'):
    name = (TW_NAMES if market == 'TW' else US_NAMES).get(code, code)
    price_hist = fetch_price(code, market)
    if price_hist is None:
        return None
    inst = fetch_institutional(code) if market == 'TW' else None
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
        bullish = "Y" if (ma_bull and macd_bull) else ("W" if macd_bull else "N")
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
            'inst': inst,
            'score': score, 'tier': get_tier(rsi),
        }
    except:
        return None

# ── Page Setup ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="Tina Scanner", page_icon="📈", layout="wide")
st.title("📈 Tina Scanner v2.2")

tw_tab, us_tab = st.tabs(["Taiwan", "US"])

# ═══════════════════════════ TW TAB ═══════════════════════════
with tw_tab:
    col_side, col_main = st.columns([1, 4], vertical_alignment="top")
    with col_side:
        st.header("Filters")
        tw_cat = st.selectbox("Category", list(TW_CATS.keys()), key="tw_cat")
        tw_rsi_max = st.slider("RSI Max", 30, 100, 100, key="tw_rsi")
        codes = TW_CATS.get(tw_cat, [])
        st.info(f"{len(codes)} stocks")
        analyze_tw = st.button("Analyze", type="primary", use_container_width=True, key="btn_tw_analyze")

    if 'tw_results' not in st.session_state:
        st.session_state.tw_results = None
        st.session_state.tw_filtered = None
        st.session_state.tw_cat_saved = None

    if analyze_tw:
        with st.spinner("Analyzing + Fetching Institutional..."):
            results = []
            bar = st.progress(0)
            for i, code in enumerate(codes):
                r = analyze(code, 'TW')
                if r:
                    results.append(r)
                bar.progress((i+1) / len(codes))
                time.sleep(0.12)
            bar.empty()
            filtered = [r for r in results if r['rsi'] <= tw_rsi_max]
            filtered.sort(key=lambda x: x['score'], reverse=True)
            st.session_state.tw_results = results
            st.session_state.tw_filtered = filtered
            st.session_state.tw_cat_saved = tw_cat

    results = st.session_state.tw_results
    filtered = st.session_state.tw_filtered
    cat_saved = st.session_state.tw_cat_saved

    if results:
        a = sum(1 for r in filtered if r['tier'] == 'A')
        b = sum(1 for r in filtered if r['tier'] == 'B')
        c = sum(1 for r in filtered if r['tier'] == 'C')
        d = sum(1 for r in filtered if r['tier'] == 'D')
        bull = sum(1 for r in filtered if r['bullish'] == 'Y')
        kd = sum(1 for r in filtered if r['kd_golden'])
        m = st.columns(6)
        m[0].metric("A", a)
        m[1].metric("B", b)
        m[2].metric("C", c)
        m[3].metric("D", d)
        m[4].metric("BULL", bull)
        m[5].metric("KD+", kd)
        st.success(f"{len(results)} stocks | {len(filtered)} after filter")

    if filtered:
        rows = []
        for r in filtered:
            inst = r.get('inst') or {}
            f_val = inst.get('foreign', 0)
            t_val = inst.get('trust', 0)
            d_val = inst.get('dealer', 0)
            rows.append({
                "Code": r['code'],
                "Name": r['name'],
                "Price": f"${r['price']:.2f}",
                "Chg%": f"{r['chg']:+.2f}%",
                "RSI": f"{r['rsi']:.0f}",
                "K": f"{r['k']:.0f}",
                "D": f"{r['d']:.0f}",
                "BB%": f"{r['bb_pct']:.0f}%",
                "BIAS5": f"{r['bias5']:+.1f}%",
                "Vol": f"{r['vol_ratio']:.1f}x",
                "MA20": f"${r['ma20']:.0f}",
                "MA60": f"${r['ma60']:.0f}" if r['ma60'] else "N/A",
                "MACD": f"{r['macd_hist']:+.2f}",
                "MA": "Y" if r['ma20_above_ma60'] else "N",
                "F": f"{f_val:+,}" if f_val != 0 else "-",
                "T": f"{t_val:+,}" if t_val != 0 else "-",
                "D": f"{d_val:+,}" if d_val != 0 else "-",
                "Tier": r['tier'],
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, height=400, hide_index=True)

        with st.expander("Send to Telegram"):
            sel = st.multiselect("Select", [f"{r['code']} {r['name'][:6]} ${r['price']:.0f} R={r['rsi']:.0f}" for r in filtered], key="tw_sel")
            sel_rows = [r for r in filtered if f"{r['code']} {r['name'][:6]} ${r['price']:.0f} R={r['rsi']:.0f}" in sel]
            sc = len(sel_rows)
            r1, r2 = st.columns(2)
            if r1.button(f"Send ({sc})", disabled=(sc==0), use_container_width=True):
                with st.spinner("Sending..."):
                    chunks = format_telegram(sel_rows, f"TW-{cat_saved}")
                    ok_all = True
                    for chunk in chunks:
                        ok, err = push_telegram(chunk)
                        if not ok:
                            ok_all = False
                            st.error(f"Error: {err}")
                            break
                    if ok_all:
                        st.success(f"Sent {sc} stocks ({len(chunks)} msgs)")
            if r2.button(f"Send All ({len(filtered)})", use_container_width=True):
                with st.spinner("Sending..."):
                    chunks = format_telegram(filtered, f"TW-{cat_saved}")
                    ok_all = True
                    for chunk in chunks:
                        ok, err = push_telegram(chunk)
                        if not ok:
                            ok_all = False
                            st.error(f"Error: {err}")
                            break
                    if ok_all:
                        st.success(f"Sent {len(filtered)} stocks ({len(chunks)} msgs)")

        if results:
            csv = pd.DataFrame(results).to_csv(index=False).encode('utf-8-sig')
            st.download_button("CSV", csv, f"tw_{cat_saved}_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", key="tw_csv")

# ═══════════════════════════ US TAB ═══════════════════════════
with us_tab:
    col_side, col_main = st.columns([1, 4], vertical_alignment="top")
    with col_side:
        st.header("Filters")
        us_cat = st.selectbox("Category", list(US_CATS.keys()), key="us_cat")
        us_rsi_max = st.slider("RSI Max", 30, 100, 100, key="us_rsi")
        codes = US_CATS.get(us_cat, [])
        st.info(f"{len(codes)} stocks")
        analyze_us = st.button("Analyze", type="primary", use_container_width=True, key="btn_us_analyze")

    if 'us_results' not in st.session_state:
        st.session_state.us_results = None
        st.session_state.us_filtered = None
        st.session_state.us_cat_saved = None

    if analyze_us:
        with st.spinner("Analyzing..."):
            results = []
            bar = st.progress(0)
            for i, code in enumerate(codes):
                r = analyze(code, 'US')
                if r:
                    results.append(r)
                bar.progress((i+1) / len(codes))
                time.sleep(0.12)
            bar.empty()
            filtered = [r for r in results if r['rsi'] <= us_rsi_max]
            filtered.sort(key=lambda x: x['score'], reverse=True)
            st.session_state.us_results = results
            st.session_state.us_filtered = filtered
            st.session_state.us_cat_saved = us_cat

    results = st.session_state.us_results
    filtered = st.session_state.us_filtered
    cat_saved = st.session_state.us_cat_saved

    if results:
        a = sum(1 for r in filtered if r['tier'] == 'A')
        b = sum(1 for r in filtered if r['tier'] == 'B')
        c = sum(1 for r in filtered if r['tier'] == 'C')
        d = sum(1 for r in filtered if r['tier'] == 'D')
        bull = sum(1 for r in filtered if r['bullish'] == 'Y')
        kd = sum(1 for r in filtered if r['kd_golden'])
        m = st.columns(6)
        m[0].metric("A", a)
        m[1].metric("B", b)
        m[2].metric("C", c)
        m[3].metric("D", d)
        m[4].metric("BULL", bull)
        m[5].metric("KD+", kd)
        st.success(f"{len(results)} stocks | {len(filtered)} after filter")

    if filtered:
        rows = []
        for r in filtered:
            rows.append({
                "Code": r['code'],
                "Name": r['name'],
                "Price": f"${r['price']:.2f}",
                "Chg%": f"{r['chg']:+.2f}%",
                "RSI": f"{r['rsi']:.0f}",
                "K": f"{r['k']:.0f}",
                "D": f"{r['d']:.0f}",
                "BB%": f"{r['bb_pct']:.0f}%",
                "BIAS5": f"{r['bias5']:+.1f}%",
                "Vol": f"{r['vol_ratio']:.1f}x",
                "MA20": f"${r['ma20']:.0f}",
                "MA60": f"${r['ma60']:.0f}" if r['ma60'] else "N/A",
                "MACD": f"{r['macd_hist']:+.2f}",
                "MA": "Y" if r['ma20_above_ma60'] else "N",
                "Tier": r['tier'],
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, height=400, hide_index=True)

        with st.expander("Send to Telegram"):
            sel = st.multiselect("Select", [f"{r['code']} {r['name'][:6]} ${r['price']:.0f} R={r['rsi']:.0f}" for r in filtered], key="us_sel")
            sel_rows = [r for r in filtered if f"{r['code']} {r['name'][:6]} ${r['price']:.0f} R={r['rsi']:.0f}" in sel]
            sc = len(sel_rows)
            r1, r2 = st.columns(2)
            if r1.button(f"Send ({sc})", disabled=(sc==0), use_container_width=True):
                with st.spinner("Sending..."):
                    chunks = format_telegram(sel_rows, f"US-{cat_saved}")
                    ok_all = True
                    for chunk in chunks:
                        ok, err = push_telegram(chunk)
                        if not ok:
                            ok_all = False
                            st.error(f"Error: {err}")
                            break
                    if ok_all:
                        st.success(f"Sent {sc} stocks ({len(chunks)} msgs)")
            if r2.button(f"Send All ({len(filtered)})", use_container_width=True):
                with st.spinner("Sending..."):
                    chunks = format_telegram(filtered, f"US-{cat_saved}")
                    ok_all = True
                    for chunk in chunks:
                        ok, err = push_telegram(chunk)
                        if not ok:
                            ok_all = False
                            st.error(f"Error: {err}")
                            break
                    if ok_all:
                        st.success(f"Sent {len(filtered)} stocks ({len(chunks)} msgs)")

        if results:
            csv = pd.DataFrame(results).to_csv(index=False).encode('utf-8-sig')
            st.download_button("CSV", csv, f"us_{cat_saved}_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", key="us_csv")

st.divider()
st.caption("Data: yfinance + FinMind Institutional | For reference only | Tina Scanner v2.2")