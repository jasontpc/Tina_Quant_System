# -*- coding: utf-8 -*-
"""Sherry - US ETF DCA Strategy System
Team: Sherry
Focus: US ETF Dollar-Cost Averaging for Steady Profits
"""
import sys, yfinance, sqlite3, json
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
DB = f'{DATA_DIR}\\sherry_etf.db'

# US ETF Watchlist - Focused on DCA-friendly ETFs
ETF_WATCHLIST = {
    # Core Index ETFs
    'SPY': ('S&P 500 ETF', 'Index', 'Large Cap', 500),
    'QQQ': ('NASDAQ 100 ETF', 'Index', 'Tech/Growth', 500),
    'VTI': ('Total Stock Market', 'Index', 'Broad', 400),
    'IVV': ('S&P 500 ETF', 'Index', 'Large Cap', 450),
    'IWM': ('Russell 2000 ETF', 'Index', 'Small Cap', 300),
    
    # Sector ETFs
    'XLK': ('Technology Sector', 'Sector', 'Tech', 400),
    'XLF': ('Financial Sector', 'Sector', 'Finance', 350),
    'XLV': ('Healthcare Sector', 'Sector', 'Healthcare', 350),
    'XLE': ('Energy Sector', 'Sector', 'Energy', 300),
    'XLY': ('Consumer Discretionary', 'Sector', 'Consumer', 350),
    'XLP': ('Consumer Staples', 'Sector', 'Defensive', 300),
    'XLI': ('Industrial Sector', 'Sector', 'Industrial', 350),
    'XLB': ('Materials Sector', 'Sector', 'Materials', 300),
    'XLU': ('Utilities Sector', 'Sector', 'Defensive', 300),
    'XLRE': ('Real Estate Sector', 'Sector', 'REIT', 300),
    
    # Strategic ETFs
    'VGT': ('Info Tech ETF', 'Sector', 'Tech', 400),
    'VHT': ('Healthcare ETF', 'Sector', 'Healthcare', 350),
    'VYM': ('High Dividend ETF', 'Income', 'Dividend', 350),
    'VNQ': ('Real Estate ETF', 'Sector', 'REIT', 350),
    'SCHD': ('Schwab US Dividend', 'Income', 'Dividend', 350),
    
    # Bond/Income ETFs
    'BND': ('Total Bond ETF', 'Bond', 'Investment', 300),
    'AGG': ('US Aggregate Bond', 'Bond', 'Investment', 300),
    'TLT': ('20+ Year Treasury', 'Bond', 'Interest Rate', 250),
    'HYG': ('High Yield Bond', 'Bond', 'Credit', 300),
    'LQD': ('Investment Grade Bond', 'Bond', 'Credit', 300),
    
    # International
    'VEU': ('Total World Stock', 'International', 'Broad', 350),
    'VXUS': ('Total Intl Stock', 'International', 'Broad', 350),
    'EFA': ('EAFE ETF', 'International', 'Developed', 350),
    'EEM': ('Emerging Markets', 'International', 'Emerging', 300),
    
    # Leveraged/Growth (for aggressive DCA)
    'SSO': ('S&P 500 2x', 'Leveraged', '2x Leverage', 200),
    'QLD': ('NASDAQ 2x', 'Leveraged', '2x Leverage', 200),
    'TQQQ': ('NASDAQ 3x', 'Leveraged', '3x Leverage', 150),
    'SPXL': ('S&P 500 3x', 'Leveraged', '3x Leverage', 150),
    
    # Commodities
    'GLD': ('Gold ETF', 'Commodity', 'Gold', 300),
    'SLV': ('Silver ETF', 'Commodity', 'Silver', 250),
    'USO': ('Oil ETF', 'Commodity', 'Oil', 200),
}

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

def detect_zone(rsi):
    if rsi < 30:
        return 'OVERSOLD'
    elif rsi < 40:
        return 'NEUTRAL_LOW'
    elif rsi < 50:
        return 'NEUTRAL'
    elif rsi < 60:
        return 'NEUTRAL_HIGH'
    elif rsi < 70:
        return 'OVERBOUGHT'
    else:
        return 'EXTREME'

def build_sherry_db():
    """Build Sherry US ETF Database"""
    print('╔══════════════════════════════════════════════════════╗')
    print('║     Sherry - US ETF DCA Database Builder         ║')
    print('╚══════════════════════════════════════════════════════╝')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
    
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    # Main ETF data table
    cur.execute('''CREATE TABLE IF NOT EXISTS etf_daily (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        date TEXT NOT NULL,
        open REAL, high REAL, low REAL, close REAL, volume INTEGER,
        sma_20 REAL, sma_50 REAL, sma_200 REAL,
        ema_12 REAL, ema_26 REAL,
        rsi_14 REAL, rsi_7 REAL,
        macd_line REAL, macd_signal REAL, macd_hist REAL,
        bb_upper REAL, bb_middle REAL, bb_lower REAL,
        atr_14 REAL,
        zone TEXT,
        yield_12m REAL,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(symbol, date)
    )''')
    
    # ETF summary
    cur.execute('''CREATE TABLE IF NOT EXISTS etf_summary (
        symbol TEXT PRIMARY KEY,
        name TEXT,
        category TEXT,
        focus TEXT,
        current_price REAL,
        current_rsi REAL,
        current_zone TEXT,
        high_52w REAL,
        low_52w REAL,
        avg_volume INTEGER,
        yield_12m REAL,
        expense_ratio REAL,
        aum REAL,
        total_records INTEGER,
        last_updated TEXT
    )''')
    
    # DCA signals
    cur.execute('''CREATE TABLE IF NOT EXISTS dca_signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        signal_date TEXT NOT NULL,
        signal_type TEXT,
        price REAL,
        rsi REAL,
        zone TEXT,
        reason TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(symbol, signal_date)
    )''')
    
    # DCA simulation table
    cur.execute('''CREATE TABLE IF NOT EXISTS dca_simulation (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        start_date TEXT NOT NULL,
        monthly_amount REAL DEFAULT 1000,
        shares REAL DEFAULT 0,
        total_invested REAL DEFAULT 0,
        current_value REAL DEFAULT 0,
        total_return REAL DEFAULT 0,
        return_pct REAL DEFAULT 0,
        avg_cost REAL DEFAULT 0,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    
    total = len(ETF_WATCHLIST)
    total_records = 0
    
    print(f'ETF Watchlist: {total} 檔\n')
    
    for i, (sym, info) in enumerate(ETF_WATCHLIST.items(), 1):
        name, category, focus, priority = info
        print(f'[{i}/{total}] {sym} ({name})...', end=' ', flush=True)
        
        try:
            t = yfinance.Ticker(sym)
            hist = t.history(period='5y')
            
            if len(hist) < 100:
                print(f'不足 {len(hist)}筆')
                continue
            
            opens = hist['Open'].tolist()
            highs = hist['High'].tolist()
            lows = hist['Low'].tolist()
            closes = hist['Close'].tolist()
            volumes = hist['Volume'].tolist()
            dates = hist.index.strftime('%Y-%m-%d').tolist()
            
            # Get ETF info
            info_data = t.info
            expense_ratio = info_data.get('expenseRatio', 0) or 0
            aum = info_data.get('totalAssets', 0) or 0
            yield_12m = info_data.get('trailingAnnualDividendYield', 0) or 0
            
            records = 0
            latest = {}
            
            for j in range(60, len(closes)):
                date = dates[j]
                close = closes[j]
                
                # SMA
                sma20 = calc_sma(closes[:j+1], 20)
                sma50 = calc_sma(closes[:j+1], 50)
                sma200 = calc_sma(closes[:j+1], 200)
                
                # EMA
                ema12 = calc_ema(closes[:j+1], 12)
                ema26 = calc_ema(closes[:j+1], 26)
                
                # RSI
                rsi14 = calc_rsi(closes[:j+1], 14)
                rsi7 = calc_rsi(closes[:j+1], 7)
                
                # MACD
                ema12_val = calc_ema(closes[:j+1], 12)
                ema26_val = calc_ema(closes[:j+1], 26)
                macd_line = ema12_val - ema26_val if ema12_val and ema26_val else 0
                macd_sig = calc_ema(closes[:j+1], 9) if j >= 26 else 0
                macd_hist = macd_line - macd_sig if macd_sig else 0
                
                # BB
                period = 20
                if j >= period - 1:
                    sma = sum(closes[j-19:j+1]) / 20
                    std = (sum((c - sma) ** 2 for c in closes[j-19:j+1]) / 20) ** 0.5
                    bb_u = sma + 2 * std
                    bb_m = sma
                    bb_l = sma - 2 * std
                else:
                    bb_u = bb_m = bb_l = close
                
                # ATR
                trs = []
                for k in range(1, 15):
                    tr = max(highs[j-k] - lows[j-k], abs(highs[j-k] - closes[j-k-1]))
                    trs.append(tr)
                atr = sum(trs) / 14 if len(trs) >= 14 else sum(trs) / len(trs)
                
                zone = detect_zone(rsi14)
                
                cur.execute('''INSERT OR REPLACE INTO etf_daily 
                    (symbol, date, open, high, low, close, volume, sma_20, sma_50, sma_200,
                     ema_12, ema_26, rsi_14, rsi_7, macd_line, macd_signal, macd_hist,
                     bb_upper, bb_middle, bb_lower, atr_14, zone, yield_12m)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (sym, date, opens[j], highs[j], lows[j], close, int(volumes[j]),
                     sma20, sma50, sma200, ema12, ema26, rsi14, rsi7,
                     macd_line, macd_sig, macd_hist, bb_u, bb_m, bb_l, atr, zone, yield_12m))
                
                records += 1
                latest = {'date': date, 'close': close, 'rsi14': rsi14, 'zone': zone}
            
            if records > 0:
                conn.commit()
                
                high_52w = max(closes[-252:]) if len(closes) >= 252 else max(closes)
                low_52w = min(closes[-252:]) if len(closes) >= 252 else min(closes)
                avg_vol = int(sum(volumes[-252:]) / min(252, len(volumes))) if len(volumes) >= 21 else int(sum(volumes) / len(volumes))
                
                cur.execute('''INSERT OR REPLACE INTO etf_summary 
                    (symbol, name, category, focus, current_price, current_rsi, current_zone,
                     high_52w, low_52w, avg_volume, yield_12m, expense_ratio, aum, total_records, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (sym, name, category, focus, latest['close'], latest['rsi14'], latest['zone'],
                     high_52w, low_52w, avg_vol, yield_12m, expense_ratio, aum, records, latest['date']))
                conn.commit()
                
                total_records += records
                print(f'{records}筆 RSI={latest["rsi14"]:.1f} {latest["zone"]}')
        
        except Exception as e:
            print(f'ERROR: {e}')
    
    # Final stats
    print(f'\n\n{"="*50}')
    print(f'=== Sherry ETF Database Built ===')
    print(f'{"="*50}')
    
    cur.execute('SELECT COUNT(DISTINCT symbol) FROM etf_daily')
    syms = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM etf_daily')
    total = cur.fetchone()[0]
    cur.execute('SELECT MIN(date), MAX(date) FROM etf_daily')
    dates = cur.fetchone()
    cur.execute('SELECT COUNT(*) FROM etf_summary')
    summaries = cur.fetchone()[0]
    
    print(f'ETFs: {syms}')
    print(f'Total Records: {total:,}')
    print(f'Date Range: {dates[0]} ~ {dates[1]}')
    print(f'Summaries: {summaries}')
    
    import os
    db_size = os.path.getsize(DB) / (1024 * 1024)
    print(f'DB Size: {db_size:.1f} MB')
    
    # RSI Distribution
    print(f'\n=== RSI Zone Distribution ===')
    cur.execute('''SELECT current_zone, COUNT(*) FROM etf_summary GROUP BY current_zone ORDER BY 
        CASE current_zone WHEN 'OVERSOLD' THEN 1 WHEN 'NEUTRAL_LOW' THEN 2 WHEN 'NEUTRAL' THEN 3 
        WHEN 'NEUTRAL_HIGH' THEN 4 WHEN 'OVERBOUGHT' THEN 5 WHEN 'EXTREME' THEN 6 END''')
    for r in cur.fetchall():
        zone = r[0]
        cnt = r[1]
        icon = '🟢' if zone == 'OVERSOLD' else ('🔴' if zone in ('OVERBOUGHT','EXTREME') else '⚪')
        print(f'  {icon} {zone}: {cnt} ETFs')
    
    conn.close()

if __name__ == '__main__':
    build_sherry_db()