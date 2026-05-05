# -*- coding: utf-8 -*-
"""
Tina 即時分析工具 v6.0 - GUI 完整版
====================================
- 依評分排序
- 分類篩選
- 價格區間篩選
- 覆蓋 S&P 500 主要股票
"""
import yfinance as yf
import numpy as np
import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime
import threading

def calc_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def calc_macd(close, fast=12, slow=26, signal=9):
    ema12 = close.ewm(span=fast, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd.values[-1], signal_line.values[-1]

def analyze_stock(sym, name=None):
    try:
        t = yf.Ticker(sym)
        h = t.history(period="3mo")
        if h is None or len(h) < 30: return None
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
        pct = (price - low) / (high - low) * 100
        return {
            "symbol": sym, "name": name or sym,
            "price": price, "chg": chg, "rsi": rsi, "macd_hist": hist,
            "ma20": ma20, "ma60": ma60, "pct": pct
        }
    except: return None

def calc_score(d):
    rsi_score = (100 - d['rsi']) / 100 * 40 if d['rsi'] <= 100 else 0
    macd_score = (d['macd_hist'] / 10 + 1) * 15 if d['macd_hist'] > 0 else max(d['macd_hist'] + 1, 0) * 5
    range_score = (100 - d['pct']) / 100 * 30 if d['pct'] <= 100 else 0
    return rsi_score + macd_score + range_score

# AI/科技
AI_TECH = [
    ("NVDA","Nvidia"),("AVGO","Broadcom"),("AMD","AMD"),
    ("MRVL","Marvell"),("ARM","ARM"),
    ("MSFT","Microsoft"),("META","Meta"),("GOOGL","Google"),
    ("AMZN","Amazon"),("PLTR","Palantir"),("COIN","Coinbase"),
    ("MSTR","MicroStrategy"),("TSLA","Tesla"),
]

# 半導體設備
SEMI_EQUIP = [
    ("ASML","ASML"),("AMAT","Applied Mat"),("LRCX","Lam Res"),
    ("KLAC","KLA"),("CAMT","Camtek"),("TER","Teradyne"),
    ("LRCX","Lam Res"),
]

# 光通訊/CPO
OPTICAL = [
    ("ANET","Arista"),("CSCO","Cisco"),("COHR","Coherent"),
    ("LITE","Lumentum"),("GLW","Corning"),("FFIV","F5"),
    ("ZBRA","Zebra"),("JBL","Jabil"),
]

# 記憶體/儲存
MEMORY = [
    ("MU","Micron"),("WDC","Western Digital"),("STX","Seagate"),
    ("NTAP","NetApp"),("PVTL","Pure Storage"),
]

# 電力/散熱/基建
INFRA = [
    ("VRT","Vertiv"),("ETN","Eaton"),("AMSC","AMSC"),
    ("NVT","nVent"),("SBGSY","Schneider"),("EMR","Emerson"),
    ("ROK","Rockwell"),("PH","Parker"),
]

# 先進封裝
PACKAGING = [
    ("AMKR","Amkor"),("ASE","ASE Tech"),("MKSI","MKS"),
    ("FORM","FormFactor"),
]

# 雲端/資料中心
CLOUD = [
    ("EQIX","Equinix"),("DLR","Digital Realty"),("ORCL","Oracle"),
    ("CRM","Salesforce"),("NOW","ServiceNow"),("WDAY","Workday"),
    ("ZS","Zscaler"),("AKAM","Akamai"),("CNT","CenturyLink"),
]

# 消費/零售
CONSUMER = [
    ("AAPL","Apple"),("NFLX","Netflix"),("DIS","Disney"),
    ("CMCSA","Comcast"),("T","AT&T"),("VZ","Verizon"),
    ("KO","Coca-Cola"),("PEP","Pepsi"),("COST","Costco"),
]

# 金融
FINANCE = [
    ("JPM","JPMorgan"),("BAC","Bank of America"),("WFC","Wells Fargo"),
    ("GS","Goldman Sachs"),("MS","Morgan Stanley"),
    ("V","Visa"),("MA","Mastercard"),("PYPL","PayPal"),
]

# 醫療
HEALTH = [
    ("UNH","UnitedHealth"),("JNJ","Johnson"),("PFE","Pfizer"),
    ("ABBV","AbbVie"),("TMO","Thermo"),("ABT","Abbott"),
    ("MRK","Merck"),("LLY","Eli Lilly"),("BMY","Bristol-Myers"),
]

# 工業/航太
INDUSTRIAL = [
    ("CAT","Caterpillar"),("DE","John Deere"),("BA","Boeing"),
    ("HON","Honeywell"),("UPS","UPS"),("RTX","Raytheon"),
    ("LMT","Lockheed"),("GD","General Dynamics"),("NOC","Northrop"),
]

# ========== ETF 分類 ==========
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

# 完整列表
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

def get_tier(rsi):
    if rsi < 35: return "A"
    if rsi < 50: return "B"
    if rsi < 70: return "C"
    return "D"

def format_stock(d):
    tier = get_tier(d['rsi'])
    icon = {"A":"🥇","B":"🥈","C":"🥉","D":"❌"}.get(tier,"?")
    rsi_ok = "✅" if d['macd_hist'] > 0 and tier in "ABC" else "⏸️"
    ma20 = d['ma20']
    ma60 = d['ma60'] if d['ma60'] else 0
    ma_bull = "✅" if ma60 and ma20 > ma60 else "❌"
    ma20_str = f"MA20 ${ma20:.0f}"
    ma60_str = f"MA60 ${ma60:.0f}" if ma60 else "MA60 N/A"
    return f"{icon} [{d['symbol']}] {d['name']} ${d['price']:.2f} ({d['chg']:+.2f}%) RSI {d['rsi']:.1f} MACD {d['macd_hist']:+.2f} {rsi_ok} {ma_bull} [{d['score']:.0f}分]\n   {ma20_str} | {ma60_str}"

def analyze_filtered(cat, rsi_max, price_min, price_max, macd_req, ma_req):
    stocks = STOCKS.get(cat, ALL_STOCKS)
    cat_names = {
        "AI/科技": "AI/科技",
        "半導體設備": "半導體設備",
        "光通訊/CPO": "光通訊/CPO",
        "記憶體/儲存": "記憶體/儲存",
        "電力/散熱": "電力/散熱/基建",
        "先進封裝": "先進封裝",
        "雲端/資料": "雲端/資料中心",
        "消費/零售": "消費/零售",
        "金融": "金融",
        "醫療": "醫療",
        "工業/航太": "工業/航太",
        "--------": "--------",
        "S&P 500": "S&P 500 指數",
        "全市場": "全市場 ETF",
        "道瓊": "道瓊工業",
        "NASDAQ100": "NASDAQ 100",
        "半導體ETF": "半導體 ETF",
        "科技ETF": "科技 ETF",
        "股息ETF": "股息 ETF",
        "產業ETF": "產業 ETF",
        "債券ETF": "債券 ETF",
        "全部": "全部股票",
    }
    cat_name = cat_names.get(cat, cat)
    cond = f"RSI<{rsi_max}" + (f" 價格{price_min}~{price_max}" if price_min or price_max else "") + (" MACD>0" if macd_req else "") + (" MA多頭" if ma_req else "")
    lines = [f"📊 {cat_name} | {datetime.now().strftime('%H:%M:%S')}", f"條件：{cond}", ""]
    
    results = []
    for sym, name in stocks:
        d = analyze_stock(sym, name)
        if d:
            d['score'] = calc_score(d)
            if d['rsi'] > rsi_max: continue
            if price_min and d['price'] < float(price_min): continue
            if price_max and d['price'] > float(price_max): continue
            if macd_req and d['macd_hist'] <= 0: continue
            if ma_req and not (d['ma60'] and d['ma20'] > d['ma60']): continue
            results.append(d)
    
    results.sort(key=lambda x: x['score'], reverse=True)
    
    if not results:
        return "\n".join(lines) + "❌ 無符合條件的股票\n嘗試放寬篩選條件"
    
    lines.append(f"✅ {len(results)} 檔符合條件（依評分排序）")
    lines.append("")
    for d in results:
        lines.append(format_stock(d))
    
    return "\n".join(lines)

# GUI
root = tk.Tk()
root.title("Tina 即時分析工具 v6.0")
root.geometry("600x800")
root.resizable(True, True)

tk.Label(root, text="📊 Tina 即時分析工具 v6.0", font=("Arial", 16, "bold")).pack(pady=3)
tk.Label(root, text="S&P 500 覆蓋 | 分類篩選 | 價格篩選", font=("Arial", 10), fg="gray").pack()

# 輸入框
input_frame = tk.Frame(root)
input_frame.pack(pady=3)
entry = tk.Entry(input_frame, width=18, font=("Arial", 12))
entry.pack(side=tk.LEFT, padx=3)

def analyze_input():
    sym = entry.get().strip().upper()
    if not sym: return
    d = analyze_stock(sym)
    if d:
        d['score'] = calc_score(d)
        result.delete('1.0', tk.END)
        result.insert('1.0', format_stock(d))
    else:
        result.delete('1.0', tk.END)
        result.insert('1.0', f"❌ 無法分析 {sym}")

tk.Button(input_frame, text="查詢", font=("Arial", 10), command=analyze_input, bg="#2196F3", fg="white", width=5).pack(side=tk.LEFT)
entry.bind('<Return>', lambda e: analyze_input())

# 分類按鈕（股票）
cat_frame = tk.Frame(root)
cat_frame.pack(pady=2)
cat_selected = tk.StringVar(value="全部")

def select_cat(c):
    cat_selected.set(c)
    run_analysis()

for cat in ["AI/科技", "半導體設備", "光通訊/CPO", "記憶體/儲存", "雲端/資料"]:
    tk.Radiobutton(cat_frame, text=cat, variable=cat_selected, value=cat, font=("Arial", 8), command=lambda c=cat: select_cat(c)).pack(side=tk.LEFT, padx=2)

# 分類按鈕（ETF）
etf_frame = tk.Frame(root)
etf_frame.pack(pady=2)
for cat in ["--------", "S&P 500", "全市場", "道瓊", "NASDAQ100", "半導體ETF", "股息ETF", "產業ETF", "債券ETF"]:
    if cat == "--------":
        tk.Label(etf_frame, text="ETF:").pack(side=tk.LEFT, padx=5)
    else:
        tk.Radiobutton(etf_frame, text=cat, variable=cat_selected, value=cat, font=("Arial", 8), command=lambda c=cat: select_cat(c)).pack(side=tk.LEFT, padx=2)

# 全部按鈕
all_frame = tk.Frame(root)
all_frame.pack(pady=2)
tk.Radiobutton(all_frame, text="全部股票", variable=cat_selected, value="全部", font=("Arial", 9, "bold"), command=lambda: select_cat("全部")).pack(side=tk.LEFT, padx=10)

# 篩選條件
filter_frame = tk.LabelFrame(root, text="篩選條件", font=("Arial", 10, "bold"))
filter_frame.pack(pady=3, fill=tk.X, padx=20)

tk.Label(filter_frame, text="RSI <").pack(side=tk.LEFT, padx=2)
rsi_var = tk.StringVar(value="60")
tk.Entry(filter_frame, width=5, textvariable=rsi_var, font=("Arial", 10)).pack(side=tk.LEFT, padx=2)

tk.Label(filter_frame, text="價格").pack(side=tk.LEFT, padx=5)
price_min_var = tk.StringVar()
price_max_var = tk.StringVar()
tk.Entry(filter_frame, width=6, textvariable=price_min_var, font=("Arial", 10)).pack(side=tk.LEFT, padx=2)
tk.Label(filter_frame, text="~").pack(side=tk.LEFT)
tk.Entry(filter_frame, width=6, textvariable=price_max_var, font=("Arial", 10)).pack(side=tk.LEFT, padx=2)

macd_var = tk.BooleanVar(value=False)
tk.Checkbutton(filter_frame, text="MACD>0", variable=macd_var).pack(side=tk.LEFT, padx=5)
ma_var = tk.BooleanVar(value=False)
tk.Checkbutton(filter_frame, text="MA多頭", variable=ma_var).pack(side=tk.LEFT, padx=5)

def run_analysis():
    btn.config(state='disabled', text='分析中...')
    result.delete('1.0', tk.END)
    result.insert('1.0', '分析中，請稍候...\n')
    root.update()
    
    def run():
        text = analyze_filtered(
            cat_selected.get(), float(rsi_var.get()),
            price_min_var.get(), price_max_var.get(),
            macd_var.get(), ma_var.get()
        )
        result.delete('1.0', tk.END)
        result.insert('1.0', text)
        btn.config(state='normal', text='🔍 篩選')
    
    threading.Thread(target=run, daemon=True).start()

btn = tk.Button(filter_frame, text="🔍 篩選", font=("Arial", 10), command=run_analysis, bg="#FF9800", fg="white", width=10)
btn.pack(side=tk.LEFT, padx=10)

# 快捷
quick_frame = tk.LabelFrame(root, text="快捷", font=("Arial", 10))
quick_frame.pack(pady=3, fill=tk.X, padx=20)

def quick(sym):
    d = analyze_stock(sym)
    if d:
        d['score'] = calc_score(d)
        result.delete('1.0', tk.END)
        result.insert('1.0', format_stock(d))

for sym, name in [("META","Meta"),("NVDA","Nvidia"),("TSLA","Tesla"),("ASML","ASML"),("PLTR","Palantir")]:
    tk.Button(quick_frame, text=name, font=("Arial", 9), command=lambda s=sym: quick(s)).pack(side=tk.LEFT, padx=3, pady=3)

# 結果
result = scrolledtext.ScrolledText(root, width=70, height=25, font=("Consolas", 9))
result.pack(pady=5, fill=tk.BOTH, expand=True, padx=20)
result.insert('1.0', """📊 Tina 即時分析工具 v6.0
========================
S&P 500 覆蓋 | 分類篩選 | 價格篩選

【11個分類】
AI/科技 | 半導體設備 | 光通訊/CPO | 記憶體/儲存
電力/散熱 | 先進封裝 | 雲端/資料 | 消費/零售
金融 | 醫療 | 工業/航太 | 全部

【篩選條件】
RSI < 60（可調整）
價格區間
MACD>0 / MA多頭

【快捷】
META / NVDA / TSLA / ASML / PLTR""")

root.mainloop()