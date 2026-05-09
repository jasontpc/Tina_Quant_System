# -*- coding: utf-8 -*-
"""Maggy AI/Tech Backtester & Strategy Optimizer"""
import sys, sqlite3, json
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
DB = f'{DATA_DIR}\\maggy_ai_tech.db'
OUTPUT = f'{DATA_DIR}\\maggy_ai_results.json'

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

def backtest_strategies():
    print('╔══════════════════════════════════════════════════════╗')
    print('║     Maggy AI/Tech 策略回測優化                 ║')
    print('╚══════════════════════════════════════════════════════╝')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
    
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    # Get all symbols
    cur.execute('SELECT symbol, name, sector FROM stock_summary ORDER BY symbol')
    stocks = cur.fetchall()
    print(f'AI/Tech 股票: {len(stocks)}檔\n')
    
    # Strategy parameters to test
    strategies = [
        # RSI Mean Reversion (Core)
        {'name': 'RSI_Rev_Low', 'entry_rsi': 30, 'exit_rsi': 55, 'max_hold': 15, 'atr_mult': 0},
        {'name': 'RSI_Rev_Mid', 'entry_rsi': 35, 'exit_rsi': 60, 'max_hold': 20, 'atr_mult': 0},
        {'name': 'RSI_Rev_High', 'entry_rsi': 40, 'exit_rsi': 65, 'max_hold': 25, 'atr_mult': 0},
        # Aggressive RSI
        {'name': 'RSI_Aggressive', 'entry_rsi': 25, 'exit_rsi': 50, 'max_hold': 10, 'atr_mult': 0},
        {'name': 'RSI_Breakout', 'entry_rsi': 35, 'exit_rsi': 70, 'max_hold': 30, 'atr_mult': 0},
        # MACD Crossover
        {'name': 'MACD_Cross', 'macd_filter': True, 'entry_rsi': 45, 'exit_rsi': 55, 'max_hold': 15},
        # BB Breakout
        {'name': 'BB_Break', 'bb_filter': True, 'entry_rsi': 40, 'exit_rsi': 60, 'max_hold': 20},
    ]
    
    all_results = []
    
    for sym, name, sector in stocks:
        cur.execute('SELECT date, close, rsi_14, macd_hist, bb_lower, atr_14 FROM daily_ohlcv WHERE symbol=? ORDER BY date LIMIT 500', (sym,))
        rows = cur.fetchall()
        
        if len(rows) < 100:
            continue
        
        dates = [r[0] for r in rows]
        closes = [r[1] for r in rows]
        
        for strat in strategies:
            strat_name = strat['name']
            entry_rsi = strat.get('entry_rsi', 35)
            exit_rsi = strat.get('exit_rsi', 60)
            max_hold = strat.get('max_hold', 20)
            macd_filter = strat.get('macd_filter', False)
            bb_filter = strat.get('bb_filter', False)
            
            position = None
            trades = []
            
            for i in range(14, len(rows)):
                rsi = rows[i][2]
                macd = rows[i][3]
                bb_l = rows[i][4]
                close = rows[i][1]
                
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
                            'symbol': sym, 'name': name, 'sector': sector,
                            'strategy': strat_name,
                            'entry_date': position['date'],
                            'exit_date': dates[i],
                            'return_pct': ret,
                            'holding_days': held,
                            'entry_rsi': position['entry_rsi'],
                            'exit_rsi': rsi,
                        })
                        position = None
                
                # Entry
                elif rsi < entry_rsi:
                    # MACD filter
                    if macd_filter and (macd is None or macd < 0):
                        continue
                    
                    # BB filter
                    if bb_filter and (bb_l is None or close > bb_l):
                        continue
                    
                    position = {'date': dates[i], 'price': close, 'idx': i, 'entry_rsi': rsi}
            
            # Analyze trades
            if len(trades) >= 3:
                wins = [t for t in trades if t['return_pct'] > 0]
                losses = [t for t in trades if t['return_pct'] <= 0]
                total_ret = sum(t['return_pct'] for t in trades)
                
                all_results.append({
                    'symbol': sym,
                    'name': name,
                    'sector': sector,
                    'strategy': strat_name,
                    'trades': len(trades),
                    'win_rate': len(wins) / len(trades) * 100 if trades else 0,
                    'total_return': total_ret,
                    'avg_return': total_ret / len(trades) if trades else 0,
                    'best_trade': max(t['return_pct'] for t in trades),
                    'worst_trade': min(t['return_pct'] for t in trades),
                })
    
    # Sort by total return
    all_results.sort(key=lambda x: x['total_return'], reverse=True)
    
    print(f'=== TOP 30 最佳策略組合 ===\n')
    print(f'{"股票":<8} {"名稱":<14} {"策略":<16} {"交易":>5} {"勝率":>7} {"總報酬":>9}')
    print('-' * 65)
    for r in all_results[:30]:
        print(f'{r["symbol"]:<8} {r["name"][:14]:<14} {r["strategy"]:<16} {r["trades"]:>5} {r["win_rate"]:>6.1f}% {r["total_return"]:>+8.1f}%')
    
    # Best by sector
    print(f'\n\n=== 類別最佳策略 ===')
    sectors = {}
    for r in all_results:
        sec = r['sector']
        if sec not in sectors:
            sectors[sec] = []
        sectors[sec].append(r)
    
    for sec, results in sorted(sectors.items(), key=lambda x: max(r['total_return'] for r in x[1]), reverse=True):
        best = max(results, key=lambda x: x['total_return'])
        print(f'{sec}: {best["symbol"]} ({best["strategy"]}) {best["total_return"]:+.1f}%')
    
    # Best strategy overall
    print(f'\n\n=== 🏆 最佳策略 ===')
    best_overall = all_results[0]
    print(f'股票: {best_overall["symbol"]}')
    print(f'名稱: {best_overall["name"]}')
    print(f'策略: {best_overall["strategy"]}')
    print(f'交易: {best_overall["trades"]}筆')
    print(f'勝率: {best_overall["win_rate"]:.1f}%')
    print(f'總報酬: {best_overall["total_return"]:+.1f}%')
    print(f'最佳: {best_overall["best_trade"]:+.1f}%')
    print(f'最差: {best_overall["worst_trade"]:+.1f}%')
    
    # Strategy comparison
    print(f'\n\n=== 策略表現比較 ===')
    strat_perf = {}
    for r in all_results:
        s = r['strategy']
        if s not in strat_perf:
            strat_perf[s] = []
        strat_perf[s].append(r['total_return'])
    
    print(f'{"策略":<18} {"平均報酬":>10} {"股票數":>8} {"最佳":>10}')
    print('-' * 50)
    for s, rets in sorted(strat_perf.items(), key=lambda x: sum(x[1])/len(x[1]), reverse=True):
        avg = sum(rets) / len(rets)
        best = max(rets)
        print(f'{s:<18} {avg:>+9.1f}% {len(rets):>8} {best:>+9.1f}%')
    
    # Save results
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    conn.close()
    print(f'\n\n✅ 結果已儲存: {OUTPUT}')
    
    return all_results

if __name__ == '__main__':
    backtest_strategies()