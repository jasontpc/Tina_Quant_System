# -*- coding: utf-8 -*-
"""
Tina 台股分析工具 - Streamlit 版本 v1.2
移除價格篩選 | 新增 MACD 多頭指標
"""

import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
import time
from datetime import datetime

# ── Session Cache ──────────────────────────────────────────────────────────────
SESSION_CACHE = {}
CACHE_TTL = 3600

# ── CATEGORIES ─────────────────────────────────────────────────────────────────
CATEGORIES = {
    "熱門台股": ["2330","2454","2317","2382","3034","3665","2881","2603","2303","1216"],
    "AI 科技": ["2317","2324","2330","2345","2353","2381","2382","2454","3034","3095","3163","3211","3231","3306","3323","3325","3349","3432","3479","3483","3491","3534","3653","3665","3702","5515"],
    "半導體": ["2303","2311","2325","2363","2379","2473","3035","3041","3063","3105","3122","3141","3169","3178","3227","3228","3257","3259","3260","3264","3265","3268","3317","3372","3374","3438","3443","3467","3474","3519","3527","3529","3534","3536","3555","3556","3567","3579","3581","3598","3675","3680","3686","3707","4749","4923","4925","4945","4951","4966","4971","4973","4991","5236","5246","5262","5272","5274","5280","5297","5299","5302","5305","5344","5347","5351","5425","5443","5468","5483","5487","6103","6104","6129","6138","6147","6182","6187","6208","6223","6229","6233","6237","6239","6261","6271","6287","6291","6411","6415","6423","6435","6451","6457","6462","6485","6488","6494","6510","6515","6525","6526","6531","6532","6548","6552","6563","6568","6594","6640","6643","6651","6679","6683","6684","6693","6695","6699","6708","6716","6719","6720","6732","6756","6770","6786","6788","6819","6823","6829","6842","6895","6907","6920","6927","6953","6996","7530","7556","7669","7704","7707","7712","7734","7751","7768","7769","7770","7772","7796","7810","7815","7828","7843","7853","7856","7866","7872","7880","7886","7887","7899","7909","8024","8040","8054","8081","8086","8088","8091","8098","8102","8131","8150","8227","8261","8271","8277","8299","8383"],
    "光通訊/CPO": ["2345","3053","3432","3491","3534","3599","3627","4944","5233","5281","6255","6409","2444","3047","3053","3432","3491","3534","3558","3564","4903","4905","4906","4908","4909","5233","5353","6109","6409","3081","2455","3363","3163","6442","6715","4979","6451","4977","4908","3450","2489","3711","3265","6830","6223","6515","2360","2499","6706","2345","3665","3533","2455","3105","6488","2303","2330","3711"],
    "儲存/記憶體": ["2330","2382","2401","2454","3034","3044","3217","3356","3592","4924","4939","6208","6488","3711"],
    "ETF": ["0050","0056","00646","00662","00713","00757","00927","00878","00900","00902","00906"],
    "金融": ["2801","2807","2809","2812","2816","2820","2823","2827","2831","2832","2833","2833A","2834","2836","2836A","2837","2838","2838A","2845","2847","2849","2850","2851","2852","2854","2855","2856","2867","2880","2881","2881A","2881B","2881C","2882","2882A","2882B","2883","2883A","2883B","2884","2885","2886","2887","2887C","2887E","2887F","2887G","2887H","2887I","2887Z1","2888","2888A","2888B","2889","2890","2891","2891A","2891B","2891C","2892","2897","2897A","2897B","5820","5854","5859","5863","5864","5876","5878","5880","6004","6005","6012","6015","6016","6020","6021","6023","6024","6026","6027","6028","6035","6878"],
    "全部": [],
}

# 全部 = 合併所有分類（去重）
ALL_CODES = []
seen = set()
for cat_codes in CATEGORIES.values():
    for c in cat_codes:
        if c not in seen:
            seen.add(c)
            ALL_CODES.append(c)
CATEGORIES["全部"] = sorted(ALL_CODES, key=lambda x: int(x))[:500]

STOCK_NAMES = {
    "2330": "台積電", "2454": "聯發科", "2317": "鴻海", "2382": "廣達",
    "3034": "緯穎", "3665": "穎崴", "2881": "富邦金", "2603": "長榮",
    "2303": "聯電", "1216": "統一", "0050": "元大台灣50", "0056": "元大高股息",
    "00646": "富邦S&P500", "00662": "富邦NASDAQ", "00713": "元大高息低波",
    "00757": "統一大FANG+", "00927": "統一手創未來", "00878": "國泰永續高股息",
    "00900": "富邦ESG", "00902": "兆豐藍籌", "00906": "凱基優選高股息",
}

def get_name(code):
    return STOCK_NAMES.get(code, code)

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
    macd_hist = macd - macd_signal
    return float(macd.iloc[-1]), float(macd_signal.iloc[-1]), float(macd_hist.iloc[-1])

# ── Price Fetch ────────────────────────────────────────────────────────────────
def fetch_price_yfinance(code):
    cache_key = str(code).zfill(4)
    now = time.time()
    if cache_key in SESSION_CACHE:
        ts, cached_h = SESSION_CACHE[cache_key]
        if now - ts < CACHE_TTL:
            return cached_h
    for suffix in ['.TW', '.TWO']:
        try:
            sym = str(code).zfill(4) + suffix
            h = yf.Ticker(sym).history(period='6mo')
            if h is not None and len(h) >= 30:
                SESSION_CACHE[cache_key] = (now, h)
                return h
        except:
            pass
    return None

# ── Analyze Single Stock ─────────────────────────────────────────────────────
def analyze_stock(code):
    name = get_name(code)
    price_hist = fetch_price_yfinance(code)
    if price_hist is None:
        return None
    try:
        close = price_hist['Close'].astype(float)
        price = float(close.iloc[-1])
        prev = float(close.iloc[-2]) if len(close) >= 2 else price
        chg = (price - prev) / prev * 100

        rsi = float(calc_rsi(close).iloc[-1])
        if np.isnan(rsi):
            rsi = 50.0

        # MA
        ma20 = float(close.rolling(20).mean().iloc[-1])
        ma60_val = float(close.rolling(60).mean().iloc[-1])
        ma60 = ma60_val if not np.isnan(ma60_val) else None
        ma20_above_ma60 = bool(ma60 and ma20 > ma60)

        # MACD
        macd_val, macd_sig, macd_hist = calc_macd(close)
        macd_bull = macd_hist > 0  # MACD histogram > 0 = 多頭

        # KD
        low_min = close.rolling(9).min()
        high_max = close.rolling(9).max()
        rsv = (close - low_min) / (high_max - low_min + 1e-9) * 100
        k_series = rsv.ewm(alpha=1/3).mean()
        d_series = k_series.ewm(alpha=1/3).mean()
        k_val = float(k_series.iloc[-1])
        d_val = float(d_series.iloc[-1])
        kd_golden = bool(k_val > d_val and k_val < 30)  # 低檔黃金交叉

        # Bollinger
        bb_ma20 = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        bb_upper = float((bb_ma20 + 2 * bb_std).iloc[-1])
        bb_lower = float((bb_ma20 - 2 * bb_std).iloc[-1])
        bb_pct = (price - bb_lower) / (bb_upper - bb_lower + 1e-9) * 100

        # BIAS5
        ma5 = close.rolling(5).mean()
        bias5 = float((close.iloc[-1] - ma5.iloc[-1]) / ma5.iloc[-1] * 100)

        # Vol ratio
        vol = price_hist['Volume'] if 'Volume' in price_hist.columns else close * 0
        vol_ma5 = float(vol.rolling(5).mean().iloc[-1])
        vol_ratio = float(vol.iloc[-1] / vol_ma5) if vol_ma5 > 0 else 1.0

        # 多頭信號
        bullish = "✅" if (ma20_above_ma60 and macd_bull) else ("⚠️" if macd_bull else "❌")

        # Score（加分：MA多頭、MACD多頭、KD低檔黃金交叉）
        rsi_score = (100 - rsi) / 100 * 30 if rsi <= 100 else 0
        macd_score = (macd_hist / 5 + 2) * 20 if macd_hist > 0 else max(macd_hist + 2, 0) * 10
        ma_score = 20 if ma20_above_ma60 else 0
        kd_bonus = 15 if kd_golden else 0
        bb_score = (100 - bb_pct) / 100 * 15 if bb_pct <= 100 else 0
        score = rsi_score + macd_score + ma_score + kd_bonus + bb_score

        return {
            'code': code, 'name': name,
            'price': price, 'chg': chg, 'rsi': rsi,
            'macd': macd_val, 'macd_sig': macd_sig, 'macd_hist': macd_hist,
            'ma20': ma20, 'ma60': ma60, 'ma20_above_ma60': ma20_above_ma60,
            'k': k_val, 'd': d_val, 'kd_golden': kd_golden,
            'bb_upper': bb_upper, 'bb_lower': bb_lower, 'bb_pct': bb_pct,
            'bias5': bias5, 'vol_ratio': vol_ratio,
            'bullish': bullish,
            'score': score, 'tier': get_tier(rsi),
        }
    except:
        return None

# ── Streamlit UI ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="Tina 台股分析", page_icon="📈", layout="wide")

st.title("📈 Tina 台股分析工具 v1.2")

# Sidebar
st.sidebar.header("📊 分類")
cat = st.sidebar.selectbox("選擇分類", list(CATEGORIES.keys()))

st.sidebar.header("🎛️ RSI 篩選")
rsi_max = st.sidebar.slider("RSI 上限", 30, 100, 100)

st.sidebar.markdown("---")
st.sidebar.caption("📌 篩選：MA多頭 + MACD多頭已內建")

# Get target stocks
target_codes = CATEGORIES.get(cat, [])
st.info(f"📊 **{cat}** | 共 {len(target_codes)} 檔")

if st.button("🔍 開始分析", type="primary", use_container_width=True):
    if not target_codes:
        st.error("此分類無股票")
    else:
        progress = st.progress(0)
        status = st.empty()
        results = []

        for i, code in enumerate(target_codes):
            r = analyze_stock(code)
            if r:
                results.append(r)
            progress.progress((i+1) / len(target_codes))
            status.text(f"分析中... {i+1}/{len(target_codes)}")
            time.sleep(0.12)

        progress.empty()
        status.empty()

        # Filter by RSI
        filtered = [r for r in results if r['rsi'] <= rsi_max]
        filtered.sort(key=lambda x: x['score'], reverse=True)

        # Stats
        a = sum(1 for r in filtered if r['tier'] == 'A')
        b = sum(1 for r in filtered if r['tier'] == 'B')
        c = sum(1 for r in filtered if r['tier'] == 'C')
        d = sum(1 for r in filtered if r['tier'] == 'D')
        bull_count = sum(1 for r in filtered if r['bullish'] == '✅')
        kd_gold_count = sum(1 for r in filtered if r['kd_golden'])

        col1, col2, col3, col4, col5, col6 = st.columns(6)
        col1.metric("🥇 A", a)
        col2.metric("🥈 B", b)
        col3.metric("🥉 C", c)
        col4.metric("❌ D", d)
        col5.metric("✅ 多頭", bull_count)
        col6.metric("💎 KD黃金", kd_gold_count)

        st.success(f"✅ 分析完成：{len(results)} 檔可用 | 篩選後：{len(filtered)} 檔")

        if filtered:
            rows = []
            for r in filtered:
                rows.append({
                    "代號": r['code'],
                    "名稱": r['name'],
                    "價格": f"${r['price']:.0f}",
                    "漲跌%": f"{r['chg']:+.2f}%",
                    "RSI": f"{r['rsi']:.0f}",
                    "MACD": f"{r['macd_hist']:+.2f}",
                    "K": f"{r['k']:.0f}",
                    "D": f"{r['d']:.0f}",
                    "BB%": f"{r['bb_pct']:.0f}%",
                    "BIAS5": f"{r['bias5']:+.1f}%",
                    "Vol": f"{r['vol_ratio']:.2f}x",
                    "MA20>60": "✅" if r['ma20_above_ma60'] else "❌",
                    "MACD多": "✅" if r['macd_hist'] > 0 else "❌",
                    "多頭": r['bullish'],
                    "分數": f"{r['score']:.0f}",
                    "等級": r['tier'],
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, height=500, hide_index=True)

            csv = pd.DataFrame(results).to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下載 CSV", csv, f"tina_tw_{cat}_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")
        else:
            st.warning("無符合條件的股票，試試放寬 RSI 篩選")

st.divider()
st.caption("📌 資料來源：yfinance | MACD多頭=MACDHistogram>0 | MA多頭=MA20>MA60 | 分析僅供參考，不構成投資建議 | Tina v1.2")