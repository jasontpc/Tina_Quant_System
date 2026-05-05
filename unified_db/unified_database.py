"""
全系統整合資料庫
Unified Trading Database
Consolidates all systems: Leo, Nana, Ray, Maggy, Sherry, Vogel
"""

import sqlite3
import json
import yfinance as yf
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

DATA_DIR = Path(__file__).parent
DB_FILE = DATA_DIR / 'unified_trading.db'

# 系統池
SYSTEMS = ['leo', 'nana', 'ray', 'maggy', 'sherry', 'vogel']

# 最佳個股池 (從歷史數據分析)
BEST_STOCKS = {
    # 台股
    '2330.TW': {'name': '台積電', 'sector': 'Semi', 'market': 'TW'},
    '2454.TW': {'name': '聯發科', 'sector': 'Tech', 'market': 'TW'},
    '2382.TW': {'name': '廣達', 'sector': 'Tech', 'market': 'TW'},
    '2317.TW': {'name': '鴻海', 'sector': 'Tech', 'market': 'TW'},
    '3034.TW': {'name': '緯穎', 'sector': 'Tech', 'market': 'TW'},
    '2379.TW': {'name': '宜霈', 'sector': 'Tech', 'market': 'TW'},
    '3665.TW': {'name': '穎崴', 'sector': 'Semi', 'market': 'TW'},
    '2474.TW': {'name': '可成', 'sector': 'Tech', 'market': 'TW'},
    '2458.TW': {'name': '義隆', 'sector': 'Tech', 'market': 'TW'},
    '3016.TW': {'name': '晶技', 'sector': 'Tech', 'market': 'TW'},
    '3533.TW': {'name': '嘉澤', 'sector': 'Tech', 'market': 'TW'},
    '4961.TW': {'name': '天璣', 'sector': 'Tech', 'market': 'TW'},
    '6412.TW': {'name': '華擎', 'sector': 'Tech', 'market': 'TW'},
    '3406.TW': {'name': '玉晶光', 'sector': 'Tech', 'market': 'TW'},
    '2201.TW': {'name': '裕融', 'sector': 'Finance', 'market': 'TW'},
    '5871.TW': {'name': '中租', 'sector': 'Finance', 'market': 'TW'},
    '2888.TW': {'name': '開發金', 'sector': 'Finance', 'market': 'TW'},
    '2884.TW': {'name': '玉山金', 'sector': 'Finance', 'market': 'TW'},
    '2891.TW': {'name': '中信金', 'sector': 'Finance', 'market': 'TW'},
    '2615.TW': {'name': '萬海', 'sector': 'Shipping', 'market': 'TW'},
    '2618.TW': {'name': '長榮航', 'sector': 'Shipping', 'market': 'TW'},
    
    # 美股
    'NVDA': {'name': 'Nvidia', 'sector': 'AI/Semi', 'market': 'US'},
    'AMD': {'name': 'AMD', 'sector': 'AI/Semi', 'market': 'US'},
    'PLTR': {'name': 'Palantir', 'sector': 'AI', 'market': 'US'},
    'GOOGL': {'name': 'Alphabet', 'sector': 'Tech', 'market': 'US'},
    'AMZN': {'name': 'Amazon', 'sector': 'Tech', 'market': 'US'},
    'META': {'name': 'Meta', 'sector': 'Social Media', 'market': 'US'},
    'TSLA': {'name': 'Tesla', 'sector': 'EV', 'market': 'US'},
    'MSFT': {'name': 'Microsoft', 'sector': 'Tech', 'market': 'US'},
    'KLAC': {'name': 'KLA Corp', 'sector': 'Semi', 'market': 'US'},
    'LRCX': {'name': 'Lam Research', 'sector': 'Semi', 'market': 'US'},
    'AMAT': {'name': 'Applied Materials', 'sector': 'Semi', 'market': 'US'},
    'SOXX': {'name': 'PHLX Semi', 'sector': 'Semi ETF', 'market': 'US'},
    'XLE': {'name': 'Energy Select', 'sector': 'Energy', 'market': 'US'},
    'XLF': {'name': 'Financial Select', 'sector': 'Financial', 'market': 'US'},
    'XLV': {'name': 'Health Care', 'sector': 'Healthcare', 'market': 'US'},
}

def init_db():
    """初始化資料庫"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    
    # 交易歷史
    cur.execute('''
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        system TEXT,
        symbol TEXT,
        name TEXT,
        market TEXT,
        sector TEXT,
        entry_price REAL,
        exit_price REAL,
        entry_date TEXT,
        exit_date TEXT,
        hold_days INTEGER,
        return_pct REAL,
        tp_pct REAL,
        sl_pct REAL,
        rsi_entry REAL,
        status TEXT,
        tags TEXT
    )
    ''')
    
    # 股票表現
    cur.execute('''
    CREATE TABLE IF NOT EXISTS stock_perf (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        symbol TEXT,
        name TEXT,
        market TEXT,
        sector TEXT,
        total_trades INTEGER,
        win_trades INTEGER,
        win_rate REAL,
        avg_return REAL,
        avg_hold_days REAL,
        best_return REAL,
        worst_return REAL,
        ann_return REAL,
        sharpe_ratio REAL,
        max_dd REAL,
        best_rsi_entry REAL,
        best_tp_pct REAL,
        best_sl_pct REAL,
        score REAL
    )
    ''')
    
    # 系統表現
    cur.execute('''
    CREATE TABLE IF NOT EXISTS system_perf (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        system TEXT,
        total_trades INTEGER,
        win_trades INTEGER,
        win_rate REAL,
        avg_return REAL,
        avg_hold_days REAL,
        total_profit REAL,
        best_stock TEXT,
        worst_stock TEXT,
        recommendation TEXT
    )
    ''')
    
    # 最佳參數
    cur.execute('''
    CREATE TABLE IF NOT EXISTS optimal_params (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        symbol TEXT,
        market TEXT,
        rsi_entry_min INTEGER,
        rsi_entry_max INTEGER,
        hold_days_min INTEGER,
        hold_days_max INTEGER,
        tp_pct REAL,
        sl_pct REAL,
        win_rate REAL,
        avg_return REAL,
        sample_size INTEGER
    )
    ''')
    
    # 綜合信號
    cur.execute('''
    CREATE TABLE IF NOT EXISTS unified_signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        symbol TEXT,
        name TEXT,
        market TEXT,
        sector TEXT,
        price REAL,
        rsi_14 REAL,
        signal TEXT,
        confidence INTEGER,
        sources TEXT,
        entry_price REAL,
        tp_price REAL,
        sl_price REAL,
        reason TEXT
    )
    ''')
    
    conn.commit()
    conn.close()
    return DB_FILE

def load_all_trades():
    """載入所有系統的交易記錄"""
    all_trades = []
    
    # Leo trades
    try:
        path = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leadtrades\leos\leos_trades.json'
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for t in data.get('trades', []):
            t['system'] = 'leo'
            t['market'] = 'TW'
            all_trades.append(t)
    except Exception as e:
        print(f"Leo load error: {e}")
    
    # Nana trades
    try:
        path = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\nana\autonomous_trades.json'
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for t in data.get('trades', []):
            t['system'] = 'nana'
            t['market'] = 'TW'
            all_trades.append(t)
    except Exception as e:
        print(f"Nana load error: {e}")
    
    # Ray DCA
    try:
        path = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\ray\autonomous_trades.json'
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for t in data.get('trades', []):
            t['system'] = 'ray'
            t['market'] = 'TW'
            all_trades.append(t)
    except Exception as e:
        print(f"Ray load error: {e}")
    
    return all_trades

def save_trades(trades):
    """儲存交易到資料庫"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    timestamp = datetime.now().isoformat()
    
    for t in trades:
        try:
            cur.execute('''
                INSERT INTO trades 
                (timestamp, system, symbol, name, market, sector, entry_price, exit_price,
                 entry_date, exit_date, hold_days, return_pct, tp_pct, sl_pct, rsi_entry, status, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                timestamp, t.get('system'), t.get('symbol'), t.get('name'),
                t.get('market'), t.get('sector'), t.get('entry_price'), t.get('exit_price'),
                t.get('entry_date'), t.get('exit_date'), t.get('hold_days'),
                t.get('return_pct'), t.get('tp_pct'), t.get('sl_pct'),
                t.get('rsi_entry'), t.get('status'), t.get('tags', '')
            ))
        except Exception as e:
            pass
    
    conn.commit()
    conn.close()

def analyze_stock_performance():
    """分析個股表現"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    timestamp = datetime.now().isoformat()
    
    # Get completed trades
    cur.execute('''
        SELECT symbol, name, market, sector, 
               COUNT(*) as total,
               SUM(CASE WHEN return_pct > 0 THEN 1 ELSE 0 END) as wins,
               AVG(return_pct) as avg_ret,
               AVG(hold_days) as avg_hold,
               MAX(return_pct) as best,
               MIN(return_pct) as worst,
               AVG(rsi_entry) as avg_rsi
        FROM trades
        WHERE status = 'closed'
        GROUP BY symbol
        HAVING total >= 3
        ORDER BY avg_ret DESC
    ''')
    
    results = []
    for row in cur.fetchall():
        sym, name, market, sector = row[0], row[1], row[2], row[3]
        total, wins = row[4], row[5]
        avg_ret = row[6] or 0
        avg_hold = row[7] or 0
        best = row[8] or 0
        worst = row[9] or 0
        avg_rsi = row[10] or 50
        
        win_rate = wins / total * 100 if total > 0 else 0
        
        # Score
        score = win_rate * 0.4 + avg_ret * 10 * 0.3 + (100 - abs(worst)) * 0.3
        
        results.append({
            'symbol': sym,
            'name': name,
            'market': market,
            'sector': sector,
            'total_trades': total,
            'win_trades': wins,
            'win_rate': win_rate,
            'avg_return': avg_ret,
            'avg_hold_days': avg_hold,
            'best_return': best,
            'worst_return': worst,
            'avg_rsi_entry': avg_rsi,
            'score': score,
            'timestamp': timestamp
        })
    
    # Save
    for r in results:
        try:
            cur.execute('''
                INSERT INTO stock_perf
                (timestamp, symbol, name, market, sector, total_trades, win_trades, 
                 win_rate, avg_return, avg_hold_days, best_return, worst_return, score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                r['timestamp'], r['symbol'], r['name'], r['market'], r['sector'],
                r['total_trades'], r['win_trades'], r['win_rate'], r['avg_return'],
                r['avg_hold_days'], r['best_return'], r['worst_return'], r['score']
            ))
        except:
            pass
    
    conn.commit()
    conn.close()
    return results

def analyze_system_performance():
    """分析系統表現"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    timestamp = datetime.now().isoformat()
    
    results = []
    for sys in SYSTEMS:
        cur.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN return_pct > 0 THEN 1 ELSE 0 END) as wins,
                AVG(return_pct) as avg_ret,
                AVG(hold_days) as avg_hold,
                SUM(return_pct) as total_profit
            FROM trades
            WHERE system = ? AND status = 'closed'
        ''', (sys,))
        
        row = cur.fetchone()
        if row and row[0]:
            total, wins = row[0], row[1]
            win_rate = wins / total * 100 if total > 0 else 0
            
            results.append({
                'system': sys,
                'total_trades': total,
                'win_trades': wins,
                'win_rate': win_rate,
                'avg_return': row[2] or 0,
                'avg_hold_days': row[3] or 0,
                'total_profit': row[4] or 0,
                'timestamp': timestamp
            })
    
    conn.commit()
    conn.close()
    return results

def find_optimal_params():
    """找出最佳參數"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    timestamp = datetime.now().isoformat()
    
    # For each RSI range
    rsi_ranges = [(20, 30), (30, 40), (40, 50), (50, 60)]
    hold_ranges = [(5, 10), (10, 15), (15, 20), (20, 30)]
    tp_ranges = [(3, 5), (5, 8), (8, 10), (10, 15)]
    sl_ranges = [(5, 8), (8, 10), (10, 15)]
    
    results = []
    
    for rsi_min, rsi_max in rsi_ranges:
        for hold_min, hold_max in hold_ranges:
            for tp in [5, 8, 10]:
                for sl in [8, 10, 15]:
                    cur.execute('''
                        SELECT COUNT(*), 
                               SUM(CASE WHEN return_pct > 0 THEN 1 ELSE 0 END),
                               AVG(return_pct)
                        FROM trades
                        WHERE status = 'closed'
                        AND rsi_entry >= ? AND rsi_entry < ?
                        AND hold_days >= ? AND hold_days < ?
                        AND tp_pct = ? AND sl_pct = ?
                    ''', (rsi_min, rsi_max, hold_min, hold_max, tp, sl))
                    
                    row = cur.fetchone()
                    if row and row[0] and row[0] >= 5:
                        total, wins, avg_ret = row[0], row[1], row[2]
                        win_rate = wins / total * 100
                        
                        results.append({
                            'rsi_min': rsi_min,
                            'rsi_max': rsi_max,
                            'hold_min': hold_min,
                            'hold_max': hold_max,
                            'tp_pct': tp,
                            'sl_pct': sl,
                            'win_rate': win_rate,
                            'avg_return': avg_ret,
                            'sample_size': total
                        })
    
    conn.commit()
    conn.close()
    return sorted(results, key=lambda x: -x['win_rate'])[:20]

def get_unified_signals():
    """產生綜合信號"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    timestamp = datetime.now().isoformat()
    
    # 取得表現好的股票
    cur.execute('''
        SELECT symbol, name, market, sector, win_rate, avg_return, score
        FROM stock_perf
        WHERE total_trades >= 5
        ORDER BY score DESC
        LIMIT 30
    ''')
    
    signals = []
    for row in cur.fetchall():
        sym, name, market, sector = row[0], row[1], row[2], row[3]
        win_rate, avg_return, score = row[4], row[5], row[6]
        
        # Get current price and RSI
        try:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period='2mo')
            if len(hist) > 14:
                price = float(hist['Close'].iloc[-1])
                
                # Calc RSI
                delta = hist['Close'].diff()
                gain = delta.clip(lower=0).rolling(14).mean()
                loss = (-delta.clip(upper=0)).rolling(14).mean()
                rs = gain / loss
                rsi = float((100 - (100 / (1 + rs))).iloc[-1])
                
                # Signal
                if rsi < 40 and win_rate > 60:
                    signal = 'BUY'
                    confidence = int(win_rate)
                elif rsi > 70:
                    signal = 'OVERBOUGHT'
                    confidence = 30
                else:
                    signal = 'WATCH'
                    confidence = 50
                
                signals.append({
                    'symbol': sym,
                    'name': name,
                    'market': market,
                    'sector': sector,
                    'price': price,
                    'rsi_14': rsi,
                    'signal': signal,
                    'confidence': confidence,
                    'win_rate': win_rate,
                    'avg_return': avg_return,
                    'score': score,
                    'timestamp': timestamp
                })
        except:
            pass
    
    conn.commit()
    conn.close()
    return sorted(signals, key=lambda x: (-x['confidence'], -x['win_rate']))

def save_unified_signals(signals):
    """儲存綜合信號"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    
    for s in signals:
        try:
            cur.execute('''
                INSERT INTO unified_signals
                (timestamp, symbol, name, market, sector, price, rsi_14, signal, confidence, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                s['timestamp'], s['symbol'], s['name'], s['market'], s['sector'],
                s['price'], s['rsi_14'], s['signal'], s['confidence'],
                f"WinRate={s['win_rate']:.1f}%, AvgReturn={s['avg_return']:.2f}%"
            ))
        except:
            pass
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    print("=" * 70)
    print("  Unified Trading Database")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Init
    print("\n[1] Initializing database...")
    init_db()
    print(f"  OK: {DB_FILE}")
    
    # Load trades
    print("\n[2] Loading all trades...")
    trades = load_all_trades()
    print(f"  Loaded {len(trades)} trades")
    
    # Save
    print("\n[3] Saving trades to database...")
    save_trades(trades)
    print("  OK")
    
    # Analyze stock performance
    print("\n[4] Analyzing stock performance...")
    stock_perf = analyze_stock_performance()
    print(f"  Analyzed {len(stock_perf)} stocks")
    
    # Analyze system performance
    print("\n[5] Analyzing system performance...")
    sys_perf = analyze_system_performance()
    for s in sys_perf:
        print(f"  {s['system']}: {s['total_trades']} trades, WR={s['win_rate']:.1f}%, Avg={s['avg_return']:.2f}%")
    
    # Find optimal params
    print("\n[6] Finding optimal parameters...")
    opt_params = find_optimal_params()
    print(f"  Found {len(opt_params)} parameter combinations")
    if opt_params:
        print("\n  Top 5 Best Parameters:")
        for p in opt_params[:5]:
            print(f"    RSI {p['rsi_min']}-{p['rsi_max']}, Hold {p['hold_min']}-{p['hold_max']}d, TP={p['tp_pct']}%, SL={p['sl_pct']}%")
            print(f"      WinRate={p['win_rate']:.1f}%, AvgReturn={p['avg_return']:.2f}%, N={p['sample_size']}")
    
    # Unified signals
    print("\n[7] Generating unified signals...")
    signals = get_unified_signals()
    print(f"  Generated {len(signals)} signals")
    
    print("\n  Top Signals:")
    for s in signals[:10]:
        print(f"  {s['symbol']:<10} {s['signal']:<12} RSI={s['rsi_14']:.1f} WR={s.get('win_rate', 0):.1f}% Conf={s['confidence']}")
    
    print("\n" + "=" * 70)
