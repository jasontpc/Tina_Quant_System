# -*- coding: utf-8 -*-
"""Maggy US Stock Simulated Trading System - With Trade Logging & Profit Verification"""
import sys, sqlite3, json, yfinance
from datetime import datetime, timedelta
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
DB = f'{DATA_DIR}\\maggy_sim_trades.db'

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

def build_trade_db():
    """Build simulated trades database"""
    print('=== 建立 Maggy 模擬交易資料庫 ===\n')
    
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    # Simulated trades table
    cur.execute('''CREATE TABLE IF NOT EXISTS sim_trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        entry_date TEXT NOT NULL,
        entry_price REAL NOT NULL,
        exit_date TEXT,
        exit_price REAL,
        quantity INTEGER DEFAULT 100,
        side TEXT DEFAULT 'LONG',
        entry_rsi REAL,
        exit_rsi REAL,
        holding_days INTEGER,
        return_pct REAL,
        return_amount REAL,
        exit_reason TEXT,
        status TEXT DEFAULT 'OPEN',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Trade history summary
    cur.execute('''CREATE TABLE IF NOT EXISTS trade_summary (
        symbol TEXT PRIMARY KEY,
        total_trades INTEGER DEFAULT 0,
        winning_trades INTEGER DEFAULT 0,
        losing_trades INTEGER DEFAULT 0,
        win_rate REAL DEFAULT 0,
        avg_return REAL DEFAULT 0,
        total_return REAL DEFAULT 0,
        avg_holding_days REAL DEFAULT 0,
        best_trade REAL DEFAULT 0,
        worst_trade REAL DEFAULT 0,
        last_updated TEXT
    )''')
    
    # Performance metrics
    cur.execute('''CREATE TABLE IF NOT EXISTS performance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT UNIQUE,
        portfolio_value REAL DEFAULT 100000,
        daily_return REAL DEFAULT 0,
        open_positions INTEGER DEFAULT 0,
        closed_positions INTEGER DEFAULT 0,
        total_pnl REAL DEFAULT 0,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    print(f'資料庫: {DB}')
    conn.close()
    return DB

def run_simulated_trades():
    """Run simulated trades based on RSI strategy"""
    print('╔══════════════════════════════════════════════════════╗')
    print('║     Maggy 模擬真實交易系統 — 獲利驗證             ║')
    print('╚══════════════════════════════════════════════════════╝')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
    
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    # Get current candidates (RSI < 35)
    us_db = f'{DATA_DIR}\\us_history.db'
    conn2 = sqlite3.connect(us_db)
    cur2 = conn2.cursor()
    cur2.execute("SELECT symbol, name, current_price, current_rsi FROM stock_summary WHERE current_rsi < 40 ORDER BY current_rsi ASC")
    candidates = cur2.fetchall()
    conn2.close()
    
    print(f'當前低檔候選: {len(candidates)}檔')
    for r in candidates[:5]:
        print(f'  {r[0]} {r[1]}: RSI={r[2]:.1f} price={r[3]}')
    
    # Strategy params
    ENTRY_RSI = 35
    EXIT_RSI = 65
    MAX_HOLD = 20
    POSITION_SIZE = 10000  # $10,000 per trade
    
    print(f'\n策略參數:')
    print(f'  進場 RSI: < {ENTRY_RSI}')
    print(f'  出場 RSI: > {EXIT_RSI}')
    print(f'  最大持倉: {MAX_HOLD}天')
    print(f'  每筆金額: ${POSITION_SIZE:,}')
    
    # Check for open positions
    cur.execute("SELECT COUNT(*) FROM sim_trades WHERE status='OPEN'")
    open_count = cur.fetchone()[0]
    print(f'\n當前倉位: {open_count}檔')
    
    if open_count > 0:
        cur.execute("SELECT symbol, entry_price, entry_date, entry_rsi FROM sim_trades WHERE status='OPEN'")
        open_trades = cur.fetchall()
        print('\n倉位明細:')
        for t in open_trades:
            sym, entry_px, entry_dt, entry_rsi = t
            # Get current price
            try:
                t_obj = yfinance.Ticker(sym)
                hist = t_obj.history(period='5d')
                curr_px = hist['Close'].iloc[-1]
                curr_rsi = calc_rsi(hist['Close'].tolist())
                pnl = (curr_px - entry_px) / entry_px * 100
                print(f'  {sym}: 進場${entry_px:.0f} @ {entry_dt} RSI={entry_rsi:.1f} → 現在${curr_px:.0f} RSI={curr_rsi:.1f} PnL={pnl:+.2f}%')
            except:
                print(f'  {sym}: 進場${entry_px:.0f} @ {entry_dt} RSI={entry_rsi:.1f}')
    
    # Generate trade ideas (RSI < 35)
    print('\n=== 模擬進場建議 ===')
    new_trades = []
    for r in candidates:
        sym, name, price, rsi = r
        if rsi < ENTRY_RSI:
            shares = int(POSITION_SIZE / price)
            new_trades.append({
                'symbol': sym,
                'name': name,
                'entry_price': price,
                'entry_rsi': rsi,
                'shares': shares,
                'value': shares * price,
            })
    
    if new_trades:
        print(f'\n🟢 建議進場（RSI < {ENTRY_RSI}）:')
        for t in new_trades[:5]:
            print(f'  {t["symbol"]} {t["name"]}: ${t["entry_price"]:.0f} x {t["shares"]}股 = ${t["value"]:,}')
    else:
        print(f'\n無符合條件進場（需 RSI < {ENTRY_RSI}）')
    
    # Recent closed trades
    print('\n=== 最近平倉記錄 ===')
    cur.execute("SELECT symbol, entry_date, entry_price, exit_date, exit_price, return_pct, exit_reason FROM sim_trades WHERE status='CLOSED' ORDER BY exit_date DESC LIMIT 10")
    closed = cur.fetchall()
    if closed:
        for t in closed:
            sym, entry_dt, entry_px, exit_dt, exit_px, ret, reason = t
            icon = '✅' if ret > 0 else '❌'
            print(f'  {icon} {sym}: ${entry_px:.0f}→${exit_px:.0f} {ret:+.2f}% ({reason}) {entry_dt}~{exit_dt}')
    else:
        print('  無平倉記錄')
    
    # Overall performance
    print('\n=== 總體績效 ===')
    cur.execute("SELECT COUNT(*), SUM(CASE WHEN return_pct > 0 THEN 1 ELSE 0 END), AVG(return_pct), SUM(return_pct * quantity * entry_price / 100) FROM sim_trades WHERE status='CLOSED'")
    stats = cur.fetchone()
    if stats[0] and stats[0] > 0:
        total, wins, avg_ret, total_pnl = stats
        win_rate = wins / total * 100 if total > 0 else 0
        print(f'  總交易: {total}筆')
        print(f'  勝率: {win_rate:.1f}%')
        print(f'  平均報酬: {avg_ret:+.2f}%' if avg_ret else '  平均報酬: N/A')
        print(f'  總獲利: ${total_pnl:,.0f}' if total_pnl else '  總獲利: $0')
    else:
        print('  尚無交易數據')
    
    conn.close()
    return new_trades

def add_sim_trade(symbol, entry_price, entry_rsi, quantity=100):
    """Add a simulated trade"""
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    cur.execute('''INSERT INTO sim_trades 
        (symbol, entry_date, entry_price, quantity, entry_rsi, status)
        VALUES (?, ?, ?, ?, ?, 'OPEN')''',
        (symbol, today, entry_price, quantity, entry_rsi))
    
    conn.commit()
    conn.close()
    print(f'✅ 新增模擬倉位: {symbol} @ ${entry_price:.0f} RSI={entry_rsi:.1f}')

def close_trade(symbol, exit_price, exit_rsi, reason):
    """Close a simulated trade"""
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    cur.execute("SELECT id, entry_date, entry_price, quantity FROM sim_trades WHERE symbol=? AND status='OPEN' ORDER BY entry_date DESC LIMIT 1", (symbol,))
    row = cur.fetchone()
    
    if row:
        trade_id, entry_date, entry_price, qty = row
        holding_days = (datetime.now() - datetime.strptime(entry_date, '%Y-%m-%d')).days
        ret_pct = (exit_price - entry_price) / entry_price * 100
        ret_amt = qty * (exit_price - entry_price)
        
        cur.execute('''UPDATE sim_trades 
            SET status='CLOSED', exit_date=?, exit_price=?, exit_rsi=?,
            holding_days=?, return_pct=?, return_amount=?, exit_reason=?,
            updated_at=CURRENT_TIMESTAMP
            WHERE id=?''',
            (today, exit_price, exit_rsi, holding_days, ret_pct, ret_amt, reason, trade_id))
        
        conn.commit()
        print(f'✅ 平倉: {symbol} {ret_pct:+.2f}% (${ret_amt:,.0f})')
    else:
        print(f'⚠️ 無倉位: {symbol}')
    
    conn.close()

def main():
    build_trade_db()
    print()
    run_simulated_trades()

if __name__ == '__main__':
    main()