# -*- coding: utf-8 -*-
"""Sherry ETF Simulated Trading Database"""
import sys, sqlite3, json, yfinance
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
DB = f'{DATA_DIR}\\sherry_sim_trades.db'

def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50
    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(diff if diff > 0 else 0)
        losses.append(abs(diff) if diff < 0 else 0)
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    rs = avg_gain / avg_loss if avg_loss > 0 else 100
    return 100 - (100 / (1 + rs))

def build_sim_trades_db():
    """Build simulated trading database for Sherry"""
    print('╔══════════════════════════════════════════════════════╗')
    print('║     Sherry ETF 模擬交易資料庫建置                ║')
    print('╚══════════════════════════════════════════════════════╝')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
    
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    # Open positions
    cur.execute('''CREATE TABLE IF NOT EXISTS open_positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        entry_date TEXT NOT NULL,
        entry_price REAL NOT NULL,
        shares REAL DEFAULT 0,
        amount REAL DEFAULT 0,
        entry_rsi REAL,
        strategy TEXT DEFAULT 'DCA',
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(symbol, entry_date)
    )''')
    
    # Closed positions
    cur.execute('''CREATE TABLE IF NOT EXISTS closed_positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        entry_date TEXT NOT NULL,
        entry_price REAL NOT NULL,
        exit_date TEXT,
        exit_price REAL,
        shares REAL DEFAULT 0,
        amount REAL DEFAULT 0,
        entry_rsi REAL,
        exit_rsi REAL,
        holding_days INTEGER DEFAULT 0,
        return_pct REAL DEFAULT 0,
        return_amount REAL DEFAULT 0,
        exit_reason TEXT,
        strategy TEXT DEFAULT 'DCA',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Trade log
    cur.execute('''CREATE TABLE IF NOT EXISTS trade_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        action TEXT NOT NULL,
        date TEXT NOT NULL,
        price REAL NOT NULL,
        shares REAL DEFAULT 0,
        amount REAL DEFAULT 0,
        rsi_14 REAL,
        zone TEXT,
        reason TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Portfolio summary
    cur.execute('''CREATE TABLE IF NOT EXISTS portfolio_summary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        total_value REAL DEFAULT 0,
        total_invested REAL DEFAULT 0,
        total_return REAL DEFAULT 0,
        return_pct REAL DEFAULT 0,
        open_positions INTEGER DEFAULT 0,
        closed_positions INTEGER DEFAULT 0,
        winning_trades INTEGER DEFAULT 0,
        losing_trades INTEGER DEFAULT 0,
        win_rate REAL DEFAULT 0,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(date)
    )''')
    
    # Performance metrics
    cur.execute('''CREATE TABLE IF NOT EXISTS performance (
        symbol TEXT PRIMARY KEY,
        total_trades INTEGER DEFAULT 0,
        winning_trades INTEGER DEFAULT 0,
        losing_trades INTEGER DEFAULT 0,
        win_rate REAL DEFAULT 0,
        avg_return REAL DEFAULT 0,
        total_return REAL DEFAULT 0,
        best_trade REAL DEFAULT 0,
        worst_trade REAL DEFAULT 0,
        avg_holding_days REAL DEFAULT 0,
        last_trade_date TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    
    # Simulate historical trades for all ETFs
    etfs = ['SPY', 'QQQ', 'VTI', 'IVW', 'IWM', 'XLK', 'XLF', 'XLV', 'XLE', 'XLY',
            'XLP', 'XLI', 'XLB', 'XLU', 'XLRE', 'VGT', 'VHT', 'VYM', 'VNQ', 'SCHD',
            'BND', 'AGG', 'TLT', 'HYG', 'LQD', 'VEU', 'VXUS', 'EFA', 'EEM',
            'SSO', 'QLD', 'TQQQ', 'SPXL', 'GLD', 'SLV', 'USO']
    
    print(f'ETF數量: {len(etfs)}\n')
    
    ENTRY_RSI = 35
    EXIT_RSI = 65
    MAX_HOLD = 20
    
    total_trades = 0
    
    for sym in etfs:
        print(f'處理 {sym}...', end=' ', flush=True)
        
        try:
            t = yfinance.Ticker(sym)
            hist = t.history(period='5y')
            
            if len(hist) < 200:
                print(f'不足 {len(hist)}筆')
                continue
            
            closes = hist['Close'].tolist()
            dates = hist.index.strftime('%Y-%m-%d').tolist()
            
            position = None
            trades = []
            
            for i in range(60, len(closes)):
                rsi = calc_rsi(closes[:i+1], 14)
                close = closes[i]
                date = dates[i]
                
                if position:
                    held = i - position['idx']
                    
                    # Exit conditions
                    exit_reason = None
                    if rsi > EXIT_RSI:
                        exit_reason = 'RSI_OVERBought'
                    elif held >= MAX_HOLD:
                        exit_reason = 'MAX_HOLD'
                    
                    if exit_reason:
                        ret_pct = (close - position['price']) / position['price'] * 100
                        ret_amt = position['shares'] * (close - position['price'])
                        holding_days = held
                        
                        trades.append({
                            'symbol': sym,
                            'entry_date': position['date'],
                            'entry_price': position['price'],
                            'exit_date': date,
                            'exit_price': close,
                            'shares': position['shares'],
                            'amount': position['amount'],
                            'entry_rsi': position['entry_rsi'],
                            'exit_rsi': rsi,
                            'holding_days': holding_days,
                            'return_pct': ret_pct,
                            'return_amount': ret_amt,
                            'exit_reason': exit_reason,
                        })
                        
                        # Save closed position
                        cur.execute('''INSERT INTO closed_positions 
                            (symbol, entry_date, entry_price, exit_date, exit_price, shares, amount,
                             entry_rsi, exit_rsi, holding_days, return_pct, return_amount, exit_reason)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                            (sym, position['date'], position['price'], date, close,
                             position['shares'], position['amount'], position['entry_rsi'],
                             rsi, holding_days, ret_pct, ret_amt, exit_reason))
                        
                        position = None
                
                # Entry: RSI < ENTRY_RSI
                elif rsi < ENTRY_RSI:
                    shares = 1000 / close  # $1000 per trade
                    amount = shares * close
                    position = {
                        'date': date, 'price': close, 'idx': i,
                        'shares': shares, 'amount': amount, 'entry_rsi': rsi
                    }
                    
                    # Save open position
                    cur.execute('''INSERT OR REPLACE INTO open_positions 
                        (symbol, entry_date, entry_price, shares, amount, entry_rsi)
                        VALUES (?, ?, ?, ?, ?, ?)''',
                        (sym, date, close, shares, amount, rsi))
            
            # Update performance for this symbol
            if trades:
                wins = [tr for tr in trades if tr['return_pct'] > 0]
                losses = [tr for tr in trades if tr['return_pct'] <= 0]
                total_return = sum(tr['return_pct'] for tr in trades)
                best = max(tr['return_pct'] for tr in trades)
                worst = min(tr['return_pct'] for tr in trades)
                avg_hold = sum(tr['holding_days'] for tr in trades) / len(trades)
                
                cur.execute('''INSERT OR REPLACE INTO performance 
                    (symbol, total_trades, winning_trades, losing_trades, win_rate,
                     avg_return, total_return, best_trade, worst_trade, avg_holding_days, last_trade_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (sym, len(trades), len(wins), len(losses),
                     len(wins) / len(trades) * 100 if trades else 0,
                     total_return / len(trades) if trades else 0,
                     total_return, best, worst, avg_hold, trades[-1]['exit_date']))
            
            conn.commit()
            total_trades += len(trades)
            print(f'{len(trades)}筆')
        
        except Exception as e:
            print(f'ERROR: {e}')
    
    # Summary stats
    print(f'\n\n{"="*50}')
    print(f'=== Sherry 模擬交易資料庫建置完成 ===')
    print(f'{"="*50}')
    
    cur.execute('SELECT COUNT(*) FROM closed_positions')
    total = cur.fetchone()[0]
    cur.execute('SELECT COUNT(DISTINCT symbol) FROM closed_positions')
    syms = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM open_positions')
    open_pos = cur.fetchone()[0]
    
    print(f'總交易: {total}筆')
    print(f'ETF數量: {syms}檔')
    print(f'當前倉位: {open_pos}檔')
    
    # Best performers
    print(f'\n=== 最佳表現 ETF ===')
    cur.execute('''SELECT symbol, total_trades, win_rate, total_return, best_trade, worst_trade
        FROM performance WHERE total_trades >= 5 ORDER BY total_return DESC LIMIT 10''')
    print(f'{"ETF":<8} {"交易":>6} {"勝率":>8} {"總報酬":>10} {"最佳":>10} {"最差":>10}')
    print('-' * 55)
    for r in cur.fetchall():
        print(f'{r[0]:<8} {r[1]:>6} {r[2]:>7.1f}% {r[3]:>+9.1f}% {r[4]:>+9.1f}% {r[5]:>+9.1f}%')
    
    # Worst performers
    print(f'\n=== 需注意 ETF ===')
    cur.execute('''SELECT symbol, total_trades, win_rate, total_return
        FROM performance WHERE total_trades >= 3 ORDER BY total_return ASC LIMIT 5''')
    for r in cur.fetchall():
        print(f'  {r[0]}: {r[3]:+.1f}% ({r[1]}筆, WR={r[2]:.1f}%)')
    
    import os
    db_size = os.path.getsize(DB) / 1024
    print(f'\nDB Size: {db_size:.0f} KB')
    
    conn.close()

if __name__ == '__main__':
    build_sim_trades_db()