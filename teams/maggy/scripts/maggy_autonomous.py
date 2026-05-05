# -*- coding: utf-8 -*-
"""Maggy Autonomous Development - 自主學習美股策略"""
import sys, sqlite3, json, random
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

DB = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\maggy.db'
STRATS = ['RSI_Rev', 'MA_Cross', 'BB_Break', 'MACD_Cross', 'Multi_Factor']

def load_data(symbol, days=500):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('SELECT date, close, rsi_14, sma_20, sma_60, bb_upper, bb_middle, bb_lower, atr_14 FROM daily WHERE symbol=? ORDER BY date DESC LIMIT ?', (symbol, days))
    rows = cur.fetchall()
    conn.close()
    return [{'date': r[0], 'close': r[1], 'rsi': r[2], 'sma20': r[3], 'sma60': r[4], 'bb_u': r[5], 'bb_m': r[6], 'bb_l': r[7], 'atr': r[8]} for r in reversed(rows)]

def backtest(data, strategy, params):
    if not data:
        return {'trades': 0, 'win_rate': 0, 'avg_return': 0, 'total_return': 0}
    
    trades = []
    position = None
    
    for i in range(len(data)):
        d = data[i]
        close = d['close']
        rsi = d['rsi'] or 50
        sma20 = d['sma20'] or close
        bb_u = d['bb_u'] or close * 1.05
        bb_l = d['bb_l'] or close * 0.95
        atr = d['atr'] or close * 0.02
        
        if position:
            held = i - position['idx']
            exit_sig = False
            
            if strategy == 'RSI_Rev':
                if rsi > params.get('rsi_exit', 55):
                    exit_sig = True
                if held >= params.get('max_hold', 20):
                    exit_sig = True
            
            elif strategy == 'MA_Cross':
                if close < sma20:
                    exit_sig = True
            
            elif strategy == 'BB_Break':
                if close < bb_l:
                    exit_sig = True
            
            if exit_sig:
                ret = (close - position['price']) / position['price'] * 100
                trades.append({'entry': position['date'], 'exit': d['date'], 'ret': ret, 'dir': position['dir']})
                position = None
        
        # Entry signals
        if not position:
            if strategy == 'RSI_Rev':
                if rsi < params.get('rsi_entry', 30):
                    position = {'date': d['date'], 'price': close, 'idx': i, 'dir': 'LONG'}
            
            elif strategy == 'MA_Cross':
                if close > sma20:
                    position = {'date': d['date'], 'price': close, 'idx': i, 'dir': 'LONG'}
            
            elif strategy == 'BB_Break':
                if close > bb_u:
                    position = {'date': d['date'], 'price': close, 'idx': i, 'dir': 'LONG'}
        
        if len(trades) >= 100:
            break
    
    if not trades:
        return {'trades': 0, 'win_rate': 0, 'avg_return': 0, 'total_return': 0}
    
    wins = [t for t in trades if t['ret'] > 0]
    return {
        'trades': len(trades),
        'win_rate': len(wins) / len(trades) * 100,
        'avg_return': sum(t['ret'] for t in trades) / len(trades),
        'total_return': sum(t['ret'] for t in trades),
        'wins': len(wins),
        'losses': len(trades) - len(wins),
    }

def mutate_params(params, strategy):
    """Mutate parameters for evolution"""
    new = dict(params)
    if strategy == 'RSI_Rev':
        new['rsi_entry'] = max(20, min(40, params.get('rsi_entry', 30) + random.choice([-5, -3, 3, 5])))
        new['rsi_exit'] = max(45, min(65, params.get('rsi_exit', 55) + random.choice([-5, -3, 3, 5])))
        new['max_hold'] = max(5, min(30, params.get('max_hold', 20) + random.choice([-3, -2, 2, 3])))
    return new

def main():
    print('=== Maggy 自主學習系統 v1.0 ===\n')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
    
    # Check DB
    import os
    if not os.path.exists(DB):
        print('資料庫不存在，先執行 build_maggy_db.py')
        return
    
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('SELECT COUNT(DISTINCT symbol) FROM daily')
    sym_count = cur.fetchone()[0]
    conn.close()
    
    if sym_count == 0:
        print('資料庫為空，先執行 build_maggy_db.py')
        return
    
    print(f'資料庫: {sym_count} 檔股票\n')
    
    # Test symbols
    test_symbols = ['SPY', 'QQQ', 'NVDA', 'AAPL']
    
    # Base params per strategy
    base_params = {
        'RSI_Rev': {'rsi_entry': 30, 'rsi_exit': 55, 'max_hold': 20},
        'MA_Cross': {},
        'BB_Break': {},
    }
    
    results = []
    
    for sym in test_symbols:
        data = load_data(sym, 300)
        if len(data) < 100:
            continue
        
        print(f'{sym}: {len(data)}筆資料', end=' ')
        
        for strat in STRATS:
            params = base_params.get(strat, {})
            result = backtest(data, strat, params)
            
            if result['trades'] >= 5:
                results.append({
                    'symbol': sym,
                    'strategy': strat,
                    'trades': result['trades'],
                    'win_rate': result['win_rate'],
                    'avg_return': result['avg_return'],
                    'total_return': result['total_return'],
                    'params': params,
                })
        
        print(f'✓')
    
    # Show best
    if results:
        print('\n=== 回測結果 ===')
        results.sort(key=lambda x: x['total_return'], reverse=True)
        
        print(f'{"策略":<15} {"股票":<6} {"交易數":>6} {"勝率":>8} {"均報酬":>8} {"總報酬":>8}')
        print('-' * 55)
        
        for r in results[:15]:
            print(f'{r["strategy"]:<15} {r["symbol"]:<6} {r["trades"]:>6} {r["win_rate"]:>7.1f}% {r["avg_return"]:>7.2f}% {r["total_return"]:>7.1f}%')
        
        # Best
        best = results[0]
        print(f'\n🏆 最佳策略: {best["strategy"]} on {best["symbol"]}')
        print(f'   交易數: {best["trades"]} | 勝率: {best["win_rate"]:.1f}% | 均報酬: {best["avg_return"]:.2f}%')
    
    # Save results
    output = {
        'timestamp': datetime.now().isoformat(),
        'results': results,
        'db_status': {'symbols': sym_count},
    }
    
    with open(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\maggy\reports\autonomous_results.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print('\n完成!')

if __name__ == '__main__':
    main()