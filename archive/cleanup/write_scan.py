"""Generate vegas_scan.py with fixed fetchers"""
import os

content = r'''"""
Vegas Tunnel Scanner - Full Market Edition
TWSE 500: FinMind (primary) + yfinance (fallback)
US: S&P500 + NASDAQ100 + SOX30 via yfinance (live)

Run: python vegas_scan.py
"""

import sys, os
sys.path.insert(0, r"C:\Users\USER\AppData\Local\Programs\Python\Python312\Lib\site-packages")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import yfinance as yf
from FinMind.data import DataLoader
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings, ssl, json, urllib.request, re, requests
from io import StringIO
warnings.filterwarnings("ignore")

MIN_SCORE = 3
BACKTEST_DAYS = 700
WIKI_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# ========================
# Stock List Loaders
# ========================
def fetch_twse_list():
    """Get TWSE listed stock codes (4-6 digit common stocks, filter out ETFs/warrants)"""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    headers = {"User-Agent": "Mozilla/5.0"}
    url = "https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date=&type=ALL&response=json"
    try:
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req, context=ctx, timeout=10)
        raw = json.loads(resp.read())
        text = json.dumps(raw, ensure_ascii=False)
        found = re.findall(r'"(\d{4,6})"', text)
        codes = sorted(set([c for c in found if 1000 <= int(c) <= 99999]))
        # Filter: remove ETF/TDR/beneficiary codes (commonly start with 00, 02, 03, 04, 05, 06, 07, 08, 09 in first 2 digits for special securities)
        # Keep only ordinary stocks (first digit 1-9, excluding known ETF/tDR codes)
        exclude_prefixes = ["00", "02", "03", "04", "05", "06", "07", "08", "09", "11", "12", "13", "14", "15", "16", "17", "18", "19"]
        filtered = [c for c in codes if c[:2] not in exclude_prefixes]
        result = filtered[:600]
        print(f"  TWSE stocks: {len(result)} (from {len(codes)} total codes)")
        return result
    except Exception as e:
        print(f"  TWSE fetch failed: {e}")
        return []

def fetch_sp500():
    """Fetch S&P 500 components from Wikipedia"""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    try:
        r = requests.get(url, headers=WIKI_HEADERS, timeout=10)
        tables = pd.read_html(StringIO(r.text))
        syms = [str(s).replace(".", "-") for s in tables[0]["Symbol"].dropna()]
        print(f"  S&P500: {len(syms)} stocks")
        return syms
    except Exception as e:
        print(f"  S&P500 fetch failed: {e}")
        return []

def fetch_nasdaq100():
    """Fetch NASDAQ-100 components from Wikipedia"""
    url = "https://en.wikipedia.org/wiki/NASDAQ-100"
    try:
        r = requests.get(url, headers=WIKI_HEADERS, timeout=10)
        tables = pd.read_html(StringIO(r.text))
        # Usually the 4th or 5th table has the component tickers
        for t in tables:
            cols = list(t.columns)
            if "Ticker" in cols or "Symbol" in cols:
                col = "Ticker" if "Ticker" in cols else "Symbol"
                syms = [str(s).replace(".", "-") for s in t[col].dropna()]
                print(f"  NASDAQ100: {len(syms)} stocks")
                return syms
        return []
    except Exception as e:
        print(f"  NASDAQ100 fetch failed: {e}")
        return []

SOX30 = [
    "NVDA","AMD","INTC","AMAT","LRCX","MU","MCHP","QRVO","QCOM",
    "AVGO","TXN","ADI","SWKS","CRUS","MPWR","ON","NXPI","GFS",
    "ENTG","KLAC","TER","ALAB","LTHM","VSH","DIOD","AXTI",
    "FORM","SNPS","CDNS","ASML"
]

# ========================
# Vegas Signal
# ========================
def vegas_signal(close, volume):
    if len(close) < 200: return None

    ema12  = close.ewm(span=12,  adjust=False).mean()
    ema144 = close.ewm(span=144, adjust=False).mean()
    ema169 = close.ewm(span=169, adjust=False).mean()
    ema576 = close.ewm(span=576, adjust=False).mean()
    ema676 = close.ewm(span=676, adjust=False).mean()

    c    = close.iloc[-1]
    c1   = close.iloc[-2] if len(close)>1 else c
    e12  = ema12.iloc[-1]
    e144 = ema144.iloc[-1]
    e169 = ema169.iloc[-1]
    e576 = ema576.iloc[-1]
    e676 = ema676.iloc[-1]
    v    = volume.iloc[-1]
    e12_1  = ema12.iloc[-2]  if len(ema12)  > 1 else e12
    e144_1 = ema144.iloc[-2] if len(ema144) > 1 else e144

    tunnel_bull = (e144 > e169) and (e144 > e144_1) and (e169 > ema169.iloc[-2])
    bigtrend_bull = (c > e576) and (c > e676) and (e576 > e676) and (e576 > ema576.iloc[-2])

    price_breakout_up = (c > e144) and (c > e169) and (c1 <= e144)
    ema12_confirm_up  = (e12 > e144) and (e12 > e169) and (e12_1 <= e144)
    false_breakout    = price_breakout_up and not ema12_confirm_up

    delta = close.diff()
    gain  = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss  = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rsi14 = (100 - (100/(1 + gain/loss))).iloc[-1]

    score = 0
    if tunnel_bull:    score += 1
    if bigtrend_bull:  score += 1
    if price_breakout_up and ema12_confirm_up and not false_breakout: score += 2
    if rsi14 < 80:     score += 1
    score = min(score, 5)

    tunnel_width = (e144 - e169) / e169 * 100 if e169 != 0 else 0

    if price_breakout_up and ema12_confirm_up and tunnel_bull and bigtrend_bull and not false_breakout:
        trend, breakout = "BULL", True
    elif tunnel_bull and bigtrend_bull:
        trend, breakout = "BULL_LAGGING", False
    else:
        trend, breakout = "NEUTRAL", False

    return dict(
        close=c, ema12=e12, ema144=e144, ema169=e169,
        ema576=e576, ema676=e676, tunnel_width=tunnel_width,
        rsi14=float(rsi14), score=score, breakout=breakout,
        trend=trend, volume=int(v)
    )

# ========================
# Scan: TWSE via FinMind
# ========================
def scan_twse_finmind(codes):
    dl = DataLoader()
    results = []
    end   = datetime.today().strftime("%Y-%m-%d")
    start = (datetime.today() - timedelta(days=BACKTEST_DAYS)).strftime("%Y-%m-%d")
    total = len(codes)

    for i, code in enumerate(codes):
        if (i+1) % 50 == 0 or (i+1) == total:
            print(f"  TWSE {i+1}/{total} ({(i+1)*100//total}%)")
        try:
            df = dl.taiwan_stock_daily(stock_id=code, start_date=start, end_date=end)
        except:
            continue
        if df is None or len(df) < 200: continue

        df = df.rename(columns={"open":"open","max":"high","min":"low","close":"close","Trading_Volume":"volume"})
        df = df[["date","open","high","low","close","volume"]].sort_values("date").reset_index(drop=True)

        sig = vegas_signal(df["close"], df["volume"])
        if sig and sig["score"] >= MIN_SCORE:
            sig["stock_id"] = code
            sig["market"] = "TWSE"
            results.append(sig)

    return results

# ========================
# Scan: US via yfinance
# ========================
def scan_us_yfinance(tickers, market_label):
    results = []
    total = len(tickers)

    for i, t in enumerate(tickers):
        if (i+1) % 50 == 0 or (i+1) == total:
            print(f"  {market_label} {i+1}/{total} ({(i+1)*100//total}%)")
        try:
            tk = yf.Ticker(t)
            h = tk.history(period="2y", auto_adjust=True)
            if h is None or len(h) < 200: continue
            sig = vegas_signal(h["Close"], h["Volume"])
            if sig and sig["score"] >= MIN_SCORE:
                sig["stock_id"] = t
                sig["market"] = market_label
                results.append(sig)
        except:
            pass
    return results

# ========================
# Report
# ========================
def print_report(results_by_market):
    for market, results in results_by_market.items():
        if not results: continue
        results.sort(key=lambda x: (x["score"], x["breakout"]), reverse=True)
        print(f"\n{'='*90}")
        print(f"{market} Vegas Signals ({len(results)} stocks)")
        print(f"{'='*90}")
        hdr = f"{'Ticker':<10}{'Close':<10}{'EMA12':<10}{'Tunnel(144)':<14}{'Tunnel(169)':<14}{'RSI':<8}{'Score':<7}{'Signal'}"
        print(hdr)
        print("-"*90)
        for r in results:
            tag = "BREAKOUT" if r["breakout"] else ("BULL_LAG" if r["trend"]=="BULL_LAGGING" else "")
            print(f"{r['stock_id']:<10}{r['close']:<10.2f}{r['ema12']:<10.2f}{r['ema144']:<14.2f}{r['ema169']:<14.2f}{r['rsi14']:<8.1f}{r['score']:<7}{tag}")

        breakouts = [x for x in results if x["breakout"]]
        if breakouts:
            print(f"\n  *** BREAKOUT ({len(breakouts)} stocks) ***")
            for r in breakouts:
                print(f"  -> {r['stock_id']} | Price:{r['close']} | EMA12:{r['ema12']} | Tunnel:{r['ema144']:.2f}-{r['ema169']:.2f} | RSI:{r['rsi14']} | Score:{r['score']}/5")

def save_csv(results_by_market):
    rows = []
    for market, results in results_by_market.items():
        for r in results:
            r2 = dict(r)
            r2["market"] = market
            rows.append(r2)
    if rows:
        df = pd.DataFrame(rows)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = f"vegas_results_{ts}.csv"
        df.to_csv(fname, index=False, encoding="utf-8-sig")
        print(f"Saved: {fname}")

# ========================
# Main
# ========================
if __name__ == "__main__":
    print("="*60)
    print("Vegas Tunnel Scanner | Full Market Edition")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    results_by_market = {}

    # Fetch lists
    print("\n[FETCH] Loading stock lists...")
    twse_codes = fetch_twse_list()
    sp500      = fetch_sp500()
    nasdaq100   = fetch_nasdaq100()
    sox30       = SOX30

    # TWSE scan
    print(f"\n[SCAN] TWSE ({len(twse_codes)} stocks via FinMind)...")
    twse_results = scan_twse_finmind(twse_codes)
    results_by_market["TWSE"] = twse_results
    print(f"  -> {len(twse_results)} matches (score>={MIN_SCORE})")

    # US scans (skip if list empty)
    if sp500:
        print(f"\n[SCAN] S&P500 ({len(sp500)} stocks via yfinance)...")
        sp_results = scan_us_yfinance(sp500, "SP500")
        results_by_market["SP500"] = sp_results
        print(f"  -> {len(sp_results)} matches")

    if nasdaq100:
        print(f"\n[SCAN] NASDAQ100 ({len(nasdaq100)} stocks via yfinance)...")
        ndq_results = scan_us_yfinance(nasdaq100, "NASDAQ100")
        results_by_market["NASDAQ100"] = ndq_results
        print(f"  -> {len(ndq_results)} matches")

    print(f"\n[SCAN] SOX30 ({len(sox30)} stocks via yfinance)...")
    sox_results = scan_us_yfinance(sox30, "SOX30")
    results_by_market["SOX30"] = sox_results
    print(f"  -> {len(sox_results)} matches")

    print_report(results_by_market)
    save_csv(results_by_market)

    total = sum(len(v) for v in results_by_market.values())
    print(f"\nTotal matches: {total}")
    print("Done.")
'''

with open(r"C:\Users\USER\.openclaw\agents\ray\vegas_scan.py", "w", encoding="utf-8") as f:
    f.write(content)
print("vegas_scan.py written OK")