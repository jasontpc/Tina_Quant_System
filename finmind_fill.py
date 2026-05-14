"""
Fill remaining symbols using FinMind API (for TW) and yfinance (for US).
FinMind is not rate-limited like Yahoo.
"""
import sqlite3
import time
import requests
from pathlib import Path

DB = Path('C:/Users/USER/.openclaw/workspace/Tina_Quant_System/data/yfinance.db')
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjJ9.1LHB4yKHeZFoXStyjK2W9F6X3nZLMA1IfPWpDVlv6K0"
BASE_URL = "https://api.finmindtrade.com/api/v4/data"

conn = sqlite3.connect(str(DB))
cur = conn.cursor()
cur.execute("SELECT DISTINCT symbol FROM daily_ohlcv")
existing = set(r[0] for r in cur.fetchall())
conn.close()

TARGET = 500
print(f"Existing: {len(existing)}, need: {max(0, TARGET - len(existing))} more")

def get_finmind(code, start_date="2024-05-01"):
    """Fetch Taiwan stock data from FinMind. Returns list of dicts or None."""
    try:
        resp = requests.get(BASE_URL, params={
            "dataset": "TaiwanStockPrice",
            "data_id": code,
            "start_date": start_date,
            "token": FINMIND_TOKEN,
        }, timeout=10)
        if resp.status_code == 200:
            d = resp.json()
            if d.get('data') and len(d.get('data', [])) >= 20:
                return d['data']
    except Exception:
        pass
    return None

def insert_rows(sym, rows):
    conn2 = sqlite3.connect(str(DB))
    cnt = 0
    for row in rows:
        try:
            d = str(row['date'])[:10]
            cur2 = conn2.cursor()
            cur2.execute(f"""INSERT OR REPLACE INTO daily_ohlcv
                (symbol, date, open, high, low, close, volume,
                 change_pct, sma_20, sma_60, sma_120, rsi_14, atr_14,
                 macd, macd_sig, macd_hist, bb_upper, bb_middle, bb_lower, vol_ratio)
                VALUES (?,?,?,?,?,?,?,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL)""",
                (sym, d,
                 float(row['open']), float(row['max']), float(row['min']), float(row['close']),
                 int(row['Trading_Volume'])))
            cnt += 1
        except Exception:
            pass
    conn2.commit()
    conn2.close()
    return cnt

# ── Step 1: FinMind for TW stocks in 2xxx-9xxx range ────────────────────────
conn2 = sqlite3.connect(str(DB))
cur2 = conn2.cursor()
cur2.execute("SELECT COUNT(DISTINCT symbol) FROM daily_ohlcv WHERE symbol LIKE '%.TW'")
existing_tw = cur2.fetchone()[0]
conn2.close()

ok_tw = 0; fail_tw = 0
print(f"\n=== TW FinMind (existing: {existing_tw}) ===")

# Known good TW stock ranges (concentrated in 2xxx tech, 3xxx electronics, etc.)
tw_ranges = []
for start in range(2000, 9999, 100):
    for offset in range(0, 100):
        code = start + offset
        sym = f"{code}.TW"
        if sym not in existing:
            tw_ranges.append(code)
        if len(tw_ranges) >= 300:
            break
    if len(tw_ranges) >= 300:
        break

# Deduplicate
tw_ranges = sorted(set(tw_ranges))
print(f"TW codes to try: {len(tw_ranges)}")

for code in tw_ranges:
    sym = f"{code}.TW"
    conn3 = sqlite3.connect(str(DB))
    cur3 = conn3.cursor()
    cur3.execute("SELECT COUNT(DISTINCT symbol) FROM daily_ohlcv")
    total = cur3.fetchone()[0]
    conn3.close()
    if total >= TARGET:
        print(f"TARGET {total} reached! Stopping TW.")
        break

    rows = get_finmind(str(code))
    if rows:
        n = insert_rows(sym, rows)
        ok_tw += 1
        print(f"  [OK] {sym} ({n} rows)  total={total+1}")
    else:
        fail_tw += 1

    if ok_tw % 20 == 0 and ok_tw > 0:
        print(f"  progress: ok={ok_tw}  fail={fail_tw}")

    time.sleep(0.25)

# Check status
conn4 = sqlite3.connect(str(DB))
cur4 = conn4.cursor()
cur4.execute("SELECT COUNT(DISTINCT symbol) FROM daily_ohlcv")
total_after_tw = cur4.fetchone()[0]
print(f"\nAfter TW FinMind: {total_after_tw} symbols (need {TARGET - total_after_tw} more)")

# If still short, try yfinance for US stocks
need_now = TARGET - total_after_tw
if need_now > 0:
    print(f"\n=== US yfinance (need {need_now}) ===")
    import yfinance as yf

    us_list = [
        'AAPL','MSFT','NVDA','AMD','AVGO','QCOM','INTC','ASML','MU','MRVL',
        'LRCX','AMAT','GOOGL','AMZN','META','NFLX','PYPL','CRM','ADBE','ORCL',
        'CSCO','TSLA','RIVN','COIN','PLTR','SNOW','D','SO','NEE','ENPH','TSM',
        'VUG','VTV','VO','VB','VCR','VDC','VGT','VHT','VIS','VTI','VOO','VEA',
        'VWO','BND','TLT','GLD','SLV','AGG','TIP','QQQ','SPY','IWM','DIA',
        'XOM','CVX','COP','SLB','HAL','OXY','MRO','DVN','FANG','PXD','EOG',
        'MPC','PSX','VLO','OKE','WMB','KMI','ET','EPD','LIN','APD','SHW',
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

    ok_us = 0; fail_us = 0
    for sym in us_to_add:
        conn5 = sqlite3.connect(str(DB))
        cur5 = conn5.cursor()
        cur5.execute("SELECT COUNT(DISTINCT symbol) FROM daily_ohlcv")
        total = cur5.fetchone()[0]
        conn5.close()
        if total >= TARGET:
            print(f"TARGET {total} reached! Stopping US.")
            break

        try:
            t = yf.Ticker(sym)
            df = t.history(period='2y', auto_adjust=True)
            if df is not None and not df.empty and len(df) >= 20:
                cnt = 0
                conn6 = sqlite3.connect(str(DB))
                for idx, row in df.iterrows():
                    try:
                        d = str(idx.date()) if hasattr(idx, 'date') else str(idx)[:10]
                        cur6 = conn6.cursor()
                        cur6.execute(f"""INSERT OR REPLACE INTO daily_ohlcv
                            (symbol, date, open, high, low, close, volume,
                             change_pct, sma_20, sma_60, sma_120, rsi_14, atr_14,
                             macd, macd_sig, macd_hist, bb_upper, bb_middle, bb_lower, vol_ratio)
                            VALUES (?,?,?,?,?,?,?,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL)""",
                            (sym, d, float(row['Open']), float(row['High']),
                             float(row['Low']), float(row['Close']), int(row['Volume'])))
                        cnt += 1
                    except Exception:
                        pass
                conn6.commit()
                conn6.close()
                ok_us += 1
                print(f"  [US OK] {sym} ({cnt} rows)  total={total+1}")
            else:
                fail_us += 1
        except Exception:
            fail_us += 1

        if ok_us % 10 == 0 and ok_us > 0:
            print(f"  progress: ok_us={ok_us}  fail_us={fail_us}")
        time.sleep(1.5)

# Final report
conn_final = sqlite3.connect(str(DB))
cur_final = conn_final.cursor()
cur_final.execute("SELECT COUNT(DISTINCT symbol) FROM daily_ohlcv")
total_sym = cur_final.fetchone()[0]
cur_final.execute("SELECT COUNT(*) FROM daily_ohlcv")
total_rows = cur_final.fetchone()[0]
conn_final.close()

print(f"\n{'='*50}")
print(f"DONE!")
print(f"  Symbols: {total_sym} (was 160, added ~{total_sym-160})")
print(f"  Rows:    {total_rows}")
print(f"  TW (FinMind): {ok_tw} ok, {fail_tw} fail")
print(f"  US (yfinance): {ok_us} ok, {fail_us} fail")