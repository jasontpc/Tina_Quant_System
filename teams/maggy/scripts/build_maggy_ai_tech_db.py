# -*- coding: utf-8 -*-
"""Maggy AI/Tech Stock Database - Focused on AI and Technology"""
import sys, yfinance, sqlite3, json
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
DB = f'{DATA_DIR}\\maggy_ai_tech.db'

# AI & Tech Focused Stock List
AI_TECH_STOCKS = {
    # AI Infrastructure
    'NVDA': ('Nvidia', 'AI/GPU', 'Leader'),
    'AMD': ('AMD', 'AI/GPU', 'Challenger'),
    'INTC': ('Intel', 'AI/CPU', 'Legacy'),
    'TSM': ('TSMC', 'AI/Semi Fab', 'Leader'),
    'ASML': ('ASML', 'AI/Semi Equip', 'Monopoly'),
    'AMAT': ('Applied Materials', 'AI/Semi Equip', 'Leader'),
    'MU': ('Micron', 'AI/Memory', 'Leader'),
    'LRCX': ('Lam Research', 'AI/Semi Equip', 'Leader'),
    'KLAC': ('KLA Corp', 'AI/Semi Equip', 'Leader'),
    
    # AI Software & Services
    'MSFT': ('Microsoft', 'AI/Cloud', 'Leader'),
    'GOOGL': ('Google', 'AI/Search', 'Leader'),
    'META': ('Meta', 'AI/Social', 'Leader'),
    'AMZN': ('Amazon', 'AI/Cloud', 'Leader'),
    'CRM': ('Salesforce', 'AI/Enterprise', 'Leader'),
    'NOW': ('ServiceNow', 'AI/Enterprise', 'Leader'),
    'SNOW': ('Snowflake', 'AI/Data', 'Leader'),
    'PLTR': ('Palantir', 'AI/Data', 'Leader'),
    'NET': ('Cloudflare', 'AI/Security', 'Leader'),
    'CRWD': ('CrowdStrike', 'AI/Security', 'Leader'),
    
    # AI Applications
    'AI': ('C3.ai', 'AI/Enterprise', 'Pure Play'),
    'UPST': ('Upstart', 'AI/Finance', 'Disruptor'),
    'PATH': ('UiPath', 'AI/Automation', 'Leader'),
    'DT': ('Dynatrace', 'AI/Observability', 'Leader'),
    
    # Robotics & Automation
    'TSLA': ('Tesla', 'AI/Robotics', 'Disruptor'),
    'HON': ('Honeywell', 'Robotics', 'Industrial'),
    'IR': ('Ingersoll Rand', 'Robotics', 'Industrial'),
    
    # Data Center / Infrastructure
    'VGT': ('Vanguard InfoTech', 'Tech ETF', 'ETF'),
    'SMH': ('VanEck Semi ETF', 'Semi ETF', 'ETF'),
    'SOXX': ('SOX Semiconductor', 'Semi ETF', 'ETF'),
    
    # Crypto/Blockchain
    'COIN': ('Coinbase', 'Crypto/AI', 'Leader'),
    
    # Flying Taxis / Future Tech
    'LYFT': ('Lyft', 'Autonomous', 'Ride'),
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
    mult = 2 / (period + 1)
    ema = sum(data[:period]) / period
    for p in data[period:]:
        ema = (p - ema) * mult + ema
    return ema

def calc_bb(closes, period=20):
    if len(closes) < period:
        return None, None, None
    sma = sum(closes[-period:]) / period
    std = (sum((c - sma) ** 2 for c in closes[-period:]) / period) ** 0.5
    return sma + 2 * std, sma, sma - 2 * std

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
    return 'EXTREME'

def build_ai_tech_db():
    print('╔══════════════════════════════════════════════════════╗')
    print('║     Maggy AI/Tech 資料庫建置                      ║')
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
        sma_20 REAL, sma_50 REAL, sma_200 REAL,
        ema_12 REAL, ema_26 REAL,
        rsi_14 REAL, rsi_7 REAL,
        macd_line REAL, macd_signal REAL, macd_hist REAL,
        bb_upper REAL, bb_middle REAL, bb_lower REAL,
        atr_14 REAL, kdj_k REAL, kdj_d REAL, kdj_j REAL,
        zone TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(symbol, date)
    )''')
    
    # Stock summary
    cur.execute('''CREATE TABLE IF NOT EXISTS stock_summary (
        symbol TEXT PRIMARY KEY,
        name TEXT,
        sector TEXT,
        subsector TEXT,
        current_price REAL,
        current_rsi REAL,
        current_zone TEXT,
        high_52w REAL,
        low_52w REAL,
        avg_volume INTEGER,
        market_cap REAL,
        total_records INTEGER,
        last_updated TEXT
    )''')
    
    # AI score
    cur.execute('''CREATE TABLE IF NOT EXISTS ai_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        date TEXT NOT NULL,
        ai_score REAL DEFAULT 50,
        momentum_score REAL DEFAULT 50,
        value_score REAL DEFAULT 50,
        quality_score REAL DEFAULT 50,
        overall_score REAL DEFAULT 50,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(symbol, date)
    )''')
    
    conn.commit()
    
    total = len(AI_TECH_STOCKS)
    total_records = 0
    
    print(f'股票: {total}檔（AI/科技為主）\n')
    
    for i, (sym, info) in enumerate(AI_TECH_STOCKS.items(), 1):
        name, sector, subsector = info
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
            
            info_data = t.info
            market_cap = info_data.get('marketCap', 0) or 0
            
            records = 0
            latest = {}
            
            for j in range(60, len(closes)):
                date = dates[j]
                close = closes[j]
                
                sma20 = calc_sma(closes[:j+1], 20)
                sma50 = calc_sma(closes[:j+1], 50)
                sma200 = calc_sma(closes[:j+1], 200)
                ema12 = calc_ema(closes[:j+1], 12)
                ema26 = calc_ema(closes[:j+1], 26)
                rsi14 = calc_rsi(closes[:j+1], 14)
                rsi7 = calc_rsi(closes[:j+1], 7)
                
                ema12_v = calc_ema(closes[:j+1], 12)
                ema26_v = calc_ema(closes[:j+1], 26)
                macd_line = ema12_v - ema26_v if ema12_v and ema26_v else 0
                macd_sig = calc_ema(closes[:j+1], 9) if j >= 26 else 0
                macd_hist = macd_line - macd_sig if macd_sig else 0
                
                bb_u, bb_m, bb_l = calc_bb(closes[:j+1])
                
                trs = []
                for k in range(1, 15):
                    tr = max(highs[j-k] - lows[j-k], abs(highs[j-k] - closes[j-k-1]))
                    trs.append(tr)
                atr = sum(trs) / 14 if len(trs) >= 14 else sum(trs) / len(trs)
                
                zone = detect_zone(rsi14)
                
                cur.execute('''INSERT OR REPLACE INTO daily_ohlcv 
                    (symbol, date, open, high, low, close, volume, sma_20, sma_50, sma_200,
                     ema_12, ema_26, rsi_14, rsi_7, macd_line, macd_signal, macd_hist,
                     bb_upper, bb_middle, bb_lower, atr_14, zone)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (sym, date, opens[j], highs[j], lows[j], close, int(volumes[j]),
                     sma20, sma50, sma200, ema12, ema26, rsi14, rsi7,
                     macd_line, macd_sig, macd_hist, bb_u, bb_m, bb_l, atr, zone))
                
                records += 1
                latest = {'date': date, 'close': close, 'rsi14': rsi14, 'zone': zone}
            
            if records > 0:
                conn.commit()
                
                high_52w = max(closes[-252:]) if len(closes) >= 252 else max(closes)
                low_52w = min(closes[-252:]) if len(closes) >= 252 else min(closes)
                avg_vol = int(sum(volumes[-252:]) / min(252, len(volumes))) if len(volumes) >= 21 else int(sum(volumes) / len(volumes))
                
                cur.execute('''INSERT OR REPLACE INTO stock_summary 
                    (symbol, name, sector, subsector, current_price, current_rsi, current_zone,
                     high_52w, low_52w, avg_volume, market_cap, total_records, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (sym, name, sector, subsector, latest['close'], latest['rsi14'], latest['zone'],
                     high_52w, low_52w, avg_vol, market_cap, records, latest['date']))
                conn.commit()
                
                total_records += records
                print(f'{records}筆 RSI={latest["rsi14"]:.1f} {latest["zone"]}')
        
        except Exception as e:
            print(f'ERROR: {e}')
    
    print(f'\n\n{"="*50}')
    print(f'=== Maggy AI/Tech 資料庫建置完成 ===')
    print(f'{"="*50}')
    
    cur.execute('SELECT COUNT(DISTINCT symbol) FROM daily_ohlcv')
    syms = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM daily_ohlcv')
    total = cur.fetchone()[0]
    cur.execute('SELECT MIN(date), MAX(date) FROM daily_ohlcv')
    dates = cur.fetchone()
    
    print(f'Symbols: {syms}')
    print(f'Total Records: {total:,}')
    print(f'Date Range: {dates[0]} ~ {dates[1]}')
    
    import os
    db_size = os.path.getsize(DB) / (1024 * 1024)
    print(f'DB Size: {db_size:.1f} MB')
    
    # RSI Distribution
    print(f'\n=== RSI Zone Distribution ===')
    cur.execute('''SELECT current_zone, COUNT(*) FROM stock_summary GROUP BY current_zone ORDER BY 
        CASE current_zone WHEN 'OVERSOLD' THEN 1 WHEN 'NEUTRAL_LOW' THEN 2 WHEN 'NEUTRAL' THEN 3 
        WHEN 'NEUTRAL_HIGH' THEN 4 WHEN 'OVERBOUGHT' THEN 5 WHEN 'EXTREME' THEN 6 END''')
    for r in cur.fetchall():
        zone, cnt = r
        icon = '🟢' if zone == 'OVERSOLD' else ('🔴' if zone in ('OVERBOUGHT','EXTREME') else '⚪')
        print(f'  {icon} {zone}: {cnt} stocks')
    
    conn.close()

if __name__ == '__main__':
    build_ai_tech_db()