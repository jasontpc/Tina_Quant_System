"""
US ETF 年化報酬率 & 殖利率資料庫
US ETF Return & Yield Database
"""

import sqlite3
import json
import yfinance as yf
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

DATA_DIR = Path(__file__).parent
DB_FILE = DATA_DIR / 'us_etf_return.db'

# ETF 池
ETF_POOL = {
    # S&P 500
    'SPY': {'name': 'SPDR S&P 500', 'sector': 'S&P 500', 'tier': 1, 'dca_weight': 25},
    'VOO': {'name': 'Vanguard S&P 500', 'sector': 'S&P 500', 'tier': 1, 'dca_weight': 20},
    'IVV': {'name': 'iShares S&P 500', 'sector': 'S&P 500', 'tier': 1, 'dca_weight': 15},
    'VTI': {'name': 'Vanguard Total Stock', 'sector': 'Total Market', 'tier': 1, 'dca_weight': 15},
    
    # Tech
    'QQQ': {'name': 'Invesco QQQ', 'sector': 'Tech', 'tier': 1, 'dca_weight': 15},
    'QQQM': {'name': 'Invesco Nasdaq 100', 'sector': 'Tech', 'tier': 2, 'dca_weight': 10},
    'XLK': {'name': 'Tech Select', 'sector': 'Tech', 'tier': 2, 'dca_weight': 10},
    
    # Dividend
    'VIG': {'name': 'Dividend Appreciation', 'sector': 'Dividend', 'tier': 2, 'dca_weight': 5},
    'SCHD': {'name': 'Schwab Dividend', 'sector': 'Dividend', 'tier': 2, 'dca_weight': 5},
    'DVY': {'name': 'iShares Dividend', 'sector': 'Dividend', 'tier': 2, 'dca_weight': 5},
    'HDV': {'name': 'High Dividend', 'sector': 'Dividend', 'tier': 2, 'dca_weight': 5},
    'DGRO': {'name': 'Dividend Growth', 'sector': 'Dividend', 'tier': 2, 'dca_weight': 5},
    'VYM': {'name': 'High Dividend Yield', 'sector': 'Dividend', 'tier': 2, 'dca_weight': 5},
    'VYM': {'name': 'High Dividend Yield', 'sector': 'Dividend', 'tier': 2, 'dca_weight': 5},
    
    # Bonds
    'TLT': {'name': '20+ Year Treasury', 'sector': 'Bond', 'tier': 2, 'dca_weight': 5},
    'IEF': {'name': '7-10 Year Treasury', 'sector': 'Bond', 'tier': 2, 'dca_weight': 5},
    'BND': {'name': 'Total Bond', 'sector': 'Bond', 'tier': 2, 'dca_weight': 5},
    'AGG': {'name': 'US Aggregate Bond', 'sector': 'Bond', 'tier': 2, 'dca_weight': 5},
    
    # Gold/Commodities
    'GLD': {'name': 'SPDR Gold', 'sector': 'Commodity', 'tier': 2, 'dca_weight': 5},
    'SLV': {'name': 'iShares Silver', 'sector': 'Commodity', 'tier': 3, 'dca_weight': 0},
    
    # International
    'VEA': {'name': 'Developed ex-US', 'sector': 'International', 'tier': 2, 'dca_weight': 5},
    'VWO': {'name': 'FTSE Emerging', 'sector': 'EM', 'tier': 2, 'dca_weight': 5},
    'EEM': {'name': 'Emerging Markets', 'sector': 'EM', 'tier': 2, 'dca_weight': 5},
    
    # Sectors
    'XLF': {'name': 'Financial Select', 'sector': 'Financial', 'tier': 2, 'dca_weight': 5},
    'XLE': {'name': 'Energy Select', 'sector': 'Energy', 'tier': 3, 'dca_weight': 0},
    'XLV': {'name': 'Health Care', 'sector': 'Healthcare', 'tier': 2, 'dca_weight': 5},
    
    # Leveraged (not for DCA)
    'TQQQ': {'name': 'ProShares 3x Long QQQ', 'sector': 'Leveraged', 'tier': 3, 'dca_weight': 0},
    'SPXL': {'name': '3x Long S&P 500', 'sector': 'Leveraged', 'tier': 3, 'dca_weight': 0},
}

# Deduplicate
ETF_POOL = {k: v for k, v in ETF_POOL.items()}

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
        dca_weight INTEGER
    )
    ''')
    
    cur.execute('''
    CREATE TABLE IF NOT EXISTS return_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        symbol TEXT,
        name TEXT,
        price REAL,
        price_1m REAL,
        price_3m REAL,
        price_6m REAL,
        price_1y REAL,
        price_3y REAL,
        price_5y REAL,
        ret_1m REAL,
        ret_3m REAL,
        ret_6m REAL,
        ret_1y REAL,
        ret_3y REAL,
        ret_5y REAL,
        ann_1y REAL,
        ann_3y REAL,
        ann_5y REAL,
        vol_1y REAL,
        sharpe_1y REAL,
        maxdd_1y REAL
    )
    ''')
    
    cur.execute('''
    CREATE TABLE IF NOT EXISTS yield_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        symbol TEXT,
        name TEXT,
        price REAL,
        dividend_yield REAL,
        annual_dividend REAL,
        monthly_income REAL,
        yield_1y REAL,
        yield_3y REAL,
        yield_5y REAL,
        dividend_growth REAL,
        payout_ratio REAL
    )
    ''')
    
    cur.execute('''
    CREATE TABLE IF NOT EXISTS etf_ranking (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        symbol TEXT,
        name TEXT,
        sector TEXT,
        ann_return REAL,
        sharpe_ratio REAL,
        yield REAL,
        max_dd REAL,
        score REAL,
        recommendation TEXT
    )
    ''')
    
    # Insert ETF pool
    for sym, info in ETF_POOL.items():
        cur.execute('''
            INSERT OR REPLACE INTO etfs (symbol, name, sector, tier, dca_weight)
            VALUES (?, ?, ?, ?, ?)
        ''', (sym, info['name'], info['sector'], info['tier'], info['dca_weight']))
    
    conn.commit()
    conn.close()
    return DB_FILE

def calc_returns(hist, periods):
    """計算各期間報酬"""
    result = {}
    for p in periods:
        if len(hist) >= p:
            ret = (hist['Close'].iloc[-1] / hist['Close'].iloc[-p] - 1) * 100
            result[f'ret_{p}d'] = ret
        else:
            result[f'ret_{p}d'] = None
    return result

def calc_annualized(ret, days):
    """年化報酬"""
    if ret is not None and days > 0:
        return ((1 + ret/100) ** (365/days) - 1) * 100
    return None

def calc_volatility(returns):
    """計算波動率"""
    if len(returns) > 0:
        return returns.std() * (252**0.5) * 100
    return None

def fetch_return_data():
    """抓取報酬數據"""
    results = []
    timestamp = datetime.now().isoformat()
    
    for sym, info in ETF_POOL.items():
        try:
            t = yf.Ticker(sym)
            hist = t.history(period='5y')
            
            if len(hist) < 60:
                continue
            
            price = float(hist['Close'].iloc[-1])
            
            # 各期間報酬
            periods = {'1d': 1, '5d': 5, '1m': 21, '3m': 63, '6m': 126, '1y': 252, '3y': 756, '5y': 1260}
            rets = calc_returns(hist, [21, 63, 126, 252, 756, 1260])
            
            # 年化報酬
            ann_1y = calc_annualized(rets.get('ret_252d'), 252) if rets.get('ret_252d') else None
            ann_3y = calc_annualized(rets.get('ret_756d'), 756) if rets.get('ret_756d') else None
            ann_5y = calc_annualized(rets.get('ret_1260d'), 1260) if rets.get('ret_1260d') else None
            
            # 波動率 (1年日報酬)
            if len(hist) >= 252:
                daily_ret = hist['Close'].pct_change().iloc[-252:]
                vol_1y = calc_volatility(daily_ret)
                
                # Sharpe (假設無風險利率 4%)
                risk_free = 4.0
                sharpe_1y = (ann_1y - risk_free) / vol_1y if ann_1y and vol_1y else None
                
                # Max Drawdown
                rolling_max = hist['Close'].iloc[-252:].cummax()
                drawdown = hist['Close'].iloc[-252:] / rolling_max - 1
                maxdd_1y = drawdown.min() * 100
            else:
                vol_1y = None
                sharpe_1y = None
                maxdd_1y = None
            
            results.append({
                'symbol': sym,
                'name': info['name'],
                'sector': info['sector'],
                'tier': info['tier'],
                'dca_weight': info['dca_weight'],
                'price': price,
                'ret_1m': rets.get('ret_21d'),
                'ret_3m': rets.get('ret_63d'),
                'ret_6m': rets.get('ret_126d'),
                'ret_1y': rets.get('ret_252d'),
                'ret_3y': rets.get('ret_756d'),
                'ret_5y': rets.get('ret_1260d'),
                'ann_1y': ann_1y,
                'ann_3y': ann_3y,
                'ann_5y': ann_5y,
                'vol_1y': vol_1y,
                'sharpe_1y': sharpe_1y,
                'maxdd_1y': maxdd_1y,
                'timestamp': timestamp
            })
            
        except Exception as e:
            results.append({
                'symbol': sym,
                'name': info['name'],
                'error': str(e)
            })
    
    return results

def fetch_yield_data():
    """抓取殖利數據"""
    results = []
    timestamp = datetime.now().isoformat()
    
    for sym, info in ETF_POOL.items():
        try:
            t = yf.Ticker(sym)
            info_data = t.info
            
            price = float(info_data.get('regularMarketPrice', 0))
            div_yield = info_data.get('dividendYield', 0) * 100 if info_data.get('dividendYield') else 0
            annual_div = info_data.get('annualDividendYield', 0) * 100 if info_data.get('annualDividendYield') else 0
            
            # 月收入 (假設 DCA 10000)
            monthly_income = price * div_yield / 100 / 12 if price and div_yield else 0
            
            results.append({
                'symbol': sym,
                'name': info['name'],
                'sector': info['sector'],
                'dca_weight': info['dca_weight'],
                'price': price,
                'dividend_yield': div_yield,
                'annual_dividend': annual_div,
                'monthly_income': monthly_income,
                'timestamp': timestamp
            })
            
        except Exception as e:
            results.append({
                'symbol': sym,
                'name': info['name'],
                'error': str(e)
            })
    
    return results

def save_return_data(data):
    """儲存報酬數據"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    
    for d in data:
        if 'error' in d:
            continue
        try:
            cur.execute('''
                INSERT INTO return_data 
                (timestamp, symbol, name, price, ret_1m, ret_3m, ret_6m, ret_1y, ret_3y, ret_5y,
                 ann_1y, ann_3y, ann_5y, vol_1y, sharpe_1y, maxdd_1y)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                d['timestamp'], d['symbol'], d['name'], d['price'],
                d.get('ret_1m'), d.get('ret_3m'), d.get('ret_6m'),
                d.get('ret_1y'), d.get('ret_3y'), d.get('ret_5y'),
                d.get('ann_1y'), d.get('ann_3y'), d.get('ann_5y'),
                d.get('vol_1y'), d.get('sharpe_1y'), d.get('maxdd_1y')
            ))
        except Exception as e:
            print(f"Error saving {d.get('symbol')}: {e}")
    
    conn.commit()
    conn.close()

def save_yield_data(data):
    """儲存殖利數據"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    
    for d in data:
        if 'error' in d:
            continue
        try:
            cur.execute('''
                INSERT INTO yield_data 
                (timestamp, symbol, name, price, dividend_yield, annual_dividend, monthly_income)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                d['timestamp'], d['symbol'], d['name'], d['price'],
                d.get('dividend_yield', 0), d.get('annual_dividend', 0), d.get('monthly_income', 0)
            ))
        except Exception as e:
            print(f"Error saving {d.get('symbol')}: {e}")
    
    conn.commit()
    conn.close()

def generate_rankings(return_data, yield_data):
    """產生 ETF 排名"""
    rankings = []
    timestamp = datetime.now().isoformat()
    
    for d in return_data:
        if 'error' in d:
            continue
        
        sym = d['symbol']
        # Find yield data
        yd = next((y for y in yield_data if y['symbol'] == sym), {})
        
        # Calculate score
        score = 0
        ann = d.get('ann_1y', 0) or 0
        sharpe = d.get('sharpe_1y', 0) or 0
        yld = yd.get('dividend_yield', 0) or 0
        mdd = d.get('maxdd_1y', 0) or 0
        
        score = ann * 30 + sharpe * 20 + yld * 10 + abs(mdd) * 5
        score = max(0, min(100, score))
        
        # Recommendation
        if ann > 15 and sharpe > 0.8:
            rec = 'STRONG_BUY'
        elif ann > 10 and sharpe > 0.5:
            rec = 'BUY'
        elif yld > 3:
            rec = 'DIVIDEND'
        elif mdd < -20:
            rec = 'WATCH'
        else:
            rec = 'NEUTRAL'
        
        rankings.append({
            'symbol': sym,
            'name': d['name'],
            'sector': d['sector'],
            'tier': d['tier'],
            'dca_weight': d['dca_weight'],
            'ann_1y': ann,
            'sharpe_1y': sharpe,
            'yield': yld,
            'maxdd_1y': mdd,
            'score': score,
            'recommendation': rec,
            'timestamp': timestamp
        })
    
    return sorted(rankings, key=lambda x: -x['score'])

if __name__ == '__main__':
    print("=" * 70)
    print("  US ETF Return & Yield Database")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Init
    print("\n[1] Initializing database...")
    init_db()
    print(f"  OK: {DB_FILE}")
    
    # Fetch Return Data
    print("\n[2] Fetching return data (5Y)...")
    ret_data = fetch_return_data()
    print(f"  Fetched {len(ret_data)} ETFs")
    
    # Fetch Yield Data
    print("\n[3] Fetching yield data...")
    yld_data = fetch_yield_data()
    print(f"  Fetched {len(yld_data)} ETFs")
    
    # Save
    print("\n[4] Saving to database...")
    save_return_data(ret_data)
    save_yield_data(yld_data)
    print("  OK")
    
    # Rankings
    print("\n[5] ETF Rankings:")
    print("-" * 70)
    
    rankings = generate_rankings(ret_data, yld_data)
    
    print(f"\n  {'Rank':<5} {'Symbol':<8} {'Name':<18} {'Ann 1Y':>8} {'Sharpe':>7} {'Yield':>6} {'Score':>6}")
    print("  " + "-" * 65)
    
    for i, r in enumerate(rankings[:20], 1):
        ann = f"{r['ann_1y']:+.1f}%" if r['ann_1y'] else "N/A"
        shp = f"{r['sharpe_1y']:.2f}" if r['sharpe_1y'] else "N/A"
        yld = f"{r['yield']:.2f}%" if r['yield'] else "N/A"
        print(f"  {i:<5} {r['symbol']:<8} {r['name']:<18} {ann:>8} {shp:>7} {yld:>6} {r['score']:>6.1f}")
    
    # Top Sharpe
    print("\n[6] Top Sharpe Ratio:")
    top_sharpe = sorted([r for r in rankings if r['sharpe_1y']], key=lambda x: -x['sharpe_1y'])[:5]
    for r in top_sharpe:
        print(f"  {r['symbol']}: Sharpe={r['sharpe_1y']:.2f}, Ann={r['ann_1y']:.1f}%")
    
    # Top Dividend
    print("\n[7] Top Dividend Yield:")
    top_yield = sorted([r for r in rankings if r['yield'] > 0], key=lambda x: -x['yield'])[:5]
    for r in top_yield:
        print(f"  {r['symbol']}: Yield={r['yield']:.2f}%, Ann={r['ann_1y']:.1f}%")
    
    print("\n" + "=" * 70)
