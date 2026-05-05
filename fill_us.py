"""
Fill remaining symbols with US stocks only - fast & targeted.
"""
import yfinance as yf
import sqlite3
from pathlib import Path
import time

DB = Path('C:/Users/USER/.openclaw/workspace/Tina_Quant_System/data/yfinance.db')
conn = sqlite3.connect(str(DB))
cur = conn.cursor()

cur.execute("SELECT DISTINCT symbol FROM daily_ohlcv")
existing = set(r[0] for r in cur.fetchall())
print(f"Existing: {len(existing)}")

def insert_rows(sym, df):
    if df is None or df.empty:
        return 0
    cnt = 0
    for idx, row in df.iterrows():
        try:
            d = str(idx.date()) if hasattr(idx, 'date') else str(idx)[:10]
            cur.execute(f"""INSERT OR REPLACE INTO daily_ohlcv
                (symbol, date, open, high, low, close, volume,
                 change_pct, sma_20, sma_60, sma_120, rsi_14, atr_14,
                 macd, macd_sig, macd_hist, bb_upper, bb_middle, bb_lower, vol_ratio)
                VALUES (?,?,?,?,?,?,?,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL)""",
                (sym, d, float(row['Open']), float(row['High']),
                 float(row['Low']), float(row['Close']), int(row['Volume'])))
            cnt += 1
        except Exception:
            pass
    conn.commit()
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

# US stock universe - 400+ stocks
us_list = [
    # Large cap tech / semis
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
    'ZM','ZS',
    # More US stocks to ensure reaching 500
    'ABB','ABBV','ABC','ABMD','ABT','ACN','ADAN','ADBE','ADI','ADM',
    'ADP','AEE','AEP','AES','AFL','AGN','AIG','AIZ','AJG','ALGN',
    'ALK','ALL','AME','AMP','ANDV','ANSS','ANTM','AON','APD','APH',
    'ARTN','ASB','ASH','ATVI','AVB','AVY','AWK','AXON','AZO','BA',
    'BAC','BAH','BALL','BAX','BBY','BCS','BDX','BFB','BHP','BIIB',
    'BIO','BJ','BK','BKNG','BLK','BLNK','BMRN','BMS','BMY','BNH',
    'BR','BRO','BSX','BTI','BUD','BUR','BWX','BYD','CAG','CAH','CAR',
    'CBO','CBU','CINF','CIVI','CLX','CMA','CMCSA','CME','CMI','CMS',
    'CNC','CNP','COF','COST','CPRT','CPT','CRBG','CSGP','CSX','CTAS',
    'CTSH','CTVA','CUBE','CUK','CURV','CVI','CVS','CWEN','CWI','CX',
    'CY','DASH','DAY','DBX','DCI','DECK','DFS','DGX','DLTR','DOCU',
    'DOMO','DRVN','DSGX','DT','DTM','DUK','DVA','DVY','DXC','DXCM',
    'EBAY','ECL','ED','EFX','EHC','ELV','EMR','ENB','EPC','EQIX',
    'EQR','EQT','ERIE','ESS','ESTC','ET','ETR','EU','EVRG','EWBC',
    'EXAS','EXC','EXPE','EXR','FANG','FAST','FB','FDS','FE','FICO',
    'FIS','FISV','FITB','FMC','FN','FNV','FRC','FRT','FSLR','FTV',
    'FWONK','G','GDDY','GEN','GHC','GIB','GILD','GIS','GLOB','GLW',
    'GPN','GRMN','GRWG','GS','GT','GWW','HAL','HBAN','HCA','HE','HEI',
    'HES','HII','HLT','HOLX','HON','HPE','HPQ','HSY','HUM','HWM',
    'IBM','ICE','ICL','IDXX','IEX','IFF','ILMN','INCY','INGR','INTU',
    'IONS','IP','IPG','IQV','IR','IRM','ISRG','IT','ITW','IVZ','J',
    'JAZZ','JBHT','JCI','JKHY','JNPR','JPM','K','KDP','KEX','KEY',
    'KEYS','KHC','KIM','KKR','KLAC','KMB','KMI','KNX','KOF','KR',
    'KSS','KTB','KWEB','L','LAD','LAZ','LBRDK','LBTYK','LDOS','LEG',
    'LEN','LH','LHX','LII','LLY','LMT','LNC','LNG','LOK','LOW',
    'LRCX','LSCC','LUV','LVS','LYB','LYV','MAA','MAIN','MAR','MMC',
    'MMM','MO','MOS','MPC','MRK','MRO','MS','MSCI','MSFT','MTCH',
    'MTD','MU','MUR','NCLH','NDAQ','NDSN','NEE','NEM','NEP','NI',
    'NICE','NKE','NLOK','NLY','NOC','NOW','NRG','NSC','NTAP','NTRS',
    'NUAN','NUE','NVCR','NVR','NWL','NYCB','NZUS','O','ODFL','OEC',
    'OGN','OKE','OKTA','OMC','OMF','ON','ORCL','ORLY','OXY','PAYX',
    'PBCT','PBYI','PCAR','PCG','PEAK','PEG','PEN','PFE','PFG','PG',
    'PGR','PH','PHM','PKG','PKI','PLD','PLTR','PM','PNC','PNR','PNW',
    'PODD','POOL','PPG','PPL','PRU','PTC','PUK','PVH','PWR','PXD',
    'QCOM','QG','QMCO','QRVO','RCL','RDVT','REG','REGN','RF','RHI',
    'RIG','RJF','RL','RMD','RNG','RNR','ROK','ROL','ROP','ROST',
    'RPM','RSG','RTX','RVTY','RY','SABR','SAIA','SALL','SAM','SANM',
    'SAVE','SBAC','SBNY','SBS','SBUX','SCCO','SCHW','SE','SEB','SEE',
    'SF','SJM','SLB','SLM','SMAR','SMCI','SMG','SNAP','SNOW','SNPS',
    'SO','SPG','SPGI','SPOT','SQ','SRC','SRCL','SRE','STE','STLD',
    'STT','STZ','SWK','SYY','T','TAP','TCOM','TDG','TECH','TFC',
    'TFX','TJX','TKO','TLK','TMUS','TNC','TNET','TOL','TPC','TREX',
    'TRGP','TRMB','TROW','TRV','TSCO','TSLA','TT','TTD','TTWO','TXN',
    'TXT','U','UBS','UDR','UGI','UHS','ULTA','UMC','UNH','UNP',
    'UPST','UPWK','USB','V','VLO','VMC','VMI','VNO','VRSK','VRSN',
    'VRTX','VTR','VZ','WAB','WAT','WBA','WCN','WDAY','WDC','WEC',
    'WELL','WFC','WHR','WIT','WIX','WMB','WMT','WNR','WPP','WRB',
    'WSO','WST','WTW','WY','WYNN','XEL','XOM','XPO','XRX','YELP',
    'YUM','ZBH','ZION','ZM','ZS','ZTO','ZTS','ZUMZ'
]

# Deduplicate and filter
us_to_add = [s for s in us_list if s not in existing]
print(f"US to add: {len(us_to_add)}")

ok = 0; fail = 0
for i, sym in enumerate(us_to_add):
    cur.execute("SELECT COUNT(DISTINCT symbol) FROM daily_ohlcv")
    total = cur.fetchone()[0]
    if total >= 500:
        print(f"TARGET {total} reached! Stopping.")
        break
    if i % 50 == 0 and i > 0:
        print(f"  progress {i}/{len(us_to_add)}  total_sym={total}  ok={ok}")

    df = safe_download(sym)
    if df is not None:
        n = insert_rows(sym, df)
        ok += 1
        if ok % 25 == 0:
            print(f"  [OK] {sym} ({n} rows)  ok={ok}")
    else:
        fail += 1
    time.sleep(0.5)

# Final
conn.commit()
cur.execute("SELECT COUNT(DISTINCT symbol) FROM daily_ohlcv")
total_sym = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM daily_ohlcv")
total_rows = cur.fetchone()[0]
conn.close()

print(f"\n{'='*50}")
print(f"DONE!")
print(f"  Symbols: {total_sym} (was 160, added ~{total_sym-160})")
print(f"  Rows:    {total_rows}")
print(f"  US OK:   {ok}  fail:{fail}")