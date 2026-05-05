"""
Robust yfinance DB expander - downloads one ticker at a time to avoid rate limits.
"""
import yfinance as yf
import sqlite3
from pathlib import Path
import time
import sys

DB = Path('C:/Users/USER/.openclaw/workspace/Tina_Quant_System/data/yfinance.db')
INSERT_BATCH = 100  # commit every N inserts

conn = sqlite3.connect(str(DB))
cur = conn.cursor()

# Get existing symbols
cur.execute("SELECT DISTINCT symbol FROM daily_ohlcv")
existing = set(r[0] for r in cur.fetchall())
print(f"Existing: {len(existing)}")

INSERTED_TOTAL = 0

def insert_ticker(sym, df):
    global INSERTED_TOTAL
    if df is None or df.empty:
        return 0
    cnt = 0
    for _, row in df.iterrows():
        try:
            adj = row.get('Adj Close') or row.get('Close')
            cur.execute("""INSERT OR REPLACE INTO daily_ohlcv
                (symbol, date, open, high, low, close, volume, adj_close,
                 change_pct, sma_20, sma_60, sma_120, rsi_14, atr_14,
                 macd, macd_sig, macd_hist, bb_upper, bb_middle, bb_lower, vol_ratio)
                VALUES (?,?,?,?,?,?,?,?,
                        NULL, NULL, NULL, NULL, NULL, NULL,
                        NULL, NULL, NULL, NULL, NULL, NULL, NULL)""",
                (sym,
                 str(row.name.date()) if hasattr(row.name, 'date') else str(row.name)[:10],
                 float(row['Open']), float(row['High']), float(row['Low']),
                 float(row['Close']), int(row['Volume']), float(adj)))
            cnt += 1
        except Exception as e:
            pass
    conn.commit()
    INSERTED_TOTAL += cnt
    return cnt

# ── TW stocks ───────────────────────────────────────────────────────────────
tw_etfs  = [f"{i:04d}.TW" for i in range(50, 100)]
tw_4dig  = [f"{i}.TW" for i in range(1101, 10000)]
tw_to_add = [s for s in tw_etfs + tw_4dig if s not in existing]
print(f"TW to add: {len(tw_to_add)}")

# ── US stocks ────────────────────────────────────────────────────────────────
us_list = [
    'AAPL','MSFT','NVDA','AMD','AVGO','QCOM','INTC','ASML','MU','MRVL',
    'LRCX','AMAT','GOOGL','AMZN','META','NFLX','PYPL','CRM','ADBE','ORCL',
    'CSCO','TSLA','RIVN','COIN','PLTR','SNOW','D','SO','NEE','ENPH','TSM',
    'VUG','VTV','VO','VB','VCR','VDC','VGT','VHT','VIS','VTI','VOO','VEA',
    'VWO','BND','TLT','GLD','SLV','AGG','SCHZ','TIP','QQQ','SPY','IWM',
    'DIA','XOM','CVX','COP','SLB','HAL','OXY','MRO','DVN','FANG','PXD',
    'EOG','MPC','PSX','VLO','OKE','WMB','KMI','ET','EPD','LIN','APD','SHW',
    'DD','LYB','DOW','PPG','ALB','CE','CTVA','FMC','MOS','CF','NUE','STLD',
    'RS','X','AA','AMKR','ALLE','AOS','ARNC','AYI','BALD','BLDR','BSET',
    'CACI','CAG','CARR','CAT','CBOE','CBRE','CCJ','CDE','CHKP','CHWY','CIM',
    'CL','CMC','CMG','CNK','CNO','COO','CPT','CRL','CRS','CUBE','CULP',
    'CVA','CVT','CWH','CZR','DAL','DAN','DAR','DE','DECK','DG','DHI','DKS',
    'DLTR','DNOW','DOV','DRI','DUK','EA','EIX','EL','EMN','ENOV','EQR','ES',
    'ETN','ETR','EVGO','EW','EXC','EXPD','EXPE','F','FAST','FATE','FCF',
    'FCN','FDS','FDX','FE','FF','FICO','FII','FL','FLEX','FN','FND','FNI',
    'FOW','FOX','FTI','FTNT','GD','GE','GILD','GIS','GL','GPC','GPN','GPRO',
    'GRMN','GS','HAL','HBAN','HBI','HCA','HII','HON','HPE','HPQ','HRB','HRL',
    'HSY','HUM','HWM','IBM','ICE','IDXX','IEX','IFF','INFO','INTU','IONS',
    'IQV','IR','IRM','ISRG','IT','ITT','IVZ','J','JBHT','JCI','JKHY','JNJ',
    'JPM','K','KBH','KBR','KHC','KIM','KKR','KLAC','KMB','KMX','KNX','KR',
    'KSS','L','LDOS','LEG','LEN','LH','LHX','LIN','LKQ','LL','LLY','LMT',
    'LNC','LNT','LOW','LSI','LYV','M','MA','MAA','MAN','MAR','MAS','MCD',
    'MCHP','MCK','MCO','MDLZ','MDRX','MDT','MET','MGM','MHK','MKC','MLM',
    'MMC','MMM','MNST','MO','MOH','MOS','MPW','MRK','MS','MSCI','MTD','MUR',
    'NCLH','NDAQ','NDSN','NEM','NI','NKE','NLOK','NLY','NMRK','NOC','NOV',
    'NOW','NRG','NSC','NTAP','NTRS','NVR','O','OC','OCFC','ODFL','OFC',
    'OGN','OMC','OSK','OTIS','PAYC','PBCT','PBF','PBI','PCAR','PCG','PD',
    'PEAK','PEG','PEN','PFE','PFGC','PG','PGR','PH','PHM','PKG','PKI','PLD',
    'PM','PNC','PNR','PNW','PODD','POOL','PPC','PPL','PRGO','PRU','PSA',
    'PTC','PVH','PWR','RCL','RD','RE','REG','RF','RHI','RIG','RJF','RL',
    'RMD','RNR','ROK','ROL','ROP','ROST','RPM','RTX','SBAC','SBUX','SCCO',
    'SCHW','SEIC','SJM','SNAP','SNPS','SPG','SPGI','SQ','SRC','SRCL','SRE',
    'STE','STZ','SWK','SYK','T','TAP','TCOM','TDG','TFC','TFX','TJX','TMO',
    'TPR','TRGP','TRMB','TROW','TRV','TSCO','TT','TTWO','TXN','TXT','UDR',
    'UHS','ULTA','UNH','UNP','UPST','USB','V','VAL','VEEV','VFC','VICI',
    'VMC','VMI','VNO','VOD','VRSN','VRTX','VTR','VZ','WAB','WAL','WAT',
    'WBA','WCG','WCN','WDC','WEC','WELL','WFC','WHR','WM','WMT','WRB',
    'WST','WTW','WY','XEC','XEL','XLNX','XPO','XRX','YUM','ZBH','ZION',
    'ZM','ZS'
]
us_to_add = [s for s in us_list if s not in existing]
print(f"US to add: {len(us_to_add)}")

# ── Download helper ─────────────────────────────────────────────────────────
def safe_download(sym, period='2y'):
    try:
        ticker = yf.Ticker(sym)
        df = ticker.history(period=period, auto_adjust=True)
        if df.empty or len(df) < 10:
            return None
        return df
    except Exception as e:
        return None

# ── Process TW ──────────────────────────────────────────────────────────────
ok_tw = 0; fail_tw = 0; skipped_tw = 0
print(f"\n=== Downloading {len(tw_to_add)} TW stocks ===")
for i, sym in enumerate(tw_to_add):
    if i % 200 == 0 and i > 0:
        pct = i * 100 // len(tw_to_add)
        print(f"  TW progress: {i}/{len(tw_to_add)} ({pct}%)  OK:{ok_tw}  Fail:{fail_tw}  Skip:{skipped_tw}")

    df = safe_download(sym)
    if df is not None:
        n = insert_ticker(sym, df)
        ok_tw += 1
        if ok_tw % 50 == 0:
            print(f"  [TW] {sym} inserted ({n} rows)  total OK={ok_tw}")
    else:
        fail_tw += 1

    time.sleep(0.3)  # gentle rate limiting

    # Check target
    cur.execute("SELECT COUNT(DISTINCT symbol) FROM daily_ohlcv")
    total = cur.fetchone()[0]
    if total >= 500:
        print(f"\n  TARGET REACHED: {total} symbols! Stopping TW download.")
        break

# ── Process US ──────────────────────────────────────────────────────────────
cur.execute("SELECT COUNT(DISTINCT symbol) FROM daily_ohlcv")
total_now = cur.fetchone()[0]
print(f"\nAfter TW: {total_now} symbols. Processing US...")

ok_us = 0; fail_us = 0
for i, sym in enumerate(us_to_add):
    cur.execute("SELECT COUNT(DISTINCT symbol) FROM daily_ohlcv")
    total = cur.fetchone()[0]
    if total >= 500:
        print(f"TARGET REACHED: {total} symbols! Stopping.")
        break

    df = safe_download(sym)
    if df is not None:
        n = insert_ticker(sym, df)
        ok_us += 1
        if ok_us % 20 == 0:
            print(f"  [US] {sym} ({n} rows)  total OK US={ok_us}, TW={ok_tw}")
    else:
        fail_us += 1
    time.sleep(0.3)

# ── Final ─────────────────────────────────────────────────────────────────────
conn.commit()
cur.execute("SELECT COUNT(DISTINCT symbol) FROM daily_ohlcv")
total_sym = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM daily_ohlcv")
total_rows = cur.fetchone()[0]
conn.close()

print(f"\n{'='*55}")
print(f"DONE!")
print(f"  Symbols: {total_sym} (was 160, added ~{total_sym-160})")
print(f"  Rows:     {total_rows}")
print(f"  TW OK:    {ok_tw}  fail:{fail_tw}")
print(f"  US OK:    {ok_us}  fail:{fail_us}")