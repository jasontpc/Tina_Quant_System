# -*- coding: utf-8 -*-
"""Maggy Comprehensive Backtest Engine - v2.0"""
import sys, sqlite3, json
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

DB = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\maggy.db'
OUTPUT = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\maggy\reports\full_backtest.json'

STRATEGIES = {
    'RSI_Rev': {'entry_rsi': 30, 'exit_rsi': 55, 'max_hold': 20},
    'RSI_Oversold_Aggressive': {'entry_rsi': 35, 'exit_rsi': 60, 'max_hold': 15},
    'MA_Golden_Cross': {},
    'BB_Break_Long': {'atr_mult': 2},
}

def load_data(symbol, limit=500):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('''SELECT date, close, rsi_14, sma_20, sma_60, bb_upper, bb_middle, bb_lower, atr_14 
        FROM daily WHERE symbol=? ORDER BY date LIMIT ?''', (symbol, limit))
    rows = cur.fetchall()
    conn.close()
    return [{'date': r[0], 'close': r[1], 'rsi': r[2], 'sma20': r[3], 'sma60': r[4], 
             'bb_u': r[5], 'bb_m': r[6], 'bb_l': r[7], 'atr': r[8]} for r in reversed(rows)]

def backtest_rsi(data, params):
    trades = []
    position = None
    for i in range(14, len(data)):
        d = data[i]
        rsi = d['rsi'] or 50
        close = d['close']
        if position:
            held = i - position['idx']
            if rsi > params['exit_rsi'] or held >= params['max_hold']:
                ret = (close - position['price']) / position['price'] * 100
                trades.append({'entry': position['date'], 'exit': d['date'], 'ret': ret, 'hold': held})
                position = None
        elif rsi < params['entry_rsi']:
            position = {'date': d['date'], 'price': close, 'idx': i}
    return trades

def backtest_ma(data, params):
    trades = []
    position = None
    for i in range(60, len(data)):
        d = data[i]
        sma20 = d['sma20'] or d['close']
        sma60 = d['sma60'] or d['close']
        close = d['close']
        if position:
            if close < sma20:
                ret = (close - position['price']) / position['price'] * 100
                trades.append({'entry': position['date'], 'exit': d['date'], 'ret': ret, 'hold': i - position['idx']})
                position = None
        elif close > sma20 and sma20 > sma60:
            position = {'date': d['date'], 'price': close, 'idx': i}
    return trades

def backtest_bb(data, params):
    trades = []
    position = None
    for i in range(20, len(data)):
        d = data[i]
        close = d['close']
        bb_u = d['bb_u'] or close * 1.05
        atr = d['atr'] or close * 0.02
        if position:
            if close < position['stop']:
                ret = (close - position['price']) / position['price'] * 100
                trades.append({'entry': position['date'], 'exit': d['date'], 'ret': ret, 'hold': i - position['idx'], 'type': 'stop'})
                position = None
            elif close > position['target']:
                ret = (close - position['price']) / position['price'] * 100
                trades.append({'entry': position['date'], 'exit': d['date'], 'ret': ret, 'hold': i - position['idx'], 'type': 'profit'})
                position = None
        elif close > bb_u:
            atr_mult = params.get('atr_mult', 2)
            position = {'date': d['date'], 'price': close, 'idx': i, 
                       'stop': close - atr * atr_mult, 'target': close + atr * atr_mult * 2}
    return trades

def analyze_trades(trades):
    if not trades:
        return None
    wins = [t for t in trades if t['ret'] > 0]
    losses = [t for t in trades if t['ret'] < 0]
    rets = [t['ret'] for t in trades]
    avg_win = sum(w['ret'] for w in wins) / len(wins) if wins else 0
    avg_loss = sum(t['ret'] for t in losses) / len(losses) if losses else 0
    return {
        'trades': len(trades), 'wins': len(wins), 'losses': len(losses),
        'win_rate': len(wins) / len(trades) * 100,
        'avg_return': sum(rets) / len(rets),
        'avg_win': avg_win, 'avg_loss': avg_loss,
        'total_return': sum(rets),
        'max_win': max(rets), 'max_loss': min(rets),
        'rr_ratio': abs(avg_win / avg_loss) if avg_loss else 0,
    }

def main():
    print('=== Maggy 全策略回測系統 v2.0 ===\n')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
    
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('SELECT DISTINCT symbol FROM daily ORDER BY symbol')
    symbols = [r[0] for r in cur.fetchall()]
    conn.close()
    
    print(f'股票: {len(symbols)}檔\n')
    all_results = []
    
    for sym in symbols:
        data = load_data(sym, 400)
        if len(data) < 100:
            continue
        
        for strat_name, params in STRATEGIES.items():
            if strat_name.startswith('RSI'):
                trades = backtest_rsi(data, params)
            elif strat_name.startswith('MA'):
                trades = backtest_ma(data, params)
            elif strat_name.startswith('BB'):
                trades = backtest_bb(data, params)
            else:
                continue
            
            stats = analyze_trades(trades)
            if stats and stats['trades'] >= 3:
                all_results.append({'symbol': sym, 'strategy': strat_name, **stats})
    
    all_results.sort(key=lambda x: x['total_return'], reverse=True)
    
    print('=== 回測結果 TOP 20（2年歷史）===')
    print(f'{"股票":<6} {"策略":<22} {"交易":>5} {"勝率":>7} {"均報酬":>8} {"總報酬":>8} {"R:R":>6}')
    print('-' * 67)
    for r in all_results[:20]:
        print(f'{r["symbol"]:<6} {r["strategy"]:<22} {r["trades"]:>5} {r["win_rate"]:>6.1f}% {r["avg_return"]:>7.2f}% {r["total_return"]:>7.1f}% {r["rr_ratio"]:>5.2f}')
    
    print('\n=== 策略勝率 ===')
    for strat in STRATEGIES:
        strat_results = [r for r in all_results if r['strategy'] == strat]
        if strat_results:
            avg_wr = sum(r['win_rate'] for r in strat_results) / len(strat_results)
            avg_ret = sum(r['total_return'] for r in strat_results) / len(strat_results)
            best = max(strat_results, key=lambda x: x['total_return'])
            print(f'{strat}: {len(strat_results)}股票, 平均勝率{avg_wr:.1f}%, 平均總報酬{avg_ret:.1f}%')
            print(f'  Best: {best["symbol"]} WR={best["win_rate"]:.1f}% ret={best["total_return"]:.1f}%')
    
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump({'timestamp': datetime.now().isoformat(), 'total_results': len(all_results), 'results': all_results}, f, ensure_ascii=False, indent=2)
    print(f'\n✅ 結果已儲存: {OUTPUT}')

if __name__ == '__main__':
    main()