# -*- coding: utf-8 -*-
"""Build Optimal Per-Stock Strategy - Maggy v3.0"""
import sys, json
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

RESULTS = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\maggy\reports\deep_optimization.json'
CONFIG = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\maggy\maggy_config.json'

def build_optimal():
    with open(RESULTS, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    top_results = data.get('top_results', [])
    
    # Get best per stock
    stock_best = {}
    for r in top_results:
        sym = r['symbol']
        if sym not in stock_best or r['total_return'] > stock_best[sym]['total_return']:
            stock_best[sym] = r
    
    # Sort by total return
    sorted_stocks = sorted(stock_best.values(), key=lambda x: x['total_return'], reverse=True)
    
    print('╔════════════════════════════════════════════════════╗')
    print('║   Maggy 最佳個股策略 — Per-Stock Optimization  ║')
    print('╚════════════════════════════════════════════════════╝')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
    
    print('=== 🏆 TOP 30 最佳個股策略 ===\n')
    print(f'{"排名":<4} {"股票":<8} {"進RSI":>6} {"出RSI":>6} {"持倉":>5} {"ATR":>5} {"交易":>5} {"勝率":>7} {"總報酬":>9}')
    print('-' * 65)
    
    for i, r in enumerate(sorted_stocks[:30], 1):
        print(f'{i:<4} {r["symbol"]:<8} {r["entry_rsi"]:>6} {r["exit_rsi"]:>6} {r["max_hold"]:>5} {"-":>5} {r["trades"]:>5} {r["win_rate"]:>6.1f}% {r["total_return"]:>8.1f}%')
    
    # Tier classification
    print('\n\n=== 📊 策略分層 ===\n')
    
    tier1 = [s for s in sorted_stocks if s['total_return'] >= 150]
    tier2 = [s for s in sorted_stocks if 100 <= s['total_return'] < 150]
    tier3 = [s for s in sorted_stocks if 50 <= s['total_return'] < 100]
    
    print(f'🔥 第一梯隊（回報 >150%）: {len(tier1)}檔')
    for s in tier1[:10]:
        print(f'   {s["symbol"]}: RSI<{s["entry_rsi"]} / RSI>{s["exit_rsi"]} / {s["max_hold"]}天 → +{s["total_return"]:.0f}%')
    
    print(f'\n💪 第二梯隊（回報 100-150%）: {len(tier2)}檔')
    for s in tier2[:10]:
        print(f'   {s["symbol"]}: RSI<{s["entry_rsi"]} / RSI>{s["exit_rsi"]} / {s["max_hold"]}天 → +{s["total_return"]:.0f}%')
    
    print(f'\n📈 第三梯隊（回報 50-100%）: {len(tier3)}檔')
    for s in tier3[:10]:
        print(f'   {s["symbol"]}: RSI<{s["entry_rsi"]} / RSI>{s["exit_rsi"]} / {s["max_hold"]}天 → +{s["total_return"]:.0f}%')
    
    # Save optimal config
    config = {
        'version': '3.0',
        'team': 'Maggy',
        'description': 'RSI均值回歸策略 v3.0（個股優化版）',
        'optimized_params': {
            'entry_rsi': 35,
            'exit_rsi': 65,
            'max_hold_days': 20,
            'macd_confirm': False,
        },
        'performance': {
            'total_stocks': len(stock_best),
            'tier1_count': len(tier1),
            'tier2_count': len(tier2),
            'tier3_count': len(tier3),
        },
        'per_stock_tiers': {
            'tier1': {s['symbol']: {'entry_rsi': s['entry_rsi'], 'exit_rsi': s['exit_rsi'], 'max_hold': s['max_hold'], 'trades': s['trades'], 'win_rate': s['win_rate'], 'return': s['total_return']} for s in tier1},
            'tier2': {s['symbol']: {'entry_rsi': s['entry_rsi'], 'exit_rsi': s['exit_rsi'], 'max_hold': s['max_hold'], 'trades': s['trades'], 'win_rate': s['win_rate'], 'return': s['total_return']} for s in tier2},
            'tier3': {s['symbol']: {'entry_rsi': s['entry_rsi'], 'exit_rsi': s['exit_rsi'], 'max_hold': s['max_hold'], 'trades': s['trades'], 'win_rate': s['win_rate'], 'return': s['total_return']} for s in tier3},
        },
        'last_updated': datetime.now().isoformat(),
    }
    
    with open(CONFIG, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print(f'\n\n✅ 策略已更新: {CONFIG}')
    print(f'\n📊 策略覆蓋: {len(stock_best)}檔股票')
    print(f'   第一梯隊: {len(tier1)}檔（回報 >150%）')
    print(f'   第二梯隊: {len(tier2)}檔（回報 100-150%）')
    print(f'   第三梯隊: {len(tier3)}檔（回報 50-100%）')

if __name__ == '__main__':
    build_optimal()