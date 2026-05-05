"""
美股 ETF 策略資料庫
US ETF Strategy Database
"""

import sqlite3
import json
import yfinance as yf
import pandas as pd
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent
DB_FILE = DATA_DIR / 'us_etf.db'

# 美股 ETF 池 (優化版)
US_ETFS = {
    'SPY': {'name': 'S&P 500', 'sector': 'S&P 500', 'tier': 1, 'dca_weight': 25},
    'QQQ': {'name': 'Nasdaq 100', 'sector': 'Tech', 'tier': 1, 'dca_weight': 20},
    'VOO': {'name': 'Vanguard S&P 500', 'sector': 'S&P 500', 'tier': 1, 'dca_weight': 20},
    'QQQM': {'name': 'Invesco Nasdaq 100', 'sector': 'Tech', 'tier': 2, 'dca_weight': 10},
    'VTI': {'name': 'Vanguard Total Stock', 'sector': 'Total Market', 'tier': 2, 'dca_weight': 10},
    'IWM': {'name': 'Russell 2000', 'sector': 'Small Cap', 'tier': 2, 'dca_weight': 5},
    'VEA': {'name': 'Developed ex-US', 'sector': 'International', 'tier': 2, 'dca_weight': 5},
    'EEM': {'name': 'Emerging Markets', 'sector': 'EM', 'tier': 3, 'dca_weight': 0},
    'TLT': {'name': '20+ Year Treasury', 'sector': 'Bond', 'tier': 2, 'dca_weight': 5},
    'IEF': {'name': '7-10 Year Treasury', 'sector': 'Bond', 'tier': 2, 'dca_weight': 5},
    'BND': {'name': 'Total Bond', 'sector': 'Bond', 'tier': 2, 'dca_weight': 5},
    'GLD': {'name': 'Gold', 'sector': 'Commodity', 'tier': 2, 'dca_weight': 5},
    'SLV': {'name': 'Silver', 'sector': 'Commodity', 'tier': 3, 'dca_weight': 0},
    'XLF': {'name': 'Financial Select', 'sector': 'Financial', 'tier': 2, 'dca_weight': 5},
    'XLE': {'name': 'Energy Select', 'sector': 'Energy', 'tier': 3, 'dca_weight': 0},
    'XLV': {'name': 'Health Care', 'sector': 'Healthcare', 'tier': 2, 'dca_weight': 5},
    'XLK': {'name': 'Technology', 'sector': 'Tech', 'tier': 1, 'dca_weight': 10},
    'XLY': {'name': 'Consumer Discretionary', 'sector': 'Consumer', 'tier': 3, 'dca_weight': 0},
    'VWO': {'name': 'FTSE Emerging', 'sector': 'EM', 'tier': 3, 'dca_weight': 0},
    'VIG': {'name': 'Dividend Appreciation', 'sector': 'Dividend', 'tier': 2, 'dca_weight': 5},
    'DVY': {'name': 'iShares Dividend', 'sector': 'Dividend', 'tier': 2, 'dca_weight': 5},
    'SCHD': {'name': 'Schwab Dividend', 'sector': 'Dividend', 'tier': 2, 'dca_weight': 5},
    'HDV': {'name': 'High Dividend', 'sector': 'Dividend', 'tier': 2, 'dca_weight': 5},
    'DGRO': {'name': 'Dividend Growth', 'sector': 'Dividend', 'tier': 2, 'dca_weight': 5},
    'VYM': {'name': 'High Dividend Yield', 'sector': 'Dividend', 'tier': 2, 'dca_weight': 5},
    'ARKK': {'name': 'Ark Innovation', 'sector': 'Innovation', 'tier': 3, 'dca_weight': 0},
    'QQQ': {'name': 'Nasdaq 100', 'sector': 'Tech', 'tier': 1, 'dca_weight': 15},
}

# 去除重複
US_ETFS = {k: v for k, v in US_ETFS.items()}

# 優化參數
OPTIMAL_PARAMS = {
    'rsi_oversold': 35,
    'rsi_overbought': 65,
    'ma_trend': 'above_ma20',
    'dca_frequency': 'monthly',
    'rebalance_threshold': 0.15,
    'max_position': 0.30
}

def init_db():
    """初始化資料庫"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    
    cur.execute('''
    CREATE TABLE IF NOT EXISTS etfs (
        symbol TEXT PRIMARY KEY,
        name TEXT,
        sector TEXT,
        tier INTEGER,
        dca_weight INTEGER,
        notes TEXT
    )
    ''')
    
    cur.execute('''
    CREATE TABLE IF NOT EXISTS daily_analysis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        symbol TEXT,
        name TEXT,
        price REAL,
        prev_price REAL,
        change_pct REAL,
        rsi_14 REAL,
        ma20 REAL,
        ma60 REAL,
        vol_ratio REAL,
        trend TEXT,
        signal TEXT,
        score INTEGER
    )
    ''')
    
    cur.execute('''
    CREATE TABLE IF NOT EXISTS dca_signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        symbol TEXT,
        name TEXT,
        price REAL,
        rsi_14 REAL,
        recommendation TEXT,
        reason TEXT,
        notes TEXT
    )
    ''')
    
    cur.execute('''
    CREATE TABLE IF NOT EXISTS performance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        symbol TEXT,
        period TEXT,
        price_then REAL,
        price_now REAL,
        return_pct REAL,
        yield_pct REAL,
        notes TEXT
    )
    ''')
    
    # 插入 ETF 池
    for sym, info in US_ETFS.items():
        cur.execute('''
            INSERT OR REPLACE INTO etfs (symbol, name, sector, tier, dca_weight)
            VALUES (?, ?, ?, ?, ?)
        ''', (sym, info['name'], info['sector'], info['tier'], info['dca_weight']))
    
    conn.commit()
    conn.close()
    return DB_FILE

def calc_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def fetch_analysis():
    """抓取最新分析"""
    results = []
    timestamp = datetime.now().isoformat()
    
    for sym, info in US_ETFS.items():
        try:
            t = yf.Ticker(sym)
            hist = t.history(period='3mo')
            
            if len(hist) < 30:
                continue
            
            close = hist['Close'].dropna()
            volumes = hist['Volume']
            
            if len(close) < 30:
                continue
            
            valid_close = close.dropna()
            if len(valid_close) == 0:
                continue
            
            latest_close = valid_close.iloc[-1]
            prev_close = valid_close.iloc[-2] if len(valid_close) >= 2 else latest_close
            
            # RSI
            rsi_series = calc_rsi(valid_close, 14)
            rsi = float(rsi_series.iloc[-1]) if not pd.isna(rsi_series.iloc[-1]) else 50.0
            
            # MA
            ma20 = float(valid_close.rolling(20).mean().iloc[-1])
            ma60 = float(valid_close.rolling(60).mean().iloc[-1]) if len(valid_close) >= 60 else None
            
            # Volume
            vol_ratio = float(volumes.iloc[-1] / volumes.iloc[-5:].mean()) if len(volumes) >= 5 else 1.0
            
            # Price
            price = float(latest_close)
            prev_price = float(prev_close)
            change_pct = (price - prev_price) / prev_price * 100
            
            # Trend
            trend = 'bullish' if price > ma20 else 'bearish'
            
            # Signal
            if rsi < 35:
                signal = 'STRONG_BUY'
            elif rsi < 45:
                signal = 'BUY'
            elif rsi > 70:
                signal = 'OVERBOUGHT'
            elif rsi > 60:
                signal = 'WATCH'
            else:
                signal = 'NEUTRAL'
            
            # Score
            score = 0
            if rsi < 35: score += 30
            elif rsi < 45: score += 20
            elif rsi > 70: score -= 20
            if price > ma20: score += 20
            if ma60 is not None and price > ma60: score += 15
            if vol_ratio > 1.5: score += 10
            score = max(0, min(100, score))
            
            results.append({
                'symbol': sym,
                'name': info['name'],
                'sector': info['sector'],
                'tier': info['tier'],
                'dca_weight': info['dca_weight'],
                'price': price,
                'prev_price': prev_price,
                'change_pct': change_pct,
                'rsi_14': rsi,
                'ma20': ma20,
                'ma60': ma60,
                'vol_ratio': vol_ratio,
                'trend': trend,
                'signal': signal,
                'score': score
            })
            
        except Exception as e:
            results.append({
                'symbol': sym,
                'name': info['name'],
                'error': str(e)
            })
    
    return results

def save_analysis(analysis_data):
    """儲存分析"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    timestamp = datetime.now().isoformat()
    
    for d in analysis_data:
        if 'error' in d:
            continue
        try:
            cur.execute('''
                INSERT INTO daily_analysis 
                (timestamp, symbol, name, price, prev_price, change_pct, rsi_14, ma20, ma60, vol_ratio, trend, signal, score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                timestamp, d['symbol'], d['name'], d['price'], d['prev_price'],
                d['change_pct'], d['rsi_14'], d['ma20'], d.get('ma60') if d.get('ma60') else 0.0,
                d['vol_ratio'], d['trend'], d['signal'], d['score']
            ))
        except Exception as e:
            print(f"Error saving {d.get('symbol', 'unknown')}: {e}")
    
    conn.commit()
    conn.close()

def generate_dca_signals(analysis_data):
    """生成 DCA 信號"""
    signals = []
    timestamp = datetime.now().isoformat()
    
    for d in analysis_data:
        if 'error' in d:
            continue
        
        sym = d['symbol']
        rsi = d['rsi_14']
        price = d['price']
        
        # DCA Recommendation
        if rsi < 35:
            rec = 'STRONG_BUY'
            reason = f'RSI={rsi:.1f} oversold, excellent entry'
        elif rsi < 45:
            rec = 'BUY'
            reason = f'RSI={rsi:.1f} low, good to add'
        elif rsi > 70:
            rec = 'REDUCE'
            reason = f'RSI={rsi:.1f} overbought, reduce exposure'
        elif rsi > 60:
            rec = 'HOLD'
            reason = f'RSI={rsi:.1f} normal, hold position'
        else:
            rec = 'BUY'
            reason = f'RSI={rsi:.1f} neutral, continue investing'
        
        if d['dca_weight'] == 0:
            rec = 'WATCH'
            reason = 'Non-core position, watch only'
        
        signals.append({
            'symbol': sym,
            'name': d['name'],
            'sector': d['sector'],
            'tier': d['tier'],
            'dca_weight': d['dca_weight'],
            'price': price,
            'rsi_14': rsi,
            'recommendation': rec,
            'reason': reason,
            'timestamp': timestamp
        })
    
    return signals

def get_top_dca():
    """取得首選 DCA ETF"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    
    cur.execute('''
        SELECT d.symbol, d.name, d.price, d.rsi_14, d.signal, d.score, e.dca_weight
        FROM daily_analysis d
        JOIN etfs e ON d.symbol = e.symbol
        WHERE d.timestamp = (SELECT MAX(timestamp) FROM daily_analysis)
        ORDER BY e.dca_weight DESC, d.score DESC
        LIMIT 10
    ''')
    
    results = []
    for row in cur.fetchall():
        results.append({
            'symbol': row[0],
            'name': row[1],
            'price': row[2],
            'rsi_14': row[3],
            'signal': row[4],
            'score': row[5],
            'dca_weight': row[6]
        })
    
    conn.close()
    return results

if __name__ == '__main__':
    print("=" * 70)
    print("  US ETF Database")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Init DB
    print("\n[1] Initializing database...")
    db_file = init_db()
    print(f"  OK: {db_file}")
    
    # Fetch
    print("\n[2] Fetching analysis...")
    analysis = fetch_analysis()
    print(f"  Analyzed {len(analysis)} ETFs")
    
    # Save
    print("\n[3] Saving to database...")
    save_analysis(analysis)
    print("  OK")
    
    # DCA signals
    print("\n[4] DCA Signals:")
    print("-" * 70)
    
    signals = generate_dca_signals(analysis)
    
    # Sort by DCA priority
    dca_priority = sorted([s for s in signals if s['dca_weight'] > 0], 
                         key=lambda x: (-x['dca_weight'], x['rsi_14']))
    
    print(f"\n  {'Symbol':<8} {'Name':<20} {'Price':>10} {'RSI':>6} {'Signal':<12} {'DCA%':>5}")
    print("  " + "-" * 65)
    
    for s in dca_priority:
        print(f"  {s['symbol']:<8} {s['name']:<20} {s['price']:>10.2f} {s['rsi_14']:>6.1f} {s['recommendation']:<12} {s['dca_weight']:>5}")
    
    # All ETFs
    print("\n[5] All ETFs Overview:")
    print("-" * 70)
    print(f"  {'Sym':<8} {'Name':<20} {'Price':>10} {'Chg':>7} {'RSI':>6} {'Signal':<12} {'Tier':>5}")
    print("  " + "-" * 75)
    
    for d in sorted(analysis, key=lambda x: (x.get('tier', 99), -x.get('score', 0))):
        if 'error' in d:
            continue
        tier_marker = "*" if d.get('tier', 3) == 1 else " "
        sign = '+' if d['change_pct'] > 0 else ''
        print(f"  {tier_marker}{d['symbol']:<7} {d['name']:<20} {d['price']:>10.2f} {sign}{d['change_pct']:>6.1f}% {d['rsi_14']:>6.1f} {d['signal']:<12} {d['tier']:>5}")
    
    # Summary
    buy_count = sum(1 for d in analysis if d.get('signal') in ['STRONG_BUY', 'BUY'])
    overbought = sum(1 for d in analysis if d.get('signal') == 'OVERBOUGHT')
    print(f"\n  Summary: {buy_count} BUY | {overbought} OVERBOUGHT")
    
    print("\n" + "=" * 70)
