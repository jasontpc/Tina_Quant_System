import sqlite3, yfinance as yf, pandas as pd
from datetime import datetime
import time

# ── helpers ──────────────────────────────────────────────────────────
def compute_indicators(df):
    df = df.sort_values("Date").copy()
    close = df["Close"]
    # SMA 20/60
    df["SMA20"]  = close.rolling(20).mean()
    df["SMA60"]  = close.rolling(60).mean()
    # RSI
    delta = close.diff()
    gain  = delta.where(delta > 0, 0.0)
    loss  = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs  = avg_gain / avg_loss.replace(0, float("nan"))
    df["RSI"] = 100 - (100 / (1 + rs))
    # MACD
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    macd  = ema12 - ema26
    signal = macd.ewm(span=9).mean()
    df["MACD"]      = macd
    df["MACD_Signal"] = signal
    df["MACD_Hist"]   = macd - signal
    return df

def get_existing_symbols():
    conn = sqlite3.connect("data/yfinance.db")
    cur  = conn.cursor()
    cur.execute("SELECT symbol FROM daily_ohlcv")
    existing = {r[0] for r in cur.fetchall()}
    conn.close()
    return existing

def batch_insert(df):
    conn = sqlite3.connect("data/yfinance.db")
    cur  = conn.cursor()
    rows = []
    for _, row in df.iterrows():
        if pd.isna(row["Close"]) or row["Close"] == 0:
            continue
        rows.append((
            row["Date"].strftime("%Y-%m-%d") if hasattr(row["Date"], "strftime") else str(row["Date"])[:10],
            row["Open"], row["High"], row["Low"], row["Close"],
            int(row["Volume"]) if pd.notna(row["Volume"]) else 0,
            row.name   # symbol
        ))
    cur.executemany(
        "INSERT OR REPLACE INTO daily_ohlcv (Date,Open,High,Low,Close,Volume,symbol) VALUES (?,?,?,?,?,?,?)",
        rows
    )
    conn.commit()
    conn.close()
    return len(rows)

# ── main ──────────────────────────────────────────────────────────────
DB_PATH = "data/yfinance.db"

existing = get_existing_symbols()
print(f"Existing symbols in DB: {len(existing)}")

# ── US stocks / ETFs ─────────────────────────────────────────────────
us_stocks = [
    "BA","CAT","GE","HON","UPS","BDX","AMGN","GILD","VRTX","REGN",
    "MRK","PFE","JNJ","ABT","UNH","LLY","ABBV","ISRG","MDT","SYK",
    "ZTS","BSX","EW","A","TMO","DHR","CI"
]
etfs = [
    "QQQQ","SPXL","SPXS","TQQQ","SOXL","LABU","LABD","YANG","SOXS","DUST","NUGT","JDST"
]
# Already in DB (per task): AAPL,MSFT,NVDA,AMD,GOOGL,AMZN,META,TSLA,NFLX,QQQ,SPY,IWM,VTI

us_new = [s for s in us_stocks + etfs if s not in existing]
print(f"US symbols to add: {len(us_new)} → {us_new[:10]}...")

added_us = 0
for i in range(0, len(us_new), 20):
    batch = us_new[i:i+20]
    print(f"  US batch {i//20+1}: {batch}")
    try:
        data = yf.download(batch, period="max", auto_adjust=True, progress=False)
        if data.empty:
            print("  → empty, skipping")
            time.sleep(2)
            continue
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.droplevel(1)
        data = data.reset_index()
        if "Date" not in data.columns and "Datetime" in data.columns:
            data.rename(columns={"Datetime":"Date"}, inplace=True)
        if "Date" not in data.columns and "Timestamp" in data.columns:
            data.rename(columns={"Timestamp":"Date"}, inplace=True)
        n = batch_insert(data)
        added_us += n
        print(f"  → inserted {n} rows")
    except Exception as e:
        print(f"  → ERROR: {e}")
    time.sleep(3)

# ── TW stocks (1101-9999) ─────────────────────────────────────────────
tw_new = []
for code in range(1101, 10000):
    s = f"{code}.TW"
    if s not in existing:
        tw_new.append(s)

print(f"TW symbols to try: {len(tw_new)}")
# Try in batches of 30
added_tw = 0
for i in range(0, len(tw_new), 30):
    batch = tw_new[i:i+30]
    print(f"  TW batch {i//30+1} (~{i//30*30+1}-{min(i//30*30+30,len(tw_new))}): {batch[:5]}...")
    try:
        data = yf.download(batch, period="5y", auto_adjust=True, progress=False)
        if data.empty:
            time.sleep(2)
            continue
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.droplevel(1)
        data = data.reset_index()
        if "Date" not in data.columns and "Datetime" in data.columns:
            data.rename(columns={"Datetime":"Date"}, inplace=True)
        n = batch_insert(data)
        added_tw += n
        print(f"  → inserted {n} rows")
    except Exception as e:
        print(f"  → ERROR: {e}")
    time.sleep(3)

# ── final stats ──────────────────────────────────────────────────────
conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()
cur.execute("SELECT COUNT(DISTINCT symbol) FROM daily_ohlcv")
syms = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM daily_ohlcv")
rows  = cur.fetchone()[0]
conn.close()

print(f"\n=== DONE ===")
print(f"Symbols: {syms}")
print(f"Rows:    {rows}")
