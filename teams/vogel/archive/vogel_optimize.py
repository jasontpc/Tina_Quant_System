# -*- coding: utf-8 -*-
"""
Vogel v5.0 - 完整參數優化（Long + Short + Holding Limits）
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

def calc_ema(prices, period):
    if len(prices) < period: return None
    ema = sum(prices[:period]) / period
    mult = 2 / (period + 1)
    for p in prices[period:]:
        ema = (p - ema) * mult + ema
    return ema

def add_macd(data):
    closes = [d['close'] for d in data]
    for i in range(len(data)):
        if i >= 26:
            ef = calc_ema(closes[:i+1], 12)
            es = calc_ema(closes[:i+1], 26)
            if ef and es:
                data[i]['macd'] = round(ef - es, 2)
                macd_vals = [calc_ema(closes[max(0,j-26):j+1], 12) - calc_ema(closes[max(0,j-26):j+1], 26)
                            for j in range(max(0,i-8), i+1) if j >= 26]
                if macd_vals:
                    data[i]['macd_signal'] = round(sum(macd_vals)/len(macd_vals), 2)
                    data[i]['macd_hist'] = round(data[i]['macd'] - data[i]['macd_signal'], 2)
        else:
            data[i]['macd'] = data[i]['macd_signal'] = data[i]['macd_hist'] = None
    return data

def backtest_full(data, entry_rsi_max_long=55, entry_rsi_min_long=25,
                  entry_rsi_min_short=45, entry_rsi_max_short=80,
                  stop_atr=2.0, profit_atr=3.0, max_hold_days=30,
                  allow_short=True):
    """完整 BB_Break 策略（Long + Short）"""
    trades = []
    position = None
    
    for i, d in enumerate(data):
        # === ENTRY LOGIC ===
        if position is None:
            bb_l = d.get('bb_lower')
            bb_u = d.get('bb_upper')
            rsi = d.get('rsi')
            close = d['close']
            atr = d.get('atr') or 0
            
            if bb_l is None or rsi is None or atr <= 0 or close <= 0:
                continue
            
            direction = None
            
            # Long
            if close <= bb_l and entry_rsi_min_long < rsi < entry_rsi_max_long:
                direction = 'LONG'
            # Short
            elif allow_short and close >= bb_u and entry_rsi_min_short < rsi < entry_rsi_max_short:
                direction = 'SHORT'
            
            if direction:
                sl_dist = stop_atr * atr
                tp_dist = profit_atr * atr
                stop_loss = close - sl_dist if direction == 'LONG' else close + sl_dist
                take_profit = close + tp_dist if direction == 'LONG' else close - tp_dist
                
                position = {
                    'entry_date': d['date'],
                    'entry_price': close,
                    'direction': direction,
                    'atr': atr,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'max_hold': max_hold_days,
                }
        
        # === EXIT LOGIC ===
        else:
            ep = position['entry_price']
            if ep <= 0:
                position = None
                continue
            
            direction = position['direction']
            held = (datetime.strptime(d['date'], '%Y-%m-%d') - 
                    datetime.strptime(position['entry_date'], '%Y-%m-%d')).days
            
            # Check max hold
            if held >= position['max_hold']:
                if direction == 'LONG':
                    pnl = (d['close'] - ep) / ep * 100
                    exit_price = d['close']
                else:
                    pnl = (ep - d['close']) / ep * 100
                    exit_price = d['close']
                trades.append({
                    'entry_date': position['entry_date'], 'exit_date': d['date'],
                    'entry_price': ep, 'exit_price': exit_price,
                    'pnl_pct': pnl, 'result': 'MAX_HOLD', 'held_days': held,
                    'direction': direction,
                })
                position = None
                continue
            
            # Stop loss check
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
            
            # Take profit check
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

def score_params(trades):
    if not trades: return None
    wins = [t for t in trades if t['pnl_pct'] > 0]
    losses = [t for t in trades if t['pnl_pct'] <= 0]
    if not wins or not losses: return None
    
    wr = len(wins) / len(trades) * 100
    avg_win = sum(t['pnl_pct'] for t in wins) / len(wins)
    avg_loss = abs(sum(t['pnl_pct'] for t in losses) / len(losses))
    rr = avg_win / avg_loss if avg_loss > 0 else 0
    total = sum(t['pnl_pct'] for t in trades)
    score = total * (rr ** 0.5) * ((len(trades) / 10) ** 0.5)
    
    tp_count = len([t for t in trades if t['result'] == 'TAKE_PROFIT'])
    sl_count = len([t for t in trades if t['result'] == 'STOP_LOSS'])
    mh_count = len([t for t in trades if t['result'] == 'MAX_HOLD'])
    
    return {
        'trades': len(trades), 'win_rate': wr,
        'avg_win': avg_win, 'avg_loss': avg_loss,
        'rr': rr, 'total': total, 'score': score,
        'tp': tp_count, 'sl': sl_count, 'mh': mh_count,
    }

def grid_search():
    print('=== Vogel v5.0 - 完整參數優化 ===\n')
    
    data = load_data()
    data = add_macd(data)
    print(f'Loaded {len(data)} days')
    
    results = []
    
    rsi_long_values = [40, 45, 50, 55, 60, 65]
    profit_atr_values = [2.0, 2.5, 3.0, 3.5, 4.0, 5.0]
    max_hold_values = [5, 10, 15, 20, 30]
    
    total_combos = len(rsi_long_values) * len(profit_atr_values) * len(max_hold_values)
    print(f'Testing {total_combos} combinations...\n')
    
    for rsi_max in rsi_long_values:
        for profit_atr in profit_atr_values:
            for max_hold in max_hold_values:
                trades = backtest_full(data, 
                                       entry_rsi_max_long=rsi_max,
                                       entry_rsi_min_long=25,
                                       entry_rsi_min_short=40,
                                       entry_rsi_max_short=80,
                                       stop_atr=2.0,
                                       profit_atr=profit_atr,
                                       max_hold_days=max_hold,
                                       allow_short=True)
                scored = score_params(trades)
                if scored and scored['trades'] >= 5:
                    scored['rsi_max_long'] = rsi_max
                    scored['profit_atr'] = profit_atr
                    scored['max_hold'] = max_hold
                    results.append(scored)
    
    results.sort(key=lambda x: x['score'], reverse=True)
    
    print('=== Top 15 Parameter Combinations ===')
    print(f'{"#":<3} {"RSI_L":<7} {"ProfA":<6} {"Hold":<5} {"Trades":<7} {"WR%":<6} '
          f'{"AvgWin":<8} {"R:R":<6} {"Total%":<8} {"TP":<4} {"SL":<4} {"MH":<4} {"Score":<7}')
    print('-' * 90)
    
    for i, r in enumerate(results[:15]):
        print(f'{i+1:<3} {r["rsi_max_long"]:<7} {r["profit_atr"]:<6.1f} {r["max_hold"]:<5} '
              f'{r["trades"]:<7} {r["win_rate"]:<6.1f} {r["avg_win"]:<8.2f} '
              f'{r["rr"]:<6.2f} {r["total"]:<8.1f} {r["tp"]:<4} {r["sl"]:<4} {r["mh"]:<4} {r["score"]:<7.1f}')
    
    best = results[0]
    print(f'\n=== Best Configuration ===')
    print(f'Entry RSI Max (Long): {best["rsi_max_long"]}')
    print(f'Profit ATR: {best["profit_atr"]}x')
    print(f'Max Hold Days: {best["max_hold"]}')
    print(f'Trades: {best["trades"]} | WR: {best["win_rate"]:.1f}%')
    print(f'Avg Win: +{best["avg_win"]:.2f}% | Avg Loss: {best["avg_loss"]:.2f}%')
    print(f'R:R: {best["rr"]:.2f}x | Total: {best["total"]:+.1f}%')
    print(f'Score: {best["score"]:.1f}')
    print(f'TP={best["tp"]}, SL={best["sl"]}, MH={best["mh"]}')
    
    # All best trades
    best_trades = backtest_full(data, 
                               entry_rsi_max_long=best['rsi_max_long'],
                               entry_rsi_min_long=25,
                               entry_rsi_min_short=40,
                               entry_rsi_max_short=80,
                               stop_atr=2.0,
                               profit_atr=best['profit_atr'],
                               max_hold_days=best['max_hold'],
                               allow_short=True)
    
    print(f'\n=== All Best Trades ({len(best_trades)}) ===')
    print(f'{"Entry Date":<12} {"Dir":<5} {"Entry":>8} {"Exit":>8} {"P&L%":>7} {"Result":<10} {"Days":>4}')
    for t in sorted(best_trades, key=lambda x: x['entry_date']):
        print(f'{t["entry_date"]:<12} {t["direction"]:<5} {t["entry_price"]:>8.0f} {t["exit_price"]:>8.0f} {t["pnl_pct"]:>+7.2f}% {t["result"]:<10} {t["held_days"]:>4}')
    
    # Save
    out_path = os.path.join(VOGEL_DIR, 'optimization_results_v5.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump({'best': best, 'all': results[:50]}, f, ensure_ascii=False, indent=2)
    print(f'\nSaved: {out_path}')
    
    return best, results

def main():
    best, results = grid_search()
    print('\n=== Vogel v5.0 Done ===')

if __name__ == '__main__':
    main()