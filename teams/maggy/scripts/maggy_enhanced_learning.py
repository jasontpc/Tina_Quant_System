# -*- coding: utf-8 -*-
"""Maggy Advanced Learning System - Increase Trades & Profits"""
import sys, sqlite3, json, random, itertools
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

DB = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\maggy.db'
OUTPUT = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\maggy\reports\enhanced_results.json'

def load_data(symbol, limit=500):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('''SELECT date, close, rsi_14, sma_20, sma_60, bb_upper, bb_middle, bb_lower, atr_14, macd_line, macd_signal, macd_hist
        FROM daily WHERE symbol=? ORDER BY date LIMIT ?''', (symbol, limit))
    rows = cur.fetchall()
    conn.close()
    return [{'date': r[0], 'close': r[1], 'rsi': r[2], 'sma20': r[3], 'sma60': r[4], 
             'bb_u': r[5], 'bb_m': r[6], 'bb_l': r[7], 'atr': r[8],
             'macd': r[9], 'macd_sig': r[10], 'macd_hist': r[11]} for r in reversed(rows)]

def backtest_rsi_params(data, entry_rsi, exit_rsi, max_hold, use_macd_confirm=False):
    """Backtest with specific RSI parameters"""
    trades = []
    position = None
    
    for i in range(14, len(data)):
        d = data[i]
        rsi = d['rsi'] or 50
        close = d['close']
        macd_hist = d['macd_hist'] or 0
        
        if position:
            held = i - position['idx']
            
            # Exit conditions
            exit_sig = False
            exit_reason = ''
            
            if rsi > exit_rsi:
                exit_sig = True
                exit_reason = f'RSI>{exit_rsi}'
            elif held >= max_hold:
                exit_sig = True
                exit_reason = f'max_hold={max_hold}'
            
            if exit_sig:
                ret = (close - position['price']) / position['price'] * 100
                trades.append({
                    'entry': position['date'],
                    'exit': d['date'],
                    'ret': ret,
                    'hold': held,
                    'exit_reason': exit_reason,
                    'entry_rsi': position['entry_rsi'],
                    'exit_rsi': rsi,
                })
                position = None
        
        # Entry with optional MACD confirmation
        elif rsi < entry_rsi:
            macd_ok = True
            if use_macd_confirm:
                macd_ok = macd_hist > 0  # MACD histogram positive = bullish
            
            if macd_ok:
                position = {'date': d['date'], 'price': close, 'idx': i, 'entry_rsi': rsi}
    
    return trades

def analyze_trades(trades):
    if not trades:
        return None
    wins = [t for t in trades if t['ret'] > 0]
    losses = [t for t in trades if t['ret'] <= 0]
    rets = [t['ret'] for t in trades]
    avg_win = sum(w['ret'] for w in wins) / len(wins) if wins else 0
    avg_loss = sum(t['ret'] for t in losses) / len(losses) if losses else 0
    return {
        'trades': len(trades),
        'wins': len(wins), 'losses': len(losses),
        'win_rate': len(wins) / len(trades) * 100,
        'avg_return': sum(rets) / len(rets),
        'avg_win': avg_win, 'avg_loss': avg_loss,
        'total_return': sum(rets),
        'max_win': max(rets), 'max_loss': min(rets),
        'rr_ratio': abs(avg_win / avg_loss) if avg_loss else 0,
    }

def main():
    print('╔══════════════════════════════════════════════════════╗')
    print('║     Maggy 自主學習系統 — 提升勝率與交易數           ║')
    print('╚══════════════════════════════════════════════════════╝')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
    
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('SELECT DISTINCT symbol FROM daily ORDER BY symbol')
    symbols = [r[0] for r in cur.fetchall()]
    conn.close()
    
    print(f'股票: {len(symbols)}檔\n')
    
    # Parameter grid for RSI strategy
    entry_rsies = [25, 28, 30, 32, 35, 38]
    exit_rsies = [50, 55, 58, 60, 65]
    max_holds = [10, 15, 20, 25]
    macd_options = [False, True]
    
    # Extended parameter grid (simpler for speed)
    param_combos = [
        {'entry_rsi': 30, 'exit_rsi': 55, 'max_hold': 20, 'macd': False},
        {'entry_rsi': 35, 'exit_rsi': 60, 'max_hold': 15, 'macd': False},
        {'entry_rsi': 32, 'exit_rsi': 58, 'max_hold': 18, 'macd': False},
        {'entry_rsi': 28, 'exit_rsi': 50, 'max_hold': 25, 'macd': False},
        {'entry_rsi': 35, 'exit_rsi': 55, 'max_hold': 20, 'macd': False},
        {'entry_rsi': 30, 'exit_rsi': 50, 'max_hold': 15, 'macd': True},
        {'entry_rsi': 25, 'exit_rsi': 55, 'max_hold': 20, 'macd': False},
        {'entry_rsi': 35, 'exit_rsi': 65, 'max_hold': 10, 'macd': False},
        {'entry_rsi': 32, 'exit_rsi': 55, 'max_hold': 12, 'macd': False},
        {'entry_rsi': 28, 'exit_rsi': 55, 'max_hold': 18, 'macd': True},
    ]
    
    all_results = []
    
    print('=== 參數優化中 ===')
    for sym in symbols:
        data = load_data(sym, 400)
        if len(data) < 100:
            continue
        
        for params in param_combos:
            trades = backtest_rsi_params(data, params['entry_rsi'], params['exit_rsi'], params['max_hold'], params['macd'])
            stats = analyze_trades(trades)
            
            if stats and stats['trades'] >= 3:
                all_results.append({
                    'symbol': sym,
                    'entry_rsi': params['entry_rsi'],
                    'exit_rsi': params['exit_rsi'],
                    'max_hold': params['max_hold'],
                    'macd_confirm': params['macd'],
                    **stats
                })
    
    # Sort by total return
    all_results.sort(key=lambda x: x['total_return'], reverse=True)
    
    print(f'\n=== TOP 30 最佳參數組合 ===')
    print(f'{"股票":<6} {"進RSI":>6} {"出RSI":>6} {"持倉":>5} {"MACD":>5} {"交易":>5} {"勝率":>7} {"均報酬":>8} {"總報酬":>8} {"R:R":>6}')
    print('-' * 75)
    
    for r in all_results[:30]:
        macd = 'Y' if r['macd_confirm'] else 'N'
        print(f'{r["symbol"]:<6} {r["entry_rsi"]:>6} {r["exit_rsi"]:>6} {r["max_hold"]:>5} {macd:>5} {r["trades"]:>5} {r["win_rate"]:>6.1f}% {r["avg_return"]:>7.2f}% {r["total_return"]:>7.1f}% {r["rr_ratio"]:>5.2f}')
    
    # Best params summary
    print('\n\n=== 最佳參數發現 ===')
    
    # Group by entry_rsi
    entry_groups = {}
    for r in all_results:
        key = (r['entry_rsi'], r['exit_rsi'], r['max_hold'], r['macd_confirm'])
        if key not in entry_groups:
            entry_groups[key] = []
        entry_groups[key].append(r)
    
    best_combos = []
    for key, results in entry_groups.items():
        avg_wr = sum(r['win_rate'] for r in results) / len(results)
        avg_ret = sum(r['total_return'] for r in results) / len(results)
        avg_trades = sum(r['trades'] for r in results) / len(results)
        best_combos.append({
            'entry_rsi': key[0], 'exit_rsi': key[1], 'max_hold': key[2], 'macd': key[3],
            'stocks_tested': len(results),
            'avg_win_rate': avg_wr,
            'avg_return': avg_ret,
            'avg_trades': avg_trades,
        })
    
    best_combos.sort(key=lambda x: x['avg_return'], reverse=True)
    
    print(f'{"進RSI":>6} {"出RSI":>6} {"持倉":>5} {"MACD":>5} {"股票數":>6} {"平均勝率":>8} {"平均報酬":>8} {"均交易":>6}')
    print('-' * 55)
    for b in best_combos[:10]:
        macd = 'Y' if b['macd'] else 'N'
        print(f'{b["entry_rsi"]:>6} {b["exit_rsi"]:>6} {b["max_hold"]:>5} {macd:>5} {b["stocks_tested"]:>6} {b["avg_win_rate"]:>7.1f}% {b["avg_return"]:>7.1f}% {b["avg_trades"]:>6.1f}')
    
    # Best overall
    best = all_results[0]
    print(f'\n🏆 全系統最佳: {best["symbol"]}')
    print(f'   參數: RSI<{best["entry_rsi"]} 進場, RSI>{best["exit_rsi"]} 出場, 最多{best["max_hold"]}天')
    print(f'   交易數: {best["trades"]} | 勝率: {best["win_rate"]:.1f}% | 總報酬: {best["total_return"]:.1f}%')
    
    # Save enhanced results
    output = {
        'timestamp': datetime.now().isoformat(),
        'total_results': len(all_results),
        'best_params': best_combos[:10],
        'top_results': all_results[:50],
    }
    
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f'\n✅ 結果已儲存: {OUTPUT}')
    
    return output

if __name__ == '__main__':
    main()