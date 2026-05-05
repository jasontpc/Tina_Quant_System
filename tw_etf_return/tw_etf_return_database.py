"""
台股 ETF 殖利率 & 年化報酬率 & EPS 資料庫
Taiwan ETF Return, Yield & EPS Database
"""

import sqlite3
import json
import yfinance as yf
import pandas as pd
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent
DB_FILE = DATA_DIR / 'tw_etf_return.db'

# 台股 ETF 池
ETF_POOL = {
    '0050': {'name': '元大台灣50', 'sector': 'Large Cap', 'tier': 1, 'dca_weight': 30},
    '0056': {'name': '元大高股息', 'sector': 'Dividend', 'tier': 1, 'dca_weight': 25},
    '00646': {'name': '富邦S&P500', 'sector': 'S&P 500', 'tier': 2, 'dca_weight': 15},
    '00662': {'name': '富邦NASDAQ100', 'sector': 'Tech', 'tier': 2, 'dca_weight': 10},
    '00713': {'name': '元大高息低波', 'sector': 'Dividend', 'tier': 1, 'dca_weight': 15},
    '00757': {'name': '統一FANG+', 'sector': 'Tech', 'tier': 2, 'dca_weight': 10},
    '00878': {'name': '國泰永續高股息', 'sector': 'Dividend', 'tier': 1, 'dca_weight': 20},
    '00881': {'name': '國泰台灣5G+', 'sector': 'Tech', 'tier': 2, 'dca_weight': 5},
    '00891': {'name': '中信金能', 'sector': 'Energy', 'tier': 3, 'dca_weight': 0},
    '00892': {'name': '富邦台灣ESG', 'sector': 'ESG', 'tier': 2, 'dca_weight': 5},
    '00893': {'name': '元大IC', 'sector': 'Semi', 'tier': 3, 'dca_weight': 0},
    '00895': {'name': '富邦元宇宙', 'sector': 'Tech', 'tier': 3, 'dca_weight': 0},
    '00896': {'name': '兆豐藍籌30', 'sector': 'Blue Chip', 'tier': 2, 'dca_weight': 5},
    '00899': {'name': 'FT台灣Smart', 'sector': 'Smart Beta', 'tier': 2, 'dca_weight': 5},
    '00900': {'name': '富邦Smart', 'sector': 'Smart Beta', 'tier': 3, 'dca_weight': 0},
    '00904': {'name': '兆豐藍籌30', 'sector': 'Blue Chip', 'tier': 3, 'dca_weight': 0},
    '00909': {'name': '永豐ESG', 'sector': 'ESG', 'tier': 2, 'dca_weight': 5},
    '00922': {'name': '中信關鍵半導體', 'sector': 'Semi', 'tier': 2, 'dca_weight': 10},
    '00923': {'name': '群益ESG', 'sector': 'ESG', 'tier': 2, 'dca_weight': 5},
    '00927': {'name': '統一是創未來', 'sector': 'Innovation', 'tier': 2, 'dca_weight': 5},
    '00927': {'name': '統一是創未來', 'sector': 'Innovation', 'tier': 2, 'dca_weight': 5},
}

# Deduplicate
seen = {}
for sym, info in ETF_POOL.items():
    if info['name'] not in seen:
        seen[info['name']] = sym
ETF_POOL = {v: k for k, v in seen.items()} if False else ETF_POOL  # keep original

# Re-deduplicate properly
_temp = {}
for sym, info in list(ETF_POOL.items()):
    key = info['name']
    if key not in _temp:
        _temp[key] = (sym, info)
ETF_POOL = {v[0]: v[1] for v in _temp.values()}

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
        ret_1m REAL,
        ret_3m REAL,
        ret_6m REAL,
        ret_1y REAL,
        ann_1y REAL,
        ann_3y REAL,
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
        payout_ratio REAL
    )
    ''')
    
    cur.execute('''
    CREATE TABLE IF NOT EXISTS eps_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        symbol TEXT,
        name TEXT,
        price REAL,
        eps_ttm REAL,
        eps_history_1y REAL,
        eps_growth REAL,
        pe_ratio REAL,
        pb_ratio REAL,
        roe REAL
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
        eps_growth REAL,
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

def calc_returns(hist, days_list):
    """計算各期間報酬"""
    result = {}
    for d in days_list:
        if len(hist) >= d:
            ret = (hist['Close'].iloc[-1] / hist['Close'].iloc[-d] - 1) * 100
            result[f'ret_{d}d'] = ret
        else:
            result[f'ret_{d}d'] = None
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
            t = yf.Ticker(sym + '.TW')
            hist = t.history(period='3y')
            
            if len(hist) < 60:
                continue
            
            # 去除 NaN
            close = hist['Close'].dropna()
            if len(close) < 60:
                continue
            
            price = float(close.iloc[-1])
            
            # 各期間報酬 (使用 dropna 確保有效數據)
            close_clean = close.dropna()
            rets = {}
            for d in [21, 63, 126, 252]:
                if len(close_clean) >= d:
                    ret = (close_clean.iloc[-1] / close_clean.iloc[-d] - 1) * 100
                    rets[f'ret_{d}d'] = ret if ret == ret else None  # handle inf
                else:
                    rets[f'ret_{d}d'] = None
            
            # 年化報酬
            ann_1y = calc_annualized(rets.get('ret_252d'), 252) if rets.get('ret_252d') else None
            
            # 波動率 (1年日報酬)
            if len(hist) >= 252:
                daily_ret = hist['Close'].pct_change().iloc[-252:]
                vol_1y = calc_volatility(daily_ret.dropna())
                
                # Sharpe (假設無風險利率 1.5%)
                risk_free = 1.5
                sharpe_1y = (ann_1y - risk_free) / vol_1y if ann_1y and vol_1y else None
                
                # Max Drawdown (處理 NaN)
                close_clean = hist['Close'].iloc[-252:].dropna()
                if len(close_clean) > 0:
                    rolling_max = close_clean.cummax()
                    drawdown = close_clean / rolling_max - 1
                    maxdd_1y = drawdown.min() * 100
                else:
                    maxdd_1y = None
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
                'ann_1y': ann_1y,
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
    """抓取殖利數據 (使用 EPS 取代配息)"""
    results = []
    timestamp = datetime.now().isoformat()
    
    for sym, info in ETF_POOL.items():
        try:
            t = yf.Ticker(sym + '.TW')
            info_data = t.info
            
            price = float(info_data.get('regularMarketPrice', 0))
            div_yield = info_data.get('dividendYield', 0) * 100 if info_data.get('dividendYield') else 0
            annual_div = info_data.get('annualDividendYield', 0) * 100 if info_data.get('annualDividendYield') else 0
            
            # 月收入
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

def fetch_eps_data():
    """抓取 EPS 數據"""
    results = []
    timestamp = datetime.now().isoformat()
    
    for sym, info in ETF_POOL.items():
        try:
            t = yf.Ticker(sym + '.TW')
            hist = t.history(period='3y')
            info_data = t.info
            
            price = float(info_data.get('regularMarketPrice', 0))
            
            # EPS (取不到就用歷史除權還原)
            eps = info_data.get('trailingEps', 0) or 0
            eps_hist = info_data.get('forwardEps', 0) or eps
            
            # PE/PB
            pe = info_data.get('trailingPE', 0) or 0
            pb = info_data.get('priceToBook', 0) or 0
            roe = info_data.get('returnOnEquity', 0) or 0
            
            # EPS Growth
            if eps > 0 and eps_hist > 0:
                eps_growth = (eps - eps_hist) / eps_hist * 100
            else:
                eps_growth = 0
            
            results.append({
                'symbol': sym,
                'name': info['name'],
                'sector': info['sector'],
                'dca_weight': info['dca_weight'],
                'price': price,
                'eps_ttm': eps,
                'eps_history_1y': eps_hist,
                'eps_growth': eps_growth,
                'pe_ratio': pe,
                'pb_ratio': pb,
                'roe': roe * 100 if roe else 0,
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
                (timestamp, symbol, name, price, ret_1m, ret_3m, ret_6m, ret_1y, ann_1y, vol_1y, sharpe_1y, maxdd_1y)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                d['timestamp'], d['symbol'], d['name'], d['price'],
                d.get('ret_1m'), d.get('ret_3m'), d.get('ret_6m'), d.get('ret_1y'),
                d.get('ann_1y'), d.get('vol_1y'), d.get('sharpe_1y'), d.get('maxdd_1y')
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

def save_eps_data(data):
    """儲存 EPS 數據"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    
    for d in data:
        if 'error' in d:
            continue
        try:
            cur.execute('''
                INSERT INTO eps_data 
                (timestamp, symbol, name, price, eps_ttm, eps_history_1y, eps_growth, pe_ratio, pb_ratio, roe)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                d['timestamp'], d['symbol'], d['name'], d['price'],
                d.get('eps_ttm', 0), d.get('eps_history_1y', 0), d.get('eps_growth', 0),
                d.get('pe_ratio', 0), d.get('pb_ratio', 0), d.get('roe', 0)
            ))
        except Exception as e:
            print(f"Error saving {d.get('symbol')}: {e}")
    
    conn.commit()
    conn.close()

def generate_rankings(return_data, yield_data, eps_data):
    """產生排名"""
    rankings = []
    timestamp = datetime.now().isoformat()
    
    for d in return_data:
        if 'error' in d:
            continue
        
        sym = d['symbol']
        yd = next((y for y in yield_data if y['symbol'] == sym), {})
        ed = next((e for e in eps_data if e['symbol'] == sym), {})
        
        # Score
        score = 0
        ann = d.get('ann_1y', 0) or 0
        sharpe = d.get('sharpe_1y', 0) or 0
        yld = yd.get('dividend_yield', 0) or 0
        eps_g = ed.get('eps_growth', 0) or 0
        mdd = d.get('maxdd_1y', 0) or 0
        
        score = ann * 30 + sharpe * 20 + yld * 10 + eps_g * 5 + abs(mdd) * 3
        score = max(0, min(100, score))
        
        # Recommendation
        if ann > 20 and sharpe > 1.0:
            rec = 'STRONG_BUY'
        elif ann > 10 and sharpe > 0.5:
            rec = 'BUY'
        elif yld > 4:
            rec = 'DIVIDEND'
        elif eps_g > 15:
            rec = 'GROWTH'
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
            'eps_growth': eps_g,
            'pe': ed.get('pe_ratio', 0) or 0,
            'pb': ed.get('pb_ratio', 0) or 0,
            'roe': ed.get('roe', 0) or 0,
            'maxdd_1y': mdd,
            'score': score,
            'recommendation': rec,
            'timestamp': timestamp
        })
    
    return sorted(rankings, key=lambda x: -x['score'])

if __name__ == '__main__':
    print("=" * 70)
    print("  TW ETF Return, Yield & EPS Database")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Init
    print("\n[1] Initializing database...")
    init_db()
    print(f"  OK: {DB_FILE}")
    
    # Fetch Return Data
    print("\n[2] Fetching return data (3Y)...")
    ret_data = fetch_return_data()
    valid_ret = [r for r in ret_data if 'error' not in r]
    print(f"  Fetched {len(ret_data)} ETFs ({len(valid_ret)} valid)")
    
    # Fetch Yield Data
    print("\n[3] Fetching yield data...")
    yld_data = fetch_yield_data()
    print(f"  Fetched {len(yld_data)} ETFs")
    
    # Fetch EPS Data
    print("\n[4] Fetching EPS data...")
    eps_data = fetch_eps_data()
    print(f"  Fetched {len(eps_data)} ETFs")
    
    # Save
    print("\n[5] Saving to database...")
    save_return_data(ret_data)
    save_yield_data(yld_data)
    save_eps_data(eps_data)
    print("  OK")
    
    # Rankings
    print("\n[6] ETF Rankings:")
    print("-" * 70)
    
    rankings = generate_rankings(ret_data, yld_data, eps_data)
    
    print(f"\n  {'Rank':<5} {'Symbol':<6} {'Name':<15} {'Ann 1Y':>8} {'Sharpe':>6} {'Yield':>6} {'Score':>6}")
    print("  " + "-" * 60)
    
    for i, r in enumerate(rankings[:20], 1):
        ann = f"{r['ann_1y']:+.1f}%" if r['ann_1y'] else "N/A"
        shp = f"{r['sharpe_1y']:.2f}" if r['sharpe_1y'] else "N/A"
        yld = f"{r['yield']:.2f}%" if r['yield'] else "N/A"
        print(f"  {i:<5} {r['symbol']:<6} {r['name']:<15} {ann:>8} {shp:>6} {yld:>6} {r['score']:>6.1f}")
    
    # DCA Recommendations
    dca_recs = [r for r in rankings if r['dca_weight'] > 0 and r['tier'] in [1, 2]]
    dca_recs = sorted(dca_recs, key=lambda x: -x['ann_1y'] if x['ann_1y'] else 0)
    
    print("\n[7] DCA Recommendations:")
    print("-" * 70)
    for r in dca_recs[:10]:
        ann = f"{r['ann_1y']:+.1f}%" if r['ann_1y'] else "N/A"
        print(f"  {r['symbol']:<6} {r['name']:<15} {r['dca_weight']:>5}% {ann:>8} {r['recommendation']}")
    
    print("\n" + "=" * 70)
