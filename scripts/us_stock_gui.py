# -*- coding: utf-8 -*-
"""
Tina 美股分析工具 v2.0 - GUI 完整版
====================================
與台股 GUI v2.2 相同介面架構
- Treeview 表格顯示（已修復 show=headings bug）
- 分類/篩選/排序/快捷查詢
- 平行抓取（yfinance）
- 雙擊查看詳細技術分析
"""
import yfinance as yf
import numpy as np
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime
import os
import sys
import threading
import concurrent.futures
import requests

# === Session Cache ===
SESSION_CACHE = {}
CACHE_TTL = 3600

def get_cache_path():
    import tempfile, os
    return os.path.join(tempfile.gettempdir(), "us_gui_session_cache.db")

def save_session_cache():
    import pickle
    if not SESSION_CACHE:
        return
    try:
        with open(get_cache_path(), "wb") as f:
            pickle.dump(SESSION_CACHE, f)
    except:
        pass

def load_session_cache():
    import pickle, os
    try:
        p = get_cache_path()
        if os.path.exists(p):
            with open(p, "rb") as f:
                return pickle.load(f)
    except:
        pass
    return {}

SESSION_CACHE = load_session_cache()
import atexit
atexit.register(save_session_cache)

import time
import tempfile
import pickle
import atexit

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, "..", ".env")

# ── Telegram Helper ────────────────────────────────────────────────────────────
def load_telegram_config():
    token = None
    chat_id = None
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, encoding='utf-8') as f:
            for line in f:
                if line.startswith('TELEGRAM_BOT_TOKEN='):
                    token = line.split('=', 1)[1].strip()
                elif line.startswith('TELEGRAM_CHAT_ID='):
                    chat_id = line.split('=', 1)[1].strip()
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

def format_us_telegram_report(results, title="美股篩選結果"):
    if not results:
        return "❌ 無符合條件的股票"
    lines = [f"📊 {title} | {datetime.now().strftime('%Y-%m-%d %H:%M')}", "─" * 40]
    for d in results[:20]:
        tier = get_tier(d["rsi"])
        tier_icon = {"A": "🥇", "B": "🥈", "C": "🥉", "D": "❌"}.get(tier, "?")
        macd_icon = "✅" if d["macd_hist"] > 0 else "⏸️"
        ma_icon = "✅" if (d["ma60"] and d["ma20"] > d["ma60"]) else "❌"
        inst_str = f" 機{ d.get('inst_pct', 'N/A') }" if d.get('inst_pct') else ""
        lines.append(
            f"{tier_icon} {d['symbol']} {d['name'][:8]} "
            f"${d['price']:.2f} ({d['chg']:+.2f}%) "
            f"RSI={d['rsi']:.0f} MACD={d['macd_hist']:+.1f} {macd_icon}{ma_icon} "
            f"[{d['score']:.0f}分]{inst_str}"
        )
    total = len(results)
    a = sum(1 for d in results if get_tier(d["rsi"]) == "A")
    b = sum(1 for d in results if get_tier(d["rsi"]) == "B")
    c = sum(1 for d in results if get_tier(d["rsi"]) == "C")
    lines.append("─" * 40)
    lines.append(f"📊 評級: 🥇A={a} 🥈B={b} 🥉C={c} | 共 {total} 檔")
    if total > 20:
        lines.append(f"（顯示前 20 檔，共 {total} 檔）")
    return "\n".join(lines)
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

# ── US Stock Categories ──────────────────────────────────────────────────────
AI_TECH = [
    ("NVDA","Nvidia"),("AVGO","Broadcom"),("AMD","AMD"),
    ("MRVL","Marvell"),("ARM","ARM"),
    ("MSFT","Microsoft"),("META","Meta"),("GOOGL","Google"),
    ("AMZN","Amazon"),("PLTR","Palantir"),("COIN","Coinbase"),
    ("MSTR","MicroStrategy"),("TSLA","Tesla"),
]
SEMI_EQUIP = [
    ("ASML","ASML"),("AMAT","Applied Mat"),("LRCX","Lam Res"),
    ("KLAC","KLA"),("TER","Teradyne"),
]
OPTICAL = [
    ("ANET","Arista"),("CSCO","Cisco"),("COHR","Coherent"),
    ("LITE","Lumentum"),("GLW","Corning"),("FFIV","F5"),
    ("ZBRA","Zebra"),("JBL","Jabil"),
]
MEMORY = [
    ("MU","Micron"),("WDC","Western Digital"),("STX","Seagate"),
    ("NTAP","NetApp"),("PVTL","Pure Storage"),
]
INFRA = [
    ("VRT","Vertiv"),("ETN","Eaton"),("NVT","nVent"),
    ("ROK","Rockwell"),("PH","Parker"),
]
PACKAGING = [
    ("AMKR","Amkor"),("ASE","ASE Tech"),("MKSI","MKS"),
    ("FORM","FormFactor"),
]
CLOUD = [
    ("EQIX","Equinix"),("DLR","Digital Realty"),("ORCL","Oracle"),
    ("CRM","Salesforce"),("NOW","ServiceNow"),("WDAY","Workday"),
    ("ZS","Zscaler"),("AKAM","Akamai"),
]
CONSUMER = [
    ("AAPL","Apple"),("NFLX","Netflix"),("DIS","Disney"),
    ("CMCSA","Comcast"),("KO","Coca-Cola"),("PEP","Pepsi"),("COST","Costco"),
]
FINANCE = [
    ("JPM","JPMorgan"),("BAC","Bank of America"),("WFC","Wells Fargo"),
    ("GS","Goldman Sachs"),("MS","Morgan Stanley"),
    ("V","Visa"),("MA","Mastercard"),("PYPL","PayPal"),
]
HEALTH = [
    ("UNH","UnitedHealth"),("JNJ","Johnson"),("PFE","Pfizer"),
    ("ABBV","AbbVie"),("TMO","Thermo"),("ABT","Abbott"),
    ("MRK","Merck"),("LLY","Eli Lilly"),("BMY","Bristol-Myers"),
]
INDUSTRIAL = [
    ("CAT","Caterpillar"),("DE","John Deere"),("BA","Boeing"),
    ("HON","Honeywell"),("UPS","UPS"),("RTX","Raytheon"),
    ("LMT","Lockheed"),("GD","General Dynamics"),("NOC","Northrop"),
]
ETF_SP500 = [("VOO","VOO"),("IVV","IVV"),("SPY","SPY")]
ETF_TOTAL = [("VTI","VTI")]
ETF_DOW = [("DIA","DIA")]
ETF_NASDAQ100 = [("QQQ","QQQ"),("QQQM","QQQM")]
ETF_SEMI = [("SOXX","SOXX"),("SMH","SMH")]
ETF_TECH = [("VGT","VGT"),("XLK","XLK")]
ETF_DIV = [("SCHD","SCHD"),("VYM","VYM"),("VIG","VIG"),("DGRO","DGRO")]
ETF_SECTOR = [("XLV","XLV"),("XLF","XLF"),("XLE","XLE"),("XLY","XLY")]
ETF_BOND = [("TLT","TLT"),("BND","BND"),("LQD","LQD")]
ETF_ALL = ETF_SP500 + ETF_TOTAL + ETF_DOW + ETF_NASDAQ100 + ETF_SEMI + ETF_TECH + ETF_DIV + ETF_SECTOR + ETF_BOND

ALL_STOCKS = (
    AI_TECH + SEMI_EQUIP + OPTICAL + MEMORY + INFRA +
    PACKAGING + CLOUD + CONSUMER + FINANCE + HEALTH + INDUSTRIAL
)

STOCKS = {
    "AI/科技": AI_TECH,
    "半導體設備": SEMI_EQUIP,
    "光通訊/CPO": OPTICAL,
    "記憶體/儲存": MEMORY,
    "電力/散熱": INFRA,
    "先進封裝": PACKAGING,
    "雲端/資料": CLOUD,
    "消費/零售": CONSUMER,
    "金融": FINANCE,
    "醫療": HEALTH,
    "工業/航太": INDUSTRIAL,
    "--------": [],
    "S&P 500": ETF_SP500,
    "全市場": ETF_TOTAL,
    "道瓊": ETF_DOW,
    "NASDAQ100": ETF_NASDAQ100,
    "半導體ETF": ETF_SEMI,
    "科技ETF": ETF_TECH,
    "股息ETF": ETF_DIV,
    "產業ETF": ETF_SECTOR,
    "債券ETF": ETF_BOND,
    "全部": ALL_STOCKS,
}

# ── Analyze Single Stock ─────────────────────────────────────────────────────
def analyze_stock(sym, name=None):
    try:
        # Session cache check
        now = time.time()
        cached = SESSION_CACHE.get(sym)
        if cached is not None:
            ts, price_hist = cached
            if now - ts < CACHE_TTL:
                price = float(price_hist.iloc[-1])
                prev = float(price_hist.iloc[-2])
                chg = (price - prev) / prev * 100
                rsi = float(calc_rsi(price_hist).iloc[-1])
                macd_val, sig_val = calc_macd(price_hist)
                hist = macd_val - sig_val
                ma20_val = float(price_hist.rolling(20).mean().iloc[-1])
                ma60_val = float(price_hist.rolling(60).mean().iloc[-1]) if len(price_hist) >= 60 else None
                high = float(price_hist["High"].max())
                low = float(price_hist["Low"].min())
                pct = (price - low) / (high - low) * 100 if high > low else 50
                t2 = yf.Ticker(sym)
                try:
                    info = t2.info
                    held = info.get("heldPercentInstitutions", None)
                    inst_pct = round(held * 100, 2) if held is not None else None
                except:
                    inst_pct = None
                return {
                    "symbol": sym, "name": name or sym,
                    "price": price, "chg": chg, "rsi": rsi,
                    "macd_hist": hist, "ma20": ma20_val, "ma60": ma60_val,
                    "pct": pct, "high": high, "low": low,
                    "inst_pct": inst_pct,
                }
        t = yf.Ticker(sym)
        h = t.history(period="6mo")
        if h is None or len(h) < 30:
            return None
        close = h["Close"]
        price = float(close.iloc[-1])
        prev = float(close.iloc[-2])
        chg = (price - prev) / prev * 100
        rsi = float(calc_rsi(close).iloc[-1])
        macd_val, sig_val = calc_macd(close)
        hist = macd_val - sig_val
        ma20 = float(close.rolling(20).mean().iloc[-1])
        ma60 = float(close.rolling(60).mean().iloc[-1]) if len(close) >= 60 else None
        high = float(h["High"].max())
        low = float(h["Low"].min())
        pct = (price - low) / (high - low) * 100 if high > low else 50
        
        # Fetch institutional % from info
        inst_pct = None
        try:
            info = t.info
            held = info.get("heldPercentInstitutions", None)
            if held is not None and held > 0:
                inst_pct = round(held * 100, 2)
        except:
            pass
        
        SESSION_CACHE[sym] = (time.time(), h)
        return {
            "symbol": sym, "name": name or sym,
            "price": price, "chg": chg, "rsi": rsi,
            "macd_hist": hist, "ma20": ma20, "ma60": ma60,
            "pct": pct, "high": high, "low": low,
            "inst_pct": inst_pct,
        }
    except:
        return None

# ── Scoring ───────────────────────────────────────────────────────────────────
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

# ── Batch Analyze ─────────────────────────────────────────────────────────────
def analyze_batch(stocks, progress_callback=None):
    results = []
    total = len(stocks)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = {
            executor.submit(analyze_stock, sym, name): sym
            for sym, name in stocks
        }
        done = 0
        for future in concurrent.futures.as_completed(futures):
            sym = futures[future]
            done += 1
            try:
                result = future.result()
            except:
                result = None
            if result:
                result["score"] = calc_score(result)
                results.append(result)
            if progress_callback and (done % 20 == 0 or done == total):
                progress_callback(done, total, "分析")
    
    return results

# ── GUI ────────────────────────────────────────────────────────────────────────
class TinaUSGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Tina 美股分析工具 v2.0")
        self.root.geometry("1050x880")
        self.root.resizable(True, True)
        self.all_results = []
        self.last_results = []
        self.running = False
        self._setup_ui()
    
    def _setup_ui(self):
        header = tk.Frame(self.root)
        header.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(header, text="📊 Tina 美股分析工具 v2.0", font=("Arial", 16, "bold")).pack(side=tk.LEFT)
        self.status_lbl = tk.Label(header, text="就緒", font=("Arial", 9), fg="gray")
        self.status_lbl.pack(side=tk.RIGHT)
        
        # Category buttons
        cat_frame = tk.LabelFrame(self.root, text="分類", font=("Arial", 10, "bold"))
        cat_frame.pack(fill=tk.X, padx=10, pady=3)
        self.cat_selected = tk.StringVar(value="AI/科技")
        for cat in list(STOCKS.keys()):
            if cat == "--------":
                tk.Label(cat_frame, text="ETF:").pack(side=tk.LEFT, padx=6)
            else:
                tk.Radiobutton(cat_frame, text=cat, variable=self.cat_selected, value=cat,
                              font=("Arial", 9), command=self.on_cat_change).pack(side=tk.LEFT, padx=3, pady=2)
        
        # Search
        search_frame = tk.Frame(self.root)
        search_frame.pack(fill=tk.X, padx=10, pady=3)
        tk.Label(search_frame, text="代號:", font=("Arial", 10)).pack(side=tk.LEFT)
        self.search_entry = tk.Entry(search_frame, width=10, font=("Arial", 11))
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_entry.bind('<Return>', lambda e: self._quick_search())
        tk.Button(search_frame, text="查詢", font=("Arial", 10), command=self._quick_search,
                 bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=3)
        tk.Button(search_frame, text="重新整理", font=("Arial", 10), command=self.run_analysis,
                 bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=3)
        
        # Technical filters
        filter_frame = tk.LabelFrame(self.root, text="技術篩選", font=("Arial", 10, "bold"))
        filter_frame.pack(fill=tk.X, padx=10, pady=3)
        
        tk.Label(filter_frame, text="RSI <", font=("Arial", 9)).pack(side=tk.LEFT, padx=3)
        self.rsi_var = tk.StringVar(value="60")
        tk.Entry(filter_frame, width=5, textvariable=self.rsi_var, font=("Arial", 10)).pack(side=tk.LEFT, padx=2)
        
        tk.Label(filter_frame, text="價格區間", font=("Arial", 9)).pack(side=tk.LEFT, padx=5)
        self.price_min_var = tk.StringVar()
        self.price_max_var = tk.StringVar()
        tk.Entry(filter_frame, width=7, textvariable=self.price_min_var, font=("Arial", 10)).pack(side=tk.LEFT, padx=2)
        tk.Label(filter_frame, text="~", font=("Arial", 9)).pack(side=tk.LEFT)
        tk.Entry(filter_frame, width=7, textvariable=self.price_max_var, font=("Arial", 10)).pack(side=tk.LEFT, padx=2)
        
        self.macd_var = tk.BooleanVar(value=False)
        tk.Checkbutton(filter_frame, text="MACD>0", variable=self.macd_var, font=("Arial", 9)).pack(side=tk.LEFT, padx=5)
        
        self.ma_var = tk.BooleanVar(value=False)
        tk.Checkbutton(filter_frame, text="MA多頭", variable=self.ma_var, font=("Arial", 9)).pack(side=tk.LEFT, padx=5)
        
        self.rsi35_var = tk.BooleanVar(value=False)
        tk.Checkbutton(filter_frame, text="RSI<35", variable=self.rsi35_var, font=("Arial", 9)).pack(side=tk.LEFT, padx=5)
        
        self.rsi50_var = tk.BooleanVar(value=False)
        tk.Checkbutton(filter_frame, text="只看RSI<50", variable=self.rsi50_var, font=("Arial", 9)).pack(side=tk.LEFT, padx=5)
        
        tk.Label(filter_frame, text="機構持有%", font=("Arial", 9)).pack(side=tk.LEFT, padx=8)
        self.inst_pct_var = tk.StringVar()
        tk.Entry(filter_frame, width=6, textvariable=self.inst_pct_var, font=("Arial", 10)).pack(side=tk.LEFT, padx=2)
        tk.Label(filter_frame, text="% 以上", font=("Arial", 9)).pack(side=tk.LEFT)
        
        # Sort
        sort_frame = tk.LabelFrame(self.root, text="排序", font=("Arial", 10, "bold"))
        sort_frame.pack(fill=tk.X, padx=10, pady=3)
        
        self.sort_var = tk.StringVar(value="評分")
        sort_combo = ttk.Combobox(sort_frame, textvariable=self.sort_var, width=15,
                                  values=["評分", "RSI (低→高)", "MACD", "機構持有%"],
                                  state="readonly", font=("Arial", 9))
        sort_combo.current(0)
        sort_combo.pack(side=tk.LEFT, padx=5)
        
        tk.Button(sort_frame, text="🔍 篩選分析", font=("Arial", 10, "bold"), command=self.run_analysis,
                 bg="#FF9800", fg="white", width=12).pack(side=tk.LEFT, padx=15)
        
        telegram_frame = tk.LabelFrame(self.root, text="Telegram", font=("Arial", 10, "bold"))
        telegram_frame.pack(fill=tk.X, padx=10, pady=3)
        tk.Button(telegram_frame, text="📤 發送結果到 Telegram", font=("Arial", 10, "bold"),
                 command=self._send_to_telegram, bg="#26A69A", fg="white", width=20).pack(side=tk.LEFT, padx=5)
        self.telegram_status = tk.Label(telegram_frame, text="", font=("Arial", 9), fg="gray")
        self.telegram_status.pack(side=tk.LEFT, padx=5)
        self.telegram_status.bind("<Configure>", lambda e: self.telegram_status.update_idletasks())
        
        # Treeview results
        result_frame = tk.Frame(self.root)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        cols = ("代號", "名稱", "價格", "漲跌%", "RSI", "MACD",
                "MA20", "MA60", "機構%", "評分", "狀態")
        self.tree = ttk.Treeview(result_frame, columns=cols, height=20)
        
        col_widths = {
            "代號": 65, "名稱": 72, "價格": 70, "漲跌%": 65,
            "RSI": 42, "MACD": 60, "MA20": 65, "MA60": 65,
            "機構%": 60, "評分": 42, "狀態": 80
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
        self.result_text.insert('1.0', "📊 Tina 美股分析工具 v2.0\n選擇分類後按「篩選分析」開始...")
    
    def on_cat_change(self):
        pass
    
    def _quick_search(self):
        q = self.search_entry.get().strip().upper()
        if not q:
            return
        found = [r for r in self.all_results if q in r["symbol"] or q in r["name"]]
        if found:
            self._show_results(found)
            return
        d = analyze_stock(q)
        if d:
            d["score"] = calc_score(d)
            self._show_results([d])
        else:
            self.result_text.delete('1.0', tk.END)
            self.result_text.insert('1.0', "❌ 無法取得 " + q + " 的資料")
    
    def _on_row_double_click(self):
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])
        sym = item["values"][0]
        found = [r for r in self.all_results if r["symbol"] == sym]
        if found:
            self.result_text.delete('1.0', tk.END)
            self.result_text.insert('1.0', self._build_detail(found[0]))
    
    def _build_detail(self, d):
        tier = get_tier(d["rsi"])
        icon = {"A": "🥇超跌", "B": "🥈低估", "C": "🥉合理", "D": "❌過熱"}.get(tier, "?")
        ma20_above = d.get("ma60") and d["ma20"] > d["ma60"]
        ma60_val = d.get("ma60")
        ma60_str = "N/A" if not ma60_val else ("$%.2f" % ma60_val)
        lines = [
            "="*55,
            icon + " " + d["symbol"] + " " + d["name"],
            "="*55,
            ("價格: $%.2f  漲跌: %+.2f%%" % (d["price"], d["chg"])),
            ("RSI(14): %.1f" % d["rsi"]),
            ("MACD: %+.3f  " % d["macd_hist"]) + ("✅ 正" if d["macd_hist"] > 0 else "⏸️ 負"),
            ("MA20: $%.2f  " % d["ma20"]) + ("✅ > MA60" if ma20_above else "MA60: " + ma60_str + " ❌"),
            ("區間: $%.2f ~ $%.2f  位置: %.1f%%" % (d["low"], d["high"], d["pct"])),
            ("評分: %.1f/100" % d["score"]),
        ]
        if d.get("inst_pct") is not None:
            lines.append("機構持有: %.1f%%" % d["inst_pct"])
        lines.append("")
        lines.append("【進場參考】" if tier in "AB" else "【觀察】")
        lines.append("理想進場: RSI 35-50，MACD 轉正，MA20 上穿 MA60")
        lines.append("停損: $%.2f (-5%)" % (d["price"] * 0.95))
        if tier in "AB":
            lines.append("目標: $%.2f (+10%)" % (d["price"] * 1.10))
        else:
            lines.append("目標: $%.2f (+5%)" % (d["price"] * 1.05))
        return "\n".join(lines)
    
    def run_analysis(self):
        if self.running:
            messagebox.showwarning("執行中", "分析正在進行中，請稍候...")
            return
        self.running = True
        self._do_analysis()
    
    def _send_to_telegram(self):
        """Send current filtered results to Telegram"""
        if not self.last_results:
            self.telegram_status.config(text="尚無分析結果可發送", fg="orange")
            return
        cat = self.cat_selected.get()
        self.telegram_status.config(text="發送中...", fg="blue")
        self.root.update()
        
        def send_async():
            report = format_us_telegram_report(self.last_results, title=f"美股篩選-{cat}")
            ok, msg = push_telegram(report)
            self.root.after(0, lambda: self.telegram_status.config(
                text="✅ 已發送" if ok else f"❌ 發送失敗: {msg}",
                fg="green" if ok else "red"
            ))
        
        threading.Thread(target=send_async, daemon=True).start()
    
    def _do_analysis(self):
        cat = self.cat_selected.get()
        stocks = STOCKS.get(cat, ALL_STOCKS)
        
        self.result_text.delete('1.0', tk.END)
        self.result_text.insert('1.0', "🔍 分析 " + str(len(stocks)) + " 檔 " + cat + "...\n")
        self.root.update()
        
        def work():
            results = analyze_batch(stocks, progress_callback=self._update_progress)
            
            rsi_max = float(self.rsi_var.get() or 60)
            price_min = self.price_min_var.get()
            price_max = self.price_max_var.get()
            macd_req = self.macd_var.get()
            ma_req = self.ma_var.get()
            rsi_35 = self.rsi35_var.get()
            rsi_50 = self.rsi50_var.get()
            inst_pct_min = self.inst_pct_var.get()
            
            filtered = []
            for r in results:
                if r["rsi"] > rsi_max: continue
                if rsi_50 and r["rsi"] > 50: continue
                if rsi_35 and r["rsi"] > 35: continue
                if price_min and r["price"] < float(price_min): continue
                if price_max and r["price"] > float(price_max): continue
                if macd_req and r["macd_hist"] <= 0: continue
                if ma_req and not (r["ma60"] and r["ma20"] > r["ma60"]): continue
                if inst_pct_min and (r.get("inst_pct") is None or r["inst_pct"] < float(inst_pct_min)): continue
                filtered.append(r)
            
            sort_by = self.sort_var.get()
            if sort_by == "RSI (低→高)":
                filtered.sort(key=lambda x: x["rsi"])
            elif sort_by == "MACD":
                filtered.sort(key=lambda x: x["macd_hist"], reverse=True)
            elif sort_by == "機構持有%":
                filtered.sort(key=lambda x: x.get("inst_pct") or 0, reverse=True)
            else:
                filtered.sort(key=lambda x: x["score"], reverse=True)
            
            self.all_results = results
            self.last_results = filtered
            self.root.after(0, lambda: self._show_results(filtered, total=len(stocks)))
            self.running = False
        
        threading.Thread(target=work, daemon=True).start()
    
    def _update_progress(self, done, total, phase=""):
        phase_str = "[" + phase + "] " if phase else ""
        self.root.after(0, lambda: self.result_text.delete('1.0', tk.END))
        self.root.after(0, lambda: self.result_text.insert('1.0',
            phase_str + "分析中... " + str(done) + "/" + str(total) + " 檔 (" + str(done*100//total) + "%)"))
    
    def _show_results(self, results, total=None):
        for row in self.tree.get_children():
            self.tree.delete(row)
        
        if not results:
            self.result_text.delete('1.0', tk.END)
            self.result_text.insert('1.0', "❌ 無符合條件的股票\n嘗試放寬篩選條件")
            return
        
        total_str = "/" + str(total) + " 檔" if total else ""
        self.result_text.delete('1.0', tk.END)
        self.result_text.insert('1.0', "✅ " + str(len(results)) + " 檔符合條件（已排序）" + total_str + "\n")
        
        for d in results:
            tier = get_tier(d["rsi"])
            tier_icon = {"A": "🥇", "B": "🥈", "C": "🥉", "D": "❌"}.get(tier, "?")
            macd_icon = "✅" if d["macd_hist"] > 0 else "⏸️"
            ma_icon = "✅" if (d["ma60"] and d["ma20"] > d["ma60"]) else "❌"
            ma20_str = "%.0f" % d["ma20"]
            ma60_str = "%.0f" % d["ma60"] if d["ma60"] else "N/A"
            inst_str = ("%.1f%%" % d["inst_pct"]) if d.get("inst_pct") is not None else "N/A"
            
            self.tree.insert("", tk.END, values=(
                d["symbol"], d["name"][:6],
                ("$%.2f" % d["price"]),
                ("%+.2f%%" % d["chg"]),
                ("%.1f" % d["rsi"]),
                ("%+.2f" % d["macd_hist"]),
                ma20_str, ma60_str,
                inst_str,
                ("%.0f" % d["score"]),
                (tier_icon + " " + macd_icon + " " + ma_icon)
            ))
        
        a = sum(1 for d in results if get_tier(d["rsi"]) == "A")
        b = sum(1 for d in results if get_tier(d["rsi"]) == "B")
        c = sum(1 for d in results if get_tier(d["rsi"]) == "C")
        self.result_text.insert(tk.END,
            ("\n📊 評級: 🥇A=%d 🥈B=%d 🥉C=%d | 共 %d 檔\n" % (a, b, c, len(results))) +
            ("💡 雙擊任一列查看詳細分析\n" if len(results) > 0 else ""))

if __name__ == "__main__":
    root = tk.Tk()
    app = TinaUSGUI(root)
    root.mainloop()