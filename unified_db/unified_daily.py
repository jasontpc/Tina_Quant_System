"""
Unified Trading Database Daily Report
全系統整合資料庫每日報告
"""

import sys
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, __file__.rsplit('\\', 1)[0] if '\\' in __file__ else '.')

from unified_database_v2 import (
    init_db, run_historical_backtest, save_trades,
    analyze_stock_performance, find_optimal_params,
    get_unified_signals, save_unified_signals,
    BEST_STOCKS
)

DATA_DIR = Path(__file__).parent

def main():
    print("=" * 70)
    print("  Unified Trading Database - Daily Report")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Init
    print("\n[1/6] Initializing database...")
    init_db()
    print("      OK")
    
    # Run backtest (add new data)
    print("\n[2/6] Running historical backtest...")
    trades = run_historical_backtest()
    save_trades(trades)
    print(f"      Added {len(trades)} trades")
    
    # Analyze
    print("\n[3/6] Analyzing performance...")
    stock_perf = analyze_stock_performance()
    print(f"      Analyzed {len(stock_perf)} stocks")
    
    # Optimal params
    print("\n[4/6] Finding optimal parameters...")
    opt_params = find_optimal_params()
    print(f"      Found {len(opt_params)} combinations")
    
    # Signals
    print("\n[5/6] Generating signals...")
    signals = get_unified_signals()
    save_unified_signals(signals)
    print(f"      Generated {len(signals)} signals")
    
    # Display
    print("\n" + "=" * 70)
    print("  TOP PERFORMING STOCKS")
    print("=" * 70)
    
    if stock_perf:
        print(f"\n  {'Symbol':<10} {'Name':<12} {'Trades':>6} {'WinRate':>8} {'AvgRet':>8} {'Score':>6}")
        print("  " + "-" * 55)
        for s in stock_perf[:15]:
            sign = '+' if s['avg_return'] > 0 else ''
            print(f"  {s['symbol']:<10} {s['name']:<12} {s['total_trades']:>6} {s['win_rate']:>7.1f}% {sign}{s['avg_return']:>6.2f}% {s['score']:>6.1f}")
    
    print("\n" + "=" * 70)
    print("  BEST PARAMETERS (WinRate > 60%)")
    print("=" * 70)
    
    best_params = [p for p in opt_params if p['win_rate'] >= 60]
    if best_params:
        print(f"\n  {'RSI':<10} {'Hold':<8} {'TP':>4} {'SL':>4} {'WinRate':>8} {'AvgRet':>8} {'N':>4}")
        print("  " + "-" * 50)
        for p in best_params[:10]:
            print(f"  {p['rsi_min']}-{p['rsi_max']:<8} {p['hold_min']}-{p['hold_max']:<5}d {p['tp_pct']:>3}% {p['sl_pct']:>4}% {p['win_rate']:>7.1f}% {p['avg_return']:>7.2f}% {p['sample_size']:>4}")
    else:
        print("\n  No parameters with WinRate > 60%")
    
    print("\n" + "=" * 70)
    print("  CURRENT SIGNALS")
    print("=" * 70)
    
    buy_signals = [s for s in signals if s['signal'] == 'BUY']
    print(f"\n  BUY Signals ({len(buy_signals)}):")
    for s in buy_signals:
        sign = '+' if s['avg_return'] > 0 else ''
        print(f"    {s['symbol']:<10} RSI={s['rsi_14']:.1f} WR={s['win_rate']:.1f}% {sign}{s['avg_return']:.1f}%")
    
    overbought = [s for s in signals if s['signal'] == 'OVERBOUGHT']
    print(f"\n  OVERBOUGHT ({len(overbought)}):")
    for s in overbought[:5]:
        print(f"    {s['symbol']:<10} RSI={s['rsi_14']:.1f} WR={s['win_rate']:.1f}%")
    
    # Save report
    print("\n[6/6] Saving report...")
    
    report = {
        'date': datetime.now().isoformat(),
        'total_trades': len(trades),
        'stocks_analyzed': len(stock_perf),
        'stock_performance': stock_perf[:20],
        'best_parameters': best_params[:10],
        'signals': signals,
        'buy_signals': buy_signals,
        'summary': {
            'best_stock': stock_perf[0] if stock_perf else None,
            'total_signals': len(signals),
            'buy_count': len(buy_signals),
            'overbought_count': len(overbought)
        }
    }
    
    report_file = DATA_DIR / f"daily_report_{datetime.now().strftime('%Y%m%d')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"      Saved: {report_file}")
    
    print("\n" + "=" * 70)
    print("  COMPLETE")
    print("=" * 70)

if __name__ == '__main__':
    main()
