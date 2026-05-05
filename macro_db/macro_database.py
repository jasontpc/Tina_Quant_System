"""
宏觀資料庫 - 地緣政治/貨幣政策/產業供應鏈/情緒分析
Macro Database - Geopolitical/Monetary/Sentiment Analysis
"""

import sqlite3
import json
import yfinance as yf
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import urllib.request
import ssl

DATA_DIR = Path(__file__).parent
DB_FILE = DATA_DIR / 'macro.db'

# Macro indices to track
MACRO_INDICES = {
    # Macro Economic
    'DXY': {'name': '美元指數', 'type': 'Currency', 'period': '1d'},
    '10Y_Yield': {'name': '10年美債殖利率', 'type': 'Interest Rate', 'period': '1d'},
    '2Y_Yield': {'name': '2年美債殖利率', 'type': 'Interest Rate', 'period': '1d'},
    'VIX': {'name': 'VIX 波動率', 'type': 'Risk', 'period': '1d'},
    'DXY': {'name': 'USD Index', 'type': 'Currency', 'period': '1d'},
    
    # Sentiment
    'CNN_FearGreed': {'name': 'CNN Fear & Greed', 'type': 'Sentiment', 'period': '1d'},
    'AAII_Sentiment': {'name': 'AAII Sentiment', 'type': 'Sentiment', 'period': '1w'},
    
    # Commodities
    'CL_F': {'name': 'WTI 原油', 'type': 'Energy', 'period': '1d'},
    'GC_F': {'name': '黃金期貨', 'type': 'Gold', 'period': '1d'},
    'NG_F': {'name': '天然氣', 'type': 'Energy', 'period': '1d'},
    'HG_F': {'name': '銅期貨', 'type': 'Industrial', 'period': '1d'},
    
    # Taiwan Relevant
    'TSMC': {'name': '台積電', 'type': 'Taiwan', 'period': '1d'},
    'SOXX': {'name': '費城半導體', 'type': 'Semi', 'period': '1d'},
    'TWII': {'name': '加權指數', 'type': 'Taiwan', 'period': '1d'},
    'TPEX': {'name': '櫃買指數', 'type': 'Taiwan', 'period': '1d'},
    
    # China
    'HSI': {'name': '恆生指數', 'type': 'China', 'period': '1d'},
    'CNY': {'name': '離岸人民幣', 'type': 'China', 'period': '1d'},
}

# Geopolitical risk keywords
RISK_KEYWORDS = {
    'high_risk': ['war', 'military', 'attack', 'invasion', 'sanction', 'ban', 'blockade', 'conflict', 'crisis', 'tension'],
    'medium_risk': ['tariff', 'trade war', 'export control', 'restriction', 'regulation', 'probe', 'investigation'],
    'low_risk': ['deal', 'agreement', 'cooperation', 'summit', 'meeting', 'progress']
}

def init_db():
    """初始化資料庫"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    
    cur.execute('''
    CREATE TABLE IF NOT EXISTS macro_indices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        symbol TEXT,
        name TEXT,
        type TEXT,
        value REAL,
        change_pct REAL,
        trend TEXT,
        signal TEXT
    )
    ''')
    
    cur.execute('''
    CREATE TABLE IF NOT EXISTS geopolitical_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        event_type TEXT,
        region TEXT,
        severity TEXT,
        headline TEXT,
        impact TEXT,
        affected_etf TEXT,
        notes TEXT
    )
    ''')
    
    cur.execute('''
    CREATE TABLE IF NOT EXISTS macro_signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        signal_type TEXT,
        macro_factor TEXT,
        direction TEXT,
        confidence INTEGER,
        value REAL,
        threshold TEXT,
        interpretation TEXT,
        action TEXT
    )
    ''')
    
    cur.execute('''
    CREATE TABLE IF NOT EXISTS regime_classification (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        regime TEXT,
        vix_level TEXT,
        dxy_level TEXT,
        yield_level TEXT,
        sentiment TEXT,
        recommendation TEXT
    )
    ''')
    
    cur.execute('''
    CREATE TABLE IF NOT EXISTS daily_summary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        regime TEXT,
        vix REAL,
        dxy REAL,
        yield_10y REAL,
        fear_greed REAL,
        twii_level TEXT,
        tech_level TEXT,
        signal TEXT,
        risk_factors TEXT,
        opportunities TEXT
    )
    ''')
    
    conn.commit()
    conn.close()
    return DB_FILE

def fetch_macro_data():
    """抓取宏觀數據"""
    results = []
    timestamp = datetime.now().isoformat()
    
    # US Macro Data
    symbols = {
        'DXY': 'US Dollar Index',
        '^TNX': '10Y Treasury Yield',
        '^VIX': 'VIX',
        '^SP500': 'S&P 500',
        'CL=F': 'WTI Crude',
        'GC=F': 'Gold',
        'SI=F': 'Silver',
        'HG=F': 'Copper',
        'TSLA': 'Tesla',
        'BTC-USD': 'Bitcoin',
    }
    
    for sym, name in symbols.items():
        try:
            t = yf.Ticker(sym)
            hist = t.history(period='5d')
            
            if len(hist) >= 2:
                curr = float(hist['Close'].iloc[-1])
                prev = float(hist['Close'].iloc[-2])
                chg = (curr - prev) / prev * 100 if prev > 0 else 0
                
                # Classify
                if sym == '^VIX':
                    signal = 'RISK_OFF' if curr > 20 else 'RISK_ON'
                elif sym == '^TNX':
                    signal = 'HIGH_RATE' if curr > 4.5 else 'NORMAL_RATE' if curr > 3.5 else 'LOW_RATE'
                elif sym == 'DXY':
                    signal = 'DOLLAR_STRONG' if curr > 105 else 'DOLLAR_WEAK'
                else:
                    signal = 'BULLISH' if chg > 0 else 'BEARISH'
                
                results.append({
                    'symbol': sym,
                    'name': name,
                    'value': curr,
                    'change_pct': chg,
                    'signal': signal,
                    'timestamp': timestamp
                })
        except Exception as e:
            pass
    
    return results

def fetch_taiwan_data():
    """抓取台股相關數據"""
    results = []
    timestamp = datetime.now().isoformat()
    
    tw_symbols = {
        '^TWII': '加權指數',
        '^TPEX': '櫃買指數',
        '2330.TW': '台積電',
        '2454.TW': '聯發科',
        'SOXX': '費城半導體',
    }
    
    for sym, name in tw_symbols.items():
        try:
            t = yf.Ticker(sym)
            hist = t.history(period='5d')
            
            if len(hist) >= 2:
                curr = float(hist['Close'].iloc[-1])
                prev = float(hist['Close'].iloc[-2])
                chg = (curr - prev) / prev * 100 if prev > 0 else 0
                
                # RSI
                delta = hist['Close'].diff()
                gain = delta.clip(lower=0).rolling(14).mean()
                loss = (-delta.clip(upper=0)).rolling(14).mean()
                rs = gain / loss
                rsi = float((100 - (100 / (1 + rs))).iloc[-1])
                
                results.append({
                    'symbol': sym,
                    'name': name,
                    'value': curr,
                    'change_pct': chg,
                    'rsi': rsi,
                    'timestamp': timestamp
                })
        except Exception as e:
            pass
    
    return results

def classify_regime(vix, dxy, yield_10y, fear_greed=None):
    """分類市場體制"""
    
    # VIX level
    if vix > 30:
        vix_level = 'EXTREME_FEAR'
    elif vix > 20:
        vix_level = 'FEAR'
    elif vix > 15:
        vix_level = 'NEUTRAL'
    else:
        vix_level = 'GREED'
    
    # Dollar level
    if dxy > 108:
        dxy_level = 'VERY_STRONG'
    elif dxy > 105:
        dxy_level = 'STRONG'
    elif dxy > 100:
        dxy_level = 'NEUTRAL'
    else:
        dxy_level = 'WEAK'
    
    # Yield level
    if yield_10y > 5:
        yield_level = 'VERY_HIGH'
    elif yield_10y > 4.5:
        yield_level = 'HIGH'
    elif yield_10y > 3.5:
        yield_level = 'NORMAL'
    else:
        yield_level = 'LOW'
    
    # Sentiment
    if fear_greed:
        if fear_greed > 75:
            sentiment = 'EXTREME_GREED'
        elif fear_greed > 55:
            sentiment = 'GREED'
        elif fear_greed > 45:
            sentiment = 'NEUTRAL'
        elif fear_greed > 25:
            sentiment = 'FEAR'
        else:
            sentiment = 'EXTREME_FEAR'
    else:
        sentiment = vix_level
    
    # Overall regime
    if vix_level in ['EXTREME_FEAR', 'FEAR']:
        regime = 'RISK_OFF'
    elif vix_level == 'NEUTRAL' and yield_level in ['HIGH', 'VERY_HIGH']:
        regime = 'RATE pressure'
    else:
        regime = 'RISK_ON'
    
    return {
        'regime': regime,
        'vix_level': vix_level,
        'dxy_level': dxy_level,
        'yield_level': yield_level,
        'sentiment': sentiment
    }

def generate_macro_signals(macro_data, tw_data, regime):
    """產生宏觀信號"""
    signals = []
    timestamp = datetime.now().isoformat()
    
    # VIX signal
    vix_data = next((d for d in macro_data if d['symbol'] == '^VIX'), None)
    if vix_data:
        if vix_data['value'] > 30:
            vix_level = 'HIGH_VOLATILITY'
            action = 'REDUCE EXPOSURE'
        elif vix_data['value'] > 20:
            vix_level = 'ELEVATED_VOL'
            action = 'CAUTION'
        else:
            vix_level = 'LOW_VOLATILITY'
            action = 'NORMAL'
        
        signals.append({
            'signal_type': 'VOLATILITY',
            'macro_factor': 'VIX',
            'direction': 'UP' if vix_data['change_pct'] > 0 else 'DOWN',
            'confidence': int(min(abs(vix_data['value'] - 20) * 3, 90)),
            'value': vix_data['value'],
            'threshold': '20',
            'interpretation': vix_level,
            'action': action
        })
    
    # Dollar signal
    dxy_data = next((d for d in macro_data if d['symbol'] == 'DXY'), None)
    if dxy_data:
        if dxy_data['value'] > 108:
            sig = 'DOLLAR_DOMINANT'
            action = 'HEDGE Taiwan exposure'
        elif dxy_data['value'] > 105:
            sig = 'DOLLAR_STRONG'
            action = 'MONITOR'
        else:
            sig = 'DOLLAR_NEUTRAL'
            action = 'NORMAL'
        
        signals.append({
            'signal_type': 'CURRENCY',
            'macro_factor': 'DXY',
            'direction': 'STRONG' if dxy_data['value'] > 105 else 'WEAK',
            'confidence': int(min(abs(dxy_data['value'] - 105) * 5, 90)),
            'value': dxy_data['value'],
            'threshold': '105',
            'interpretation': sig,
            'action': action
        })
    
    # Yield signal
    yield_data = next((d for d in macro_data if d['symbol'] == '^TNX'), None)
    if yield_data:
        if yield_data['value'] > 4.5:
            sig = 'HIGH_RATE'
            action = 'REDUCE Tech/FANG+'
        elif yield_data['value'] > 4.0:
            sig = 'ELEVATED_RATE'
            action = 'MONITOR'
        else:
            sig = 'LOW_RATE'
            action = 'FAVOR Tech'
        
        signals.append({
            'signal_type': 'RATES',
            'macro_factor': '10Y Yield',
            'direction': 'UP' if yield_data['change_pct'] > 0 else 'DOWN',
            'confidence': int(min(abs(yield_data['value'] - 4.0) * 20, 90)),
            'value': yield_data['value'],
            'threshold': '4.5',
            'interpretation': sig,
            'action': action
        })
    
    return signals

def save_data(macro_data, tw_data, regime, signals):
    """儲存數據"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    timestamp = datetime.now().isoformat()
    
    for d in macro_data:
        try:
            cur.execute('''
                INSERT INTO macro_indices 
                (timestamp, symbol, name, type, value, change_pct, signal)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (timestamp, d['symbol'], d['name'], d.get('type', ''),
                  d['value'], d['change_pct'], d['signal']))
        except:
            pass
    
    for s in signals:
        try:
            cur.execute('''
                INSERT INTO macro_signals
                (timestamp, signal_type, macro_factor, direction, confidence,
                 value, threshold, interpretation, action)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (timestamp, s['signal_type'], s['macro_factor'], s['direction'],
                  s['confidence'], s['value'], s['threshold'], s['interpretation'], s['action']))
        except:
            pass
    
    conn.commit()
    conn.close()

def analyze_current_state():
    """分析當前狀態"""
    macro_data = fetch_macro_data()
    tw_data = fetch_taiwan_data()
    
    # Default values
    vix = 15.0
    dxy = 100.0
    yield_10y = 4.0
    
    vix_data = next((d for d in macro_data if d['symbol'] == '^VIX'), None)
    if vix_data:
        vix = vix_data['value']
    
    dxy_data = next((d for d in macro_data if d['symbol'] == 'DXY'), None)
    if dxy_data:
        dxy = dxy_data['value']
    
    yield_data = next((d for d in macro_data if d['symbol'] == '^TNX'), None)
    if yield_data:
        yield_10y = yield_data['value']
    
    regime = classify_regime(vix, dxy, yield_10y)
    signals = generate_macro_signals(macro_data, tw_data, regime)
    
    save_data(macro_data, tw_data, regime, signals)
    
    return macro_data, tw_data, regime, signals

if __name__ == '__main__':
    print("=" * 70)
    print("  Macro Database - Global Market Analysis")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Init
    print("\n[1] Initializing database...")
    init_db()
    print(f"  OK: {DB_FILE}")
    
    # Fetch & Analyze
    print("\n[2] Fetching macro data...")
    macro_data, tw_data, regime, signals = analyze_current_state()
    print(f"  Fetched {len(macro_data)} macro indicators")
    print(f"  Fetched {len(tw_data)} Taiwan indicators")
    
    # Regime
    print("\n[3] Market Regime:")
    print("-" * 70)
    print(f"  Regime: {regime['regime']}")
    print(f"  VIX Level: {regime['vix_level']}")
    print(f"  Dollar Level: {regime['dxy_level']}")
    print(f"  Yield Level: {regime['yield_level']}")
    print(f"  Sentiment: {regime['sentiment']}")
    
    # Macro signals
    print("\n[4] Macro Signals:")
    print("-" * 70)
    for s in signals:
        print(f"  {s['signal_type']:<15} {s['macro_factor']:<12} {s['interpretation']:<20} Action: {s['action']}")
    
    # Key indicators
    print("\n[5] Key Indicators:")
    print("-" * 70)
    for d in macro_data:
        sign = '+' if d['change_pct'] > 0 else ''
        print(f"  {d['name']:<25} {d['value']:>10.2f} {sign}{d['change_pct']:>6.2f}%")
    
    # Taiwan data
    print("\n[6] Taiwan Indicators:")
    print("-" * 70)
    for d in tw_data:
        sign = '+' if d['change_pct'] > 0 else ''
        rsi_str = f" RSI={d.get('rsi', 0):.1f}" if 'rsi' in d else ''
        print(f"  {d['name']:<20} {d['value']:>10.2f} {sign}{d['change_pct']:>6.2f}%{rsi_str}")
    
    print("\n" + "=" * 70)
