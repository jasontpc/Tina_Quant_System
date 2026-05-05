"""
台股 ETF 策略資料庫
Taiwan ETF Strategy Database
"""

import sqlite3
import json
import yfinance as yf
import pandas as pd
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent
DB_FILE = DATA_DIR / 'tw_etf.db'

# 台股 ETF 池 (優化版)
TW_ETFS = {
    '0050': {'name': '元大台灣50', 'sector': '藍籌', 'tier': 1, 'dca_weight': 30},
    '0056': {'name': '元大高股息', 'sector': '高股息', 'tier': 1, 'dca_weight': 25},
    '00646': {'name': '富邦S&P500', 'sector': '美股', 'tier': 2, 'dca_weight': 15},
    '00662': {'name': '富邦NASDAQ100', 'sector': '科技', 'tier': 2, 'dca_weight': 10},
    '00713': {'name': '元大高息低波', 'sector': '高股息', 'tier': 2, 'dca_weight': 15},
    '00757': {'name': '統一FANG+', 'sector': '科技', 'tier': 2, 'dca_weight': 5},
    '00878': {'name': '國泰永續高股息', 'sector': '高股息', 'tier': 1, 'dca_weight': 20},
    '00881': {'name': '中信關鍵半導體', 'sector': '半導體', 'tier': 2, 'dca_weight': 5},
    '00891': {'name': '中信特選科技', 'sector': '科技', 'tier': 3, 'dca_weight': 0},
    '00892': {'name': '台新永續高科技', 'sector': '科技', 'tier': 3, 'dca_weight': 0},
    '00893': {'name': '元大IC設計', 'sector': '半導體', 'tier': 3, 'dca_weight': 0},
    '00895': {'name': '富邦核心創新科技', 'sector': '科技', 'tier': 3, 'dca_weight': 0},
    '00896': {'name': '元大全球AI', 'sector': 'AI', 'tier': 2, 'dca_weight': 5},
    '00899': {'name': '國泰北美科技', 'sector': '科技', 'tier': 3, 'dca_weight': 0},
    '00900': {'name': '富邦Smart美股', 'sector': '美股', 'tier': 3, 'dca_weight': 0},
    '00904': {'name': '元大全球品牌', 'sector': '消費', 'tier': 3, 'dca_weight': 0},
    '00922': {'name': '台新ESG永續', 'sector': '永續', 'tier': 3, 'dca_weight': 0},
    '00923': {'name': '野村趨勢ETF', 'sector': '主題', 'tier': 3, 'dca_weight': 0},
    '00927': {'name': '統一是未來', 'sector': '主題', 'tier': 2, 'dca_weight': 5},

}

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
    for sym, info in TW_ETFS.items():
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
    
    for sym, info in TW_ETFS.items():
        try:
            t = yf.Ticker(f"{sym}.TW")
            hist = t.history(period='3mo')
            
            if len(hist) < 30:
                continue
            
            close = hist['Close'].dropna()
            volumes = hist['Volume']
            
            if len(close) < 30:
                continue
            
            # Get valid close (drop NaN)
            valid_close = close.dropna()
            if len(valid_close) == 0:
                continue
            
            latest_close = valid_close.iloc[-1]
            prev_close = valid_close.iloc[-2] if len(valid_close) >= 2 else latest_close
            
            # RSI
            rsi_series = calc_rsi(valid_close, 14)
            rsi = float(rsi_series.iloc[-1]) if not pd.isna(rsi_series.iloc[-1]) else 50.0
            
            # MA (use valid_close for calculations)
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
            elif rsi > 65:
                signal = 'OVERBOUGHT'
            elif rsi > 55:
                signal = 'WATCH'
            else:
                signal = 'NEUTRAL'
            
            # Score
            score = 0
            if rsi < 35: score += 30
            elif rsi < 45: score += 20
            elif rsi > 65: score -= 20
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
        score = d['score']
        
        # DCA Recommendation
        if rsi < 35:
            rec = 'STRONG_BUY'
            reason = f'RSI={rsi:.1f} 超賣，極佳進場點'
        elif rsi < 45:
            rec = 'BUY'
            reason = f'RSI={rsi:.1f} 偏低，適合加碼'
        elif rsi > 65:
            rec = 'REDUCE'
            reason = f'RSI={rsi:.1f} 過熱，減碼觀望'
        elif rsi > 55:
            rec = 'HOLD'
            reason = f'RSI={rsi:.1f} 正常，持續持有'
        else:
            rec = 'BUY'
            reason = f'RSI={rsi:.1f} 中性，持續投入'
        
        if d['dca_weight'] == 0:
            rec = 'WATCH'
            reason = '非核心部位，觀望'
        
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
        AND d.signal IN ('STRONG_BUY', 'BUY')
        ORDER BY e.dca_weight DESC, d.score DESC
        LIMIT 5
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
    print("  Taiwan ETF Database")
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
    
    print(f"\n  {'Symbol':<6} {'Name':<12} {'Price':>8} {'RSI':>6} {'Signal':<14} {'DCA%':>5}")
    print("  " + "-" * 60)
    
    for s in dca_priority:
        print(f"  {s['symbol']:<6} {s['name']:<12} {s['price']:>8.0f} {s['rsi_14']:>6.1f} {s['recommendation']:<14} {s['dca_weight']:>5}")
    
    # All ETFs
    print("\n[5] All ETFs Overview:")
    print("-" * 70)
    print(f"  {'Sym':<6} {'Name':<12} {'Price':>8} {'Chg':>7} {'RSI':>6} {'Signal':<14} {'Tier':>5}")
    print("  " + "-" * 65)
    
    for d in sorted(analysis, key=lambda x: (x.get('tier', 99), -x.get('score', 0))):
        if 'error' in d:
            continue
        tier_marker = "*" if d.get('tier', 3) == 1 else " "
        sign = '+' if d['change_pct'] > 0 else ''
        print(f"  {tier_marker}{d['symbol']:<5} {d['name']:<12} {d['price']:>8.0f} {sign}{d['change_pct']:>6.1f}% {d['rsi_14']:>6.1f} {d['signal']:<14} {d['tier']:>5}")
    
    # Summary
    buy_count = sum(1 for d in analysis if d.get('signal') in ['STRONG_BUY', 'BUY'])
    overbought = sum(1 for d in analysis if d.get('signal') == 'OVERBOUGHT')
    print(f"\n  Summary: {buy_count} BUY | {overbought} OVERBOUGHT")
    
    print("\n" + "=" * 70)
