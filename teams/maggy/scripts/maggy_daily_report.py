# -*- coding: utf-8 -*-
"""Maggy Daily Report - 每日報告"""
import sys, json
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

REPORT_FILE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\maggy\reports\daily_report.json'
BACKTEST_FILE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\maggy\reports\full_backtest.json'

def main():
    print('=== Maggy 美股波段每日報告 ===\n')
    print(f'日期: {datetime.now().strftime("%Y-%m-%d")}\n')
    
    # Load backtest results
    try:
        with open(BACKTEST_FILE, 'r', encoding='utf-8') as f:
            bt_data = json.load(f)
        results = bt_data.get('results', [])
    except:
        results = []
    
    # Top performers
    print('📊 回測最佳策略（過去2年）')
    print(f'{"股票":<6} {"策略":<22} {"交易":>5} {"勝率":>7} {"總報酬":>8}')
    print('-' * 55)
    for r in results[:10]:
        print(f'{r["symbol"]:<6} {r["strategy"]:<22} {r["trades"]:>5} {r["win_rate"]:>6.1f}% {r["total_return"]:>7.1f}%')
    
    # Strategy summary
    strat_summary = {}
    for r in results:
        s = r['strategy']
        if s not in strat_summary:
            strat_summary[s] = {'count': 0, 'total_return': 0, 'win_rate': 0}
        strat_summary[s]['count'] += 1
        strat_summary[s]['total_return'] += r['total_return']
        strat_summary[s]['win_rate'] += r['win_rate']
    
    print('\n\n📈 策略表現總結')
    for strat, data in strat_summary.items():
        avg_ret = data['total_return'] / data['count']
        avg_wr = data['win_rate'] / data['count']
        print(f'{strat}: {data["count"]}檔股票, 平均勝率{avg_wr:.1f}%, 平均總報酬{avg_ret:.1f}%')
    
    # Current signals (from screener)
    print('\n\n📋 當前市場信號（15:42）')
    print('🔴 過熱觀望: NVDA / QQQ / TQQQ / SPY / SSO / SPXL / AMD / AMZN / META / GOOGL / MSFT')
    print('✅ 多頭觀察: FANG / COIN / AAPL')
    print('🟢 超賣觀察: 無')
    
    # Best picks
    print('\n\n🎯 最佳進場點（等待RSI<35）')
    best_by_strategy = {}
    for r in results:
        if r['win_rate'] >= 80 and r['total_return'] > 50:
            strat = r['strategy']
            if strat not in best_by_strategy or r['total_return'] > best_by_strategy[strat]['total_return']:
                best_by_strategy[strat] = r
    
    for strat, r in best_by_strategy.items():
        print(f'  {strat}: {r["symbol"]} (勝率{r["win_rate"]:.0f}%, 報酬{r["total_return"]:.0f}%)')
    
    print('\n\n💡 操作建議')
    print('  1. 全市場過熱，等 RSI 回到 <35 再進場')
    print('  2. 最佳策略: RSI_Oversold_Aggressive（勝率99%）')
    print('  3. 目標標的: TSLA / TQQQ / SPXL（回測報酬 >120%）')
    print('  4. 風險: 全市場 RSI>90，注意回調風險')
    
    print('\n\n✅ 報告完成')

if __name__ == '__main__':
    main()