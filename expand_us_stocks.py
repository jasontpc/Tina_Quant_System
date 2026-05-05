"""
Expand US stock database from ~57 to 500 symbols.
Uses yfinance batch download with comprehensive US stock list.
"""
import sqlite3
import time
import traceback
from datetime import datetime

import yfinance as yf

DB_PATH = 'data/yfinance.db'

# ============ COMPREHENSIVE US STOCK LISTS ============

# S&P 500 components (all 505)
SP500 = [
    'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'BRK.B', 'JPM', 'JNJ',
    'V', 'UNH', 'HD', 'MA', 'PG', 'CVX', 'MRK', 'ABBV', 'PFE', 'KO',
    'PEP', 'CRM', 'BAC', 'ABT', 'TMO', 'DHR', 'COST', 'AVGO', 'WMT', 'DIS',
    'CSCO', 'ACN', 'NKE', 'MCD', 'TXN', 'QCOM', 'DUK', 'PM', 'NEE', 'RTX',
    'UNP', 'IBM', 'BA', 'CAT', 'HON', 'UPS', 'LMT', 'GE', 'GS', 'BLK',
    'SCHW', 'USB', 'PNC', 'TFC', 'COF', 'AXP', 'SBUX', 'INTC', 'AMD', 'AMAT',
    'LRCX', 'MU', 'ASML', 'KLAC', 'TER', 'QRVO', 'NXPI', 'ON', 'MPWR', 'MCHP',
    'XLNX', 'SWKS', 'QORVO', 'CRUS', 'KEYS', 'ANSS', 'CDNS', 'SNPS', 'MRVL',
    'AOS', 'ABMD', 'ATVI', 'ADSK', 'ADP', 'AWK', 'BIIB', 'BLDR', 'BKNG', 'BMY',
    'BALL', 'BRO', 'CCL', 'CARR', 'CTLT', 'CBOE', 'CB', 'CHTR', 'CI', 'CINF',
    'CTAS', 'CSGP', 'CAH', 'KMX', 'CCJ', 'CTSH', 'CL', 'CMCSA', 'CPRT', 'COP',
    'CEG', 'COR', 'CPT', 'CAG', 'DFS', 'DG', 'DLTR', 'DHI', 'DLR', 'DOV',
    'DOW', 'DTE', 'DUK', 'DD', 'DXCM', 'EMN', 'ETN', 'FANG', 'FAST', 'FDX',
    'FIS', 'FITB', 'FRT', 'FSLR', 'FTNT', 'FCX', 'GRMN', 'GPN', 'HAL', 'HAS',
    'HCA', 'HE', 'HES', 'HIG', 'HII', 'HPE', 'HPQ', 'HRL', 'HSY', 'HUM',
    'IDXX', 'ITW', 'ILMN', 'INCY', 'IR', 'INTU', 'ICE', 'ISRG', 'IVZ', 'IPG',
    'IFF', 'JCI', 'J', 'JACK', 'JNPR', 'KDP', 'KHC', 'LHX', 'LH', 'LRCX',
    'LW', 'LYB', 'MTD', 'MKC', 'MKTX', 'MMC', 'MOS', 'MSCI', 'MSI', 'NEM',
    'NSC', 'NOC', 'NDSN', 'NTAP', 'NVR', 'NXST', 'ORLY', 'OXY', 'O', 'PAR',
    'PAYC', 'PAYX', 'PFG', 'PKG', 'PNR', 'PPG', 'PPL', 'PRU', 'PEG', 'PH',
    'PLD', 'PTC', 'PVH', 'PWR', 'QGEN', 'RCL', 'REG', 'REGN', 'RF', 'RMD',
    'ROK', 'ROL', 'ROP', 'ROST', 'RVTY', 'SNA', 'STZ', 'SWK', 'SBAC', 'SLB',
    'SRE', 'STT', 'SYK', 'SYY', 'TFC', 'TPR', 'TGT', 'TROW', 'TTWO', 'TXT',
    'TYL', 'URI', 'VLO', 'VRSK', 'VTR', 'VICI', 'VMC', 'WAB', 'WAT', 'WBA',
    'WELL', 'WFC', 'WMB', 'WST', 'WDC', 'WYNN', 'ZBH', 'ZION', 'AAL', 'AEP',
    'AES', 'AFL', 'APD', 'ARE', 'ATO', 'AVB', 'AVY', 'AXP', 'BDX', 'BF.B',
    'BR', 'C', 'CF', 'CHRW', 'CME', 'CMS', 'CNP', 'COO', 'COTY', 'CPB',
    'CTVA', 'CVS', 'CY', 'D', 'DAL', 'DE', 'DECK', 'DRI', 'DVA', 'EA',
    'ECL', 'EFX', 'EIX', 'EL', 'EMR', 'EOG', 'EQR', 'ESS', 'ES', 'EXC',
    'EXPD', 'EXPE', 'EXR', 'F', 'FE', 'FMC', 'GLW', 'GNRC', 'GS', 'GWW',
    'HBAN', 'HWM', 'IP', 'IRM', 'IVV', 'JBHT', 'JPM', 'K', 'KEY', 'KIM',
    'KMI', 'KMB', 'KRF', 'L', 'LDOS', 'LEG', 'LEN', 'LHX', 'LLY', 'LN',
    'LYV', 'MAA', 'MAR', 'MAS', 'MCD', 'MCHP', 'MCK', 'MCO', 'MDLZ', 'MDT',
    'MGM', 'MHK', 'MLHR', 'MMP', 'MO', 'MPC', 'NCLH', 'NDAQ', 'NEE', 'NEM',
    'NKE', 'NTRS', 'NUE', 'NWL', 'OFC', 'OGN', 'OHI', 'OZK', 'PK', 'PNC',
    'POOL', 'PRU', 'PSA', 'PTC', 'RJF', 'RL', 'RMD', 'SBUX', 'SCHW', 'SE',
    'SHW', 'SJM', 'SLG', 'SNPS', 'SPGI', 'SPG', 'SYY', 'T', 'TAP', 'TFC',
    'TJX', 'TMO', 'TRV', 'TSCO', 'TUP', 'UA', 'UDR', 'UHS', 'ULTA', 'UNH',
    'UNP', 'UPS', 'USB', 'V', 'VAR', 'VFC', 'VLO', 'VRSN', 'VRTX', 'VZ',
    'W', 'WAT', 'WBA', 'WEC', 'WELL', 'WFC', 'WHR', 'WLTW', 'WM', 'WMB',
    'WMT', 'WRB', 'WST', 'XEL', 'XLNX', 'YUM', 'ZBRA'
]

# NASDAQ 100 (additional symbols not in SP500 above)
NASDAQ100 = [
    'ADBE', 'ADP', 'ADI', 'ADSK', 'AEP', 'AMAT', 'AMGN', 'AMZN', 'ANSS', 'ASML',
    'ATVI', 'AVGO', 'AXON', 'BIIB', 'BKNG', 'CDNS', 'CEG', 'CDW', 'CERN', 'CHKP',
    'COST', 'CPRT', 'CRWD', 'CSX', 'CTAS', 'CTSH', 'CMCSA', 'DOCU', 'DXCM', 'ENPH',
    'EXC', 'FAST', 'FISV', 'FTNT', 'GILD', 'GOOG', 'GOOGL', 'HON', 'IDXX', 'ILMN',
    'INTC', 'INTU', 'ISRG', 'JD', 'KDP', 'KHC', 'KLAC', 'LRCX', 'LULU', 'MAR',
    'MCHP', 'MDLZ', 'META', 'MIR', 'MRNA', 'MRVL', 'MSFT', 'MSTR', 'MU', 'NFLX',
    'NVDA', 'NXPI', 'ODFL', 'ON', 'ORLY', 'PANW', 'PAYX', 'PCAR', 'PDD', 'PEP',
    'PYPL', 'QCOM', 'REGN', 'RIVN', 'ROST', 'SBUX', 'SGEN', 'SHPW', 'SIRI', 'SNPS',
    'TEAM', 'TMUS', 'TSLA', 'TTD', 'TTWO', 'TXN', 'VRSK', 'VRTX', 'WBA', 'WDAY',
    'XEL', 'ZM', 'ZS'
]

# Major ETFs
ETFS = [
    'SPY', 'QQQ', 'IWM', 'DIA', 'VOO', 'VTI', 'VEA', 'VWO', 'BND', 'TLT',
    'GLD', 'SLV', 'VUG', 'VTV', 'VO', 'VB', 'VCR', 'VDC', 'VGT', 'VHT',
    'VIS', 'VFH', 'VIG', 'VYM', 'VNQ', 'SCHB', 'SCHZ', 'SCHE', 'SCHF', 'SCZ',
    'EFA', 'EFAV', 'EEM', 'IEFA', 'IEMG', 'IJR', 'IJS', 'IJU', 'IWO', 'IWP',
    'IWR', 'IWS', 'IWV', 'IUSV', 'IUSU', 'SPDW', 'SPEM', 'SPGM', 'SPHB', 'SPHD',
    'SPHQ', 'SPLV', 'SPMO', 'SPMB', 'SPMD', 'SPNE', 'SPG', 'SPGI', 'SCHA', 'SCHD',
    'FNDX', 'FNDA', 'FNDB', 'RSP', 'RPG', 'RPX', 'RZG', 'RZV', 'XMLV', 'XMMO',
    'XSLV', 'XSHQ', 'XSMO', 'XSOE', 'SPXL', 'SPXS', 'TQQQ', 'SOXL', 'SOXS',
    'LABU', 'LABD', 'YANG', 'DUST', 'NUGT', 'JDST', 'KOLD', 'TNA', 'DRIP',
    'GUSH', 'EMSX', 'EUO', 'UGLD', 'DZZ', 'AGQ', 'SQQQ', 'UPRO', 'VIXY',
    'VIXM', 'VXX', 'SVIX', 'UVXY', 'PRO', 'ONEQ', 'VXF', 'IWB', 'BSV', 'BIB',
    'TMF', 'TMV', 'Tmf', 'CURE', 'LEAD', 'FINX', 'AIK', 'THINK', 'BOTZ', 'ROBO',
    'SOCL', 'FM', 'FTC', 'HOOL', 'DTN', 'WOTN', 'TDVI', '芒格', 'KMLM'
]

# Additional high-quality US stocks by sector
ADDITIONAL = [
    'AIG', 'ALLE', 'APLS', 'ARE', 'ATO', 'AVB', 'AVY', 'AIZ', 'AJG', 'ALGN',
    'ALB', 'ALGN', 'ALK', 'AME', 'AMP', 'ANTM', 'ARE', 'AON', 'ARNC', 'ASH',
    'ATO', 'AXON', 'AZO', 'BAX', 'BBY', 'BKR', 'BIO', 'BK', 'BLK', 'BMRN',
    'BSX', 'BXP', 'CAG', 'CAH', 'CBOE', 'CBRE', 'CDW', 'CE', 'CERN', 'CF',
    'CHD', 'CHRW', 'CHTR', 'CI', 'CINF', 'CLX', 'CMA', 'CME', 'CNC', 'COF',
    'COO', 'COTY', 'CTAS', 'CTSH', 'CZR', 'DAR', 'DAT', 'DBX', 'DECK', 'DG',
    'DGX', 'DHI', 'DLTR', 'DOV', 'DRI', 'DTE', 'DUK', 'DVN', 'DXC', 'DXCM',
    'EBAY', 'ECL', 'ED', 'EFX', 'EIX', 'EL', 'EMN', 'EMR', 'ENPH', 'EOG',
    'EQR', 'ESS', 'ES', 'ETN', 'ETR', 'EVRG', 'EW', 'EXC', 'EXPD', 'EXPE',
    'EXR', 'F', 'FANG', 'FAS', 'FE', 'FFIV', 'FIS', 'FITB', 'FLT', 'FMC',
    'FRC', 'FRT', 'FSLR', 'FTI', 'FTNT', 'FTV', 'GD', 'GEN', 'GILD', 'GLW',
    'GNRC', 'GPC', 'GPN', 'GPS', 'GRMN', 'GT', 'GWW', 'HBI', 'HCA', 'HCHP',
    'HE', 'HES', 'HII', 'HIG', 'HPE', 'HPQ', 'HRL', 'HSIC', 'HSY', 'HUM',
    'HIIQ', 'ICLR', 'IDXX', 'IEX', 'IFF', 'ILMN', 'INCY', 'INGN', 'INTU', 'IP',
    'IPG', 'IRM', 'ISRG', 'ITW', 'IVZ', 'J', 'JBHT', 'JCI', 'JKHY', 'JNPR',
    'K', 'KAI', 'KDP', 'KEY', 'KEYS', 'KHC', 'KIM', 'KMB', 'KMI', 'KMX',
    'KNX', 'KSS', 'KYC', 'LH', 'LHX', 'LKQ', 'LLY', 'LMT', 'LNC', 'LNN',
    'LOGI', 'LOW', 'LRCX', 'LSXMR', 'LVS', 'LYB', 'LYV', 'MAA', 'MAS', 'MCD',
    'MCHP', 'MCK', 'MCO', 'MDLA', 'MDT', 'MGM', 'MHK', 'MKC', 'MLHR', 'MMC',
    'MMP', 'MO', 'MPC', 'MPWR', 'MRO', 'MS', 'MSCI', 'MTB', 'MTD', 'MYL',
    'NBL', 'NCLH', 'NDAQ', 'NDSN', 'NEP', 'NEE', 'NEM', 'NHI', 'NI', 'NKE',
    'NLOK', 'NOC', 'NTAP', 'NTRS', 'NUE', 'NVR', 'NWL', 'O', 'OAK', 'OFC',
    'OGE', 'OHI', 'OKE', 'OMC', 'ON', 'ORCL', 'ORLY', 'OSK', 'OZK', 'PAYC',
    'PAYX', 'PBCT', 'PTC', 'PBI', 'PCAR', 'PEAK', 'PEG', 'PFG', 'PG', 'PGR',
    'PH', 'PHM', 'PK', 'PKG', 'PKI', 'PLD', 'PM', 'PNC', 'PNR', 'PNW', 'POOL',
    'PPG', 'PPL', 'PRGO', 'PRU', 'PSA', 'PTC', 'PWR', 'PXD', 'QGEN', 'RCL',
    'REG', 'REHR', 'RF', 'RHI', 'RHT', 'RJF', 'RL', 'RMD', 'RNR', 'ROK',
    'ROL', 'ROP', 'ROST', 'RPM', 'RSG', 'RTN', 'RVTY', 'SABR', 'SAIA', 'SALK',
    'SBAC', 'SBNY', 'SEDG', 'SEE', 'SF', 'SGP', 'SHW', 'SJM', 'SLG', 'SMCI',
    'SNPS', 'SNY', 'SO', 'SPB', 'SPG', 'SPGI', 'SRCL', 'SRE', 'STE', 'STT',
    'STX', 'SVB', 'SWK', 'SYY', 'TAP', 'TCOM', 'TFC', 'TFX', 'TGT', 'TJX',
    'TPR', 'TROW', 'TRMB', 'TROW', 'TRU', 'TSCO', 'TTD', 'TTWO', 'TUP', 'TV',
    'TWLO', 'TXN', 'TYL', 'UA', 'UAA', 'UDR', 'UHS', 'ULTA', 'UNH', 'UNM',
    'UNP', 'UPST', 'URI', 'USB', 'UTHR', 'V', 'VAL', 'VAR', 'VFC', 'VICI',
    'VLO', 'VMC', 'VNO', 'VRSK', 'VRSN', 'VTR', 'VTV', 'WAB', 'WAL', 'WAT',
    'WBA', 'WCG', 'WCN', 'WEC', 'WELL', 'WFC', 'WHR', 'WLTW', 'WM', 'WMB',
    'WMT', 'WRB', 'WRI', 'WSO', 'WST', 'WTW', 'WY', 'WYNN', 'XEL', 'XOM',
    'XRAY', 'YUM', 'ZBH', 'ZION', 'ZM', 'ZS'
]

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def get_existing_symbols():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT symbol FROM daily_ohlcv WHERE symbol NOT LIKE '%.TW' AND symbol NOT LIKE '%^%'")
    existing = {r[0] for r in cur.fetchall()}
    conn.close()
    return existing

def get_all_target_symbols():
    all_symbols = set()
    for lst in [SP500, NASDAQ100, ETFS, ADDITIONAL]:
        for s in lst:
            all_symbols.add(s.strip().replace('.', '_'))
    # Remove existing and indices
    existing = get_existing_symbols()
    to_add = sorted(all_symbols - existing)
    return to_add

def compute_indicators(df):
    """Compute RSI, MACD, SMA for a DataFrame."""
    import numpy as np
    
    df = df.sort_values('Date')
    
    # SMA
    for window in [20, 60, 120]:
        df[f'SMA_{window}'] = df['Close'].rolling(window=window).mean()
    
    # RSI
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['RSI_14'] = 100 - (100 / (1 + rs))
    
    # MACD
    ema12 = df['Close'].ewm(span=12).mean()
    ema26 = df['Close'].ewm(span=26).mean()
    df['MACD'] = ema12 - ema26
    df['MACD_signal'] = df['MACD'].ewm(span=9).mean()
    df['MACD_hist'] = df['MACD'] - df['MACD_signal']
    
    # ATR
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR_14'] = tr.rolling(window=14).mean()
    
    # Bollinger Bands
    sma20 = df['Close'].rolling(window=20).mean()
    std20 = df['Close'].rolling(window=20).std()
    df['BB_upper'] = sma20 + 2 * std20
    df['BB_middle'] = sma20
    df['BB_lower'] = sma20 - 2 * std20
    
    # Volume ratio
    df['Vol_ratio'] = df['Volume'] / df['Volume'].rolling(window=20).mean()
    
    # Change percent
    df['Change_pct'] = df['Close'].pct_change() * 100
    
    return df

def insert_ohlcv(conn, symbol, df):
    cur = conn.cursor()
    rows = []
    for _, row in df.iterrows():
        if pd.isna(row['Close']) or row['Close'] == 0:
            continue
        rows.append((
            symbol, str(row['Date'].date()) if hasattr(row['Date'], 'date') else str(row['Date'])[:10],
            float(row['Open']), float(row['High']), float(row['Low']), float(row['Close']),
            int(row['Volume']),
            float(row.get('Change_pct', 0)) if not pd.isna(row.get('Change_pct')) else 0,
            float(row.get('SMA_20', 0)) if not pd.isna(row.get('SMA_20')) else None,
            float(row.get('SMA_60', 0)) if not pd.isna(row.get('SMA_60')) else None,
            float(row.get('SMA_120', 0)) if not pd.isna(row.get('SMA_120')) else None,
            float(row.get('RSI_14', 0)) if not pd.isna(row.get('RSI_14')) else None,
            float(row.get('ATR_14', 0)) if not pd.isna(row.get('ATR_14')) else None,
            float(row.get('MACD', 0)) if not pd.isna(row.get('MACD')) else None,
            float(row.get('MACD_signal', 0)) if not pd.isna(row.get('MACD_signal')) else None,
            float(row.get('MACD_hist', 0)) if not pd.isna(row.get('MACD_hist')) else None,
            float(row.get('BB_upper', 0)) if not pd.isna(row.get('BB_upper')) else None,
            float(row.get('BB_middle', 0)) if not pd.isna(row.get('BB_middle')) else None,
            float(row.get('BB_lower', 0)) if not pd.isna(row.get('BB_lower')) else None,
            float(row.get('Vol_ratio', 0)) if not pd.isna(row.get('Vol_ratio')) else None,
        ))
    
    if not rows:
        return 0
    
    cur.executemany("""
        INSERT OR IGNORE INTO daily_ohlcv 
        (symbol, date, open, high, low, close, volume, change_pct,
         sma_20, sma_60, sma_120, rsi_14, atr_14, macd, macd_sig, macd_hist,
         bb_upper, bb_middle, bb_lower, vol_ratio)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    conn.commit()
    return len(rows)

def add_to_symbols_table(conn, symbol, group='us_stock'):
    cur = conn.cursor()
    now = datetime.now().isoformat()
    cur.execute("""
        INSERT OR IGNORE INTO symbols (symbol, name, exchange, category, universe_group, last_updated, notes)
        VALUES (?, NULL, NULL, NULL, ?, ?, NULL)
    """, (symbol, group, now))
    conn.commit()

def process_batch(symbols, batch_size=50):
    """Download a batch of symbols and insert into DB."""
    conn = get_db_connection()
    total_added = 0
    errors = []
    
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i+batch_size]
        batch = [s for s in batch if s]  # filter empty
        if not batch:
            continue
            
        print(f"  Batch {i//batch_size + 1}: Downloading {len(batch)} symbols...")
        
        try:
            # Batch download
            data = yf.download(batch, period='2y', group_by='ticker', progress=False, auto_adjust=True)
            
            if data.empty:
                print(f"    Empty data for batch")
                continue
            
            for symbol in batch:
                try:
                    if len(batch) == 1:
                        df = data
                    elif symbol not in data.columns.get_level_values(0):
                        continue
                    else:
                        df = data[symbol]
                    
                    if df.empty or df['Close'].isna().all():
                        print(f"    {symbol}: No data")
                        continue
                    
                    # Compute indicators
                    df = compute_indicators(df)
                    df = df.reset_index()
                    
                    # Insert
                    n = insert_ohlcv(conn, symbol, df)
                    if n > 0:
                        add_to_symbols_table(conn, symbol)
                        total_added += n
                        print(f"    {symbol}: inserted {n} rows")
                    else:
                        print(f"    {symbol}: 0 rows inserted (maybe duplicate)")
                        
                except Exception as e:
                    errors.append((symbol, str(e)))
                    print(f"    {symbol}: ERROR - {e}")
                    continue
            
            # Small delay between batches to avoid rate limit
            if i + batch_size < len(symbols):
                time.sleep(2)
                
        except Exception as e:
            print(f"  Batch error: {e}")
            errors.append(('BATCH', str(e)))
            time.sleep(30)  # longer sleep on batch error
            continue
    
    conn.close()
    return total_added, errors

if __name__ == '__main__':
    import pandas as pd
    
    print("=" * 60)
    print("US STOCK DATABASE EXPANSION")
    print("=" * 60)
    
    existing = get_existing_symbols()
    print(f"\nExisting US symbols: {len(existing)}")
    print(f"Existing: {sorted(existing)}")
    
    all_targets = get_all_target_symbols()
    print(f"\nTarget symbols to add: {len(all_targets)}")
    print(f"First 30: {all_targets[:30]}")
    
    if not all_targets:
        print("No new symbols to add. Database already complete!")
    else:
        print(f"\nStarting download of {len(all_targets)} symbols...")
        print(f"Estimated batches (batch_size=50): {len(all_targets) // 50 + 1}")
        
        total_rows, errors = process_batch(all_targets, batch_size=50)
        
        print(f"\n{'=' * 60}")
        print(f"COMPLETED")
        print(f"Total rows inserted: {total_rows}")
        print(f"Errors: {len(errors)}")
        if errors:
            print("Error details:")
            for sym, err in errors[:10]:
                print(f"  {sym}: {err}")
    
    # Final count
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(DISTINCT symbol) FROM daily_ohlcv 
        WHERE symbol NOT LIKE '%.TW' AND symbol NOT LIKE '%^%'
    """)
    total_us = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT symbol) FROM daily_ohlcv")
    total_all = cur.fetchone()[0]
    conn.close()
    
    print(f"\nFINAL COUNT:")
    print(f"  US symbols: {total_us}")
    print(f"  Total symbols: {total_all}")
    print(f"  Target: 500 US symbols")
    print(f"  Status: {'✓ COMPLETE' if total_us >= 500 else f'IN PROGRESS ({total_us}/500)'}")