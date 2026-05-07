# -*- coding: utf-8 -*-
"""
Vogel v7.0 - 短線 Short-Specific 策略
針對短線交易優化（1-5天持仓）
"""
import sys, sqlite3, os, json
from datetime import datetime
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

def add_volatility(data):
    for i, d in enumerate(data):
        d['atr_pct'] = d['atr'] / d['close'] * 100 if d['atr'] and d['close'] > 0 else 0
        d['bb_width'] = ((d['bb_upper'] - d['bb_lower']) / d['bb_middle'] * 100) if d['bb_upper'] and d['bb_lower'] and d['bb_middle'] and d['bb_middle'] > 0 else 0
        if i > 0:
            prev_close = data[i-1]['close']
            d['gap_pct'] = (d['open'] - prev_close) / prev_close * 100 if prev_close > 0 else 0
        else:
            d['gap_pct'] = 0
    return data

def backtest(data, params):
    trades = []
    position = None
    
    # SHORT-specific params
    short_rsi_min = params.get('short_rsi_min', 50)
    short_rsi_max = params.get('short_rsi_max', 80)
    short_stop_atr = params.get('short_stop_atr', 2.0)
    short_profit_atr = params.get('short_profit_atr', 2.5)
    short_max_hold = params.get('short_max_hold', 5)
    short_slip_atr = params.get('short_slip_atr', 1.0)  # slippage buffer
    
    # LONG params (optional)
    long_rsi_min = params.get('long_rsi_min', 25)
    long_rsi_max = params.get('long_rsi_max', 40)
    long_stop_atr = params.get('long_stop_atr', 2.0)
    long_profit_atr = params.get('long_profit_atr', 3.0)
    long_max_hold = params.get('long_max_hold', 10)
    allow_long = params.get('allow_long', True)
    allow_short = params.get('allow_short', True)
    min_trades = params.get('min_trades', 5)
    
    for i, d in enumerate(data):
        if position is None:
            bb_l = d.get('bb_lower')
            bb_u = d.get('bb_upper')
            rsi = d.get('rsi')
            close = d['close']
            atr = d.get('atr') or 0
            
            if bb_l is None or rsi is None or atr <= 0 or close <= 0:
                continue
            
            direction = None
            sl_dist = tp_dist = 0
            
            # SHORT: BB upper touch + RSI in range
            if allow_short and close >= bb_u and short_rsi_min < rsi < short_rsi_max:
                direction = 'SHORT'
                sl_dist = short_stop_atr * atr + (short_slip_atr * atr)  # account for slippage
                tp_dist = short_profit_atr * atr
                stop_loss = close + sl_dist
                take_profit = close - tp_dist
                max_hold = short_max_hold
            
            # LONG: BB lower touch + RSI in range (only when RSI very oversold)
            elif allow_long and close <= bb_l and long_rsi_min < rsi < long_rsi_max:
                direction = 'LONG'
                sl_dist = long_stop_atr * atr
                tp_dist = long_profit_atr * atr
                stop_loss = close - sl_dist
                take_profit = close + tp_dist
                max_hold = long_max_hold
            
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
                })
                position = None
    
    return trades

def score(trades):
    if not trades: return None
    wins = [t for t in trades if t['pnl_pct'] > 0]
    losses = [t for t in trades if t['pnl_pct'] <= 0]
    if not wins or not losses: return None
    
    wr = len(wins) / len(trades) * 100
    avg_win = sum(t['pnl_pct'] for t in wins) / len(wins)
    avg_loss = abs(sum(t['pnl_pct'] for t in losses) / len(losses))
    rr = avg_win / avg_loss if avg_loss > 0 else 0
    total = sum(t['pnl_pct'] for t in trades)
    score_val = total * (rr ** 0.5) * min(len(trades) / 10, 3)
    
    short_trades = [t for t in trades if t['direction'] == 'SHORT']
    long_trades = [t for t in trades if t['direction'] == 'LONG']
    
    short_wr = len([t for t in short_trades if t['pnl_pct'] > 0]) / len(short_trades) * 100 if short_trades else 0
    long_wr = len([t for t in long_trades if t['pnl_pct'] > 0]) / len(long_trades) * 100 if long_trades else 0
    short_total = sum(t['pnl_pct'] for t in short_trades)
    long_total = sum(t['pnl_pct'] for t in long_trades)
    
    return {
        'trades': len(trades), 'win_rate': wr,
        'avg_win': avg_win, 'avg_loss': avg_loss,
        'rr': rr, 'total': total, 'score': score_val,
        'short_trades': len(short_trades), 'short_wr': short_wr, 'short_total': short_total,
        'long_trades': len(long_trades), 'long_wr': long_wr, 'long_total': long_total,
        'tp': len([t for t in trades if t['result'] == 'TAKE_PROFIT']),
        'sl': len([t for t in trades if t['result'] == 'STOP_LOSS']),
        'mh': len([t for t in trades if t['result'] == 'MAX_HOLD']),
    }

def optimize():
    print('=== Vogel v7.0 - 短線 Short-Specific 策略優化 ===\n')
    
    data = load_data()
    data = add_volatility(data)
    print(f'Loaded {len(data)} days')
    
    results = []
    
    # Short-specific grid
    short_rsi_min_values = [45, 50, 55]
    short_rsi_max_values = [65, 70, 75, 80]
    short_stop_atr_values = [1.5, 2.0, 2.5]
    short_profit_atr_values = [1.5, 2.0, 2.5, 3.0]
    short_max_hold_values = [3, 5, 7]
    
    print(f'Testing SHORT-specific strategies...')
    
    for rsi_min in short_rsi_min_values:
        for rsi_max in short_rsi_max_values:
            if rsi_min >= rsi_max: continue
            for stop_a in short_stop_atr_values:
                for profit_a in short_profit_atr_values:
                    for max_h in short_max_hold_values:
                        p = {
                            'short_rsi_min': rsi_min, 'short_rsi_max': rsi_max,
                            'short_stop_atr': stop_a, 'short_profit_atr': profit_a,
                            'short_max_hold': max_h,
                            'short_slip_atr': 0.5,
                            'allow_long': False, 'allow_short': True,
                            'min_trades': 5,
                        }
                        trades = backtest(data, p)
                        s = score(trades)
                        if s and s['short_trades'] >= 5:
                            s.update({k: v for k, v in p.items()})
                            results.append(s)
    
    results.sort(key=lambda x: x['score'], reverse=True)
    
    print(f'\n=== Top 20 SHORT Strategies ===')
    print(f'{"#":<3} {"RSI_Min":<8} {"RSI_Max":<8} {"StopA":<6} {"ProfA":<6} {"Hold":<5} '
          f'{"Trades":<7} {"WR%":<6} {"AvgWin":<7} {"R:R":<5} {"Total%":<7} {"Shorts":<7} {"S_WR%":<6} {"S_Tot%":<7} {"Score":<6}')
    print('-' * 110)
    
    for i, r in enumerate(results[:20]):
        print(f'{i+1:<3} {r["short_rsi_min"]:<8} {r["short_rsi_max"]:<8} {r["short_stop_atr"]:<6.1f} '
              f'{r["short_profit_atr"]:<6.1f} {r["short_max_hold"]:<5} '
              f'{r["short_trades"]:<7} {r["short_wr"]:<6.1f} {r["avg_win"]:<7.2f} '
              f'{r["rr"]:<5.2f} {r["total"]:<7.1f} {r["short_trades"]:<7} {r["short_wr"]:<6.1f} {r["short_total"]:<7.1f} '
              f'{r["score"]:<6.1f}')
    
    # Best SHORT
    best_s = results[0]
    print(f'\n=== Best SHORT Configuration ===')
    print(f'RSI Range: {best_s["short_rsi_min"]} - {best_s["short_rsi_max"]}')
    print(f'Stop ATR: {best_s["short_stop_atr"]}x | Profit ATR: {best_s["short_profit_atr"]}x')
    print(f'Max Hold: {best_s["short_max_hold"]} days')
    print(f'Short Trades: {best_s["short_trades"]} | Short WR: {best_s["short_wr"]:.1f}%')
    print(f'Total Return: {best_s["total"]:+.1f}% | Score: {best_s["score"]:.1f}')
    
    # Run best SHORT
    best_params = {k: v for k, v in best_s.items() if k in [
        'short_rsi_min', 'short_rsi_max', 'short_stop_atr', 'short_profit_atr',
        'short_max_hold', 'short_slip_atr', 'allow_long', 'allow_short'
    ]}
    short_trades = backtest(data, best_params)
    
    print(f'\n=== Short Trade Log ===')
    print(f'{"Entry Date":<12} {"Entry":>8} {"Exit":>8} {"P&L%":>7} {"Result":<10} {"Days":>4}')
    for t in sorted(short_trades, key=lambda x: x['entry_date']):
        print(f'{t["entry_date"]:<12} {t["entry_price"]:>8.0f} {t["exit_price"]:>8.0f} {t["pnl_pct"]:>+7.2f}% {t["result"]:<10} {t["held_days"]:>4}')
    
    # Combined: Short + selective Long
    print('\n--- Combined: Short + Selective Long ---')
    results2 = []
    
    for rsi_min in [40, 45, 50]:
        for rsi_max in [65, 70, 75]:
            for stop_a in [1.5, 2.0]:
                for profit_a in [2.0, 2.5, 3.0]:
                    for max_h in [3, 5, 7]:
                        p = {
                            'short_rsi_min': 50, 'short_rsi_max': 75,
                            'short_stop_atr': stop_a, 'short_profit_atr': profit_a,
                            'short_max_hold': max_h, 'short_slip_atr': 0.5,
                            'long_rsi_min': 20, 'long_rsi_max': 40,
                            'long_stop_atr': 2.0, 'long_profit_atr': 3.0,
                            'long_max_hold': 10,
                            'allow_long': True, 'allow_short': True,
                        }
                        trades = backtest(data, p)
                        s = score(trades)
                        if s and s['trades'] >= 8:
                            s.update({k: v for k, v in p.items()})
                            results2.append(s)
    
    results2.sort(key=lambda x: x['score'], reverse=True)
    
    print(f'\n=== Top 10 Combined (Short + Long) Strategies ===')
    print(f'{"#":<3} {"Trades":<7} {"WR%":<6} {"AvgWin":<7} {"R:R":<5} {"Total%":<7} '
          f'{"Shorts":<7} {"Longs":<6} {"Score":<6}')
    print('-' * 70)
    
    for i, r in enumerate(results2[:10]):
        print(f'{i+1:<3} {r["trades"]:<7} {r["win_rate"]:<6.1f} {r["avg_win"]:<7.2f} '
              f'{r["rr"]:<5.2f} {r["total"]:<7.1f} {r["short_trades"]:<7} {r["long_trades"]:<6} {r["score"]:<6.1f}')
    
    # Best combined
    best_c = results2[0] if results2 else None
    if best_c:
        print(f'\n=== Best Combined Configuration ===')
        print(f'Trades: {best_c["trades"]} | WR: {best_c["win_rate"]:.1f}%')
        print(f'Shorts: {best_c["short_trades"]} ({best_c["short_wr"]:.1f}% WR, {best_c["short_total"]:+.1f}%)')
        print(f'Longs: {best_c["long_trades"]} ({best_c["long_wr"]:.1f}% WR, {best_c["long_total"]:+.1f}%)')
        print(f'Total Return: {best_c["total"]:+.1f}% | Score: {best_c["score"]:.1f}')
        
        best_params_c = {k: v for k, v in best_c.items() if k in [
            'short_rsi_min', 'short_rsi_max', 'short_stop_atr', 'short_profit_atr',
            'short_max_hold', 'short_slip_atr', 'long_rsi_min', 'long_rsi_max',
            'long_stop_atr', 'long_profit_atr', 'long_max_hold', 'allow_long', 'allow_short'
        ]}
        c_trades = backtest(data, best_params_c)
        
        print(f'\n=== All Trades ===')
        print(f'{"Entry Date":<12} {"Dir":<5} {"Entry":>8} {"Exit":>8} {"P&L%":>7} {"Result":<10} {"Days":>4}')
        for t in sorted(c_trades, key=lambda x: x['entry_date']):
            print(f'{t["entry_date"]:<12} {t["direction"]:<5} {t["entry_price"]:>8.0f} {t["exit_price"]:>8.0f} {t["pnl_pct"]:>+7.2f}% {t["result"]:<10} {t["held_days"]:>4}')
    
    # Save
    out = os.path.join(VOGEL_DIR, 'v7_short_strategies.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump({
            'short_only': results[:30],
            'combined': results2[:30] if results2 else [],
            'best_short': best_s,
            'best_combined': best_c,
        }, f, ensure_ascii=False, indent=2)
    print(f'\nSaved: {out}')
    
    return best_s, short_trades, best_c, results2

def main():
    optimize()
    print('\n=== Vogel v7.0 Done ===')

if __name__ == '__main__':
    main()