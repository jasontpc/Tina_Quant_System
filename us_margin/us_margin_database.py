"""
美股 Margin 資料庫
US Margin Database - Margin Debt, Short Interest, Financial Data
"""

import sqlite3
import json
import yfinance as yf
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

DATA_DIR = Path(__file__).parent
DB_FILE = DATA_DIR / 'us_margin.db'

# Margin 監控股票池
MARGIN_STOCKS = {
    'AAPL': {'name': 'Apple', 'sector': 'Tech', 'margin_eligible': True},
    'MSFT': {'name': 'Microsoft', 'sector': 'Tech', 'margin_eligible': True},
    'NVDA': {'name': 'Nvidia', 'sector': 'AI/Semi', 'margin_eligible': True},
    'AMD': {'name': 'AMD', 'sector': 'AI/Semi', 'margin_eligible': True},
    'GOOGL': {'name': 'Alphabet', 'sector': 'Tech', 'margin_eligible': True},
    'AMZN': {'name': 'Amazon', 'sector': 'Tech', 'margin_eligible': True},
    'META': {'name': 'Meta', 'sector': 'Social Media', 'margin_eligible': True},
    'TSLA': {'name': 'Tesla', 'sector': 'EV', 'margin_eligible': True},
    'PLTR': {'name': 'Palantir', 'sector': 'AI', 'margin_eligible': True},
    'AMD': {'name': 'AMD', 'sector': 'AI/Semi', 'margin_eligible': True},
    'INTC': {'name': 'Intel', 'sector': 'Semi', 'margin_eligible': True},
    'QQQ': {'name': 'Nasdaq 100 ETF', 'sector': 'ETF', 'margin_eligible': True},
    'SPY': {'name': 'S&P 500 ETF', 'sector': 'ETF', 'margin_eligible': True},
    'IWM': {'name': 'Russell 2000 ETF', 'sector': 'ETF', 'margin_eligible': True},
    'TQQQ': {'name': 'ProShares 3x Long', 'sector': 'Leveraged', 'margin_eligible': False},
    'SQQQ': {'name': 'ProShares 3x Short', 'sector': 'Leveraged', 'margin_eligible': False},
    'SPXL': {'name': '3x Long S&P 500', 'sector': 'Leveraged', 'margin_eligible': False},
    'SPXS': {'name': '3x Short S&P 500', 'sector': 'Leveraged', 'margin_eligible': False},
    'QQQ': {'name': 'Nasdaq 100', 'sector': 'ETF', 'margin_eligible': True},
}

# 去除重複
MARGIN_STOCKS = {k: v for k, v in MARGIN_STOCKS.items()}

# Margin 參數
MARGIN_PARAMS = {
    'initial_margin': 0.50,      # 美股初始保證金 50%
    'maintenance_margin': 0.25,  # 維持保證金 25%
    'margin_call_threshold': 0.30, #  Margin call 門檻 30%
    'max_margin_ratio': 0.40,    # 建議最大 margin ratio
}

def init_db():
    """初始化資料庫"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    
    # 股票池
    cur.execute('''
    CREATE TABLE IF NOT EXISTS stocks (
        symbol TEXT PRIMARY KEY,
        name TEXT,
        sector TEXT,
        margin_eligible INTEGER,
        notes TEXT
    )
    ''')
    
    # 日線數據 (價格、成交量、融券)
    cur.execute('''
    CREATE TABLE IF NOT EXISTS daily_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        symbol TEXT,
        name TEXT,
        price REAL,
        prev_price REAL,
        change_pct REAL,
        volume REAL,
        avg_volume_20 REAL,
        short_interest REAL,
        days_to_cover REAL,
        short_ratio REAL,
        margin_balance REAL,
        shortable_share REAL,
        fee_rate REAL,
        rsi_14 REAL,
        trend TEXT
    )
    ''')
    
    # Margin 餘額 (個股槓桿)
    cur.execute('''
    CREATE TABLE IF NOT EXISTS margin_balance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        symbol TEXT,
        margin_debt REAL,
        margin_used REAL,
        margin_available REAL,
        cash_balance REAL,
        margin_ratio REAL,
        margin_call_price REAL,
        notes TEXT
    )
    ''')
    
    # Market Margin Data (市場整體)
    cur.execute('''
    CREATE TABLE IF NOT EXISTS market_margin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        total_margin_debt REAL,
        margin_debt_chg REAL,
        sp500_price REAL,
        vix REAL,
        put_call_ratio REAL,
        margin_interest_rate REAL,
        sentiment TEXT,
        notes TEXT
    )
    ''')
    
    # Margin Alert
    cur.execute('''
    CREATE TABLE IF NOT EXISTS margin_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        symbol TEXT,
        alert_type TEXT,
        severity TEXT,
        price REAL,
        margin_ratio REAL,
        reason TEXT,
        status TEXT,
        notes TEXT
    )
    ''')
    
    # 插入股票池
    for sym, info in MARGIN_STOCKS.items():
        cur.execute('''
            INSERT OR REPLACE INTO stocks (symbol, name, sector, margin_eligible)
            VALUES (?, ?, ?, ?)
        ''', (sym, info['name'], info['sector'], 1 if info['margin_eligible'] else 0))
    
    conn.commit()
    conn.close()
    return DB_FILE

def calc_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def fetch_daily_data():
    """抓取每日數據"""
    results = []
    timestamp = datetime.now().isoformat()
    
    for sym, info in MARGIN_STOCKS.items():
        try:
            t = yf.Ticker(sym)
            hist = t.history(period='1mo')
            info_hist = t.info
            
            if len(hist) < 5:
                continue
            
            close = hist['Close']
            volumes = hist['Volume']
            
            # 基本數據
            price = float(close.iloc[-1])
            prev_price = float(close.iloc[-2]) if len(close) >= 2 else price
            change_pct = (price - prev_price) / prev_price * 100
            
            # 成交量
            volume = float(volumes.iloc[-1])
            avg_volume = float(volumes.iloc[-20:].mean()) if len(volumes) >= 20 else volume
            
            # RSI
            rsi_series = calc_rsi(close, 14)
            rsi = float(rsi_series.iloc[-1]) if not pd.isna(rsi_series.iloc[-1]) else 50.0
            
            # Trend
            ma20 = float(close.rolling(20).mean().iloc[-1]) if len(close) >= 20 else price
            trend = 'bullish' if price > ma20 else 'bearish'
            
            # 從 info 取得 short 數據
            short_interest = info_hist.get('shortInterest', 0)
            days_to_cover = info_hist.get('daysToCover', 0)
            short_ratio = info_hist.get('shortRatio', 0)
            margin_balance = info_hist.get('marginSharesBuying', 0)
            shortable = info_hist.get('sharesShort', 0)
            fee_rate = info_hist.get('commissionRate', 0)
            
            results.append({
                'symbol': sym,
                'name': info['name'],
                'sector': info['sector'],
                'price': price,
                'prev_price': prev_price,
                'change_pct': change_pct,
                'volume': volume,
                'avg_volume_20': avg_volume,
                'short_interest': short_interest,
                'days_to_cover': days_to_cover,
                'short_ratio': short_ratio,
                'margin_balance': margin_balance,
                'shortable_share': shortable,
                'fee_rate': fee_rate,
                'rsi_14': rsi,
                'trend': trend,
                'timestamp': timestamp
            })
            
        except Exception as e:
            results.append({
                'symbol': sym,
                'name': info['name'],
                'error': str(e)
            })
    
    return results

def save_daily_data(data):
    """儲存每日數據"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    
    for d in data:
        if 'error' in d:
            continue
        try:
            cur.execute('''
                INSERT INTO daily_data 
                (timestamp, symbol, name, price, prev_price, change_pct, volume, avg_volume_20,
                 short_interest, days_to_cover, short_ratio, margin_balance, shortable_share,
                 fee_rate, rsi_14, trend)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                d['timestamp'], d['symbol'], d['name'], d['price'], d['prev_price'],
                d['change_pct'], d['volume'], d['avg_volume_20'], d['short_interest'],
                d['days_to_cover'], d['short_ratio'], d['margin_balance'],
                d['shortable_share'], d['fee_rate'], d['rsi_14'], d['trend']
            ))
        except Exception as e:
            print(f"Error saving {d.get('symbol', 'unknown')}: {e}")
    
    conn.commit()
    conn.close()

def analyze_margin_risk(data):
    """分析 Margin 風險"""
    alerts = []
    timestamp = datetime.now().isoformat()
    
    for d in data:
        if 'error' in d:
            continue
        
        sym = d['symbol']
        price = d['price']
        rsi = d['rsi_14']
        change = d['change_pct']
        
        # RSI 過高警示
        if rsi > 80:
            alerts.append({
                'symbol': sym,
                'alert_type': 'OVERBOUGHT',
                'severity': 'HIGH',
                'price': price,
                'margin_ratio': None,
                'reason': f'RSI={rsi:.1f} overbought, margin risk high',
                'timestamp': timestamp
            })
        
        # 短期暴漲
        if change > 10:
            alerts.append({
                'symbol': sym,
                'alert_type': 'SHORT_SQUEEZE_RISK',
                'severity': 'HIGH',
                'price': price,
                'margin_ratio': None,
                'reason': f'+{change:.1f}% in one day, short squeeze risk',
                'timestamp': timestamp
            })
        
        # 高 short interest
        if d['short_ratio'] > 10:
            alerts.append({
                'symbol': sym,
                'alert_type': 'HIGH_SHORT',
                'severity': 'MEDIUM',
                'price': price,
                'margin_ratio': None,
                'reason': f'Short ratio={d["short_ratio"]:.1f}, high short interest',
                'timestamp': timestamp
            })
        
        # 融券回補壓力
        if d['days_to_cover'] > 8:
            alerts.append({
                'symbol': sym,
                'alert_type': 'SHORT_COVER_PRESSURE',
                'severity': 'MEDIUM',
                'price': price,
                'margin_ratio': None,
                'reason': f'Days to cover={d["days_to_cover"]:.1f}, short cover pressure',
                'timestamp': timestamp
            })
    
    return alerts

def get_high_risk_stocks():
    """取得高風險股票"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    
    cur.execute('''
        SELECT d.symbol, d.name, d.price, d.rsi_14, d.short_ratio, d.days_to_cover, d.change_pct
        FROM daily_data d
        WHERE d.timestamp = (SELECT MAX(timestamp) FROM daily_data)
        AND d.rsi_14 > 70
        ORDER BY d.rsi_14 DESC
        LIMIT 10
    ''')
    
    results = []
    for row in cur.fetchall():
        results.append({
            'symbol': row[0],
            'name': row[1],
            'price': row[2],
            'rsi_14': row[3],
            'short_ratio': row[4],
            'days_to_cover': row[5],
            'change_pct': row[6]
        })
    
    conn.close()
    return results

def get_short_squeeze_candidates():
    """取得潛在 Short Squeeze 候選"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    
    cur.execute('''
        SELECT d.symbol, d.name, d.price, d.short_ratio, d.days_to_cover, d.change_pct, d.rsi_14
        FROM daily_data d
        WHERE d.timestamp = (SELECT MAX(timestamp) FROM daily_data)
        AND d.short_ratio > 5
        AND d.days_to_cover > 5
        ORDER BY d.short_ratio * d.days_to_cover DESC
        LIMIT 10
    ''')
    
    results = []
    for row in cur.fetchall():
        results.append({
            'symbol': row[0],
            'name': row[1],
            'price': row[2],
            'short_ratio': row[3],
            'days_to_cover': row[4],
            'change_pct': row[5],
            'rsi_14': row[6],
            'squeeze_score': row[3] * row[4]
        })
    
    conn.close()
    return results

if __name__ == '__main__':
    print("=" * 70)
    print("  US Margin Database")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Init
    print("\n[1] Initializing database...")
    init_db()
    print(f"  OK: {DB_FILE}")
    
    # Fetch
    print("\n[2] Fetching daily data...")
    data = fetch_daily_data()
    print(f"  Fetched {len(data)} stocks")
    
    # Save
    print("\n[3] Saving to database...")
    save_daily_data(data)
    print("  OK")
    
    # Analyze
    print("\n[4] Margin Risk Analysis:")
    print("-" * 70)
    
    alerts = analyze_margin_risk(data)
    print(f"\n  Found {len(alerts)} risk alerts")
    
    # High Risk Stocks
    print("\n[5] High Risk Stocks (RSI > 70):")
    high_risk = get_high_risk_stocks()
    if high_risk:
        print(f"  {'Symbol':<8} {'Name':<15} {'Price':>10} {'RSI':>6} {'Short%':>8}")
        print("  " + "-" * 50)
        for s in high_risk:
            print(f"  {s['symbol']:<8} {s['name']:<15} ${s['price']:>9.2f} {s['rsi_14']:>6.1f} {s['short_ratio']:>7.1f}%")
    else:
        print("  None")
    
    # Short Squeeze Candidates
    print("\n[6] Short Squeeze Candidates:")
    squeeze = get_short_squeeze_candidates()
    if squeeze:
        print(f"  {'Symbol':<8} {'Name':<15} {'Price':>10} {'ShortRatio':>10} {'DaysCover':>10}")
        print("  " + "-" * 60)
        for s in squeeze:
            print(f"  {s['symbol']:<8} {s['name']:<15} ${s['price']:>9.2f} {s['short_ratio']:>10.1f} {s['days_to_cover']:>10.1f}")
    else:
        print("  None")
    
    # Alerts
    if alerts:
        print("\n[7] Margin Alerts:")
        high_alerts = [a for a in alerts if a['severity'] == 'HIGH']
        med_alerts = [a for a in alerts if a['severity'] == 'MEDIUM']
        
        if high_alerts:
            print("\n  HIGH SEVERITY:")
            for a in high_alerts:
                print(f"    {a['symbol']}: {a['reason']}")
        
        if med_alerts:
            print("\n  MEDIUM SEVERITY:")
            for a in med_alerts[:5]:
                print(f"    {a['symbol']}: {a['reason']}")
    
    print("\n" + "=" * 70)
