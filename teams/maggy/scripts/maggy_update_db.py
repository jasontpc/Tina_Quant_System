# -*- coding: utf-8 -*-
"""Update Maggy optimized parameters to local database"""
import sys, json, sqlite3
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

DB = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\maggy.db'
RESULTS_FILE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\maggy\reports\enhanced_results.json'
CONFIG_FILE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\maggy\maggy_config.json'

def update_optimized_params():
    print('=== 更新 Maggy 優化參數 ===\n')
    
    # Load enhanced results
    with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    best_params = data.get('best_params', [])
    top_results = data.get('top_results', [])
    
    # Best overall params (averaged across all stocks)
    best = best_params[0] if best_params else None
    print(f'最佳參數組合:')
    if best:
        print(f'  進場RSI: < {best["entry_rsi"]}')
        print(f'  出場RSI: > {best["exit_rsi"]}')
        print(f'  最大持倉: {best["max_hold"]} 天')
        print(f'  平均勝率: {best["avg_win_rate"]:.1f}%')
        print(f'  平均報酬: {best["avg_return"]:.1f}%')
        print(f'  平均交易數: {best["avg_trades"]:.1f} 筆/股票')
    
    # Best per stock
    print(f'\n各股票最佳參數:')
    stock_best = {}
    for r in top_results:
        sym = r['symbol']
        if sym not in stock_best or r['total_return'] > stock_best[sym]['total_return']:
            stock_best[sym] = r
    
    print(f'{"股票":<8} {"進RSI":>6} {"出RSI":>6} {"持倉":>5} {"交易":>5} {"勝率":>7} {"總報酬":>8}')
    print('-' * 50)
    
    for sym in sorted(stock_best.keys())[:20]:
        r = stock_best[sym]
        print(f'{sym:<8} {r["entry_rsi"]:>6} {r["exit_rsi"]:>6} {r["max_hold"]:>5} {r["trades"]:>5} {r["win_rate"]:>6.1f}% {r["total_return"]:>7.1f}%')
    
    # Save to config
    config = {
        'team': 'Maggy',
        'optimized_params': {
            'entry_rsi': best['entry_rsi'] if best else 35,
            'exit_rsi': best['exit_rsi'] if best else 55,
            'max_hold_days': best['max_hold'] if best else 20,
            'macd_confirm': False,
            'description': 'RSI均值回歸策略（優化版）',
        },
        'per_stock_params': {
            sym: {
                'entry_rsi': r['entry_rsi'],
                'exit_rsi': r['exit_rsi'],
                'max_hold': r['max_hold'],
                'trades': r['trades'],
                'win_rate': r['win_rate'],
                'total_return': r['total_return'],
            }
            for sym, r in stock_best.items()
        },
        'last_updated': datetime.now().isoformat(),
    }
    
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print(f'\n✅ 已更新: {CONFIG_FILE}')
    
    # Update database with optimized signal tracking
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    # Create optimized_signals table
    cur.execute('''CREATE TABLE IF NOT EXISTS optimized_signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT, entry_rsi INTEGER, exit_rsi INTEGER, max_hold INTEGER,
        entry_date TEXT, entry_price REAL,
        UNIQUE(symbol, entry_date)
    )''')
    
    # Get current prices and check signals
    import yfinance
    print('\n=== 當前市場信號（優化參數）===\n')
    
    entry_rsi = best['entry_rsi'] if best else 35
    exit_rsi = best['exit_rsi'] if best else 55
    
    for sym in list(stock_best.keys())[:10]:
        try:
            t = yfinance.Ticker(sym)
            info = t.fast_info
            price = info.get('lastPrice') or info.get('regularMarketPrice')
            
            hist = t.history(period='60d')
            closes = hist['Close'].tolist()
            
            gains = []
            losses = []
            for i in range(1, len(closes)):
                diff = closes[i] - closes[i-1]
                gains.append(diff if diff > 0 else 0)
                losses.append(abs(diff) if diff < 0 else 0)
            
            if len(gains) >= 14:
                avg_gain = sum(gains[-14:]) / 14
                avg_loss = sum(losses[-14:]) / 14
                rs = avg_gain / avg_loss if avg_loss > 0 else 100
                rsi = 100 - (100 / (1 + rs))
                
                if rsi < entry_rsi:
                    sig = '🟢 進場'
                elif rsi < 50:
                    sig = '🟡 觀察'
                elif rsi > exit_rsi:
                    sig = '🔴 過熱'
                else:
                    sig = '⚪ 中性'
                
                params = stock_best.get(sym, {})
                exp_ret = params.get('total_return', 0)
                
                print(f'{sym:<8} 現價={price:.0f} RSI={rsi:.1f} {sig} (預期+{exp_ret:.0f}%)')
        except:
            pass
    
    conn.close()
    
    print('\n=== 資料庫更新完成 ===')

if __name__ == '__main__':
    update_optimized_params()