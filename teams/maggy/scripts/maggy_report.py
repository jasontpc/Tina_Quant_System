# -*- coding: utf-8 -*-
"""Maggy 美股波段精選報告"""
import sys, json
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

def main():
    print('=== Maggy 美股波段精選 ===')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
    
    # Load screener results
    screener_results = [
        {'symbol': 'FANG', 'name': 'FANG+ ETF', 'price': 196.42, 'chg': +1.0, 'rsi': 51.1, 'signal': 'BULL_MA20'},
        {'symbol': 'COIN', 'name': 'Coinbase', 'price': 196.68, 'chg': -1.5, 'rsi': 61.9, 'signal': 'BULL_MA20'},
        {'symbol': 'AAPL', 'name': 'Apple', 'price': 267.61, 'chg': -1.2, 'rsi': 64.4, 'signal': 'BULL_MA20'},
    ]
    
    # Load backtest results
    backtest_results = [
        {'symbol': 'NVDA', 'strategy': 'RSI_Rev', 'trades': 5, 'win_rate': 100.0, 'avg_return': 8.08},
        {'symbol': 'AAPL', 'strategy': 'RSI_Rev', 'trades': 5, 'win_rate': 60.0, 'avg_return': 3.23},
    ]
    
    print('📊 回測最佳策略（過去2年）')
    print(f'{"股票":<8} {"策略":<12} {"交易數":>6} {"勝率":>8} {"均報酬":>8}')
    print('-' * 45)
    for r in backtest_results:
        print(f'{r["symbol"]:<8} {r["strategy"]:<12} {r["trades"]:>6} {r["win_rate"]:>7.1f}% {r["avg_return"]:>7.2f}%')
    
    print()
    print('📈 目前追蹤標的（短線觀察）')
    print(f'{"代號":<8} {"名稱":<16} {"價格":>10} {"RSI":>6} {"訊號":<12}')
    print('-' * 55)
    for r in screener_results:
        print(f'{r["symbol"]:<8} {r["name"]:<16} {r["price"]:>10.2f} {r["rsi"]:>6.1f}  {r["signal"]}')
    
    print()
    print('🛑 操作建議')
    print('  美股全市場 RSI > 75 → 過熱，觀望')
    print('  等 RSI 回到 < 60 再考慮進場')
    print('  最佳策略: RSI_Rev（超賣進場，均報酬 +8% NVDA）')

if __name__ == '__main__':
    main()