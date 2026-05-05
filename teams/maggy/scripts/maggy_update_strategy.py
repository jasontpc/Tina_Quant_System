# -*- coding: utf-8 -*-
"""Update Maggy Optimized Strategy - v2.0"""
import sys, json
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

RESULTS = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\maggy\reports\deep_optimization.json'
CONFIG = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\maggy\maggy_config.json'

def update_strategy():
    with open(RESULTS, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    best_params = data.get('best_params', [])
    top_results = data.get('top_results', [])
    
    # Best overall
    best = best_params[0]
    
    print('╔════════════════════════════════════════╗')
    print('║   Maggy 策略優化更新 — v2.0         ║')
    print('╚════════════════════════════════════════╝')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
    
    print('=== 🏆 最佳參數（深度優化後）===\n')
    print(f'  進場 RSI:     < {best["entry_rsi"]}')
    print(f'  出場 RSI:     > {best["exit_rsi"]}')
    print(f'  最大持倉:     {best["max_hold"]} 天')
    print(f'  平均勝率:     {best["avg_win_rate"]:.1f}%')
    print(f'  平均報酬:     {best["avg_return"]:.1f}%')
    print(f'  平均交易數:   {best["avg_trades"]:.1f} 筆/股票')
    print(f'  適用股票:     {best["stocks_tested"]}檔')
    
    # Per-stock best params
    print('\n\n=== 各股票最佳參數（TOP 20）===\n')
    print(f'{"股票":<8} {"進RSI":>6} {"出RSI":>6} {"持倉":>5} {"交易":>5} {"勝率":>7} {"總報酬":>9}')
    print('-' * 55)
    
    stock_best = {}
    for r in top_results:
        sym = r['symbol']
        if sym not in stock_best or r['total_return'] > stock_best[sym]['total_return']:
            stock_best[sym] = r
    
    for sym in sorted(stock_best.keys(), key=lambda x: stock_best[x]['total_return'], reverse=True)[:20]:
        r = stock_best[sym]
        print(f'{sym:<8} {r["entry_rsi"]:>6} {r["exit_rsi"]:>6} {r["max_hold"]:>5} {r["trades"]:>5} {r["win_rate"]:>6.1f}% {r["total_return"]:>8.1f}%')
    
    # Save config
    config = {
        'version': '2.0',
        'team': 'Maggy',
        'description': 'RSI均值回歸策略 v2.0（深度優化版）',
        'optimized_params': {
            'entry_rsi': best['entry_rsi'],
            'exit_rsi': best['exit_rsi'],
            'max_hold_days': best['max_hold'],
            'macd_confirm': False,
            'sma_filter': False,
            'atr_min': 0,
        },
        'performance': {
            'avg_win_rate': round(best['avg_win_rate'], 1),
            'avg_return': round(best['avg_return'], 1),
            'avg_trades_per_stock': round(best['avg_trades'], 1),
            'stocks_tested': best['stocks_tested'],
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
    
    with open(CONFIG, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print(f'\n\n✅ 策略已更新: {CONFIG}')
    
    # Strategy comparison
    print('\n\n=== 策略升級比較 ===')
    print(f'{"版本":<10} {"進RSI":>8} {"出RSI":>8} {"持倉":>6} {"勝率":>8} {"報酬":>8}')
    print('-' * 50)
    print(f'v1.0 (前)   {"<35":>8} {">55":>8} {"20天":>6} {"99.1%":>8} {"+81.8%":>8}')
    print(f'v2.0 (新)   {"<"+str(best["entry_rsi"]):>8} {">"+str(best["exit_rsi"]):>8} {str(best["max_hold"])+"天":>6} {str(best["avg_win_rate"])+"%":>8} {"+"+str(best["avg_return"])+"%":>8}')
    
    improvement = best['avg_return'] - 81.8
    print(f'\n📈 報酬提升: {improvement:+.1f}%（{81.8:.1f}% → {best["avg_return"]:.1f}%）')

if __name__ == '__main__':
    update_strategy()