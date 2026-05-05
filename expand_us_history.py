# -*- coding: utf-8 -*-
"""美股歷史K線資料庫擴充 - 增至100+檔"""
import sys, sqlite3, os, yfinance
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
DB = f'{DATA_DIR}\\us_history.db'

def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(diff if diff > 0 else 0)
        losses.append(abs(diff) if diff < 0 else 0)
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    rs = avg_gain / avg_loss if avg_loss > 0 else 100
    return 100 - (100 / (1 + rs))

def calc_all_indicators(hist):
    """計算完整技術指標"""
    closes = hist['Close'].tolist()
    highs = hist['High'].tolist()
    lows = hist['Low'].tolist()
    vols = hist['Volume'].tolist()
    n = len(closes)
    
    # SMA
    sma20 = sum(closes[-20:]) / 20 if n >= 20 else closes[-1]
    sma60 = sum(closes[-60:]) / 60 if n >= 60 else sma20
    sma120 = sum(closes[-120:]) / 120 if n >= 120 else sma60
    
    # EMA
    ema12 = closes[-1]
    ema26 = closes[-1]
    if n >= 26:
        k12 = 2 / 13
        k26 = 2 / 27
        ema12 = sum([closes[max(0, n-12+j)] * k12 * ((1-k12)**(11-j)) for j in range(min(12, n))])
        ema26 = sum([closes[max(0, n-26+j)] * k26 * ((1-k26)**(25-j)) for j in range(min(26, n))])
    
    # RSI
    rsi14 = calc_rsi(closes, 14)
    rsi7 = calc_rsi(closes, 7)
    rsi28 = calc_rsi(closes, 28)
    
    # MACD
    macd_line = ema12 - ema26
    macd_signal = macd_line  # simplified
    macd_hist = macd_line * 0.5
    
    # Bollinger Bands
    period = 20
    start = max(0, n - period)
    slice_ = closes[start:n]
    sma20_bb = sum(slice_) / len(slice_)
    std = (sum([(c - sma20_bb)**2 for c in slice_]) / len(slice_))**0.5
    bb_upper = sma20_bb + 2 * std
    bb_middle = sma20_bb
    bb_lower = sma20_bb - 2 * std
    
    # ATR
    atr = 0
    if n > 14:
        trs = [max(highs[j] - lows[j], abs(highs[j] - closes[j-1]), abs(lows[j] - closes[j-1])) 
               for j in range(max(1, n-13), n)]
        atr = sum(trs) / len(trs)
    
    # KDJ
    period = 9
    start = max(0, n - period)
    low_min = min(lows[start:n])
    high_max = max(highs[start:n])
    rsv = (closes[-1] - low_min) / (high_max - low_min) * 100 if high_max > low_min else 50
    kdj_k = rsv
    kdj_d = kdj_k * 0.5 + 50 * 0.5
    kdj_j = kdj_k * 3 - kdj_d * 2
    
    # CCI
    typical = (closes[-1] + highs[-1] + lows[-1]) / 3
    sma_typical = typical
    cci = (typical - sma_typical) / 0.015 / 0.01 if sma_typical > 0 else 0
    
    # Zone
    if rsi14 < 30:
        zone = 'OVERSOLD'
    elif rsi14 < 40:
        zone = 'NEUTRAL_LOW'
    elif rsi14 < 70:
        zone = 'NEUTRAL'
    else:
        zone = 'OVERBOUGHT'
    
    return {
        'sma_20': sma20, 'sma_60': sma60, 'sma_120': sma120,
        'ema_12': ema12, 'ema_26': ema26,
        'rsi_14': rsi14, 'rsi_7': rsi7, 'rsi_28': rsi28,
        'macd_line': macd_line, 'macd_signal': macd_signal, 'macd_hist': macd_hist,
        'bb_upper': bb_upper, 'bb_middle': bb_middle, 'bb_lower': bb_lower,
        'atr_14': atr, 'kdj_k': kdj_k, 'kdj_d': kdj_d, 'kdj_j': kdj_j,
        'cci_14': cci, 'zone': zone
    }

def add_stocks():
    """新增股票"""
    print('=== 擴充美股歷史K線資料庫 ===\n')
    
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    # 確認表格結構
    cur.execute('''CREATE TABLE IF NOT EXISTS daily_ohlcv (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        date TEXT NOT NULL,
        open REAL, high REAL, low REAL, close REAL, volume INTEGER,
        sma_20 REAL, sma_60 REAL, sma_120 REAL,
        ema_12 REAL, ema_26 REAL,
        rsi_14 REAL, rsi_7 REAL, rsi_28 REAL,
        macd_line REAL, macd_signal REAL, macd_hist REAL,
        bb_upper REAL, bb_middle REAL, bb_lower REAL,
        atr_14 REAL, kdj_k REAL, kdj_d REAL, kdj_j REAL,
        cci_14 REAL, zone TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(symbol, date)
    )''')
    
    cur.execute('''CREATE TABLE IF NOT EXISTS stock_summary (
        symbol TEXT PRIMARY KEY,
        name TEXT, sector TEXT,
        current_price REAL, current_rsi REAL, current_zone TEXT,
        high_52w REAL, low_52w REAL, total_records INTEGER, last_updated TEXT
    )''')
    conn.commit()
    
    # 新增股票列表
    NEW_STOCKS = [
        # More Tech
        ('ON', 'ON Semi'), ('MPWR', 'Monolithic'), ('GLW', 'Corning'),
        ('NOC', 'Northrop'), ('LMT', 'Lockheed'), ('RTX', 'RTX'),
        ('GD', 'General Dynamics'), ('MSI', 'Motorola'),
        # More Finance
        ('AXP', 'Amex'), ('BRK-B', 'Berkshire'), ('C', 'Citigroup'),
        ('AXS', 'Axa'), ('PRU', 'Prudential'),
        # More Energy
        ('PSX', 'Phillips 66'), ('VLO', 'Valero'),
        ('OXY', 'Occidental'), ('HAL', 'Halliburton'),
        # More Healthcare
        ('BIIB', 'Biogen'), ('REGN', 'Regeneron'), ('MRNA', 'Moderna'),
        ('GILD', 'Gilead'), ('VRTX', 'Vertex'),
        # More Consumer
        ('WMT', 'Walmart'), ('HD', 'Home Depot'), ('LOW', "Lowe's"),
        ('TGT', 'Target'), ('COST', 'Costco'),
        ('ROST', 'Ross Stores'), ('DLTR', 'Dollar Tree'),
        # More Industrial
        ('MMM', '3M'), ('UPS', 'UPS'), ('FDX', 'FedEx'),
        ('RSG', 'Republic Services'), ('WM', 'Waste Management'),
        # More Telecom
        ('TMUS', 'T-Mobile'), ('S', 'Sprint'),
        # More Real Estate
        ('AMT', 'American Tower'), ('PLD', 'Prologis'),
        ('EQIX', 'Equinix'), ('SPG', 'Simon Property'),
        # More Utilities
        ('NEE', 'NextEra'), ('DUK', 'Duke'), ('SO', 'Southern'),
        # More Materials
        ('LIN', 'Linde'), ('APD', 'Air Products'), ('ECL', 'Ecolab'),
        # More ETFs
        ('IYR', 'Real Estate ETF'), ('IYF', 'Financials ETF'),
        ('IYE', 'Energy ETF'), ('IYM', 'Materials ETF'),
        ('IAI', 'Broker ETF'), ('IYZ', 'Telecom ETF'),
        ('SOXL', 'SOXL'), ('TNA', 'TNA'),
        ('EDC', 'EDC'), ('UMDD', 'UMDD'),
        # Crypto
        ('MSTR', 'MicroStrategy'), ('COIN', 'Coinbase'),
        # More AI/Tech
        ('PANW', 'Palo Alto'), ('FTNT', 'Fortinet'),
        ('ZS', 'Zscaler'), ('CRWD', 'CrowdStrike'),
        ('GEN', 'Gen Digital'), ('CDNS', 'Cadence'),
        ('SNPS', 'Synopsys'), ('MRVL', 'Marvell'),
        ('ARM', 'ARM Holdings'), ('SMCI', 'Super Micro'),
    ]
    
    added = 0
    for sym, name in NEW_STOCKS:
        try:
            cur.execute('SELECT COUNT(*) FROM stock_summary WHERE symbol=?', (sym,))
            if cur.fetchone()[0] > 0:
                continue
            
            print(f'+ {sym} {name}...', end='', flush=True)
            
            t = yfinance.Ticker(sym)
            hist = t.history(period='3y')
            
            if len(hist) < 500:
                print(f' 不足({len(hist)})')
                continue
            
            closes = hist['Close'].tolist()
            dates = hist.index.strftime('%Y-%m-%d').tolist()
            
            # Insert daily_ohlcv
            for i in range(len(hist)):
                row = hist.iloc[i]
                ind = calc_all_indicators(hist.iloc[max(0,i):i+1])
                
                cur.execute('''INSERT OR IGNORE INTO daily_ohlcv 
                    (symbol, date, open, high, low, close, volume,
                    sma_20, sma_60, sma_120, ema_12, ema_26,
                    rsi_14, rsi_7, rsi_28, macd_line, macd_signal, macd_hist,
                    bb_upper, bb_middle, bb_lower, atr_14,
                    kdj_k, kdj_d, kdj_j, cci_14, zone, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (sym, dates[i], row['Open'], row['High'], row['Low'], row['Close'], row['Volume'],
                     ind['sma_20'], ind['sma_60'], ind['sma_120'], ind['ema_12'], ind['ema_26'],
                     ind['rsi_14'], ind['rsi_7'], ind['rsi_28'], ind['macd_line'], ind['macd_signal'], ind['macd_hist'],
                     ind['bb_upper'], ind['bb_middle'], ind['bb_lower'], ind['atr_14'],
                     ind['kdj_k'], ind['kdj_d'], ind['kdj_j'], ind['cci_14'], ind['zone'], dates[i]))
            
            conn.commit()
            
            # Summary
            rsi = calc_rsi(closes)
            high_52w = max(closes[-252:]) if len(closes) >= 252 else max(closes)
            low_52w = min(closes[-252:]) if len(closes) >= 252 else min(closes)
            zone = 'OVERSOLD' if rsi < 30 else 'NEUTRAL_LOW' if rsi < 40 else 'NEUTRAL' if rsi < 70 else 'OVERBOUGHT'
            
            cur.execute('''INSERT OR REPLACE INTO stock_summary 
                (symbol, name, sector, current_price, current_rsi, current_zone, high_52w, low_52w, total_records, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (sym, name, 'US_STOCK', closes[-1], rsi, zone, high_52w, low_52w, len(hist), dates[-1]))
            conn.commit()
            
            print(f' {len(hist)}筆')
            added += 1
            
        except Exception as e:
            print(f' ERR: {e}')
    
    conn.close()
    return added

def main():
    print('=== 美股歷史K線資料庫擴充 ===\n')
    added = add_stocks()
    
    print(f'\n=== 完成: 新增{added}檔 ===')
    
    # Final status
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    syms = cur.execute('SELECT COUNT(DISTINCT symbol) FROM daily_ohlcv').fetchone()[0]
    total = cur.execute('SELECT COUNT(*) FROM daily_ohlcv').fetchone()[0]
    recent = cur.execute('SELECT date FROM daily_ohlcv ORDER BY date DESC LIMIT 1').fetchone()[0]
    size = os.path.getsize(DB) / 1024
    print(f'\n📊 us_history.db: {syms}檔, {total}筆, 最新:{recent}')
    print(f'大小: {size:.0f} KB')
    conn.close()

if __name__ == '__main__':
    main()