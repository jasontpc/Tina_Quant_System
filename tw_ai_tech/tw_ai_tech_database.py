"""
台股 AI 科技股策略資料庫
Taiwan AI Tech Stock Strategy Database
"""

import sqlite3
import json
import yfinance as yf
import pandas as pd
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent
DB_FILE = DATA_DIR / 'tw_ai_tech.db'

# 台股 AI 科技股池
TW_AI_STOCKS = {
    '2330': {'name': '台積電', 'sector': 'AI晶片/半導體', 'tier': 1, 'us_adp': 'NVDA'},
    '2454': {'name': '聯發科', 'sector': 'AI晶片/IC設計', 'tier': 1, 'us_adp': 'QCOM'},
    '2317': {'name': '鴻海', 'sector': 'AI伺服器/EMS', 'tier': 1, 'us_adp': 'AAPL'},
    '2382': {'name': '廣達', 'sector': 'AI伺服器', 'tier': 1, 'us_adp': 'DELL'},
    '3034': {'name': '緯穎', 'sector': 'AI伺服器', 'tier': 1, 'us_adp': 'SMCI'},
    '2379': {'name': '瑞昱', 'sector': 'AI網通/IC設計', 'tier': 2, 'us_adp': 'AVGO'},
    '2376': {'name': '技嘉', 'sector': 'AI伺服器', 'tier': 2, 'us_adp': 'AMD'},
    '3665': {'name': '穎崴', 'sector': 'AI半導體設備', 'tier': 2, 'us_adp': 'AMAT'},
    '2303': {'name': '聯電', 'sector': 'AI成熟製程', 'tier': 2, 'us_adp': 'UMC'},
    '3003': {'name': '台達電', 'sector': 'AI電源/散熱', 'tier': 2, 'us_adp': 'VRT'},
    '3231': {'name': '緯創', 'sector': 'AI伺服器', 'tier': 2, 'us_adp': 'WDC'},
    '4952': {'name': '凌通', 'sector': 'AI IC設計', 'tier': 3, 'us_adp': 'MXL'},
    '3533': {'name': '嘉澤', 'sector': 'AI連接器', 'tier': 3, 'us_adp': 'ANET'},
    '2458': {'name': '義隆', 'sector': 'AI觸控/IC', 'tier': 3, 'us_adp': 'SYNA'},
    '3037': {'name': '欣興', 'sector': 'AI ABF載板', 'tier': 2, 'us_adp': 'IBUY'},
    '2449': {'name': '京元電子', 'sector': 'AI測試', 'tier': 3, 'us_adp': 'FORM'},
    '2476': {'name': '鉅祥', 'sector': 'AI散熱', 'tier': 3, 'us_adp': 'LRCX'},
    '5269': {'name': '祥碩', 'sector': 'AI高速傳輸', 'tier': 3, 'us_adp': 'LSCC'},
    '3014': {'name': '聯陽', 'sector': 'AI網通IC', 'tier': 3, 'us_adp': 'MRVL'},

}

# 優化參數 (基於全系統分析)
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
    'twii_rsi_max': 85,
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
        us_adp TEXT,
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
        rsi_28 REAL,
        momentum_5d REAL,
        momentum_20d REAL,
        ma20 REAL,
        ma60 REAL,
        ma120 REAL,
        vol_ratio REAL,
        inst_flow REAL,
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
    CREATE TABLE IF NOT EXISTS us_adp_correlation (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        tw_symbol TEXT,
        us_symbol TEXT,
        tw_price REAL,
        us_price REAL,
        tw_rsi REAL,
        us_rsi REAL,
        correlation REAL,
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
    for sym, info in TW_AI_STOCKS.items():
        cur.execute('''
            INSERT OR REPLACE INTO stocks (symbol, name, sector, tier, us_adp)
            VALUES (?, ?, ?, ?, ?)
        ''', (sym, info['name'], info['sector'], info['tier'], info['us_adp']))
    
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
    """抓取最新分析數據"""
    results = []
    timestamp = datetime.now().isoformat()
    
    for sym, info in TW_AI_STOCKS.items():
        try:
            t = yf.Ticker(f"{sym}.TW")
            hist = t.history(period='3mo')
            
            if len(hist) < 30:
                continue
            
            close = hist['Close']
            volumes = hist['Volume']
            
            # RSI (14)
            rsi_14_series = calc_rsi(close, 14)
            rsi_14 = float(rsi_14_series.iloc[-1]) if not pd.isna(rsi_14_series.iloc[-1]) else 50.0
            
            # RSI (28)
            rsi_28_series = calc_rsi(close, 28)
            rsi_28 = float(rsi_28_series.iloc[-1]) if not pd.isna(rsi_28_series.iloc[-1]) else 50.0
            
            # Momentum
            momentum_5d = float(close.pct_change(5).iloc[-1] * 100)
            momentum_20d = float(close.pct_change(20).iloc[-1] * 100)
            
            # Moving Averages
            ma20 = float(close.rolling(20).mean().iloc[-1])
            ma60 = float(close.rolling(60).mean().iloc[-1]) if len(close) >= 60 else None
            ma120 = float(close.rolling(120).mean().iloc[-1]) if len(close) >= 120 else None
            
            # Volume
            vol_ratio = float(volumes.iloc[-1] / volumes.iloc[-5:].mean()) if len(volumes) >= 5 else 1.0
            
            # Price change
            price = float(close.iloc[-1])
            prev_price = float(close.iloc[-2])
            change_pct = (price - prev_price) / prev_price * 100
            
            # Trend
            trend = 'bullish' if price > ma20 else 'bearish'
            
            # Signal
            if rsi_14 < 30 and momentum_5d < 0:
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
            if ma60 is not None and ma20 > ma60: score += 10
            score = max(0, min(100, score))
            
            results.append({
                'symbol': sym,
                'name': info['name'],
                'sector': info['sector'],
                'tier': info['tier'],
                'us_adp': info['us_adp'],
                'price': price,
                'prev_price': prev_price,
                'change_pct': change_pct,
                'rsi_14': rsi_14,
                'rsi_28': rsi_28,
                'momentum_5d': momentum_5d,
                'momentum_20d': momentum_20d,
                'ma20': ma20,
                'ma60': ma60,
                'ma120': ma120,
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
            (timestamp, symbol, name, price, prev_price, change_pct, rsi_14, rsi_28,
             momentum_5d, momentum_20d, ma20, ma60, ma120, vol_ratio, trend, signal, score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            timestamp, d['symbol'], d['name'], d['price'], d['prev_price'],
            d['change_pct'], d['rsi_14'], d['rsi_28'], d['momentum_5d'],
            d['momentum_20d'], d['ma20'], d.get('ma60'), d.get('ma120'),
            d['vol_ratio'], d['trend'], d['signal'], d['score']
        ))
    
    conn.commit()
    conn.close()

def fetch_us_correlation(tw_symbol, us_symbol):
    """抓取美股 ADP 相關性數據"""
    try:
        t_tw = yf.Ticker(f"{tw_symbol}.TW")
        t_us = yf.Ticker(us_symbol)
        
        hist_tw = t_tw.history(period='3mo')
        hist_us = t_us.history(period='3mo')
        
        if len(hist_tw) < 30 or len(hist_us) < 30:
            return None
        
        tw_price = float(hist_tw['Close'].iloc[-1])
        us_price = float(hist_us['Close'].iloc[-1])
        
        # Calculate RSI for both (14-day)
        tw_rsi_series = calc_rsi(hist_tw['Close'], 14)
        us_rsi_series = calc_rsi(hist_us['Close'], 14)
        
        # Handle NaN values
        tw_rsi = float(tw_rsi_series.iloc[-1]) if not pd.isna(tw_rsi_series.iloc[-1]) else 50.0
        us_rsi = float(us_rsi_series.iloc[-1]) if not pd.isna(us_rsi_series.iloc[-1]) else 50.0
        
        # Calculate 5-day correlation
        tw_ret = hist_tw['Close'].pct_change().dropna()
        us_ret = hist_us['Close'].pct_change().dropna()
        
        min_len = min(len(tw_ret), len(us_ret))
        if min_len >= 3:
            correlation = float(tw_ret.iloc[-min_len:].corr(us_ret.iloc[-min_len:]))
            if pd.isna(correlation):
                correlation = 0.0
        else:
            correlation = 0.0
        
        return {
            'tw_symbol': tw_symbol,
            'us_symbol': us_symbol,
            'tw_price': tw_price,
            'us_price': us_price,
            'tw_rsi': tw_rsi,
            'us_rsi': us_rsi,
            'correlation': correlation
        }
    except Exception as e:
        return {'error': str(e)}

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
                'sector': d['sector'],
                'tier': d['tier'],
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
    print("=" * 70)
    print("  Taiwan AI Tech Stock Database")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Initialize DB
    print("\n[1] Initializing database...")
    db_file = init_db()
    print(f"  Database: {db_file}")
    
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
    print("-" * 70)
    
    signals = generate_trade_signals(analysis)
    if signals:
        print(f"\n  {'Symbol':<6} {'Name':<10} {'Price':>10} {'RSI':>6} {'Target':>10} {'Stop':>10}")
        print("  " + "-" * 60)
        for s in signals:
            print(f"  {s['symbol']:<6} {s['name']:<10} ${s['entry_price']:>9.0f} {s['entry_rsi']:>6.1f} ${s['target_price']:>9.0f} ${s['stop_loss']:>9.0f}")
    else:
        print("\n  No signals today (no stocks with RSI < 40)")
    
    # Display all stocks
    print("\n[5] All Stocks Overview:")
    print("-" * 70)
    print(f"  {'Sym':<6} {'Name':<10} {'Price':>10} {'Chg':>7} {'RSI':>6} {'Signal':<14} {'Trend':<10}")
    print("  " + "-" * 70)
    
    for d in sorted(analysis, key=lambda x: (x.get('tier', 99), -x.get('score', 0))):
        if 'error' in d:
            continue
        tier_marker = "*" if d.get('tier', 3) == 1 else " "
        sign = '+' if d['change_pct'] > 0 else ''
        print(f"  {tier_marker}{d['symbol']:<5} {d['name']:<10} {d['price']:>10.0f} {sign}{d['change_pct']:>6.1f}% {d['rsi_14']:>6.1f} {d['signal']:<14} {d['trend']:<10}")
    
    # Summary
    buy_count = sum(1 for d in analysis if d.get('signal') in ['STRONG_BUY', 'BUY'])
    watch_count = sum(1 for d in analysis if d.get('signal') == 'WATCH')
    overbought_count = sum(1 for d in analysis if d.get('signal') == 'OVERBOUGHT')
    
    print(f"\n  Summary: {buy_count} BUY | {watch_count} WATCH | {overbought_count} OVERBOUGHT")
    
    print("\n" + "=" * 70)
