# -*- coding: utf-8 -*-
"""
Vogel v6.0 - 高頻交易策略開發
策略A: 短持倉（1-3日）BB 突破
策略B: ATR 突破動量策略
策略C: RSI 極端區域逆势
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
    """Add volatility metrics"""
    closes = [d['close'] for d in data]
    highs = [d['high'] for d in data]
    lows = [d['low'] for d in data]
    
    for i, d in enumerate(data):
        # Daily range %
        d['daily_range_pct'] = ((d['high'] - d['low']) / d['close'] * 100) if d['close'] > 0 else 0
        
        # ATR as % of price
        if d['atr'] and d['close'] > 0:
            d['atr_pct'] = d['atr'] / d['close'] * 100
        else:
            d['atr_pct'] = 0
        
        # Bollinger width (volatility indicator)
        if d['bb_upper'] and d['bb_lower'] and d['bb_middle']:
            d['bb_width'] = (d['bb_upper'] - d['bb_lower']) / d['bb_middle'] * 100 if d['bb_middle'] > 0 else 0
        else:
            d['bb_width'] = 0
        
        # Gap %
        if i > 0 and closes[i-1] > 0:
            d['gap_pct'] = (d['open'] - closes[i-1]) / closes[i-1] * 100
        else:
            d['gap_pct'] = 0
    
    return data

def backtest(data, params, name):
    """通用回測引擎"""
    trades = []
    position = None
    
    entry_rsi_max = params.get('entry_rsi_max', 55)
    entry_rsi_min = params.get('entry_rsi_min', 25)
    stop_atr = params.get('stop_atr', 2.0)
    profit_atr = params.get('profit_atr', 3.0)
    max_hold = params.get('max_hold', 10)
    atr_mult = params.get('atr_mult', 1.0)
    allow_short = params.get('allow_short', True)
    use_bb_squeeze = params.get('use_bb_squeeze', False)
    min_bb_width = params.get('min_bb_width', 5.0)
    entry_rsi_short_max = params.get('entry_rsi_short_max', 80)
    entry_rsi_short_min = params.get('entry_rsi_short_min', 50)
    
    for i, d in enumerate(data):
        if position is None:
            bb_l = d.get('bb_lower')
            bb_u = d.get('bb_upper')
            bb_w = d.get('bb_width', 0)
            rsi = d.get('rsi')
            close = d['close']
            atr = d.get('atr') or 0
            
            if bb_l is None or rsi is None or atr <= 0 or close <= 0:
                continue
            
            # BB squeeze filter
            if use_bb_squeeze and bb_w < min_bb_width:
                continue
            
            direction = None
            reason = None
            
            # Long entry: BB lower + RSI in range
            if close <= bb_l and entry_rsi_min < rsi < entry_rsi_max:
                direction = 'LONG'
                reason = f'BB_L, RSI={rsi:.0f}'
            
            # Short entry
            elif allow_short and close >= bb_u and entry_rsi_short_min < rsi < entry_rsi_short_max:
                direction = 'SHORT'
                reason = f'BB_U, RSI={rsi:.0f}'
            
            if direction:
                # Dynamic ATR multiplier for stops
                effective_atr = atr * atr_mult
                sl_dist = stop_atr * effective_atr
                tp_dist = profit_atr * effective_atr
                
                stop_loss = close - sl_dist if direction == 'LONG' else close + sl_dist
                take_profit = close + tp_dist if direction == 'LONG' else close - tp_dist
                
                position = {
                    'entry_date': d['date'],
                    'entry_price': close,
                    'direction': direction,
                    'atr': effective_atr,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'max_hold': max_hold,
                    'reason': reason,
                }
        
        else:
            ep = position['entry_price']
            if ep <= 0:
                position = None
                continue
            
            direction = position['direction']
            held = (datetime.strptime(d['date'], '%Y-%m-%d') - 
                    datetime.strptime(position['entry_date'], '%Y-%m-%d')).days
            
            # Max hold - force close
            if held >= position['max_hold']:
                exit_price = d['close']
                pnl = (exit_price - ep) / ep * 100 if direction == 'LONG' else (ep - exit_price) / ep * 100
                trades.append({
                    'entry_date': position['entry_date'], 'exit_date': d['date'],
                    'entry_price': ep, 'exit_price': exit_price,
                    'pnl_pct': pnl, 'result': 'MAX_HOLD', 'held_days': held,
                    'direction': direction, 'reason': position['reason'],
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
                    'direction': direction, 'reason': position['reason'],
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
                    'direction': direction, 'reason': position['reason'],
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
    
    # Score = total return * sqrt(R:R) * min(trades/10, 3)
    score = total * (rr ** 0.5) * min(len(trades) / 10, 3)
    
    return {
        'trades': len(trades), 'win_rate': wr,
        'avg_win': avg_win, 'avg_loss': avg_loss,
        'rr': rr, 'total': total, 'score': score,
        'tp': len([t for t in trades if t['result'] == 'TAKE_PROFIT']),
        'sl': len([t for t in trades if t['result'] == 'STOP_LOSS']),
        'mh': len([t for t in trades if t['result'] == 'MAX_HOLD']),
    }

def analyze_winners_losers(trades):
    """分析贏家 vs 輸家的差異"""
    wins = sorted([t for t in trades if t['pnl_pct'] > 0], key=lambda x: x['pnl_pct'], reverse=True)
    losses = sorted([t for t in trades if t['pnl_pct'] <= 0], key=lambda x: x['pnl_pct'])
    
    print('\n=== Top 5 Winners ===')
    for t in wins[:5]:
        print(f'  {t["entry_date"]} {t["direction"]:<5} {t["pnl_pct"]:+.2f}% held={t["held_days"]}d {t["reason"][:30]}')
    
    print('\n=== Top 5 Losers ===')
    for t in losses[:5]:
        print(f'  {t["entry_date"]} {t["direction"]:<5} {t["pnl_pct"]:+.2f}% held={t["held_days"]}d {t["reason"][:30]}')
    
    # Key differences
    if wins and losses:
        avg_win_held = sum(t['held_days'] for t in wins) / len(wins)
        avg_loss_held = sum(t['held_days'] for t in losses) / len(losses)
        win_short = len([t for t in wins if t['direction'] == 'SHORT'])
        loss_short = len([t for t in losses if t['direction'] == 'SHORT'])
        
        print(f'\n=== Pattern Analysis ===')
        print(f'Avg Win held: {avg_win_held:.1f}d | Avg Loss held: {avg_loss_held:.1f}d')
        print(f'Winners Short: {win_short}/{len(wins)} ({win_short/len(wins)*100:.0f}%) | Losers Short: {loss_short}/{len(losses)} ({loss_short/len(losses)*100:.0f}%)')
        print(f'Avg Win: {sum(t["pnl_pct"] for t in wins)/len(wins):+.2f}% | Avg Loss: {sum(t["pnl_pct"] for t in losses)/len(losses):.2f}%')

def run_strategies():
    print('=== Vogel v6.0 - 高頻交易策略 ===\n')
    
    data = load_data()
    data = add_volatility(data)
    print(f'Loaded {len(data)} days, Range: {data[0]["date"]} to {data[-1]["date"]}')
    print(f'Avg ATR%: {sum(d["atr_pct"] for d in data)/len(data):.2f}%')
    print(f'Avg BB Width: {sum(d["bb_width"] for d in data)/len(data):.2f}%')
    
    results = []
    
    # Strategy A: Short hold (1-5 days) with tight stops
    print('\n--- Strategy A: Short Hold ---')
    short_params = {
        'entry_rsi_max': 55, 'entry_rsi_min': 25,
        'entry_rsi_short_min': 45, 'entry_rsi_short_max': 80,
        'stop_atr': 1.5, 'profit_atr': 2.0,
        'max_hold': 5, 'atr_mult': 1.0,
        'allow_short': True, 'use_bb_squeeze': False,
    }
    
    for max_h in [3, 5, 7]:
        for stop_a in [1.0, 1.5, 2.0]:
            for profit_a in [1.5, 2.0, 2.5, 3.0]:
                p = short_params.copy()
                p['max_hold'] = max_h
                p['stop_atr'] = stop_a
                p['profit_atr'] = profit_a
                trades = backtest(data, p, f'ShortA_h{max_h}_sl{stop_a}_tp{profit_a}')
                s = score(trades)
                if s and s['trades'] >= 5:
                    p_copy = {k: v for k, v in p.items()}
                    p_copy['strategy'] = 'SHORT_HOLD'
                    s.update(p_copy)
                    results.append(s)
    
    # Strategy B: ATR Momentum (dynamic entry based on volatility)
    print('--- Strategy B: ATR Momentum ---')
    for atr_m in [0.5, 0.75, 1.0]:
        for stop_a in [1.5, 2.0, 2.5]:
            for profit_a in [2.0, 2.5, 3.0, 3.5]:
                for max_h in [5, 10, 15]:
                    p = {
                        'entry_rsi_max': 55, 'entry_rsi_min': 25,
                        'entry_rsi_short_min': 45, 'entry_rsi_short_max': 80,
                        'stop_atr': stop_a, 'profit_atr': profit_a,
                        'max_hold': max_h, 'atr_mult': atr_m,
                        'allow_short': True, 'use_bb_squeeze': False,
                    }
                    trades = backtest(data, p, 'ATR_MOM')
                    s = score(trades)
                    if s and s['trades'] >= 5:
                        p_copy = {k: v for k, v in p.items()}
                        p_copy['strategy'] = 'ATR_MOM'
                        s.update(p_copy)
                        results.append(s)
    
    # Strategy C: BB Squeeze breakout (low volatility -> high volatility transition)
    print('--- Strategy C: BB Squeeze ---')
    for min_bbw in [3.0, 4.0, 5.0, 6.0]:
        for stop_a in [1.5, 2.0, 2.5]:
            for profit_a in [2.0, 3.0]:
                for max_h in [5, 10]:
                    p = {
                        'entry_rsi_max': 55, 'entry_rsi_min': 25,
                        'entry_rsi_short_min': 45, 'entry_rsi_short_max': 80,
                        'stop_atr': stop_a, 'profit_atr': profit_a,
                        'max_hold': max_h, 'atr_mult': 1.0,
                        'allow_short': True, 'use_bb_squeeze': True,
                        'min_bb_width': min_bbw,
                    }
                    trades = backtest(data, p, 'BB_SQUEEZE')
                    s = score(trades)
                    if s and s['trades'] >= 5:
                        p_copy = {k: v for k, v in p.items()}
                        p_copy['strategy'] = 'BB_SQUEEZE'
                        s.update(p_copy)
                        results.append(s)
    
    # Sort by score
    results.sort(key=lambda x: x['score'], reverse=True)
    
    print(f'\n=== Top 20 All Strategies ===')
    print(f'{"#":<3} {"Strategy":<12} {"Trades":<7} {"WR%":<6} {"AvgWin":<7} {"R:R":<5} {"Total%":<7} {"Score":<7} {"Stop":<5} {"Profit":<6} {"MaxHold":<7}')
    print('-' * 90)
    
    for i, r in enumerate(results[:20]):
        print(f'{i+1:<3} {r["strategy"]:<12} {r["trades"]:<7} {r["win_rate"]:<6.1f} '
              f'{r["avg_win"]:<7.2f} {r["rr"]:<5.2f} {r["total"]:<7.1f} {r["score"]:<7.1f} '
              f'{r.get("stop_atr","-"):<5} {r.get("profit_atr","-"):<6} {r.get("max_hold","-"):<7}')
    
    # Best
    best = results[0]
    print(f'\n=== BEST: {best["strategy"]} ===')
    print(f'Trades: {best["trades"]} | WR: {best["win_rate"]:.1f}%')
    print(f'Avg Win: +{best["avg_win"]:.2f}% | Avg Loss: {best["avg_loss"]:.2f}%')
    print(f'R:R: {best["rr"]:.2f}x | Total: {best["total"]:+.1f}%')
    print(f'Score: {best["score"]:.1f}')
    
    # Run best params
    best_params = {k: v for k, v in best.items() if k not in ['trades','win_rate','avg_win','avg_loss','rr','total','score','tp','sl','mh']}
    best_trades = backtest(data, best_params, 'BEST')
    
    print(f'\n=== Best Trades ===')
    print(f'{"Entry Date":<12} {"Dir":<5} {"Entry":>8} {"Exit":>8} {"P&L%":>7} {"Result":<10} {"Days":>4}')
    for t in sorted(best_trades, key=lambda x: x['entry_date']):
        print(f'{t["entry_date"]:<12} {t["direction"]:<5} {t["entry_price"]:>8.0f} {t["exit_price"]:>8.0f} {t["pnl_pct"]:>+7.2f}% {t["result"]:<10} {t["held_days"]:>4}')
    
    analyze_winners_losers(best_trades)
    
    # Save
    out = os.path.join(VOGEL_DIR, 'v6_all_strategies.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f'\nSaved: {out} ({len(results)} strategies)')
    
    return best, best_trades, results

def main():
    best, trades, results = run_strategies()
    print('\n=== Vogel v6.0 Done ===')

if __name__ == '__main__':
    main()