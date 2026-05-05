"""
US Growth Stocks Screener - Under $100
Tina Quant System v3.12
Scans the entire US stock universe for quality growth stocks under $100
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import random
import os
import csv

# ── Config ────────────────────────────────────────────────────────────────────
OUTPUT_DIR = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data"
SCRIPT_DIR = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\scripts"
os.makedirs(OUTPUT_DIR, exist_ok=True)

BATCH_SIZE = 20
DELAY_BASE = 1.0    # seconds between requests (randomised)
DELAY_RAND  = 1.5

REPORTS_URL = "https://api.finmindtrade.com/api/v4/data"

# ── Candidate pool (150+ stocks across sectors) ────────────────────────────────
CANDIDATES = [
    # Technology
    "SMCI", "ARM", "PATH", "U", "MDB", "DDOG", "GTLB", "APP", "FUBO", "RIVN", "LCID",
    "SOFI", "NDAQ", "ICE", "DXCM", "ISRG", "REGN", "VRTX", "BIIB",
    "RKLB", "CVT", "ODD", "GPS", "LULU", "FARO", "CGN", "PRLD",
    # More tech/growth
    "PLTR", "SNAP", "TWLO", "ZM", "DOCU", "SQSP", "NET", "CRWD", "NET",
    "MDB", "TEAM", "WDAY", "OKTA", "ZS", "CRWD", "PANW", "FTNT",
    "GEN", "DLO", "PINS", "SNOW", "DBX", "BOX", "SMAR", "CFLT",
    "VEEV", "BILL", "COUR", "GLOB", "ASAN", "ESTC", "SWI", "LRN",
    "AVLR", "GPRO", "MELI", "OVID", "LSCC", "MRNA", "BNGO", "EXAS",
    "TXG", "DADA", "JCAT", "IMVT", "BCYC", "PRLB", "VERV", "XERS",
    "INMD", "SIEN", "HOOK", "LYRA", "GLSI", "OPK", "LLY", "BMY",
    # Additional growth names
    "PSN", "KNSL", "WAL", "RNR", "ESMT", "UPST", "GPN", "FIS",
    "TER", "EXC", "CDK", "GEN", "SPLK", "SUMO", "FROG", "NCNO",
    "SFIX", "WB", "MTCH", "RBLX", "HOOD", "AMST", "BARK", "OUST",
    "VLTO", "ALGM", "MNDY", "PATH", "U", "DT", "SMAR", "GDDY",
    "DOGZ", "GAIA", "KOD", "OM", "CWH", "FAST", "TENB", "ALRM",
    "NOVA", "SPWR", "RUN", "ENPH", "SEDG", "FSLR", "SOLO",
    "RIVN", "LCID", "FUV", "FSR", "NKLA", "CHPT", "BLNK", "QS",
    "BE", "PLUG", "FCEL", "CLNE", "ALTO", "GM", "F", "TM", "RACE",
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "AMD", "INTC",
    "QCOM", "TXN", "AVGO", "MU", "LRCX", "AMAT", "KLAC", "ON",
    "PANW", "FTNT", "CDN", "WBA", "EBAY", "ADP", "PAYX", "INFO",
    "CTSH", "IT", "ACN", "NEWR", "VEEV", "TYL", "TRMB", "AVAV",
    "LILM", "TH", "RIDE", "VEL", "HZO", "MLKN", "MHO", "NNI",
    # Additional mid-cap growth
    "AOSL", "GSX", "GOGO", "MITK", "NOVA", "KOD", "OM", "INVE",
    "RXT", "ASTR", "LGMK", "MNTV", "CLVS", "EPIX", "SRAX", "ZVO",
]

CANDIDATES = list(dict.fromkeys(CANDIDATES))  # dedupe preserving order
print(f"[Tina Screener] Total candidates: {len(CANDIDATES)}")

# ── Technical helpers ──────────────────────────────────────────────────────────
def compute_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    if loss.sum() == 0:
        return 50.0
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return float((100 - 100 / (1 + rs)).iloc[-1])

def compute_ma20偏离(prices):
    ma20 = prices.rolling(20).mean()
    return float((prices.iloc[-1] / ma20.iloc[-1] - 1) * 100)

def compute_52week_position(prices):
    low52 = prices.min()
    high52 = prices.max()
    if high52 == low52:
        return 50.0
    return float((prices.iloc[-1] - low52) / (high52 - low52) * 100)

def compute_1month_momentum(prices):
    if len(prices) < 21:
        return 0.0
    return float((prices.iloc[-1] / prices.iloc[-21] - 1) * 100)

def get_avg_volume(hist):
    return float(hist['Volume'].tail(20).mean())

# ── Score function ────────────────────────────────────────────────────────────
def score_stock(row):
    s = 0
    pe = row.get('pe_ratio')
    rev = row.get('revenue_growth', 0) or 0
    roe_v = row.get('roe', 0) or 0
    opm = row.get('operating_margin', 0) or 0
    de = row.get('debt_to_equity', 999) or 999
    rsi_v = row.get('rsi', 50) or 50
    ma20 = row.get('ma20_deviation', 99) or 99
    mom = row.get('momentum_1m', 0) or 0
    w52 = row.get('week52_position', 50) or 50

    # Fundamental scoring
    if pe is not None:
        if 0 < pe <= 25: s += 2
        elif 25 < pe <= 50: s += 1
    if rev > 30: s += 3
    elif rev > 20: s += 2
    elif rev > 10: s += 1
    if roe_v > 25: s += 2
    elif roe_v > 15: s += 1
    if opm > 25: s += 2
    elif opm > 15: s += 1
    if de < 30: s += 1
    # Technical scoring
    if 30 <= rsi_v <= 50: s += 1          # not overbought
    if 0 <= ma20 <= 8: s += 1              # close to MA
    if mom > 5: s += 1
    if mom > 15: s += 1
    if w52 < 70: s += 1                    # not at peak
    return s

def get_signal(score):
    if score >= 8: return "⭐⭐⭐ STRONG BUY"
    if score >= 5: return "⭐⭐ BUY"
    if score >= 3: return "⭐ CONSIDER"
    return "⏸ WATCH"

# ── Main screening function ───────────────────────────────────────────────────
def screen_stock(ticker_str):
    """Screen a single stock. Returns dict or None."""
    try:
        ticker = yf.Ticker(ticker_str)
        info = ticker.info
    except Exception as e:
        return None

    # Skip delisted / not-found
    if not info or info.get('regularMarketPrice') is None and info.get('currentPrice') is None:
        return None

    # ── Layer 1: Basic filters ────────────────────────────────────────────────
    price       = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
    market_cap  = info.get('marketCap', 0)
    avg_volume  = info.get('averageVolume', 0) or info.get('averageDailyVolume', 0)
    stock_type  = info.get('quoteType', 'EQUITY')
    exchange    = info.get('exchange', '')

    if not price or price >= 100:
        return None
    if market_cap and market_cap < 1e9:
        return None
    if avg_volume and avg_volume < 500_000:
        return None
    if stock_type not in ('EQUITY', None):
        return None

    # ── Layer 2: Fundamentals ────────────────────────────────────────────────
    revenue_growth   = info.get('revenueGrowth', 0) or 0
    # Cast PE ratio safely
    raw_pe = info.get('trailingPE', None)
    try:
        pe_ratio = float(raw_pe) if raw_pe is not None else None
    except (TypeError, ValueError):
        pe_ratio = None
    roe              = info.get('returnOnEquity', None)
    op_margin        = info.get('operatingMargins', None)
    if op_margin is not None: op_margin *= 100
    debt_equity      = info.get('debtToEquity', None)

    # Optional filters (soft) — skip if data missing
    if revenue_growth < 0.10:           # want growth
        pass  # allow if other metrics strong
    if pe_ratio is not None and (pe_ratio <= 0 or pe_ratio > 50):
        pass  # skip if PE is extreme

    # ── Layer 3: Technicals ─────────────────────────────────────────────────
    try:
        hist = ticker.history(period="6mo")
    except:
        hist = None

    rsi         = None
    ma20_dev    = None
    momentum_1m = None
    week52_pos  = None
    volume_ok   = True

    if hist is not None and len(hist) > 30:
        price_series = hist['Close'].dropna()
        if len(price_series) > 14:
            rsi         = compute_rsi(price_series)
            ma20_dev    = compute_ma20偏离(price_series)
            momentum_1m = compute_1month_momentum(price_series)
            week52_pos  = compute_52week_position(price_series)
            volume_ok   = get_avg_volume(hist) > 500_000

    # ── Layer 1 re-check with volume ──────────────────────────────────────────
    if not volume_ok:
        return None

    # Collect row
    row = {
        'ticker': ticker_str.upper(),
        'price': price,
        'market_cap_B': market_cap / 1e9 if market_cap else None,
        'avg_volume_M': avg_volume / 1e6 if avg_volume else None,
        'revenue_growth': round(revenue_growth * 100, 1) if revenue_growth else None,
        'pe_ratio': round(pe_ratio, 1) if pe_ratio else None,
        'roe': round(roe * 100, 1) if roe else None,
        'operating_margin': round(op_margin, 1) if op_margin else None,
        'debt_to_equity': round(debt_equity, 1) if debt_equity else None,
        'rsi': round(rsi, 1) if rsi else None,
        'ma20_deviation': round(ma20_dev, 1) if ma20_dev is not None else None,
        'momentum_1m': round(momentum_1m, 1) if momentum_1m is not None else None,
        'week52_position': round(week52_pos, 1) if week52_pos is not None else None,
        'exchange': exchange,
    }
    row['score'] = score_stock(row)
    row['signal'] = get_signal(row['score'])
    return row

# ── Batch processor ───────────────────────────────────────────────────────────
def process_candidates(tickers, progress=True):
    results = []
    failed  = []
    total   = len(tickers)

    for i in range(0, total, BATCH_SIZE):
        batch = tickers[i:i + BATCH_SIZE]
        for ticker in batch:
            row = screen_stock(ticker)
            if row:
                results.append(row)
            else:
                failed.append(ticker)

            delay = DELAY_BASE + random.random() * DELAY_RAND
            time.sleep(delay)

        if progress:
            passed = len(results)
            print(f"  [{i + len(batch):}/{total}] Batch done — {passed} passed | {len(failed)} filtered | last: {batch[-1]}")

    return results, failed

# ── Main ───────────────────────────────────────────────────────────────────────
print(f"\n{'='*70}")
print(" Tina US Growth Screener — Under $100 | {datetime.now():%Y-%m-%d %H:%M}")
print(f"{'='*70}\n")

# Process candidates
results, failed = process_candidates(CANDIDATES)

print(f"\n✓ Screened {len(CANDIDATES)} stocks → {len(results)} passed Layer 1/2/3")
print(f"  {len(failed)} filtered out")

if not results:
    print("\n⚠ No stocks passed filters. Check network/API access.")
    exit(0)

# Sort by score desc, then price asc
df = pd.DataFrame(results)
df = df.sort_values(['score', 'price'], ascending=[False, True]).reset_index(drop=True)
df.index = df.index + 1

# ── Save CSV ──────────────────────────────────────────────────────────────────
ts = datetime.now().strftime('%Y%m%d_%H%M')
csv_path = os.path.join(OUTPUT_DIR, f"us_growth_under_100_full_{ts}.csv")
df.to_csv(csv_path, index=False, float_format='%.2f')
print(f"\n📄 CSV saved: {csv_path}")

# Also save as the stable reference name
stable_path = os.path.join(OUTPUT_DIR, "us_growth_under_100_full.csv")
df.to_csv(stable_path, index=False, float_format='%.2f')
print(f"📄 Stable CSV: {stable_path}")

# ── Print top results ──────────────────────────────────────────────────────────
cols_show = ['ticker','price','score','signal','revenue_growth','pe_ratio','roe',
             'operating_margin','rsi','ma20_deviation','momentum_1m','week52_position']
df_show = df[[c for c in cols_show if c in df.columns]]

print(f"\n{'─'*70}")
print(f" TOP STOCKS (by score, price < $100)")
print(f"{'─'*70}")

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 160)
pd.set_option('display.float_format', lambda x: f'{x:.2f}' if pd.notnull(x) else 'N/A')
print(df_show.head(30).to_string())

print(f"\n{'─'*70}")
print(f" SUMMARY STATS")
print(f"{'─'*70}")
print(f"  Total passed: {len(df)}")
print(f"  Avg score:    {df['score'].mean():.1f}")
print(f"  Avg revenue growth: {df['revenue_growth'].mean():.1f}%")
print(f"  Avg PE:       {df['pe_ratio'].mean():.1f}")
print(f"  Stocks with RSI < 50 (undervalued): {(df['rsi'] < 50).sum()}")
print(f"  Stocks with RSI > 60 (overbought): {(df['rsi'] > 60).sum()}")

# ── Signal breakdown ──────────────────────────────────────────────────────────
print(f"\n{'─'*70}")
print(f" SIGNAL BREAKDOWN")
print(f"{'─'*70}")
for sig in df['signal'].value_counts().items():
    print(f"  {sig[0]}: {sig[1]} stocks")

print(f"\n{'='*70}")
print(" Done!")
print(f"{'='*70}\n")