# -*- coding: utf-8 -*-
"""
Tina 台股分析工具 v2.3 - GUI 完整版
"""
import yfinance as yf
import numpy as np
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime, timedelta
import sqlite3
import os
import sys
import threading
import concurrent.futures
import json

import time
import tempfile
import os

# === Session Cache for yfinance data ===
SESSION_CACHE = {}  # code -> (timestamp, price_hist)
CACHE_TTL = 3600   # 1 hour TTL

def get_cache_path():
    tmpdir = tempfile.gettempdir()
    return os.path.join(tmpdir, 'tw_gui_session_cache.db')

def save_session_cache():
    """Save session cache to temp file"""
    if not SESSION_CACHE:
        return
    import pickle
    cache_path = get_cache_path()
    try:
        with open(cache_path, 'wb') as f:
            pickle.dump(SESSION_CACHE, f)
    except:
        pass

def load_session_cache():
    """Load session cache from temp file"""
    import pickle
    cache_path = get_cache_path()
    try:
        if os.path.exists(cache_path):
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
    except:
        pass
    return {}

# Load cache at startup
SESSION_CACHE = load_session_cache()

import urllib.request
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "data", "tw_stock_registry.db")
ENV_PATH = os.path.join(BASE_DIR, "..", ".env")
FINMIND_BASE = "https://api.finmindtrade.com/api/v4/data"
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjF9.ivums9mfJUrM2MYazJiOEg49RiYLOJMZtejqX79YWS8"

def calc_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def calc_macd(close, fast=12, slow=26, signal=9):
    ema12 = close.ewm(span=fast, adjust=False).mean()
    ema26 = close.ewm(span=slow, adjust=False).mean()
    macd = ema12 - ema26
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd.values[-1], signal_line.values[-1]

def load_registry():
    if not os.path.exists(DB_PATH):
        return []
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT code, name_cn, industry, market FROM stock_registry ORDER BY market, code")
    rows = cur.fetchall()
    conn.close()
    return rows

def get_symbol(code):
    return str(code).zfill(4) + ".TW"

def fetch_price_yfinance(code):
    """Try .TW first, then .TWO for TPEx stocks"""
    # Check session cache first
    import time as time_module
    now = time_module.time()
    cache_key = code.zfill(4)
    if cache_key in SESSION_CACHE:
        ts, cached_h = SESSION_CACHE[cache_key]
        if now - ts < CACHE_TTL:
            return cached_h

    for suffix in [".TW", ".TWO"]:
        try:
            h = yf.Ticker(str(code).zfill(4) + suffix).history(period="6mo")
            if h is not None and len(h) >= 30:
                SESSION_CACHE[cache_key] = (now, h)
                return h
        except:
            pass
    return None

def fetch_price_finmind(code, days=120):
    try:
        from FinMind.data import DataLoader
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=days+10)).strftime("%Y-%m-%d")
        dl = DataLoader()
        dl.token = FINMIND_TOKEN
        df = dl.taiwan_stock_daily(stock_id=str(code).zfill(4), start_date=start, end_date=end)
        if df is None or len(df) < 30:
            return None
        df = df.rename(columns={
            'date': 'Date', 'open': 'Open', 'max': 'High',
            'min': 'Low', 'close': 'Close', 'Trading_Volume': 'Volume'
        })
        df = df.set_index('Date').sort_index()
        return df
    except:
        return None

def fetch_price_with_fallback(code):
    h = fetch_price_yfinance(code)
    if h is not None and len(h) >= 30:
        return h, "yfinance"
    h = fetch_price_finmind(code)
    if h is not None and len(h) >= 30:
        return h, "finmind"
    return None, "none"

def fetch_price_with_fallback(code, mode="auto"):
    """mode: yfinance | finmind | auto"""
    if mode == "yfinance" or (mode == "auto"):
        h = fetch_price_yfinance(code)
        if h is not None and len(h) >= 30:
            return h, "yfinance"
    if mode == "finmind" or (mode == "auto"):
        h = fetch_price_finmind(code)
        if h is not None and len(h) >= 30:
            return h, "finmind"
    # last resort: try the other if auto failed
    if mode == "auto":
        h = fetch_price_yfinance(code)
        if h is not None and len(h) >= 30:
            return h, "yfinance"
        h = fetch_price_finmind(code)
        if h is not None and len(h) >= 30:
            return h, "finmind"
    return None, "none"

def analyze_stock_with_sources(code, name, source_mode="auto"):
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

        # Additional indicators
        # KD (9-day RSV)
        low_min = close.rolling(9).min()
        high_max = close.rolling(9).max()
        rsv = (close - low_min) / (high_max - low_min + 1e-9) * 100
        k_series = rsv.ewm(alpha=1/3).mean()
        d_series = k_series.ewm(alpha=1/3).mean()
        k_val = float(k_series.iloc[-1])
        d_val = float(d_series.iloc[-1])

        # Bollinger Bands (20-day)
        bb_ma20 = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        bb_upper = float((bb_ma20 + 2 * bb_std).iloc[-1])
        bb_lower = float((bb_ma20 - 2 * bb_std).iloc[-1])
        bb_pct = (price - bb_lower) / (bb_upper - bb_lower + 1e-9) * 100

        # BIAS5
        ma5 = close.rolling(5).mean()
        bias5 = float((close.iloc[-1] - ma5.iloc[-1]) / ma5.iloc[-1] * 100)

        # Volume ratio (vs 5-day MA)
        vol = price_hist["Volume"] if "Volume" in price_hist.columns else close * 0
        vol_ma5 = float(vol.rolling(5).mean().iloc[-1])
        vol_ratio = float(vol.iloc[-1] / vol_ma5) if vol_ma5 > 0 else 1.0
        return {
            "code": code, "name": name, "sym": get_symbol(code),
            "price": price, "chg": chg, "rsi": rsi,
            "macd_hist": hist, "ma20": ma20, "ma60": ma60,
            "pct": pct, "high": high, "low": low,
            "source": source,
            "k": k_val, "d": d_val,
            "bb_upper": bb_upper, "bb_lower": bb_lower, "bb_pct": bb_pct,
            "bias5": bias5,
            "vol_ratio": vol_ratio,
        }
    except:
        return None

def fetch_inst_summary(code, days=5):
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=days+7)).strftime("%Y-%m-%d")
    params = {
        "dataset": "TaiwanStockInstitutionalInvestorsBuySell",
        "data_id": str(code).zfill(4),
        "start_date": start,
        "end_date": end,
        "token": FINMIND_TOKEN,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{FINMIND_BASE}?{query}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        rows = data.get("data", [])
        if not rows:
            return None
        totals = {}
        for r in rows:
            name = r.get("name", "")
            net = int(r.get("buy") or 0) - int(r.get("sell") or 0)
            if "Foreign_Investor" in name:
                totals["foreign"] = totals.get("foreign", 0) + net
            elif "Investment_Trust" in name:
                totals["trust"] = totals.get("trust", 0) + net
            elif "Dealer" in name or "Self" in name:
                totals["dealer"] = totals.get("dealer", 0) + net
        return {
            "foreign": totals.get("foreign", 0),
            "trust": totals.get("trust", 0),
            "dealer": totals.get("dealer", 0),
        }
    except:
        return None

def fetch_inst_batch(codes, days=5, progress_callback=None):
    results = {}
    total = len(codes)
    def fetch_one(code):
        return code, fetch_inst_summary(code, days)
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        futures = {executor.submit(fetch_one, code): code for code in codes}
        done = 0
        for future in concurrent.futures.as_completed(futures):
            code = futures[future]
            done += 1
            try:
                _, inst = future.result()
            except:
                inst = None
            if inst:
                results[code] = inst
            if progress_callback and (done % 50 == 0 or done == total):
                progress_callback(done, total, "法人資料")
    return results

def calc_score(d):
    rsi_score = (100 - d["rsi"]) / 100 * 40 if d["rsi"] <= 100 else 0
    macd_score = (d["macd_hist"] / 10 + 1) * 15 if d["macd_hist"] > 0 else max(d["macd_hist"] + 1, 0) * 5
    range_score = (100 - d["pct"]) / 100 * 30 if d["pct"] <= 100 else 0
    return rsi_score + macd_score + range_score

def get_tier(rsi):
    if rsi < 35: return "A"
    if rsi < 50: return "B"
    if rsi < 70: return "C"
    return "D"

def analyze_batch(symbols, progress_callback=None, source_mode="auto"):
    results = []
    total = len(symbols)
    seen = {}
    for code, name, _, _ in symbols:
        if code not in seen:
            seen[code] = name
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futures = {}
        for code, name in seen.items():
            futures[executor.submit(analyze_stock_with_sources, code, name, source_mode)] = code
            time.sleep(0.12)  # stagger requests to avoid yfinance rate limit
        done = 0
        for future in concurrent.futures.as_completed(futures):
            code = futures[future]
            done += 1
            try:
                result = future.result()
            except:
                result = None
            if result:
                result["score"] = calc_score(result)
                results.append(result)
            if progress_callback and (done % 30 == 0 or done == total):
                progress_callback(done, total, "技術分析")
    return results

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

def get_industry_filter(cat):
    mapping = {
        "熱門台股": None,
        "AI 科技": None,
        "半導體": ["半導體業"],
        "光通訊/CPO": None,
        "儲存/記憶體": None,
        "ETF": ["ETF"],
        "金融": None,
        "全部": None,
    }
    return mapping.get(cat)

def load_telegram_config():
    token = None
    chat_id = None
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, encoding="utf-8") as f:
            for line in f:
                if line.startswith("TELEGRAM_BOT_TOKEN="):
                    token = line.split("=", 1)[1].strip()
                elif line.startswith("TELEGRAM_CHAT_ID="):
                    chat_id = line.split("=", 1)[1].strip()
    return token, chat_id

def push_telegram(message, token=None, chat_id=None):
    if not token or not chat_id:
        token, chat_id = load_telegram_config()
    if not token or not chat_id:
        return False, "Telegram config not found"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, json=payload, timeout=15)
        return r.status_code == 200, f"HTTP {r.status_code}"
    except Exception as e:
        return False, str(e)

def format_telegram_report(results, title="台股篩選結果"):
    if not results:
        return "None: No results"
    lines = [f"*{title}* | {datetime.now().strftime('%Y-%m-%d %H:%M')}", "=" * 50]
    for d in results[:20]:
        tier = get_tier(d["rsi"])
        tier_icon = {"A": "A", "B": "B", "C": "C", "D": "X"}.get(tier, "?")
        macd_icon = "+" if d["macd_hist"] > 0 else "-"
        ma_icon = "Y" if (d["ma60"] and d["ma20"] > d["ma60"]) else "N"
        k_val = d.get("k", 0)
        d_val = d.get("d", 0)
        bb_pct = d.get("bb_pct", 50)
        bias5 = d.get("bias5", 0)
        vol_r = d.get("vol_ratio", 1.0)
        inst = d.get("inst", {})
        f = inst.get("foreign", 0)
        t = inst.get("trust", 0)
        dv = inst.get("dealer", 0)
        inst_str = f"F:{f:+,} T:{t:+,} D:{dv:,}" if inst else ""
        # KD signal
        kd_sig = "K+D+" if (k_val > d_val and k_val < 30) else ("K-D+" if k_val < d_val else "")
        bb_sig = "BB Ov" if bb_pct > 80 else ("BB Up" if bb_pct > 60 else ("BB Dn" if bb_pct < 40 else ""))
        lines.append(
            f"[{tier_icon}] {d['code']} {d['name'][:8]} "
            f"${d['price']:.0f} ({d['chg']:+.2f}%) "
            f"R={d['rsi']:.0f} K={k_val:.0f} D={d_val:.0f} "
            f"BB%={bb_pct:.0f} BIAS={bias5:+.1f}% Vol={vol_r:.1f}x "
            f"M={macd_icon} MA={ma_icon} S={d['score']:.0f}{inst_str} "
            f"{kd_sig} {bb_sig}".strip()
        )
    total = len(results)
    a = sum(1 for d in results if get_tier(d["rsi"]) == "A")
    b = sum(1 for d in results if get_tier(d["rsi"]) == "B")
    c = sum(1 for d in results if get_tier(d["rsi"]) == "C")
    lines.append("=" * 50)
    lines.append(f"Grade: A={a} B={b} C={c} | Total={total}")
    if total > 20:
        lines.append(f"(Showing 20 of {total})")
    lines.append("Key: K+D+ = KD GoldenCross | BB Ov=Overbought | BB Dn=Oversold")
    return "\n".join(lines)

class TinaTWGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Tina 台股分析工具 v2.3")
        self.root.geometry("1050x880")
        self.root.resizable(True, True)
        self.registry = []
        self.all_results = []
        self.last_results = []
        self.running = False
        self._setup_ui()
        self.registry = load_registry()
        self.status_lbl.config(text=f"DB: {len(self.registry)} stocks")
        self.result_text.insert(tk.END, f"\nLoaded {len(self.registry)} stocks")

    def _setup_ui(self):
        header = tk.Frame(self.root)
        header.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(header, text="Tina 台股分析工具 v2.3", font=("Arial", 16, "bold")).pack(side=tk.LEFT)
        self.status_lbl = tk.Label(header, text="", font=("Arial", 9), fg="gray")
        self.status_lbl.pack(side=tk.RIGHT)

        cat_frame = tk.LabelFrame(self.root, text="Category", font=("Arial", 10, "bold"))
        cat_frame.pack(fill=tk.X, padx=10, pady=3)
        self.cat_selected = tk.StringVar(value="熱門")
        for cat in list(CATEGORIES.keys()):
            tk.Radiobutton(cat_frame, text=cat, variable=self.cat_selected, value=cat,
                          font=("Arial", 9), command=self.on_cat_change).pack(side=tk.LEFT, padx=3, pady=2)

        search_frame = tk.Frame(self.root)
        search_frame.pack(fill=tk.X, padx=10, pady=3)
        tk.Label(search_frame, text="4-digit Code:", font=("Arial", 10)).pack(side=tk.LEFT)
        self.search_entry = tk.Entry(search_frame, width=12, font=("Arial", 11))
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_entry.bind('<Return>', lambda e: self._quick_search())
        tk.Button(search_frame, text="Search", font=("Arial", 10), command=self._quick_search,
                 bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=3)
        tk.Button(search_frame, text="Refresh", font=("Arial", 10), command=self.run_analysis,
                 bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=3)

        filter_frame = tk.LabelFrame(self.root, text="Tech Filters", font=("Arial", 10, "bold"))
        filter_frame.pack(fill=tk.X, padx=10, pady=3)

        tk.Label(filter_frame, text="RSI <", font=("Arial", 9)).pack(side=tk.LEFT, padx=3)
        self.rsi_var = tk.StringVar(value="60")
        tk.Entry(filter_frame, width=5, textvariable=self.rsi_var, font=("Arial", 10)).pack(side=tk.LEFT, padx=2)

        tk.Label(filter_frame, text="Price Range", font=("Arial", 9)).pack(side=tk.LEFT, padx=5)
        self.price_min_var = tk.StringVar()
        self.price_max_var = tk.StringVar()
        tk.Entry(filter_frame, width=7, textvariable=self.price_min_var, font=("Arial", 10)).pack(side=tk.LEFT, padx=2)
        tk.Label(filter_frame, text="~", font=("Arial", 9)).pack(side=tk.LEFT)
        tk.Entry(filter_frame, width=7, textvariable=self.price_max_var, font=("Arial", 10)).pack(side=tk.LEFT, padx=2)

        self.macd_var = tk.BooleanVar(value=False)
        tk.Checkbutton(filter_frame, text="MACD>0", variable=self.macd_var, font=("Arial", 9)).pack(side=tk.LEFT, padx=5)
        self.ma_var = tk.BooleanVar(value=False)
        tk.Checkbutton(filter_frame, text="MA Bull", variable=self.ma_var, font=("Arial", 9)).pack(side=tk.LEFT, padx=5)
        self.rsi35_var = tk.BooleanVar(value=False)
        tk.Checkbutton(filter_frame, text="RSI<35", variable=self.rsi35_var, font=("Arial", 9)).pack(side=tk.LEFT, padx=5)
        self.rsi50_var = tk.BooleanVar(value=False)
        tk.Checkbutton(filter_frame, text="RSI<50 Only", variable=self.rsi50_var, font=("Arial", 9)).pack(side=tk.LEFT, padx=5)

        inst_frame = tk.LabelFrame(self.root, text="Institutional (5 days)", font=("Arial", 10, "bold"))
        inst_frame.pack(fill=tk.X, padx=10, pady=3)

        tk.Label(inst_frame, text="Filter:", font=("Arial", 9)).pack(side=tk.LEFT, padx=3)
        self.inst_var = tk.StringVar(value="")
        inst_combo = ttk.Combobox(inst_frame, textvariable=self.inst_var, width=18,
                                  values=["", "All", "Foreign>0", "Trust>0", "Dealer>0",
                                         "Foreign+Trust", "All 3 Buy", "Foreign>1000", "Trust>500", "Any Buy"],
                                  state="readonly", font=("Arial", 9))
        inst_combo.current(0)
        inst_combo.pack(side=tk.LEFT, padx=3)

        tk.Label(inst_frame, text="Sort:", font=("Arial", 9)).pack(side=tk.LEFT, padx=8)
        self.inst_sort_var = tk.StringVar(value="Score")
        sort_combo = ttk.Combobox(inst_frame, textvariable=self.inst_sort_var, width=12,
                                  values=["Score", "Foreign", "Trust", "Dealer", "Total Inst"],
                                  state="readonly", font=("Arial", 9))
        sort_combo.current(0)
        sort_combo.pack(side=tk.LEFT, padx=3)

        # Data source priority
        src_frame = tk.LabelFrame(self.root, text="Data Source", font=("Arial", 10, "bold"))
        src_frame.pack(fill=tk.X, padx=10, pady=3)
        self.source_var = tk.StringVar(value="yfinance")
        tk.Radiobutton(src_frame, text="yfinance (Fast)", variable=self.source_var, value="yfinance",
                      font=("Arial", 9)).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(src_frame, text="FinMind (Backup)", variable=self.source_var, value="finmind",
                      font=("Arial", 9)).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(src_frame, text="Auto (yfinance -> FinMind)", variable=self.source_var, value="auto",
                      font=("Arial", 9)).pack(side=tk.LEFT, padx=5)
        tk.Label(src_frame, text="   ", font=("Arial", 9)).pack(side=tk.LEFT)
        self.src_status = tk.Label(src_frame, text="", font=("Arial", 9), fg="gray")
        self.src_status.pack(side=tk.LEFT)

        tk.Button(inst_frame, text="ANALYZE", font=("Arial", 10, "bold"), command=self.run_analysis,
                 bg="#FF9800", fg="white", width=10).pack(side=tk.LEFT, padx=10)

        tg_frame = tk.LabelFrame(self.root, text="Telegram", font=("Arial", 10, "bold"))
        tg_frame.pack(fill=tk.X, padx=10, pady=3)
        tk.Button(tg_frame, text="SEND TO TELEGRAM", font=("Arial", 10, "bold"),
                 command=self._send_to_telegram, bg="#26A69A", fg="white", width=18).pack(side=tk.LEFT, padx=5)
        self.telegram_status = tk.Label(tg_frame, text="", font=("Arial", 9), fg="gray")
        self.telegram_status.pack(side=tk.LEFT, padx=5)

        result_frame = tk.Frame(self.root)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        cols = ("Code", "Name", "Price", "Chg%", "RSI", "K", "D",
                "BB%", "BIAS5", "Vol", "MA20", "MA60", "Foreign", "Trust", "Dealer", "Score", "Status")
        self.tree = ttk.Treeview(result_frame, columns=cols, height=20)
        col_widths = {
            "Code": 52, "Name": 62, "Price": 60, "Chg%": 52,
            "RSI": 35, "K": 30, "D": 30,
            "BB%": 38, "BIAS5": 45, "Vol": 40,
            "MA20": 50, "MA60": 50,
            "Foreign": 65, "Trust": 60, "Dealer": 60,
            "Score": 38, "Status": 65
        }
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=col_widths.get(col, 60), anchor=tk.CENTER)
        vsb = ttk.Scrollbar(result_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(result_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.bind("<Double-1>", lambda e: self._on_row_double_click())

        self.result_text = scrolledtext.ScrolledText(self.root, width=115, height=9, font=("Consolas", 8))
        self.result_text.pack(pady=2, fill=tk.X, padx=10)
        self.result_text.insert('1.0', "Tina TW Stock GUI v2.3\nClick ANALYZE to start...")

    def _load_registry_async(self):
        def load():
            self.registry = load_registry()
            count = len(self.registry)
            self.root.after(0, lambda: self.status_lbl.config(text=f"DB: {count} stocks"))
            self.root.after(0, lambda: self.result_text.insert(tk.END, f"\nLoaded {count} stocks"))
        threading.Thread(target=load, daemon=True).start()

    def _quick_search(self):
        q = self.search_entry.get().strip().upper()
        if not q:
            return
        # Normalize to 4-digit code
        q_code = q.zfill(4)
        
        # Try exact code match first in registry
        if self.registry:
            matches = [(code, name) for code, name, _, _ in self.registry
                      if code == q_code]
            if matches:
                d = analyze_stock_with_sources(matches[0][0], matches[0][1], self.source_var.get())
                if d:
                    d["score"] = calc_score(d)
                    inst = fetch_inst_summary(matches[0][0])
                    if inst:
                        d["inst"] = inst
                    self._show_results([d])
                    return
        
        # Try current results
        found = [r for r in self.all_results if q_code in r["code"] or q in r["code"]]
        if found:
            self._show_results(found[:1])
            return
        
        self.result_text.delete('1.0', tk.END)
        self.result_text.insert('1.0', f"Code {q_code} not found. Try 4-digit like 2330, 1216, 2382")

    def _on_row_double_click(self):
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])
        code = item["values"][0]
        name_row = next(((c, n) for c, n, _, _ in self.registry if c == code), None)
        if name_row:
            d = analyze_stock_with_sources(code, name_row[1], self.source_var.get())
            if d:
                d["score"] = calc_score(d)
                inst = fetch_inst_summary(code)
                if inst:
                    d["inst"] = inst
                self.result_text.delete('1.0', tk.END)
                self.result_text.insert('1.0', self._build_detail(d))

    def _build_detail(self, d):
        tier = get_tier(d["rsi"])
        icons = {"A": "A-oversold", "B": "B-undervalued", "C": "C-fair", "D": "X-overbought"}
        icon = icons.get(tier, "?")
        ma20_above = d.get("ma60") and d["ma20"] > d["ma60"]
        ma60_val = d.get("ma60")
        ma60_str = "N/A" if not ma60_val else f"${ma60_val:.2f}"
        lines = [
            "=" * 55,
            f"[{icon}] {d['code']} {d['name']}",
            "=" * 55,
            f"Price: ${d['price']:.2f}  Chg: {d['chg']:+.2f}%",
            f"RSI(14): {d['rsi']:.1f}",
            f"MACD: {d['macd_hist']:+.3f}  {'+' if d['macd_hist'] > 0 else '-'}",
            f"MA20: ${d['ma20']:.2f}  {'> MA60' if ma20_above else 'MA60: ' + ma60_str}",
            f"Range: ${d['low']:.2f} ~ ${d['high']:.2f}  Pos: {d['pct']:.1f}%",
            f"K: {d.get('k',0):.1f}  D: {d.get('d',0):.1f}  BB%: {d.get('bb_pct',50):.1f}%",
            f"BIAS5: {d.get('bias5',0):+.2f}%  Vol: {d.get('vol_ratio',1.0):.2f}x",
            f"BB: ${d.get('bb_lower',0):.2f} ~ ${d.get('bb_upper',0):.2f}  MA20: ${d['ma20']:.2f}",
            f"Score: {d['score']:.1f}/100  [Source: {d.get('source','?')}]",
            "",
        ]
        inst = d.get("inst", {})
        if inst:
            f, t, dv = inst.get("foreign", 0), inst.get("trust", 0), inst.get("dealer", 0)
            total = f + t + dv
            lines.append("--- INSTITUTIONAL (5 days) ---")
            lines.append(f"Foreign: {f:+,}  {'BUY' if f>0 else 'SELL' if f<0 else 'NEUT'}")
            lines.append(f"Trust:   {t:+,}  {'BUY' if t>0 else 'SELL' if t<0 else 'NEUT'}")
            lines.append(f"Dealer:  {dv:+,}  {'BUY' if dv>0 else 'SELL' if dv<0 else 'NEUT'}")
            lines.append(f"Total:   {total:+,}  {'NET BUY' if total>0 else 'NET SELL' if total<0 else 'NEUT'}")
            lines.append("")
            if tier in "AB":
                lines.append(f"Stop loss: ${d['price']*0.95:.2f} (-5%)")
                lines.append(f"Target:   ${d['price']*1.10:.2f} (+10%)")
            else:
                lines.append(f"Target: ${d['price']*1.05:.2f} (+5%)")
        return "\n".join(lines)

    def on_cat_change(self):
        pass

    def run_analysis(self):
        if self.running:
            messagebox.showwarning("Running", "Please wait...")
            return
        self.running = True
        self._do_analysis()

    def _inst_filter(self, inst, setting):
        if not inst or not setting or setting in ("All", ""):
            return True
        f = inst.get("foreign", 0)
        t = inst.get("trust", 0)
        dv = inst.get("dealer", 0)
        total = f + t + dv
        if setting == "Foreign>0": return f > 0
        elif setting == "Trust>0": return t > 0
        elif setting == "Dealer>0": return dv > 0
        elif setting == "Foreign+Trust": return f > 0 and t > 0
        elif setting == "All 3 Buy": return f > 0 and t > 0 and dv > 0
        elif setting == "Foreign>1000": return f > 1000
        elif setting == "Trust>500": return t > 500
        elif setting == "Any Buy": return total > 0
        return True

    def _do_analysis(self):
        cat = self.cat_selected.get()
        industry_filter = get_industry_filter(cat)
        if cat == "全部":
            target_stocks = list(self.registry)
        elif cat == "熱門台股":
            hot_codes = CATEGORIES["熱門台股"]
            target_stocks = [(code, name, ind, mkt) for code, name, ind, mkt in self.registry if code in hot_codes]
        elif industry_filter:
            target_stocks = []
            for code, name, ind, mkt in self.registry:
                for kw in industry_filter:
                    if kw in ind:
                        target_stocks.append((code, name, ind, mkt))
                        break
        else:
            codes = CATEGORIES.get(cat, [])
            target_stocks = [(code, name, ind, mkt) for code, name, ind, mkt in self.registry if code in codes]

        target_stocks = target_stocks[:500]  # cap analysis at 500

        if not target_stocks:
            self.result_text.delete('1.0', tk.END)
            self.result_text.insert('1.0', f"No stocks for category: {cat}")
            self.running = False
            return

        self.result_text.delete('1.0', tk.END)
        self.result_text.insert('1.0', f"Analyzing {len(target_stocks)} stocks in {cat}...\n")
        self.root.update()

        def work():
            source_mode = self.source_var.get()
            mode_label = {"yfinance":"yfinance", "finmind":"FinMind", "auto":"Auto(yf->FM)"}[source_mode]
            self.root.after(0, lambda: self.result_text.delete('1.0', tk.END))
            self.root.after(0, lambda: self.result_text.insert('1.0',
                f"Analyzing {len(target_stocks)} stocks [{mode_label}] in {cat}...\n"))
            self.root.update()
            
            results = analyze_batch(target_stocks, progress_callback=self._update_progress, source_mode=source_mode)
            yf_count = sum(1 for r in results if r.get("source") == "yfinance")
            fm_count = sum(1 for r in results if r.get("source") == "finmind")
            none_count = len(results) - yf_count - fm_count
            self.root.after(0, lambda: self.result_text.delete('1.0', tk.END))
            self.root.after(0, lambda: self.result_text.insert('1.0',
                f"Done: {len(results)} stocks (yfinance:{yf_count} finmind:{fm_count} failed:{none_count})\n"
                f"Source: {source_mode}\n"
                f"Applying filters...\n"))
            self.root.update()

            rsi_max = float(self.rsi_var.get() or 60)
            price_min = self.price_min_var.get()
            price_max = self.price_max_var.get()
            macd_req = self.macd_var.get()
            ma_req = self.ma_var.get()
            rsi_35 = self.rsi35_var.get()
            rsi_50 = self.rsi50_var.get()

            filtered = []
            for r in results:
                if r["rsi"] > rsi_max: continue
                if rsi_50 and r["rsi"] > 50: continue
                if rsi_35 and r["rsi"] > 35: continue
                if price_min and r["price"] < float(price_min): continue
                if price_max and r["price"] > float(price_max): continue
                if macd_req and r["macd_hist"] <= 0: continue
                if ma_req and not (r["ma60"] and r["ma20"] > r["ma60"]): continue
                filtered.append(r)

            inst_filter = self.inst_var.get()
            need_inst = inst_filter and inst_filter not in ("All", "")
            if need_inst and filtered:
                inst_map = fetch_inst_batch([r["code"] for r in filtered],
                                           progress_callback=self._update_progress)
                for r in filtered:
                    r["inst"] = inst_map.get(r["code"])

            if need_inst:
                final = [r for r in filtered if self._inst_filter(r.get("inst"), inst_filter)]
            else:
                final = filtered

            sort_by = self.inst_sort_var.get()
            if sort_by == "Foreign":
                final.sort(key=lambda x: x.get("inst", {}).get("foreign", 0), reverse=True)
            elif sort_by == "Trust":
                final.sort(key=lambda x: x.get("inst", {}).get("trust", 0), reverse=True)
            elif sort_by == "Dealer":
                final.sort(key=lambda x: x.get("inst", {}).get("dealer", 0), reverse=True)
            elif sort_by == "Total Inst":
                final.sort(key=lambda x: sum(x.get("inst", {}).values()), reverse=True)
            else:
                final.sort(key=lambda x: x["score"], reverse=True)

            self.all_results = results
            self.last_results = final
            self.root.after(0, lambda: self._show_results(final, total=len(target_stocks)))
            self.running = False

        threading.Thread(target=work, daemon=True).start()

    def _update_progress(self, done, total, phase=""):
        phase_str = f"[{phase}] " if phase else ""
        self.root.after(0, lambda: self.result_text.delete('1.0', tk.END))
        self.root.after(0, lambda: self.result_text.insert('1.0',
            f"{phase_str}Analyzing... {done}/{total} ({done*100//total}%)"))

    def _show_results(self, results, total=None):
        for row in self.tree.get_children():
            self.tree.delete(row)
        if not results:
            self.result_text.delete('1.0', tk.END)
            self.result_text.insert('1.0', "No results. Try relaxing filters.")
            return
        total_str = f"/{total} stocks" if total else ""
        self.result_text.delete('1.0', tk.END)
        self.result_text.insert('1.0', f"{len(results)} results{total_str}\n")
        for d in results:
            tier = get_tier(d["rsi"])
            tier_icon = {"A": "A", "B": "B", "C": "C", "D": "X"}.get(tier, "?")
            macd_icon = "+" if d["macd_hist"] > 0 else "-"
            ma_icon = "+" if (d["ma60"] and d["ma20"] > d["ma60"]) else "-"
            ma20_str = f"{d['ma20']:.0f}"
            ma60_str = f"{d['ma60']:.0f}" if d["ma60"] else "N/A"
            inst = d.get("inst", {})
            f_str = f"{inst.get('foreign', 0):+,}"
            t_str = f"{inst.get('trust', 0):+,}"
            d_str = f"{inst.get('dealer', 0):+,}"
            self.tree.insert("", tk.END, values=(
                d["code"], d["name"][:6],
                f"${d['price']:.2f}",
                f"{d['chg']:+.2f}%",
                f"{d['rsi']:.1f}",
                f"{d.get('k', 0):.1f}",
                f"{d.get('d', 0):.1f}",
                f"{d.get('bb_pct', 50):.1f}%",
                f"{d.get('bias5', 0):+.2f}%",
                f"{d.get('vol_ratio', 1.0):.2f}x",
                ma20_str, ma60_str,
                f_str, t_str, d_str,
                f"{d['score']:.0f}",
                f"{tier_icon} {macd_icon} {ma_icon}"
            ))
        a = sum(1 for d in results if get_tier(d["rsi"]) == "A")
        b = sum(1 for d in results if get_tier(d["rsi"]) == "B")
        c = sum(1 for d in results if get_tier(d["rsi"]) == "C")
        self.result_text.insert(tk.END,
            f"Grade: A={a} B={b} C={c} | Total={len(results)}\n")
        if any(d.get("inst") for d in results):
            tf = sum(d.get("inst", {}).get("foreign", 0) for d in results)
            tt = sum(d.get("inst", {}).get("trust", 0) for d in results)
            td = sum(d.get("inst", {}).get("dealer", 0) for d in results)
            self.result_text.insert(tk.END, f"Inst Total: F:{tf:+,} T:{tt:+,} D:{td:,}\n")
        self.result_text.insert(tk.END, "Double-click row for details\n")

    def _send_to_telegram(self):
        if not self.last_results:
            self.telegram_status.config(text="No results yet", fg="orange")
            return
        self.telegram_status.config(text="Sending...", fg="blue")
        self.root.update()
        def send():
            cat = self.cat_selected.get()
            report = format_telegram_report(self.last_results, title=f"TW-{cat}")
            ok, msg = push_telegram(report)
            self.root.after(0, lambda: self.telegram_status.config(
                text="OK" if ok else f"Error: {msg}",
                fg="green" if ok else "red"
            ))
        threading.Thread(target=send, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = TinaTWGUI(root)
    root.mainloop()
save_session_cache()

