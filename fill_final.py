"""
Final fill script - run in background with long sleeps to avoid rate limit.
Adds remaining US stocks until target of 500 is reached.
"""
import yfinance as yf
import sqlite3
import time
from pathlib import Path

DB = Path('C:/Users/USER/.openclaw/workspace/Tina_Quant_System/data/yfinance.db')
conn = sqlite3.connect(str(DB))
cur = conn.cursor()
cur.execute("SELECT DISTINCT symbol FROM daily_ohlcv")
existing = set(r[0] for r in cur.fetchall())
conn.close()

print(f"Starting: {len(existing)} symbols. Need {500 - len(existing)} more.")

def insert_rows(sym, df):
    if df is None or df.empty:
        return 0
    cnt = 0
    conn2 = sqlite3.connect(str(DB))
    for idx, row in df.iterrows():
        try:
            d = str(idx.date()) if hasattr(idx, 'date') else str(idx)[:10]
            cur2 = conn2.cursor()
            cur2.execute(f"""INSERT OR REPLACE INTO daily_ohlcv
                (symbol, date, open, high, low, close, volume,
                 change_pct, sma_20, sma_60, sma_120, rsi_14, atr_14,
                 macd, macd_sig, macd_hist, bb_upper, bb_middle, bb_lower, vol_ratio)
                VALUES (?,?,?,?,?,?,?,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL)""",
                (sym, d, float(row['Open']), float(row['High']),
                 float(row['Low']), float(row['Close']), int(row['Volume'])))
            cnt += 1
        except Exception:
            pass
    conn2.commit()
    conn2.close()
    return cnt

def safe_download(sym, period='2y'):
    try:
        t = yf.Ticker(sym)
        df = t.history(period=period, auto_adjust=True)
        if df is None or df.empty or len(df) < 20:
            return None
        return df
    except Exception:
        return None

# US stocks to try - well-known names likely not in DB
us_to_try = [
    'ABB','ABBV','ABC','ABT','ACN','ADP','AEE','AEP','AES','AFL',
    'AIG','AIZ','AJG','ALGN','ALK','ALL','AME','AMP','AMGN','APH',
    'ARE','ATO','AVB','AVY','AWK','AXON','AZO','BA','BAC','BALL',
    'BAX','BBY','BCS','BDX','BFB','BHP','BIIB','BIO','BJ','BK',
    'BKNG','BLK','BMRN','BMS','BMY','BR','BRO','BSX','BTI','BUD',
    'CAG','CAH','CAR','CAT','CBO','CBU','CINF','CLX','CMA','CMCSA',
    'CME','CMI','CMS','CNC','CNP','COF','COST','CPRT','CRBG','CSGP',
    'CSX','CTAS','CTSH','CUBE','CUK','CURV','CVI','CVS','CWEN','CWI',
    'DASH','DAY','DBX','DCI','DFS','DGX','DOCU','DOMO','DRVN','DSGX',
    'DT','DTM','DVA','DVY','DXC','DXCM','EBAY','ECL','ED','EFX',
    'EHC','ELV','EMR','ENB','EPC','EQIX','EQT','ERIE','ESS','ESTC',
    'EVRG','EWBC','EXAS','EXC','EXPE','EXR','FAST','FE','FICO','FIS',
    'FISV','FITB','FMC','FNV','FRC','FRT','FSLR','FTV','G','GDDY',
    'GEN','GHC','GIB','GILD','GIS','GLOB','GLW','GRMN','GRWG','GS',
    'GT','GWW','HAL','HBAN','HCA','HE','HEI','HES','HII','HLT','HOLX',
    'HON','HPE','HPQ','HSY','HUM','HWM','IBM','ICE','ICL','IDXX',
    'IEX','IFF','ILMN','INCY','INGR','INTU','IONS','IP','IPG','IQV',
    'IR','IRM','ISRG','IT','ITW','IVZ','JAZZ','JBHT','JCI','JKHY','JNPR',
    'JPM','K','KDP','KEX','KEY','KEYS','KHC','KIM','KKR','KLAC','KMB',
    'KMI','KNX','KOF','KR','KSS','KTB','KWEB','L','LAD','LAZ','LBRDK',
    'LBTYK','LDOS','LEG','LEN','LH','LHX','LII','LLY','LMT','LNC',
    'LNG','LOK','LOW','LSCC','LUV','LVS','LYB','LYV','MAA','MAIN','MAR',
    'MCHP','MCK','MCO','MDLZ','MDRX','MDT','MET','MGM','MHK','MKC','MLM',
    'MMC','MMM','MO','MOS','MPC','MRK','MRO','MS','MSCI','MTCH','MTD',
    'MU','MUR','NCLH','NDAQ','NDSN','NEE','NEM','NEP','NI','NICE','NKE',
    'NLOK','NLY','NOC','NOW','NRG','NSC','NTAP','NTRS','NUAN','NUE',
    'NVCR','NVR','NWL','NYCB','NZUS','ODFL','OEC','OGN','OKE','OKTA',
    'OMC','OMF','ON','ORLY','OXY','PAYX','PBCT','PBYI','PCAR','PCG',
    'PEAK','PEG','PEN','PFE','PFG','PG','PGR','PH','PHM','PKG','PKI',
    'PLD','PM','PNC','PNR','PNW','PODD','POOL','PPG','PPL','PRU','PTC',
    'PUK','PVH','PWR','PXD','QCOM','QG','QMCO','QRVO','RCL','RDVT','REG',
    'REGN','RF','RHI','RIG','RJF','RL','RMD','RNG','RNR','ROK','ROL',
    'ROP','ROST','RPM','RSG','RTX','RVTY','SABR','SAIA','SALL','SAM',
    'SANM','SAVE','SBNY','SBS','SCCO','SCHW','SE','SEB','SEE','SF',
    'SJM','SLB','SLM','SMAR','SMCI','SMG','SNAP','SNOW','SNPS','SO',
    'SPG','SPGI','SPOT','SQ','SRC','SRCL','SRE','STE','STLD','STT',
    'STZ','SWK','SYY','TAP','TCOM','TDG','TECH','TFC','TFX','TJX',
    'TKO','TLK','TMUS','TNC','TNET','TOL','TPC','TREX','TRGP','TRMB',
    'TROW','TRV','TSCO','TT','TTD','TTWO','TXN','TXT','U','UBS',
    'UGI','UHS','ULTA','UMC','UNH','UNP','UPST','UPWK','USB','VLO',
    'VMC','VMI','VNO','VRSK','VRSN','VRTX','VTR','VZ','WAB','WAT',
    'WBA','WCN','WDAY','WDC','WEC','WELL','WFC','WHR','WIT','WIX',
    'WMB','WMT','WNR','WPP','WRB','WSO','WST','WTW','WY','WYNN',
    'XEL','XPO','XRX','YELP','ZTO','ZTS','ZUMZ'
]

ok = 0; fail = 0; skip = 0
for i, sym in enumerate(us_to_try):
    # Check target
    conn3 = sqlite3.connect(str(DB))
    cur3 = conn3.cursor()
    cur3.execute("SELECT COUNT(DISTINCT symbol) FROM daily_ohlcv")
    total = cur3.fetchone()[0]
    conn3.close()
    if total >= 500:
        print(f"\nTARGET {total} REACHED! Done.")
        break

    if i % 20 == 0:
        print(f"  progress {i}/{len(us_to_try)}  total={total}  ok={ok}  fail={fail}  skip={skip}")

    if sym in existing:
        skip += 1
        continue

    df = safe_download(sym)
    if df is not None:
        n = insert_rows(sym, df)
        ok += 1
        print(f"  [OK] {sym} ({n} rows)  total={total+1}")
    else:
        fail += 1

    # Exponential backoff on failure
    if 'rate limit' in str(df).lower() if df else True:
        time.sleep(3)
    else:
        time.sleep(1.5)

print(f"\nFinal: {ok} added, {fail} failed, {skip} skipped")