# -*- coding: utf-8 -*-
"""Tina 全系統主動回測收集系統 - 擴充所有資料庫"""
import sys, sqlite3, os, yfinance, json
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'

def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(diff if diff > 0 else 0)
        losses.append(abs(diff) if diff < 0 else 0)
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    rs = avg_gain / avg_loss if avg_loss > 0 else 100
    return 100 - (100 / (1 + rs))

def init_master_db():
    """初始化主回測資料庫"""
    db = f'{DATA_DIR}\\master_backtest.db'
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    
    # 策略回測結果
    cur.execute('''CREATE TABLE IF NOT EXISTS backtest_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        system TEXT NOT NULL,
        symbol TEXT NOT NULL,
        strategy TEXT NOT NULL,
        entry_rsi REAL,
        exit_rsi REAL,
        max_hold INTEGER,
        total_trades INTEGER,
        winning_trades INTEGER,
        losing_trades INTEGER,
        win_rate REAL,
        avg_return REAL,
        total_return REAL,
        best_trade REAL,
        worst_trade REAL,
        avg_holding_days REAL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(system, symbol, strategy)
    )''')
    
    # 交易記錄歸檔
    cur.execute('''CREATE TABLE IF NOT EXISTS trade_archive (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        system TEXT NOT NULL,
        symbol TEXT NOT NULL,
        strategy TEXT,
        entry_date TEXT,
        entry_price REAL,
        exit_date TEXT,
        exit_price REAL,
        quantity INTEGER,
        return_pct REAL,
        return_amount REAL,
        holding_days INTEGER,
        entry_rsi REAL,
        exit_rsi REAL,
        exit_reason TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # 每日市場狀態
    cur.execute('''CREATE TABLE IF NOT EXISTS market_daily (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL UNIQUE,
        twii_rsi REAL,
        tx_price REAL,
        tx_rsi REAL,
        sp500_rsi REAL,
        nasdaq_rsi REAL,
        market_zone TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    return conn

def backtest_symbol(symbol, entry_rsi, exit_rsi, max_hold=20, years=3):
    """回測單一股票"""
    try:
        t = yfinance.Ticker(symbol)
        hist = t.history(period=f'{years}y')
        if len(hist) < 500:
            return None
        
        closes = hist['Close'].tolist()
        dates = hist.index.strftime('%Y-%m-%d').tolist()
        
        trades = []
        in_pos = False
        entry_px = 0
        entry_dt = ''
        entry_rsi_val = 0
        hold = 0
        
        for i in range(50, len(closes)):
            rsi = calc_rsi(closes[:i+1])
            close = closes[i]
            date = dates[i]
            
            if not in_pos:
                if rsi < entry_rsi:
                    in_pos = True
                    entry_px = close
                    entry_dt = date
                    entry_rsi_val = rsi
                    hold = 0
            else:
                hold += 1
                should_exit = False
                reason = ''
                
                if rsi > exit_rsi:
                    should_exit = True
                    reason = 'RSI_EXIT'
                elif hold >= max_hold:
                    should_exit = True
                    reason = 'MAX_HOLD'
                elif close < entry_px * 0.92:
                    should_exit = True
                    reason = 'STOP_LOSS'
                
                if should_exit:
                    ret = (close - entry_px) / entry_px * 100
                    trades.append({
                        'entry_date': entry_dt,
                        'entry_price': entry_px,
                        'exit_date': date,
                        'exit_price': close,
                        'holding_days': hold,
                        'return_pct': ret,
                        'entry_rsi': entry_rsi_val,
                        'exit_rsi': rsi,
                        'exit_reason': reason
                    })
                    in_pos = False
        
        return trades
    except:
        return None

def run_maggy_backtest(conn):
    """Maggy AI/科技股回測"""
    print('\n=== Maggy AI/科技股回測 ===')
    
    cur = conn.cursor()
    STOCKS = [
        'NVDA', 'AMD', 'INTC', 'MSFT', 'AMZN', 'GOOGL', 'META', 'TSLA',
        'CRM', 'NOW', 'PLTR', 'SNOW', 'NET', 'CRWD',
        'TSM', 'ASML', 'AMAT', 'MU', 'LRCX', 'KLAC',
        'COIN', 'VGT', 'SMH', 'SOXX',
        'HON', 'IR',
    ]
    
    STRATS = [
        {'name': 'RSI_Rev_Low', 'entry': 30, 'exit': 55, 'hold': 15},
        {'name': 'RSI_Rev_Mid', 'entry': 35, 'exit': 60, 'hold': 20},
        {'name': 'RSI_Rev_High', 'entry': 40, 'exit': 65, 'hold': 25},
        {'name': 'RSI_Aggressive', 'entry': 25, 'exit': 50, 'hold': 10},
    ]
    
    total_trades = 0
    
    for strat in STRATS:
        name = strat['name']
        print(f'  {name}...', end='', flush=True)
        
        strat_trades = 0
        for sym in STOCKS:
            trades = backtest_symbol(sym, strat['entry'], strat['exit'], strat['hold'])
            if trades:
                strat_trades += len(trades)
                total_trades += len(trades)
                
                # Save to archive
                for t in trades:
                    cur.execute('''INSERT INTO trade_archive 
                        (system, symbol, strategy, entry_date, entry_price, exit_date, exit_price,
                        return_pct, holding_days, entry_rsi, exit_rsi, exit_reason)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        ('Maggy', sym, name, t['entry_date'], t['entry_price'], t['exit_date'], t['exit_price'],
                         t['return_pct'], t['holding_days'], t['entry_rsi'], t['exit_rsi'], t['exit_reason']))
        
        conn.commit()
        print(f' {strat_trades}筆')
    
    print(f'  總交易: {total_trades}筆')
    return total_trades

def run_sherry_backtest(conn):
    """Sherry ETF DCA回測"""
    print('\n=== Sherry ETF DCA回測 ===')
    
    cur = conn.cursor()
    ETFS = [
        'SPY', 'QQQ', 'IWM', 'DIA', 'VTI',
        'VGT', 'VFH', 'XLK', 'XLV', 'XLE', 'XLF', 'XLY',
        'SMH', 'SOXX', 'ARKK',
        'TQQQ', 'SPXL',
        'GLD', 'SLV', 'TLT', 'BND',
    ]
    
    STRATS = [
        {'name': 'DCA_Monthly', 'entry': 35, 'exit': 65, 'hold': 30},
        {'name': 'DCA_Weekly', 'entry': 30, 'exit': 60, 'hold': 15},
    ]
    
    total_trades = 0
    
    for strat in STRATS:
        name = strat['name']
        print(f'  {name}...', end='', flush=True)
        
        strat_trades = 0
        for sym in ETFS:
            trades = backtest_symbol(sym, strat['entry'], strat['exit'], strat['hold'])
            if trades:
                strat_trades += len(trades)
                total_trades += len(trades)
                
                for t in trades:
                    cur.execute('''INSERT INTO trade_archive 
                        (system, symbol, strategy, entry_date, entry_price, exit_date, exit_price,
                        return_pct, holding_days, entry_rsi, exit_rsi, exit_reason)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        ('Sherry', sym, name, t['entry_date'], t['entry_price'], t['exit_date'], t['exit_price'],
                         t['return_pct'], t['holding_days'], t['entry_rsi'], t['exit_rsi'], t['exit_reason']))
        
        conn.commit()
        print(f' {strat_trades}筆')
    
    print(f'  總交易: {total_trades}筆')
    return total_trades

def run_vogel_backtest(conn):
    """Vogel 台指期回測"""
    print('\n=== Vogel 台指期回測 ===')
    
    cur = conn.cursor()
    
    # TX 回測（使用概略數據）
    STRATS = [
        {'name': 'BB_Short', 'entry_rsi': 65, 'exit_rsi': 45, 'hold': 5},
        {'name': 'BB_Long', 'entry_rsi': 35, 'exit_rsi': 55, 'hold': 10},
        {'name': 'RSI_Rev', 'entry_rsi': 40, 'exit_rsi': 60, 'hold': 15},
    ]
    
    print('  台指期策略')
    total_trades = 0
    
    for strat in STRATS:
        name = strat['name']
        print(f'  {name}...', end='', flush=True)
        
        # Use placeholder - real TX data from vogel_indicators.db
        trades = []
        
        # Save placeholder
        for t in trades:
            cur.execute('''INSERT INTO trade_archive 
                (system, symbol, strategy, entry_date, entry_price, exit_date, exit_price,
                return_pct, holding_days, entry_rsi, exit_rsi, exit_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                ('Vogel', 'TX', name, t['entry_date'], t['entry_price'], t['exit_date'], t['exit_price'],
                 t['return_pct'], t['holding_days'], t['entry_rsi'], t['exit_rsi'], t['exit_reason']))
        
        conn.commit()
        print(f' {len(trades)}筆')
    
    print('  總交易: 0筆')
    return 0

def update_market_daily(conn):
    """更新每日市場狀態"""
    print('\n=== 更新市場狀態 ===')
    
    try:
        t = yfinance.Ticker('^TWII')
        hist = h = t.history(period='1mo')
        if len(hist) > 0:
            closes = hist['Close'].tolist()
            rsi = calc_rsi(closes)
            print(f'  TWII: RSI={rsi:.1f}')
        else:
            rsi = 50
    except:
        rsi = 50
    
    try:
        t = yfinance.Ticker('^IXIC')
        hist = t.history(period='1mo')
        if len(hist) > 0:
            closes = hist['Close'].tolist()
            nasdaq_rsi = calc_rsi(closes)
            print(f'  NASDAQ: RSI={nasdaq_rsi:.1f}')
        else:
            nasdaq_rsi = 50
    except:
        nasdaq_rsi = 50
    
    try:
        t = yfinance.Ticker('^GSPC')
        hist = t.history(period='1mo')
        if len(hist) > 0:
            closes = hist['Close'].tolist()
            sp500_rsi = calc_rsi(closes)
            print(f'  S&P500: RSI={sp500_rsi:.1f}')
        else:
            sp500_rsi = 50
    except:
        sp500_rsi = 50
    
    zone = 'OVERBOUGHT' if max(rsi, nasdaq_rsi, sp500_rsi) > 70 else 'NEUTRAL' if max(rsi, nasdaq_rsi, sp500_rsi) > 40 else 'OVERSOLD'
    
    cur = conn.cursor()
    cur.execute('''INSERT OR REPLACE INTO market_daily 
        (date, twii_rsi, sp500_rsi, nasdaq_rsi, market_zone)
        VALUES (?, ?, ?, ?, ?)''',
        (datetime.now().strftime('%Y-%m-%d'), rsi, sp500_rsi, nasdaq_rsi, zone))
    conn.commit()
    print(f'  Zone: {zone}')

def main():
    print('╔══════════════════════════════════════════════════════════════╗')
    print('║     Tina 全系統主動回測收集系統                    ║')
    print('╚══════════════════════════════════════════════════════════════╝')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
    
    conn = init_master_db()
    
    # Run backtests
    maggy_trades = run_maggy_backtest(conn)
    sherry_trades = run_sherry_backtest(conn)
    vogel_trades = run_vogel_backtest(conn)
    
    # Update market status
    update_market_daily(conn)
    
    # Summary
    print('\n\n=== 回測收集完成 ===')
    print(f'Maggy:  {maggy_trades}筆')
    print(f'Sherry:  {sherry_trades}筆')
    print(f'Vogel:  {vogel_trades}筆')
    print(f'總計:    {maggy_trades + sherry_trades + vogel_trades}筆')
    
    # DB size
    db_size = os.path.getsize(f'{DATA_DIR}\\master_backtest.db') / 1024
    print(f'\n資料庫: master_backtest.db ({db_size:.0f}KB)')
    
    conn.close()

if __name__ == '__main__':
    main()