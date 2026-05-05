# -*- coding: utf-8 -*-
"""Build Comprehensive US Stock Historical K-Line Database"""
import sys, yfinance, sqlite3, json
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
DB = f'{DATA_DIR}\\us_history.db'

# Comprehensive US Stock/ETF Watchlist
WATCHLIST = {
    # Major ETFs
    'SPY': 'S&P 500 ETF', 'QQQ': 'NASDAQ ETF', 'DIA': 'Dow Jones ETF',
    'IWM': 'Russell 2000', 'EEM': 'Emerging Markets', 'TLT': '20Y Treasury',
    'GLD': 'Gold ETF', 'SLV': 'Silver ETF', 'USO': 'Oil ETF',
    'XLE': 'Energy Sector', 'XLF': 'Financial Sector', 'XLV': 'Healthcare',
    'XLI': 'Industrial', 'XLK': 'Technology', 'XLY': 'Consumer Discretionary',
    'XLP': 'Consumer Staples', 'XLU': 'Utilities', 'XLB': 'Materials',
    'VGT': 'Info Tech ETF', 'VHT': 'Healthcare ETF', 'VNQ': 'Real Estate',
    # Leveraged ETFs
    'SSO': 'S&P 500 2x', 'QLD': 'NASDAQ 2x', 'TQQQ': 'NASDAQ 3x',
    'SPXL': 'S&P 500 3x', 'FANG': 'FANG+ ETF', 'ARKK': 'ARK Innovation',
    # Mega Cap Tech
    'NVDA': 'Nvidia', 'AAPL': 'Apple', 'MSFT': 'Microsoft', 'GOOGL': 'Alphabet',
    'AMZN': 'Amazon', 'META': 'Meta', 'TSLA': 'Tesla', 'BRK.B': 'Berkshire',
    'JPM': 'JPMorgan', 'V': 'Visa', 'MA': 'Mastercard', 'JNJ': 'Johnson & Johnson',
    'UNH': 'UnitedHealth', 'PG': 'Procter & Gamble', 'HD': 'Home Depot',
    # AI/Tech Semis
    'AMD': 'AMD', 'INTC': 'Intel', 'ASML': 'ASML', 'TSM': 'Taiwan Semi',
    'MU': 'Micron', 'AMAT': 'Applied Materials', 'LRCX': 'Lam Research',
    'KLAC': 'KLA Corp', 'QRVO': 'Qorvo', 'NXPI': 'NXP Semi',
    # Internet/Software
    'NFLX': 'Netflix', 'DIS': 'Disney', 'PYPL': 'PayPal', 'SQ': 'Block',
    'COIN': 'Coinbase', 'UBER': 'Uber', 'ABNB': 'Airbnb', 'SNOW': 'Snowflake',
    'PLTR': 'Palantir', 'CRWD': 'CrowdStrike', 'NET': 'Cloudflare',
    # Growth/Innovation
    'CRM': 'Salesforce', 'NOW': 'ServiceNow', 'INTU': 'Intuit',
    'UBER': 'Uber', 'LYFT': 'Lyft', 'COIN': 'Coinbase',
    # Finance
    'BAC': 'Bank of America', 'GS': 'Goldman Sachs', 'MS': 'Morgan Stanley',
    'WFC': 'Wells Fargo', 'AXP': 'American Express', 'BLK': 'BlackRock',
    # Oil/Energy
    'XOM': 'Exxon', 'CVX': 'Chevron', 'COP': 'ConocoPhillips',
    'SLB': 'Schlumberger', 'EOG': 'EOG Resources',
}

def calc_sma(data, period):
    if len(data) < period:
        return None
    return sum(data[-period:]) / period

def calc_ema(data, period):
    if len(data) < period:
        return None
    multiplier = 2 / (period + 1)
    ema = sum(data[:period]) / period
    for price in data[period:]:
        ema = (price - ema) * multiplier + ema
    return ema

def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50
    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(diff if diff > 0 else 0)
        losses.append(abs(diff) if diff < 0 else 0)
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    rs = avg_gain / avg_loss if avg_loss > 0 else 100
    return 100 - (100 / (1 + rs))

def calc_macd(closes, fast=12, slow=26, signal=9):
    if len(closes) < slow + signal:
        return None, None, None
    ema_fast = calc_ema(closes, fast)
    ema_slow = calc_ema(closes, slow)
    macd_line = ema_fast - ema_slow
    macd_values = []
    for i in range(slow, len(closes)):
        e_f = calc_ema(closes[:i+1], fast)
        e_s = calc_ema(closes[:i+1], slow)
        macd_values.append(e_f - e_s)
    if len(macd_values) < signal:
        return macd_line, 0, 0
    ema_signal = calc_ema(macd_values, signal)
    hist = macd_line - ema_signal
    return macd_line, ema_signal, hist

def calc_bb(closes, period=20):
    if len(closes) < period:
        return None, None, None
    sma = sum(closes[-period:]) / period
    std = (sum((c - sma) ** 2 for c in closes[-period:]) / period) ** 0.5
    return sma + 2 * std, sma, sma - 2 * std

def calc_atr(highs, lows, closes, period=14):
    if len(highs) < period + 1:
        return None
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        trs.append(tr)
    return sum(trs[-period:]) / period if len(trs) >= period else sum(trs) / len(trs)

def calc_kdj(highs, lows, closes, period=9):
    if len(closes) < period:
        return 50, 50, 50
    lowest_lows = [min(lows[max(0,i-period+1):i+1]) for i in range(period-1, len(lows))]
    highest_highs = [max(highs[max(0,i-period+1):i+1]) for i in range(period-1, len(highs))]
    k_values = []
    for i in range(period - 1, len(closes)):
        ll = lowest_lows[i - (period - 1)]
        hh = highest_highs[i - (period - 1)]
        rsv = (closes[i] - ll) / (hh - ll) * 100 if hh != ll else 50
        k = 2/3 * (k_values[-1] if k_values else 50) + 1/3 * rsv
        k_values.append(k)
    d = sum(k_values[-3:]) / 3 if len(k_values) >= 3 else sum(k_values) / len(k_values)
    k = sum(k_values[-3:]) / 3 if len(k_values) >= 3 else sum(k_values) / len(k_values)
    j = 3 * k - 2 * d
    return k, d, j

def detect_zone(rsi):
    if rsi < 30:
        return 'OVERSOLD'
    elif rsi < 40:
        return 'NEUTRAL_LOW'
    elif rsi < 60:
        return 'NEUTRAL'
    elif rsi < 70:
        return 'NEUTRAL_HIGH'
    elif rsi < 80:
        return 'OVERBOUGHT'
    else:
        return 'EXTREME'

def build_us_history_db():
    print('╔══════════════════════════════════════════════════════╗')
    print('║   US Stock Historical K-Line Database Builder      ║')
    print('╚══════════════════════════════════════════════════════╝')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
    
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    # Main OHLCV table
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
        cci_14 REAL,
        zone TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(symbol, date)
    )''')
    
    # Summary table
    cur.execute('''CREATE TABLE IF NOT EXISTS stock_summary (
        symbol TEXT PRIMARY KEY,
        name TEXT,
        sector TEXT,
        current_price REAL, current_rsi REAL, current_zone TEXT,
        high_52w REAL, low_52w REAL,
        avg_volume INTEGER,
        total_records INTEGER,
        last_updated TEXT
    )''')
    
    # Watchlist table
    cur.execute('''CREATE TABLE IF NOT EXISTS watchlist (
        symbol TEXT PRIMARY KEY,
        name TEXT,
        sector TEXT,
        added_at TEXT
    )''')
    
    conn.commit()
    
    # Insert watchlist
    for sym, name in WATCHLIST.items():
        sector = 'ETF' if sym.isupper() and len(sym) <= 5 else 'STOCK'
        cur.execute('INSERT OR IGNORE INTO watchlist VALUES (?, ?, ?, ?)', 
                   (sym, name, sector, datetime.now().isoformat()))
    conn.commit()
    
    total = len(WATCHLIST)
    total_records = 0
    failed = []
    
    for i, (sym, name) in enumerate(WATCHLIST.items(), 1):
        sector = 'ETF' if sym.isupper() and len(sym) <= 5 else 'STOCK'
        print(f'[{i}/{total}] {sym} ({name})...', end=' ', flush=True)
        
        try:
            t = yfinance.Ticker(sym)
            hist = t.history(period='3y')
            
            if len(hist) < 100:
                print(f'不足 {len(hist)}筆')
                failed.append((sym, name, 'insufficient data'))
                continue
            
            opens = hist['Open'].tolist()
            highs = hist['High'].tolist()
            lows = hist['Low'].tolist()
            closes = hist['Close'].tolist()
            volumes = hist['Volume'].tolist()
            dates = hist.index.strftime('%Y-%m-%d').tolist()
            
            records = 0
            latest = {}
            
            for j in range(60, len(closes)):
                date = dates[j]
                close = closes[j]
                open_p = opens[j]
                high = highs[j]
                low = lows[j]
                vol = volumes[j]
                
                # SMA
                sma20 = calc_sma(closes[:j+1], 20)
                sma60 = calc_sma(closes[:j+1], 60)
                sma120 = calc_sma(closes[:j+1], 120)
                
                # EMA
                ema12 = calc_ema(closes[:j+1], 12)
                ema26 = calc_ema(closes[:j+1], 26)
                
                # RSI
                rsi14 = calc_rsi(closes[:j+1], 14)
                rsi7 = calc_rsi(closes[:j+1], 7)
                rsi28 = calc_rsi(closes[:j+1], 28)
                
                # MACD
                macd_line, macd_sig, macd_hist = calc_macd(closes[:j+1])
                
                # Bollinger Bands
                bb_u, bb_m, bb_l = calc_bb(closes[:j+1])
                
                # ATR
                atr = calc_atr(highs[:j+1], lows[:j+1], closes[:j+1])
                
                # KDJ
                k, d, j_val = calc_kdj(highs[:j+1], lows[:j+1], closes[:j+1])
                
                # CCI
                typical = (high + low + close) / 3
                sma_tp = sum([(highs[p] + lows[p] + closes[p]) / 3 for p in range(max(0,j-13), j+1)]) / min(14, j+1)
                cci = (typical - sma_tp) / (0.015 * sum(abs((highs[p] + lows[p] + closes[p]) / 3 - sma_tp) for p in range(max(0,j-13), j+1)) / min(14, j+1)) if sma_tp else 0
                
                zone = detect_zone(rsi14)
                
                cur.execute('''INSERT OR REPLACE INTO daily_ohlcv 
                    (symbol, date, open, high, low, close, volume, sma_20, sma_60, sma_120,
                     ema_12, ema_26, rsi_14, rsi_7, rsi_28, macd_line, macd_signal, macd_hist,
                     bb_upper, bb_middle, bb_lower, atr_14, kdj_k, kdj_d, kdj_j, cci_14, zone)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (sym, date, open_p, high, low, close, int(vol), sma20, sma60, sma120,
                     ema12, ema26, rsi14, rsi7, rsi28, macd_line, macd_sig, macd_hist,
                     bb_u, bb_m, bb_l, atr, k, d, j_val, cci, zone))
                
                records += 1
                latest = {'date': date, 'close': close, 'rsi14': rsi14, 'zone': zone}
            
            if records > 0:
                conn.commit()
                
                # Summary
                high_52w = max(closes[-252:]) if len(closes) >= 252 else max(closes)
                low_52w = min(closes[-252:]) if len(closes) >= 252 else min(closes)
                avg_vol = int(sum(volumes[-252:]) / min(252, len(volumes))) if len(volumes) >= 21 else int(sum(volumes) / len(volumes))
                
                cur.execute('''INSERT OR REPLACE INTO stock_summary 
                    (symbol, name, sector, current_price, current_rsi, current_zone, high_52w, low_52w, avg_volume, total_records, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (sym, name, sector, latest['close'], latest['rsi14'], latest['zone'],
                     high_52w, low_52w, avg_vol, records, latest['date']))
                conn.commit()
                
                total_records += records
                print(f'{records}筆 RSI={latest["rsi14"]:.1f} {latest["zone"]}')
            else:
                failed.append((sym, name, 'no records'))
                
        except Exception as e:
            print(f'ERROR: {e}')
            failed.append((sym, name, str(e)))
    
    # Report
    print(f'\n\n{"="*50}')
    print(f'=== US History Database Built ===')
    print(f'{"="*50}')
    
    cur.execute('SELECT COUNT(DISTINCT symbol) FROM daily_ohlcv')
    syms = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM daily_ohlcv')
    total = cur.fetchone()[0]
    cur.execute('SELECT MIN(date), MAX(date) FROM daily_ohlcv')
    dates = cur.fetchone()
    cur.execute('SELECT COUNT(*) FROM stock_summary')
    summaries = cur.fetchone()[0]
    
    print(f'Symbols: {syms}')
    print(f'Total Records: {total:,}')
    print(f'Date Range: {dates[0]} ~ {dates[1]}')
    print(f'Summaries: {summaries}')
    print(f'Failed: {len(failed)}')
    
    if failed:
        print(f'\nFailed symbols:')
        for sym, name, reason in failed:
            print(f'  {sym}: {name} - {reason}')
    
    # Current RSI distribution
    print(f'\n=== Current RSI Distribution ===')
    cur.execute('''SELECT zone, COUNT(*) FROM stock_summary GROUP BY zone ORDER BY 
        CASE zone WHEN 'OVERSOLD' THEN 1 WHEN 'NEUTRAL_LOW' THEN 2 WHEN 'NEUTRAL' THEN 3 
        WHEN 'NEUTRAL_HIGH' THEN 4 WHEN 'OVERBOUGHT' THEN 5 WHEN 'EXTREME' THEN 6 END''')
    for r in cur.fetchall():
        zone = r[0]
        cnt = r[1]
        icon = '🟢' if zone == 'OVERSOLD' else ('🔴' if zone in ('OVERBOUGHT', 'EXTREME') else '⚪')
        print(f'  {icon} {zone}: {cnt} stocks')
    
    # Size
    import os
    db_size = os.path.getsize(DB) / (1024 * 1024)
    print(f'\nDB Size: {db_size:.1f} MB')
    
    conn.close()

if __name__ == '__main__':
    build_us_history_db()