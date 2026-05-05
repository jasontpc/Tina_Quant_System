# -*- coding: utf-8 -*-
"""
Vogel v8.0 - 實戰參數固化 + 交易模擬器
固定最優參數，生成實際交易信號
"""
import sys, sqlite3, os, json
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
VOGEL_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\vogel'

def load_data():
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'vogel.db'))
    cur = conn.cursor()
    cur.execute('''
        SELECT date, open, high, low, close, volume, bb_upper, bb_middle, bb_lower, rsi, atr
        FROM futures_daily WHERE futures_id="TX" ORDER BY date ASC
    ''')
    rows = cur.fetchall()
    conn.close()
    return [{
        'date': r[0], 'open': r[1], 'high': r[2], 'low': r[3],
        'close': r[4], 'volume': r[5],
        'bb_upper': r[6], 'bb_middle': r[7], 'bb_lower': r[8],
        'rsi': r[9], 'atr': r[10]
    } for r in rows]

def calc_ema(prices, period):
    if len(prices) < period: return None
    ema = sum(prices[:period]) / period
    mult = 2 / (period + 1)
    for p in prices[period:]:
        ema = (p - ema) * mult + ema
    return ema

def add_indicators(data):
    closes = [d['close'] for d in data]
    for i, d in enumerate(data):
        d['atr_pct'] = d['atr'] / d['close'] * 100 if d['atr'] and d['close'] > 0 else 0
        d['bb_width'] = ((d['bb_upper'] - d['bb_lower']) / d['bb_middle'] * 100) if d['bb_upper'] and d['bb_lower'] and d['bb_middle'] and d['bb_middle'] > 0 else 0
        d['gap_pct'] = (d['open'] - closes[i-1]) / closes[i-1] * 100 if i > 0 and closes[i-1] > 0 else 0
        if i >= 26:
            ef = calc_ema(closes[:i+1], 12)
            es = calc_ema(closes[:i+1], 26)
            if ef and es:
                d['macd'] = round(ef - es, 2)
                macd_vals = [calc_ema(closes[max(0,j-26):j+1], 12) - calc_ema(closes[max(0,j-26):j+1], 26)
                            for j in range(max(0,i-8), i+1) if j >= 26]
                if macd_vals:
                    d['macd_signal'] = round(sum(macd_vals)/len(macd_vals), 2)
                    d['macd_hist'] = round(d['macd'] - d['macd_signal'], 2)
        else:
            d['macd'] = d['macd_signal'] = d['macd_hist'] = None
    return data

def run_final_strategy(data, params):
    """使用最終固化參數運行策略"""
    trades = []
    position = None
    
    for i, d in enumerate(data):
        if position is None:
            bb_l = d.get('bb_lower')
            bb_u = d.get('bb_upper')
            rsi = d.get('rsi')
            close = d['close']
            atr = d.get('atr') or 0
            macd_hist = d.get('macd_hist')
            
            if bb_l is None or rsi is None or atr <= 0 or close <= 0:
                continue
            
            direction = None
            
            # SHORT: BB Upper touch + RSI 45-80
            if close >= bb_u and 45 < rsi < 80:
                direction = 'SHORT'
                stop_loss = close + 1.5 * atr
                take_profit = close - 3.0 * atr
                max_hold = 5
            
            # LONG: BB Lower touch + RSI < 40
            elif close <= bb_l and rsi < 40:
                direction = 'LONG'
                stop_loss = close - 2.0 * atr
                take_profit = close + 3.0 * atr
                max_hold = 10
            
            # MACD confirmation (optional second filter)
            if direction == 'SHORT' and macd_hist is not None and macd_hist < 0:
                pass  # Already have SHORT signal with MACD confirming
            elif direction == 'LONG' and macd_hist is not None and macd_hist > 0:
                pass  # MACD bullish confirmation
            
            if direction:
                position = {
                    'entry_date': d['date'],
                    'entry_price': close,
                    'direction': direction,
                    'atr': atr,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'max_hold': max_hold,
                }
        
        else:
            ep = position['entry_price']
            if ep <= 0:
                position = None
                continue
            
            direction = position['direction']
            held = (datetime.strptime(d['date'], '%Y-%m-%d') - 
                    datetime.strptime(position['entry_date'], '%Y-%m-%d')).days
            
            # Force close on max hold
            if held >= position['max_hold']:
                exit_price = d['close']
                pnl = (exit_price - ep) / ep * 100 if direction == 'LONG' else (ep - exit_price) / ep * 100
                trades.append({
                    'entry_date': position['entry_date'], 'exit_date': d['date'],
                    'entry_price': ep, 'exit_price': exit_price,
                    'pnl_pct': pnl, 'result': 'MAX_HOLD', 'held_days': held,
                    'direction': direction,
                    'entry_rsi': position.get('entry_rsi'),
                    'atr_at_entry': position['atr'],
                })
                position = None
                continue
            
            # Stop loss
            sl_hit = (direction == 'LONG' and d['close'] <= position['stop_loss']) or \
                     (direction == 'SHORT' and d['close'] >= position['stop_loss'])
            if sl_hit:
                exit_price = position['stop_loss']
                pnl = (exit_price - ep) / ep * 100 if direction == 'LONG' else (ep - exit_price) / ep * 100
                trades.append({
                    'entry_date': position['entry_date'], 'exit_date': d['date'],
                    'entry_price': ep, 'exit_price': exit_price,
                    'pnl_pct': pnl, 'result': 'STOP_LOSS', 'held_days': held,
                    'direction': direction,
                    'atr_at_entry': position['atr'],
                })
                position = None
                continue
            
            # Take profit
            tp_hit = (direction == 'LONG' and d['close'] >= position['take_profit']) or \
                     (direction == 'SHORT' and d['close'] <= position['take_profit'])
            if tp_hit:
                exit_price = position['take_profit']
                pnl = (exit_price - ep) / ep * 100 if direction == 'LONG' else (ep - exit_price) / ep * 100
                trades.append({
                    'entry_date': position['entry_date'], 'exit_date': d['date'],
                    'entry_price': ep, 'exit_price': exit_price,
                    'pnl_pct': pnl, 'result': 'TAKE_PROFIT', 'held_days': held,
                    'direction': direction,
                    'atr_at_entry': position['atr'],
                })
                position = None
    
    return trades

def generate_trade_signals(data):
    """產生當前交易信號"""
    if not data: return None
    
    latest = data[-1]
    prev = data[-2] if len(data) > 1 else None
    
    signals = {}
    
    # Current market info
    signals['market'] = {
        'date': latest['date'],
        'close': latest['close'],
        'rsi': round(latest['rsi'], 1) if latest['rsi'] else None,
        'atr': round(latest['atr'], 0) if latest['atr'] else None,
        'bb_upper': round(latest['bb_upper'], 0) if latest['bb_upper'] else None,
        'bb_middle': round(latest['bb_middle'], 0) if latest['bb_middle'] else None,
        'bb_lower': round(latest['bb_lower'], 0) if latest['bb_lower'] else None,
        'macd_hist': round(latest.get('macd_hist', 0), 2) if latest.get('macd_hist') else None,
    }
    
    # SHORT signal conditions
    bb_u = latest.get('bb_upper')
    rsi = latest.get('rsi')
    close = latest['close']
    atr = latest.get('atr') or 0
    
    if bb_u and rsi and close >= bb_u and 45 < rsi < 80:
        signals['short_signal'] = {
            'direction': 'SHORT',
            'entry_price': close,
            'stop_loss': round(close + 1.5 * atr, 0),
            'take_profit': round(close - 3.0 * atr, 0),
            'risk_pts': round(1.5 * atr, 0),
            'reward_pts': round(3.0 * atr, 0),
            'risk_pct': round(1.5 * atr / close * 100, 2),
            'max_hold_days': 5,
            'entry_rsi': round(rsi, 1),
            'bb_upper': round(bb_u, 0),
            'reason': f'BB Upper touch, RSI={rsi:.0f}',
        }
    else:
        signals['short_signal'] = None
    
    # LONG signal conditions
    bb_l = latest.get('bb_lower')
    if bb_l and rsi and close <= bb_l and rsi < 40:
        signals['long_signal'] = {
            'direction': 'LONG',
            'entry_price': close,
            'stop_loss': round(close - 2.0 * atr, 0),
            'take_profit': round(close + 3.0 * atr, 0),
            'risk_pts': round(2.0 * atr, 0),
            'reward_pts': round(3.0 * atr, 0),
            'risk_pct': round(2.0 * atr / close * 100, 2),
            'max_hold_days': 10,
            'entry_rsi': round(rsi, 1),
            'bb_lower': round(bb_l, 0),
            'reason': f'BB Lower touch, RSI={rsi:.0f}',
        }
    else:
        signals['long_signal'] = None
    
    return signals

def analyze_equity_curve(trades):
    """分析資金曲線"""
    if not trades: return
    
    # Build equity curve
    equity = 100000  # Starting capital
    points = [equity]
    dates = []
    
    for t in sorted(trades, key=lambda x: x['entry_date']):
        pnl = t['pnl_pct'] / 100 * equity
        equity += pnl
        points.append(equity)
        dates.append(t['entry_date'])
    
    # Metrics
    peak = 100000
    max_dd = 0
    
    for p in points:
        if p > peak: peak = p
        dd = (peak - p) / peak * 100
        if dd > max_dd: max_dd = dd
    
    print(f'\n=== Equity Curve ===')
    print(f'Starting: $100,000')
    print(f'Ending: ${equity:,.0f}')
    print(f'Net Return: {equity - 100000:+,.0f} ({equity/100000*100-100:+.1f}%)')
    print(f'Max Drawdown: {max_dd:.1f}%')
    print(f'Peak: ${peak:,.0f}')
    
    return equity, max_dd

def main():
    print('=== Vogel v8.0 - Final Strategy + Trade Signals ===\n')
    
    data = load_data()
    data = add_indicators(data)
    print(f'Loaded {len(data)} days: {data[0]["date"]} to {data[-1]["date"]}')
    
    # Run final strategy
    trades = run_final_strategy(data, {})
    
    wins = [t for t in trades if t['pnl_pct'] > 0]
    losses = [t for t in trades if t['pnl_pct'] <= 0]
    wr = len(wins) / len(trades) * 100 if trades else 0
    avg_win = sum(t['pnl_pct'] for t in wins) / len(wins) if wins else 0
    avg_loss = abs(sum(t['pnl_pct'] for t in losses) / len(losses)) if losses else 0
    total = sum(t['pnl_pct'] for t in trades)
    rr = avg_win / avg_loss if avg_loss > 0 else 0
    
    tp_count = len([t for t in trades if t['result'] == 'TAKE_PROFIT'])
    sl_count = len([t for t in trades if t['result'] == 'STOP_LOSS'])
    mh_count = len([t for t in trades if t['result'] == 'MAX_HOLD'])
    
    short_trades = [t for t in trades if t['direction'] == 'SHORT']
    long_trades = [t for t in trades if t['direction'] == 'LONG']
    
    print(f'\n=== FINAL BACKTEST RESULTS ===')
    print(f'Total Trades: {len(trades)} | Period: {data[0]["date"]} to {data[-1]["date"]}')
    print(f'Win Rate: {wr:.1f}%')
    print(f'Avg Win: +{avg_win:.2f}% | Avg Loss: {avg_loss:.2f}%')
    print(f'R:R: {rr:.2f}x')
    print(f'Total Return: {total:.1f}%')
    print(f'Results: TP={tp_count}, SL={sl_count}, MH={mh_count}')
    print(f'Short: {len(short_trades)} ({len([t for t in short_trades if t["pnl_pct"]>0])/len(short_trades)*100:.0f}% WR)')
    print(f'Long: {len(long_trades)} ({len([t for t in long_trades if t["pnl_pct"]>0])/len(long_trades)*100:.0f}% WR)')
    
    equity, max_dd = analyze_equity_curve(trades)
    
    print(f'\n=== ALL TRADES ===')
    print(f'{"#":<3} {"Entry Date":<12} {"Dir":<5} {"Entry":>8} {"Exit":>8} {"P&L%":>7} {"Result":<10} {"Days":>4}')
    for i, t in enumerate(sorted(trades, key=lambda x: x['entry_date']), 1):
        print(f'{i:<3} {t["entry_date"]:<12} {t["direction"]:<5} {t["entry_price"]:>8.0f} {t["exit_price"]:>8.0f} {t["pnl_pct"]:>+7.2f}% {t["result"]:<10} {t["held_days"]:>4}')
    
    # Generate current signals
    signals = generate_trade_signals(data)
    
    print(f'\n=== CURRENT TRADE SIGNALS ===')
    print(f'Market: Date={signals["market"]["date"]}, Close={signals["market"]["close"]:,.0f}')
    print(f'RSI={signals["market"]["rsi"]}, ATR={signals["market"]["atr"]}')
    print(f'BB: {signals["market"]["bb_upper"]:,.0f} / {signals["market"]["bb_middle"]:,.0f} / {signals["market"]["bb_lower"]:,.0f}')
    
    if signals['short_signal']:
        s = signals['short_signal']
        print(f'\nSHORT SIGNAL!')
        print(f'  Entry: {s["entry_price"]:,.0f}')
        print(f'  Stop Loss: {s["stop_loss"]:,.0f} (risk {s["risk_pts"]:,.0f} pts = {s["risk_pct"]}%)')
        print(f'  Take Profit: {s["take_profit"]:,.0f} (reward {s["reward_pts"]:,.0f} pts)')
        print(f'  Max Hold: {s["max_hold_days"]} days')
        print(f'  Reason: {s["reason"]}')
    else:
        print(f'\nNo SHORT signal')
        print(f'  Conditions: close >= bb_upper ({signals["market"]["close"]:,.0f} >= {signals["market"]["bb_upper"]:,.0f})? {"YES" if signals["market"]["close"] >= signals["market"]["bb_upper"] else "NO"}')
        print(f'  RSI in range (45-80): {signals["market"]["rsi"]}')
    
    if signals['long_signal']:
        l = signals['long_signal']
        print(f'\nLONG SIGNAL!')
        print(f'  Entry: {l["entry_price"]:,.0f}')
        print(f'  Stop Loss: {l["stop_loss"]:,.0f} (risk {l["risk_pts"]:,.0f} pts = {l["risk_pct"]}%)')
        print(f'  Take Profit: {l["take_profit"]:,.0f} (reward {l["reward_pts"]:,.0f} pts)')
        print(f'  Max Hold: {l["max_hold_days"]} days')
        print(f'  Reason: {l["reason"]}')
    else:
        print(f'No LONG signal')
    
    # Save strategy config
    config = {
        'version': 'v8.0',
        'description': 'Vogel Final Strategy - Short Focused BB Breakout',
        'parameters': {
            'short': {
                'entry': 'BB Upper touch + RSI 45-80',
                'stop_atr': 1.5,
                'profit_atr': 3.0,
                'max_hold_days': 5,
            },
            'long': {
                'entry': 'BB Lower touch + RSI < 40',
                'stop_atr': 2.0,
                'profit_atr': 3.0,
                'max_hold_days': 10,
            },
        },
        'backtest': {
            'trades': len(trades),
            'win_rate': round(wr, 1),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'rr': round(rr, 2),
            'total_return': round(total, 1),
            'max_drawdown': round(max_dd, 1),
            'period': f'{data[0]["date"]} to {data[-1]["date"]}',
        },
        'current_signals': signals,
    }
    
    config_path = os.path.join(VOGEL_DIR, 'vogel_strategy_config.json')
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    trades_path = os.path.join(VOGEL_DIR, 'vogel_trade_log_v8.json')
    with open(trades_path, 'w', encoding='utf-8') as f:
        json.dump(trades, f, ensure_ascii=False, indent=2)
    
    print(f'\nConfig saved: {config_path}')
    print(f'Trades saved: {trades_path} ({len(trades)} trades)')
    print('\n=== Vogel v8.0 Complete ===')

if __name__ == '__main__':
    main()