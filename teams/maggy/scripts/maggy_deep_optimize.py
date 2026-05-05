# -*- coding: utf-8 -*-
"""Deep Optimization - Find Best Strategy Across All US Stocks"""
import sys, sqlite3, json, itertools
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

DB = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\us_history.db'
OUTPUT = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\maggy\reports\deep_optimization.json'

def load_data(symbol, limit=500):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('''SELECT date, close, rsi_14, rsi_7, rsi_28, macd_hist, bb_upper, bb_lower, atr_14, sma_20, sma_60
        FROM daily_ohlcv WHERE symbol=? ORDER BY date LIMIT ?''', (symbol, limit))
    rows = cur.fetchall()
    conn.close()
    return [{'date': r[0], 'close': r[1], 'rsi14': r[2], 'rsi7': r[3], 'rsi28': r[4],
             'macd_hist': r[5], 'bb_u': r[6], 'bb_l': r[7], 'atr': r[8],
             'sma20': r[9], 'sma60': r[10]} for r in reversed(rows)]

def backtest(data, params):
    entry_rsi = params['entry_rsi']
    exit_rsi = params['exit_rsi']
    max_hold = params['max_hold']
    use_macd = params.get('macd', False)
    use_sma_filter = params.get('sma_filter', False)
    atr_min = params.get('atr_min', 0)
    zone_filter = params.get('zone', 'ALL')
    
    trades = []
    position = None
    
    for i in range(14, len(data)):
        d = data[i]
        rsi = d['rsi14'] or 50
        close = d['close']
        macd = d['macd_hist'] or 0
        atr = d['atr'] or 0
        sma20 = d['sma20'] or close
        sma60 = d['sma60'] or close
        
        if position:
            held = i - position['idx']
            
            # Exit
            exit_sig = False
            if rsi > exit_rsi:
                exit_sig = True
            elif held >= max_hold:
                exit_sig = True
            
            if exit_sig:
                ret = (close - position['price']) / position['price'] * 100
                trades.append({
                    'entry': position['date'], 'exit': d['date'],
                    'ret': ret, 'hold': held,
                    'entry_rsi': position['entry_rsi'],
                    'exit_rsi': rsi,
                    'macd_confirm': position.get('macd', False),
                })
                position = None
        
        # Entry
        elif rsi < entry_rsi:
            # ATR filter
            if atr < atr_min:
                continue
            
            # MACD confirm
            macd_ok = True
            if use_macd:
                macd_ok = macd > 0
            
            # SMA filter (price above SMA20)
            sma_ok = True
            if use_sma_filter:
                sma_ok = close > sma20
            
            if macd_ok and sma_ok:
                position = {'date': d['date'], 'price': close, 'idx': i, 'entry_rsi': rsi, 'macd': macd > 0}
    
    return trades

def analyze(trades):
    if not trades:
        return None
    wins = [t for t in trades if t['ret'] > 0]
    losses = [t for t in trades if t['ret'] <= 0]
    rets = [t['ret'] for t in trades]
    avg_win = sum(w['ret'] for w in wins) / len(wins) if wins else 0
    avg_loss = abs(sum(t['ret'] for t in losses) / len(losses)) if losses else 0
    
    return {
        'trades': len(trades),
        'win_rate': len(wins) / len(trades) * 100,
        'avg_return': sum(rets) / len(rets),
        'total_return': sum(rets),
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'rr_ratio': avg_win / avg_loss if avg_loss else 0,
        'max_win': max(rets),
        'max_loss': min(rets),
    }

def main():
    print('╔══════════════════════════════════════════════════════╗')
    print('║     Maggy 深度優化系統 — 全面搜索最佳策略        ║')
    print('╚══════════════════════════════════════════════════════╝')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
    
    # Get all symbols
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('SELECT symbol FROM stock_summary ORDER BY symbol')
    symbols = [r[0] for r in cur.fetchall()]
    conn.close()
    
    print(f'股票池: {len(symbols)}檔\n')
    
    # Extended parameter grid
    param_combos = []
    
    # RSI strategies
    for er in [25, 28, 30, 32, 35, 38, 40]:
        for xr in [50, 55, 58, 60, 65]:
            for mh in [10, 15, 20, 25]:
                for macd in [False, True]:
                    for sma_f in [False, True]:
                        param_combos.append({
                            'entry_rsi': er, 'exit_rsi': xr, 'max_hold': mh,
                            'macd': macd, 'sma_filter': sma_f, 'atr_min': 0, 'zone': 'ALL'
                        })
    
    # ATR-filtered strategies
    for er in [30, 35, 40]:
        for xr in [55, 60]:
            for mh in [15, 20]:
                for atr in [50, 100, 150]:
                    param_combos.append({
                        'entry_rsi': er, 'exit_rsi': xr, 'max_hold': mh,
                        'macd': False, 'sma_filter': False, 'atr_min': atr, 'zone': 'ALL'
                    })
    
    print(f'總共 {len(param_combos)} 組參數\n')
    
    all_results = []
    
    print('=== 深度搜索中 ===')
    for sym in symbols:
        data = load_data(sym, 400)
        if len(data) < 100:
            continue
        
        for params in param_combos:
            trades = backtest(data, params)
            stats = analyze(trades)
            
            if stats and stats['trades'] >= 4:
                all_results.append({
                    'symbol': sym,
                    'entry_rsi': params['entry_rsi'],
                    'exit_rsi': params['exit_rsi'],
                    'max_hold': params['max_hold'],
                    'macd': params['macd'],
                    'sma_filter': params['sma_filter'],
                    'atr_min': params['atr_min'],
                    **stats
                })
    
    # Sort by total return
    all_results.sort(key=lambda x: x['total_return'], reverse=True)
    
    print(f'\n=== TOP 50 最佳策略 ===')
    print(f'{"股票":<8} {"進RSI":>6} {"出RSI":>6} {"持倉":>5} {"MACD":>5} {"SMA":>5} {"ATR":>5} {"交易":>5} {"勝率":>7} {"均報酬":>8} {"總報酬":>9}')
    print('-' * 85)
    
    for r in all_results[:50]:
        macd = 'Y' if r['macd'] else 'N'
        sma = 'Y' if r['sma_filter'] else 'N'
        atr = str(r['atr_min']) if r['atr_min'] else '0'
        print(f'{r["symbol"]:<8} {r["entry_rsi"]:>6} {r["exit_rsi"]:>6} {r["max_hold"]:>5} {macd:>5} {sma:>5} {atr:>5} {r["trades"]:>5} {r["win_rate"]:>6.1f}% {r["avg_return"]:>7.2f}% {r["total_return"]:>8.1f}%')
    
    # Best params across all stocks
    print('\n\n=== 最佳平均參數（跨所有股票）===')
    
    # Group by params
    param_groups = {}
    for r in all_results:
        key = (r['entry_rsi'], r['exit_rsi'], r['max_hold'], r['macd'], r['sma_filter'], r['atr_min'])
        if key not in param_groups:
            param_groups[key] = []
        param_groups[key].append(r)
    
    best_params = []
    for key, results in param_groups.items():
        avg_wr = sum(r['win_rate'] for r in results) / len(results)
        avg_ret = sum(r['total_return'] for r in results) / len(results)
        avg_trades = sum(r['trades'] for r in results) / len(results)
        best_params.append({
            'entry_rsi': key[0], 'exit_rsi': key[1], 'max_hold': key[2],
            'macd': key[3], 'sma_filter': key[4], 'atr_min': key[5],
            'stocks_tested': len(results),
            'avg_win_rate': avg_wr,
            'avg_return': avg_ret,
            'avg_trades': avg_trades,
        })
    
    best_params.sort(key=lambda x: x['avg_return'], reverse=True)
    
    print(f'{"進RSI":>6} {"出RSI":>6} {"持倉":>5} {"MACD":>5} {"SMA":>5} {"ATR":>5} {"股票數":>6} {"平均勝率":>8} {"平均報酬":>8}')
    print('-' * 65)
    for b in best_params[:15]:
        macd = 'Y' if b['macd'] else 'N'
        sma = 'Y' if b['sma_filter'] else 'N'
        atr = str(b['atr_min']) if b['atr_min'] else '0'
        print(f'{b["entry_rsi"]:>6} {b["exit_rsi"]:>6} {b["max_hold"]:>5} {macd:>5} {sma:>5} {atr:>5} {b["stocks_tested"]:>6} {b["avg_win_rate"]:>7.1f}% {b["avg_return"]:>7.1f}%')
    
    # Best stock recommendations
    print('\n\n=== 股票最佳參數（TOP 20）===')
    print(f'{"股票":<8} {"進RSI":>6} {"出RSI":>6} {"持倉":>5} {"ATR":>5} {"交易":>5} {"勝率":>7} {"總報酬":>9}')
    print('-' * 60)
    for r in all_results[:20]:
        atr = str(r['atr_min']) if r['atr_min'] else '-'
        print(f'{r["symbol"]:<8} {r["entry_rsi"]:>6} {r["exit_rsi"]:>6} {r["max_hold"]:>5} {atr:>5} {r["trades"]:>5} {r["win_rate"]:>6.1f}% {r["total_return"]:>8.1f}%')
    
    # Save
    output = {
        'timestamp': datetime.now().isoformat(),
        'total_results': len(all_results),
        'best_params': best_params[:20],
        'top_results': all_results[:100],
    }
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f'\n✅ 深度優化結果已儲存: {OUTPUT}')
    
    # Summary
    print('\n\n=== 🏆 優化結論 ===')
    bp = best_params[0]
    print(f'最佳參數: RSI<{bp["entry_rsi"]} 進場, RSI>{bp["exit_rsi"]} 出場, 持倉{bp["max_hold"]}天')
    print(f'平均勝率: {bp["avg_win_rate"]:.1f}%')
    print(f'平均報酬: {bp["avg_return"]:.1f}%')
    print(f'適用股票: {bp["stocks_tested"]}檔')

if __name__ == '__main__':
    main()