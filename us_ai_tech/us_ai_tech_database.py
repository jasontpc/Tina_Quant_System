"""
美股 AI 科技股策略資料庫
US AI Tech Stock Strategy Database
"""

import sqlite3
import json
import yfinance as yf
import pandas as pd
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent
DB_FILE = DATA_DIR / 'us_ai_tech.db'

# AI 科技股池
US_AI_STOCKS = {
    'NVDA': {'name': 'Nvidia', 'sector': 'AI/GPU', 'tier': 1},
    'AMD': {'name': 'AMD', 'sector': 'AI/GPU', 'tier': 1},
    'PLTR': {'name': 'Palantir', 'sector': 'AI/大數據', 'tier': 1},
    'AI': {'name': 'C3.ai', 'sector': 'AI/軟體', 'tier': 2},
    'PATH': {'name': 'UiPath', 'sector': 'AI/自動化', 'tier': 2},
    'UPST': {'name': 'Upstart', 'sector': 'AI/金融', 'tier': 2},
    'OKTA': {'name': 'Okta', 'sector': '資安/AI', 'tier': 2},
    'NET': {'name': 'Cloudflare', 'sector': '資安/AI', 'tier': 2},
    'SNOW': {'name': 'Snowflake', 'sector': '雲端/AI', 'tier': 2},
    'COIN': {'name': 'Coinbase', 'sector': 'AI/金融', 'tier': 3},
    'GOOGL': {'name': 'Alphabet', 'sector': 'AI/搜尋', 'tier': 1},
    'MSFT': {'name': 'Microsoft', 'sector': 'AI/雲端', 'tier': 1},
    'META': {'name': 'Meta', 'sector': 'AI/社群', 'tier': 1},
    'AMZN': {'name': 'Amazon', 'sector': 'AI/雲端', 'tier': 1},
    'TSLA': {'name': 'Tesla', 'sector': 'AI/自駕', 'tier': 2},
}

# 最佳化參數
OPTIMAL_PARAMS = {
    'rsi_entry_min': 30,
    'rsi_entry_max': 40,
    'rsi_oversold': 30,
    'hold_days_min': 11,
    'hold_days_max': 20,
    'tp_pct': 5,
    'sl_pct': 8,
    'tp_sl_ratio': 2.0,
    'ma_bull_only': True,
    'qqq_rsi_max': 80,
    'risk_off_mode': 'reduce_exposure'
}

def init_db():
    """初始化資料庫"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    
    cur.execute('''
    CREATE TABLE IF NOT EXISTS stocks (
        symbol TEXT PRIMARY KEY,
        name TEXT,
        sector TEXT,
        tier INTEGER,
        notes TEXT
    )
    ''')
    
    cur.execute('''
    CREATE TABLE IF NOT EXISTS daily_analysis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        symbol TEXT,
        price REAL,
        rsi_14 REAL,
        rsi_28 REAL,
        momentum_5d REAL,
        momentum_20d REAL,
        ma20 REAL,
        ma60 REAL,
        ma200 REAL,
        vol_ratio REAL,
        trend TEXT,
        signal TEXT,
        score INTEGER
    )
    ''')
    
    cur.execute('''
    CREATE TABLE IF NOT EXISTS trade_signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        symbol TEXT,
        name TEXT,
        entry_price REAL,
        entry_rsi REAL,
        target_price REAL,
        stop_loss REAL,
        tp_pct REAL,
        sl_pct REAL,
        hold_days INTEGER,
        status TEXT,
        exit_reason TEXT,
        exit_price REAL,
        exit_date TEXT,
        return_pct REAL,
        notes TEXT
    )
    ''')
    
    cur.execute('''
    CREATE TABLE IF NOT EXISTS performance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        symbol TEXT,
        period TEXT,
        trade_count INTEGER,
        win_count INTEGER,
        win_rate REAL,
        avg_return REAL,
        total_return REAL,
        max_win REAL,
        max_loss REAL,
        sharpe_ratio REAL,
        notes TEXT
    )
    ''')
    
    cur.execute('''
    CREATE TABLE IF NOT EXISTS params_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        symbol TEXT,
        rsi_entry_min INTEGER,
        rsi_entry_max INTEGER,
        hold_days_min INTEGER,
        hold_days_max INTEGER,
        tp_pct REAL,
        sl_pct REAL,
        win_rate REAL,
        avg_return REAL,
        notes TEXT
    )
    ''')
    
    # 插入股票池
    for sym, info in US_AI_STOCKS.items():
        cur.execute('''
            INSERT OR REPLACE INTO stocks (symbol, name, sector, tier)
            VALUES (?, ?, ?, ?)
        ''', (sym, info['name'], info['sector'], info['tier']))
    
    conn.commit()
    conn.close()
    return DB_FILE

def fetch_analysis():
    """抓取最新分析數據"""
    results = []
    timestamp = datetime.now().isoformat()
    
    for sym, info in US_AI_STOCKS.items():
        try:
            t = yf.Ticker(sym)
            hist = t.history(period='3mo')
            
            if len(hist) < 30:
                continue
            
            close = hist['Close']
            volumes = hist['Volume']
            
            # RSI (14)
            delta = close.diff()
            gain = delta.clip(lower=0).rolling(14).mean()
            loss = (-delta.clip(upper=0)).rolling(14).mean()
            rs = gain / loss
            rsi_14 = float((100 - (100 / (1 + rs))).iloc[-1])
            
            # RSI (28)
            gain28 = delta.clip(lower=0).rolling(28).mean()
            loss28 = (-delta.clip(upper=0)).rolling(28).mean()
            rs28 = gain28 / loss28
            rsi_28 = float((100 - (100 / (1 + rs28))).iloc[-1])
            
            # Momentum
            momentum_5d = float(close.pct_change(5).iloc[-1] * 100)
            momentum_20d = float(close.pct_change(20).iloc[-1] * 100)
            
            # Moving Averages
            ma20 = float(close.rolling(20).mean().iloc[-1])
            ma60 = float(close.rolling(60).mean().iloc[-1]) if len(close) >= 60 else None
            ma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None
            
            # Volume
            vol_ratio = float(volumes.iloc[-1] / volumes.iloc[-5:].mean()) if len(volumes) >= 5 else 1.0
            
            # Trend
            price = float(close.iloc[-1])
            trend = 'bullish' if price > ma20 else 'bearish'
            
            # Signal
            if rsi_14 < 35 and momentum_5d < 0:
                signal = 'STRONG_BUY'
            elif rsi_14 < 40:
                signal = 'BUY'
            elif rsi_14 > 70:
                signal = 'OVERBOUGHT'
            elif rsi_14 > 60:
                signal = 'WATCH'
            else:
                signal = 'NEUTRAL'
            
            # Score (0-100)
            score = 0
            if rsi_14 < 30: score += 30
            elif rsi_14 < 40: score += 20
            elif rsi_14 > 70: score -= 20
            if momentum_5d > 5: score += 15
            elif momentum_5d < -5: score += 10
            if price > ma20: score += 20
            if vol_ratio > 1.5: score += 10
            score = max(0, min(100, score))
            
            results.append({
                'symbol': sym,
                'name': info['name'],
                'sector': info['sector'],
                'tier': info['tier'],
                'price': price,
                'rsi_14': rsi_14,
                'rsi_28': rsi_28,
                'momentum_5d': momentum_5d,
                'momentum_20d': momentum_20d,
                'ma20': ma20,
                'ma60': ma60,
                'ma200': ma200,
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
    """儲存分析數據到資料庫"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    timestamp = datetime.now().isoformat()
    
    for d in analysis_data:
        if 'error' in d:
            continue
        cur.execute('''
            INSERT INTO daily_analysis 
            (timestamp, symbol, price, rsi_14, rsi_28, momentum_5d, momentum_20d,
             ma20, ma60, ma200, vol_ratio, trend, signal, score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            timestamp, d['symbol'], d['price'], d['rsi_14'], d['rsi_28'],
            d['momentum_5d'], d['momentum_20d'], d['ma20'], d.get('ma60'),
            d.get('ma200'), d['vol_ratio'], d['trend'], d['signal'], d['score']
        ))
    
    conn.commit()
    conn.close()

def get_latest_signals():
    """取得最新買入信號"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    
    cur.execute('''
        SELECT symbol, name, price, rsi_14, signal, score
        FROM daily_analysis
        WHERE timestamp = (SELECT MAX(timestamp) FROM daily_analysis)
        ORDER BY score DESC
    ''')
    
    results = []
    for row in cur.fetchall():
        results.append({
            'symbol': row[0],
            'name': row[1],
            'price': row[2],
            'rsi_14': row[3],
            'signal': row[4],
            'score': row[5]
        })
    
    conn.close()
    return results

def generate_trade_signals(analysis_data):
    """根據分析數據生成交易信號"""
    signals = []
    
    for d in analysis_data:
        if 'error' in d:
            continue
        
        sym = d['symbol']
        price = d['price']
        rsi = d['rsi_14']
        
        # 只對 RSI < 40 的股票生成信號
        if rsi < 40:
            tp = price * (1 + OPTIMAL_PARAMS['tp_pct'] / 100)
            sl = price * (1 - OPTIMAL_PARAMS['sl_pct'] / 100)
            
            signals.append({
                'symbol': sym,
                'name': d['name'],
                'entry_price': price,
                'entry_rsi': rsi,
                'target_price': round(tp, 2),
                'stop_loss': round(sl, 2),
                'tp_pct': OPTIMAL_PARAMS['tp_pct'],
                'sl_pct': OPTIMAL_PARAMS['sl_pct'],
                'hold_days': OPTIMAL_PARAMS['hold_days_max'],
                'status': 'SIGNAL',
                'timestamp': datetime.now().isoformat()
            })
    
    return signals

if __name__ == '__main__':
    print("=" * 60)
    print("  US AI Tech Stock Database")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Initialize DB
    print("\n[1] Initializing database...")
    init_db()
    print(f"  Database: {DB_FILE}")
    
    # Fetch analysis
    print("\n[2] Fetching analysis...")
    analysis = fetch_analysis()
    print(f"  Analyzed {len(analysis)} stocks")
    
    # Save to DB
    print("\n[3] Saving to database...")
    save_analysis(analysis)
    print("  Done!")
    
    # Display signals
    print("\n[4] Trading Signals (RSI < 40):")
    print("-" * 60)
    
    signals = generate_trade_signals(analysis)
    for s in signals:
        print(f"  {s['symbol']:6} {s['name']:<15} @ ${s['entry_price']:.2f}")
        print(f"         RSI={s['entry_rsi']:.1f}  Target=${s['target_price']:.2f}  Stop=${s['stop_loss']:.2f}")
        print()
    
    # Display all stocks
    print("\n[5] All Stocks Overview:")
    print("-" * 60)
    print(f"  {'Symbol':<6} {'Name':<15} {'Price':>10} {'RSI':>6} {'Signal':<12} {'Score':>5}")
    print("  " + "-" * 55)
    
    for d in sorted(analysis, key=lambda x: x.get('score', 0), reverse=True):
        if 'error' in d:
            continue
        print(f"  {d['symbol']:<6} {d['name']:<15} ${d['price']:>9.2f} {d['rsi_14']:>6.1f} {d['signal']:<12} {d['score']:>5}")
    
    print("\n" + "=" * 60)
