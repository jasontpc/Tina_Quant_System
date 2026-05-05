# -*- coding: utf-8 -*-
"""Maggy Simulated Trade System - 模擬真實交易"""
import sys, sqlite3, json
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding='utf-8')

DB = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\maggy.db'
TRADE_LOG = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\maggy\reports\maggy_trades.json'
CONFIG = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\maggy\maggy_config.json'

# Best strategy from backtest
BEST_STRATEGY = 'RSI_Oversold_Aggressive'  # RSI<35 entry, RSI>60 exit, max 15 days

def load_latest_data(symbol, days=20):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('''SELECT date, close, rsi_14, sma_20, atr_14 FROM daily 
        WHERE symbol=? ORDER BY date DESC LIMIT ?''', (symbol, days))
    rows = cur.fetchall()
    conn.close()
    return [{'date': r[0], 'close': r[1], 'rsi': r[2], 'sma20': r[3], 'atr': r[4]} for r in reversed(rows)]

def get_current_price(symbol):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('SELECT close, rsi_14 FROM daily WHERE symbol=? ORDER BY date DESC LIMIT 1', (symbol,))
    row = cur.fetchone()
    conn.close()
    return {'close': row[0], 'rsi': row[1]} if row else None

def check_signals():
    """Check current signals for watchlist"""
    signals = []
    
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('SELECT DISTINCT symbol FROM daily ORDER BY symbol')
    symbols = [r[0] for r in cur.fetchall()]
    conn.close()
    
    for sym in symbols:
        data = get_current_price(sym)
        if not data:
            continue
        
        close = data['close']
        rsi = data['rsi'] or 50
        
        # RSI_Oversold_Aggressive signal
        if rsi < 35:
            signal = 'LONG_ENTRY'
            confidence = (35 - rsi) / 35 * 100
        elif rsi > 60 and rsi < 75:
            signal = 'HOLD'
        elif rsi > 75:
            signal = 'OVERBOUGHT_EXIT'
        else:
            signal = 'WATCH'
        
        signals.append({
            'symbol': sym,
            'close': close,
            'rsi': rsi,
            'signal': signal,
            'confidence': confidence if rsi < 35 else 0,
            'strategy': BEST_STRATEGY,
        })
    
    return signals

def run_simulated_trades():
    """Run simulated trades based on best strategy"""
    print('=== Maggy 模擬真實交易系統 ===\n')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
    
    # Load existing trade log or create new
    try:
        with open(TRADE_LOG, 'r', encoding='utf-8') as f:
            trade_log = json.load(f)
    except:
        trade_log = {'trades': [], 'stats': {}, 'last_updated': None}
    
    # Get current signals
    signals = check_signals()
    
    # Current positions (from previous trades still open)
    open_positions = trade_log.get('open_positions', [])
    closed_trades = trade_log.get('trades', [])
    
    print(f'現有倉位: {len(open_positions)}個')
    for pos in open_positions:
        data = get_current_price(pos['symbol'])
        if data:
            pnl = (data['close'] - pos['entry_price']) / pos['entry_price'] * 100
            print(f"  {pos['symbol']}: entry={pos['entry_price']:.0f} now={data['close']:.0f} PnL={pnl:+.1f}%")
    
    # Check for new signals
    new_signals = [s for s in signals if s['signal'] == 'LONG_ENTRY' and s['confidence'] > 50]
    overbought = [s for s in signals if s['signal'] == 'OVERBOUGHT_EXIT']
    
    print(f'\n新進場信號: {len(new_signals)}個')
    for s in new_signals[:5]:
        print(f"  {s['symbol']}: RSI={s['rsi']:.1f} confidence={s['confidence']:.0f}%")
    
    print(f'\n過熱準備出場: {len(overbought)}個')
    for s in overbought[:5]:
        print(f"  {s['symbol']}: RSI={s['rsi']:.1f}")
    
    # Update stats
    if closed_trades:
        wins = [t for t in closed_trades if t.get('return_pct', 0) > 0]
        losses = [t for t in closed_trades if t.get('return_pct', 0) <= 0]
        total_pnl = sum(t.get('return_pct', 0) for t in closed_trades)
        
        trade_log['stats'] = {
            'total_trades': len(closed_trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': len(wins) / len(closed_trades) * 100 if closed_trades else 0,
            'avg_return': total_pnl / len(closed_trades) if closed_trades else 0,
            'total_return': total_pnl,
            'last_updated': datetime.now().isoformat(),
        }
    
    trade_log['signals'] = signals
    trade_log['last_check'] = datetime.now().isoformat()
    
    # Save
    with open(TRADE_LOG, 'w', encoding='utf-8') as f:
        json.dump(trade_log, f, ensure_ascii=False, indent=2)
    
    # Summary
    stats = trade_log.get('stats', {})
    print(f'\n=== 模擬交易統計 ===')
    print(f'總交易數: {stats.get("total_trades", 0)}')
    print(f'勝率: {stats.get("win_rate", 0):.1f}%')
    print(f'均報酬: {stats.get("avg_return", 0):.2f}%')
    print(f'總報酬: {stats.get("total_return", 0):.1f}%')
    
    return trade_log

def add_trade(symbol, entry_price, entry_date, strategy):
    """Add a new simulated trade"""
    try:
        with open(TRADE_LOG, 'r', encoding='utf-8') as f:
            trade_log = json.load(f)
    except:
        trade_log = {'trades': [], 'open_positions': [], 'stats': {}}
    
    trade_log['open_positions'].append({
        'symbol': symbol,
        'entry_price': entry_price,
        'entry_date': entry_date,
        'strategy': strategy,
        'size': 100,  # shares
    })
    
    with open(TRADE_LOG, 'w', encoding='utf-8') as f:
        json.dump(trade_log, f, ensure_ascii=False, indent=2)
    
    print(f'新增模擬倉位: {symbol} @ {entry_price}')

if __name__ == '__main__':
    run_simulated_trades()