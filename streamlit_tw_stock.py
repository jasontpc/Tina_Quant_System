# -*- coding: utf-8 -*-
"""
Tina 台股分析工具 - Streamlit 版本
===================================
Based on tw_stock_gui.py v2.5
"""

import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
import sqlite3
import time
import os
import sys
import json
import urllib.request
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_PATH = os.path.join(DATA_DIR, 'tw_stock_registry.db')
ENV_PATH = os.path.join(BASE_DIR, '..', '.env')

# ── FinMind ────────────────────────────────────────────────────────────────────
FINMIND_TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSJ9.oCdQO1qNRUCYxHZSVuRQCqlF7X2DbQ77wury5ARCKzM'
FINMIND_BASE = 'https://api.finmindtrade.com/api/v4/data'

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

INDUSTRY_FILTER = {
    "熱門台股": None,
    "AI 科技": None,
    "半導體": ["半導體業"],
    "光通訊/CPO": None,
    "儲存/記憶體": None,
    "ETF": ["ETF"],
    "金融": None,
    "全部": None,
}

# ── DB Registry ────────────────────────────────────────────────────────────────
def load_registry():
    if not os.path.exists(DB_PATH):
        return []
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT code, name_cn, industry, market FROM stock_registry ORDER BY code")
    rows = [(str(r[0]).zfill(4), r[1], r[2], r[3]) for r in c.fetchall()]
    conn.close()
    return rows

# ── Indicators ────────────────────────────────────────────────────────────────
def calc_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def calc_macd(close, fast=12, slow=26, signal=9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    macd_signal = macd.ewm(span=signal, adjust=False).mean()
    return macd.iloc[-1], macd_signal.iloc[-1]

def get_tier(rsi):
    if rsi < 35: return "A"
    if rsi < 50: return "B"
    if rsi < 70: return "C"
    return "D"

# ── Price Fetch ────────────────────────────────────────────────────────────────
def get_symbol(code):
    return code + '.TW'

def fetch_price_yfinance(code):
    cache_key = str(code).zfill(4)
    now = time.time()
    if cache_key in SESSION_CACHE:
        ts, cached_h = SESSION_CACHE[cache_key]
        if now - ts < CACHE_TTL:
            return cached_h
    for suffix in ['.TW', '.TWO']:
        try:
            h = yf.Ticker(str(code).zfill(4) + suffix).history(period='6mo')
            if h is not None and len(h) >= 30:
                SESSION_CACHE[cache_key] = (now, h)
                return h
        except:
            pass
    return None

def fetch_price_finmind(code, days=120):
    try:
        from FinMind.data import DataLoader
        end = datetime.now().strftime('%Y-%m-%d')
        start = (datetime.now() - timedelta(days=days+10)).strftime('%Y-%m-%d')
        dl = DataLoader()
        dl.token = FINMIND_TOKEN
        df = dl.taiwan_stock_daily(stock_id=str(code).zfill(4), start_date=start, end_date=end)
        if df is None or len(df) < 30:
            return None
        df = df.rename(columns={'date': 'Date', 'open': 'Open', 'max': 'High', 'min': 'Low', 'close': 'Close', 'Trading_Volume': 'Volume'})
        df = df.set_index('Date').sort_index()
        return df
    except:
        return None

def fetch_price_with_fallback(code, mode='auto'):
    if mode == 'yfinance' or (mode == 'auto'):
        h = fetch_price_yfinance(code)
        if h is not None and len(h) >= 30:
            return h, 'yfinance'
    if mode == 'finmind' or (mode == 'auto'):
        h = fetch_price_finmind(code)
        if h is not None and len(h) >= 30:
            return h, 'finmind'
    if mode == 'auto':
        h = fetch_price_yfinance(code)
        if h is not None and len(h) >= 30:
            return h, 'yfinance'
        h = fetch_price_finmind(code)
        if h is not None and len(h) >= 30:
            return h, 'finmind'
    return None, 'none'

# ── Analyze Single Stock ─────────────────────────────────────────────────────
def analyze_stock(code, name, source_mode='auto'):
    price_hist, source = fetch_price_with_fallback(code, source_mode)
    if price_hist is None:
        return None
    try:
        close = price_hist['Close'].astype(float)
        price = float(close.iloc[-1])
        prev = float(close.iloc[-2])
        chg = (price - prev) / prev * 100
        rsi = float(calc_rsi(close).iloc[-1])
        if np.isnan(rsi):
            rsi = 50.0
        macd_val, sig_val = calc_macd(close)
        hist = macd_val - sig_val
        ma20 = float(close.rolling(20).mean().iloc[-1])
        ma60_val = float(close.rolling(60).mean().iloc[-1])
        ma60 = ma60_val if not np.isnan(ma60_val) else None
        high = float(price_hist['High'].max()) if 'High' in price_hist.columns else float(close.max() * 1.05)
        low = float(price_hist['Low'].min()) if 'Low' in price_hist.columns else float(close.min() * 0.95)
        pct = (price - low) / (high - low) * 100 if high > low else 50

        # KD
        low_min = close.rolling(9).min()
        high_max = close.rolling(9).max()
        rsv = (close - low_min) / (high_max - low_min + 1e-9) * 100
        k_series = rsv.ewm(alpha=1/3).mean()
        d_series = k_series.ewm(alpha=1/3).mean()
        k_val = float(k_series.iloc[-1])
        d_val = float(d_series.iloc[-1])

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

        # Score
        rsi_score = (100 - rsi) / 100 * 40 if rsi <= 100 else 0
        macd_score = (hist / 10 + 1) * 15 if hist > 0 else max(hist + 1, 0) * 5
        range_score = (100 - pct) / 100 * 30 if pct <= 100 else 0
        score = rsi_score + macd_score + range_score

        return {
            'code': code, 'name': name,
            'price': price, 'chg': chg, 'rsi': rsi,
            'macd_hist': hist, 'ma20': ma20, 'ma60': ma60,
            'pct': pct, 'high': high, 'low': low,
            'source': source,
            'k': k_val, 'd': d_val,
            'bb_upper': bb_upper, 'bb_lower': bb_lower, 'bb_pct': bb_pct,
            'bias5': bias5, 'vol_ratio': vol_ratio,
            'score': score,
            'tier': get_tier(rsi),
        }
    except:
        return None

# ── Batch Analyze ─────────────────────────────────────────────────────────────
def analyze_batch(codes_names, source_mode='auto', progress_callback=None):
    results = []
    total = len(codes_names)
    for i, (code, name) in enumerate(codes_names):
        r = analyze_stock(code, name, source_mode)
        if r:
            results.append(r)
        if progress_callback and (i % 10 == 0 or i == total - 1):
            progress_callback(i+1, total)
        time.sleep(0.12)  # stagger
    return results

# ── Streamlit UI ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Tina 台股分析",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.title("📈 Tina 台股分析工具 v1.0")

# Sidebar - Category Selection
st.sidebar.header("📊 分類")
cat = st.sidebar.selectbox("選擇分類", list(CATEGORIES.keys()), index=7)  # 全部 default

st.sidebar.header("🎛️ 篩選")
rsi_max = st.sidebar.slider("RSI 上限", 30, 100, 70)
price_min = st.sidebar.number_input("價格下限", value=0.0)
price_max = st.sidebar.number_input("價格上限", value=0.0)
source_mode = st.sidebar.radio("資料來源", ["auto", "yfinance", "finmind"], format_func=lambda x: {"auto": "Auto (YF→FM)", "yfinance": "yfinance", "finmind": "FinMind"}[x])

st.sidebar.header("📤 Telegram")
telegram_enabled = st.sidebar.checkbox("分析完成後發送到 Telegram")
if telegram_enabled:
    st.sidebar.info("Telegram Bot 已啟用")

# Load registry
@st.cache_data(ttl=3600)
def get_registry():
    return load_registry()

registry = get_registry()

# Get target stocks for category
if cat == "全部":
    target_stocks = [(code, name) for code, name, _, _ in registry]
else:
    codes = CATEGORIES.get(cat, [])
    target_stocks = [(code, name) for code, name, _, _ in registry if code in codes]

target_stocks = target_stocks[:500]
st.info(f"📊 分類：**{cat}** | 共 {len(target_stocks)} 檔")

# Analyze button
if st.button("🔍 開始分析", type="primary", use_container_width=True):
    if not target_stocks:
        st.error("此分類無股票")
    else:
        progress_bar = st.progress(0, text="分析中...")
        status_text = st.empty()

        results = []
        def update_progress(done, total):
            progress_bar.progress(done/total)
            status_text.text(f"分析中... {done}/{total} ({done*100//total}%)")

        results = analyze_batch(target_stocks, source_mode, update_progress)
        progress_bar.empty()
        status_text.empty()

        # Apply filters
        filtered = [r for r in results if r['rsi'] <= rsi_max]
        if price_min > 0:
            filtered = [r for r in filtered if r['price'] >= price_min]
        if price_max > 0:
            filtered = [r for r in filtered if r['price'] <= price_max]

        # Sort by score
        filtered.sort(key=lambda x: x['score'], reverse=True)

        st.success(f"✅ 分析完成：{len(results)} 檔 | 篩選後：{len(filtered)} 檔")

        if filtered:
            # Summary stats
            a = sum(1 for r in filtered if r['tier'] == 'A')
            b = sum(1 for r in filtered if r['tier'] == 'B')
            c = sum(1 for r in filtered if r['tier'] == 'C')
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("🥇 A 級", a)
            col2.metric("🥈 B 級", b)
            col3.metric("🥉 C 級", c)
            col4.metric("總計", len(filtered))

            # DataFrame
            df = pd.DataFrame(filtered)

            def make_clickable(code, name):
                return f"{code}"

            display_cols = ['code', 'name', 'price', 'chg', 'rsi', 'k', 'd', 'bb_pct', 'bias5', 'vol_ratio', 'ma20', 'ma60', 'score', 'tier']
            df_disp = df[display_cols].copy()
            df_disp.columns = ['代號', '名稱', '價格', '漲跌%', 'RSI', 'K', 'D', 'BB%', 'BIAS5', 'Vol', 'MA20', 'MA60', '分數', '等級']
            df_disp['價格'] = df_disp['價格'].apply(lambda x: f"${x:.0f}")
            df_disp['漲跌%'] = df_disp['漲跌%'].apply(lambda x: f"{x:+.2f}%")
            df_disp['RSI'] = df_disp['RSI'].apply(lambda x: f"{x:.0f}")
            df_disp['K'] = df_disp['K'].apply(lambda x: f"{x:.0f}")
            df_disp['D'] = df_disp['D'].apply(lambda x: f"{x:.0f}")
            df_disp['BB%'] = df_disp['BB%'].apply(lambda x: f"{x:.0f}%")
            df_disp['BIAS5'] = df_disp['BIAS5'].apply(lambda x: f"{x:+.2f}%")
            df_disp['Vol'] = df_disp['Vol'].apply(lambda x: f"{x:.2f}x")
            df_disp['MA20'] = df_disp['MA20'].apply(lambda x: f"${x:.0f}")
            df_disp['MA60'] = df_disp['MA60'].apply(lambda x: f"${x:.0f}" if x else "N/A")
            df_disp['分數'] = df_disp['分數'].apply(lambda x: f"{x:.0f}")

            st.dataframe(
                df_disp,
                use_container_width=True,
                height=400,
                hide_index=True,
            )

            # Download CSV
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下載 CSV", csv, f"tina_tw_{cat}_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")
        else:
            st.warning("無符合條件的股票，試試放寬篩選")

# Footer
st.divider()
st.caption("📌 資料來源：yfinance + FinMind | 分析僅供參考，不構成投資建議 | Tina v1.0 Streamlit Edition")