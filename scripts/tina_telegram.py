# -*- coding: utf-8 -*-
"""
Tina 即時分析工具 v4.0 - 分類篩選版
====================================
- 依評分排序
- 半導體/AI/光通訊 分類篩選
"""
import yfinance as yf
import numpy as np
import sys
from datetime import datetime

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

# 分類股票
STOCKS = {
    "半導體": [
        ("NVDA","Nvidia"),("AVGO","Broadcom"),("AMD","AMD"),
        ("ASML","ASML"),("LRCX","Lam Res"),("AMAT","Applied Mat"),
        ("MU","Micron"),("INTC","Intel"),("QCOM","Qualcomm"),
        ("TXN","Texas Ins"),("SNPS","Synopsys"),
    ],
    "AI": [
        ("MSFT","Microsoft"),("META","Meta"),("GOOGL","Google"),
        ("AMZN","Amazon"),("PLTR","Palantir"),("COIN","Coinbase"),
        ("MSTR","MicroStrategy"),
    ],
    "光通訊": [
        ("LRCX","Lam Res"),("AMAT","Applied Mat"),("ANET","Arista"),
        ("JBL","Jabil"),("FFIV","F5 Inc"),("ZBRA","Zebra"),
    ],
    "完整": [
        ("NVDA","Nvidia"),("AVGO","Broadcom"),("AMD","AMD"),
        ("ASML","ASML"),("LRCX","Lam Res"),("AMAT","Applied Mat"),
        ("MU","Micron"),("INTC","Intel"),("QCOM","Qualcomm"),
        ("MSFT","Microsoft"),("META","Meta"),("GOOGL","Google"),
        ("AMZN","Amazon"),("PLTR","Palantir"),("TSLA","Tesla"),
        ("AAPL","Apple"),("NFLX","Netflix"),("IBM","IBM"),
        ("ORCL","Oracle"),("CRM","Salesforce"),("COIN","Coinbase"),
        ("MSTR","MicroStrategy"),("TXN","Texas Ins"),("SNPS","Synopsys"),
        ("ANET","Arista"),
    ],
}

def get_tier(rsi):
    if rsi < 35: return "A"
    if rsi < 50: return "B"
    if rsi < 70: return "C"
    return "D"

def format_stock(d, show_score=True):
    tier = get_tier(d['rsi'])
    icon = {"A":"🥇","B":"🥈","C":"🥉","D":"❌"}.get(tier,"?")
    rsi_ok = "✅" if d['macd_hist'] > 0 and tier in "ABC" else "⏸️"
    score_str = f" [{d['score']:.0f}分]" if show_score and 'score' in d else ""
    ma20_str = f"MA20 ${d['ma20']:.0f}"
    ma60_str = f"MA60 ${d['ma60']:.0f}" if d['ma60'] else "MA60 N/A"
    return f"{icon} [{d['symbol']}] {d['name']} ${d['price']:.2f} ({d['chg']:+.2f}%) RSI {d['rsi']:.1f} MACD {d['macd_hist']:+.2f} {rsi_ok}{score_str}\n   {ma20_str} | {ma60_str}"

def analyze_category(cat="完整", rsi_max=60, macd_req=False):
    stocks = STOCKS.get(cat, STOCKS["完整"])
    lines = [
        f"📊 {cat} 股分析 | {datetime.now().strftime('%H:%M:%S')}",
        f"   RSI < {rsi_max}" + (" | MACD>0" if macd_req else ""),
        ""
    ]
    
    results = []
    for sym, name in stocks:
        d = analyze_stock(sym, name)
        if d:
            d['score'] = calc_score(d)
            # 篩選
            if d['rsi'] > rsi_max: continue
            if macd_req and d['macd_hist'] <= 0: continue
            results.append(d)
    
    if not results:
        lines.append("❌ 無符合條件的股票")
        return "\n".join(lines)
    
    results.sort(key=lambda x: x['score'], reverse=True)
    
    lines.append(f"✅ {len(results)} 檔符合條件（依評分排序）")
    lines.append("")
    for d in results:
        lines.append(format_stock(d))
    
    return "\n".join(lines)

def analyze_all(rsi_max=60, macd_req=False):
    """分析所有分類"""
    lines = [
        f"📊 美股全面分析 | {datetime.now().strftime('%H:%M:%S')}",
        f"   RSI < {rsi_max}" + (" | MACD>0" if macd_req else ""),
        ""
    ]
    
    all_results = []
    for cat, stocks in STOCKS.items():
        if cat == "完整": continue
        for sym, name in stocks:
            d = analyze_stock(sym, name)
            if d:
                d['category'] = cat
                d['score'] = calc_score(d)
                if d['rsi'] <= rsi_max and (not macd_req or d['macd_hist'] > 0):
                    all_results.append(d)
    
    if not all_results:
        lines.append("❌ 無符合條件的股票")
        return "\n".join(lines)
    
    all_results.sort(key=lambda x: x['score'], reverse=True)
    
    lines.append(f"✅ {len(all_results)} 檔符合條件（依評分排序）")
    lines.append("")
    
    # 按分類顯示
    for cat in ["半導體", "AI", "光通訊"]:
        cat_results = [d for d in all_results if d.get('category') == cat]
        if cat_results:
            lines.append(f"【{cat}】({len(cat_results)}檔)")
            for d in cat_results:
                lines.append(format_stock(d))
            lines.append("")
    
    return "\n".join(lines)

def analyze_us_market():
    """美股市場概況"""
    lines = [f"📊 美股即時分析 | {datetime.now().strftime('%H:%M:%S')}", ""]
    
    lines.append("【指數】")
    for sym, name in [("^DJI","道瓊"),("^IXIC","Nasdaq"),("^GSPC","S&P 500"),("^VIX","VIX")]:
        d = analyze_stock(sym, name)
        if d:
            status = "🔴" if d['rsi'] > 70 else ("⚠️" if d['rsi'] > 60 else "✅")
            lines.append(f"{status} {name}: {d['price']:,.2f} ({d['chg']:+.2f}%) RSI {d['rsi']:.1f}")
    
    lines.append("")
    lines.append("【評分排序 Top 10】")
    
    all_stocks = STOCKS["完整"]
    results = []
    for sym, name in all_stocks:
        d = analyze_stock(sym, name)
        if d:
            d['score'] = calc_score(d)
            results.append(d)
    
    results.sort(key=lambda x: x['score'], reverse=True)
    
    for d in results[:10]:
        lines.append(format_stock(d))
    
    return "\n".join(lines)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print("  python tina_telegram.py --us          美股市場概況")
        print("  python tina_telegram.py --semi        半導體股")
        print("  python tina_telegram.py --ai          AI股")
        print("  python tina_telegram.py --optical     光通訊")
        print("  python tina_telegram.py --all         全面分析（所有分類）")
        print("  python tina_telegram.py --score       評分排序（RSI<60）")
        print("  python tina_telegram.py META          單一股票")
    else:
        arg = sys.argv[1].upper()
        if arg == "--US":
            print(analyze_us_market())
        elif arg == "--SEMI":
            print(analyze_category("半導體"))
        elif arg == "--AI":
            print(analyze_category("AI"))
        elif arg == "--OPTICAL":
            print(analyze_category("光通訊"))
        elif arg == "--ALL":
            print(analyze_all())
        elif arg == "--SCORE":
            print(analyze_us_market())
        elif arg.startswith("--"):
            print(f"未知參數: {arg}")
        else:
            d = analyze_stock(arg)
            if d:
                d['score'] = calc_score(d)
                print(format_stock(d, True))
            else:
                print(f"❌ 無法分析 {arg}")