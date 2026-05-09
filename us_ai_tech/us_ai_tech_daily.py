"""
US AI Tech Stocks Daily Report
美股 AI 科技股每日報告
"""

import sys
sys.path.insert(0, __file__.rsplit('\\', 1)[0] if '\\' in __file__ else '.')

from us_ai_tech_database import (
    init_db, fetch_analysis, save_analysis, 
    get_latest_signals, generate_trade_signals,
    US_AI_STOCKS, OPTIMAL_PARAMS
)
import json
from datetime import datetime
from pathlib import Path

# Tina 標準化框架
sys.path.insert(0, str(Path(__file__).parent.parent / 'stores'))
from script_standards import ScriptStandard

DATA_DIR = Path(__file__).parent

def main():
    print("=" * 70)
    print("  US AI Tech Stocks - Daily Report")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Initialize DB
    print("\n[1/5] Initializing database...")
    db_file = init_db()
    print(f"      OK: {db_file}")
    
    # Fetch analysis
    print("\n[2/5] Fetching market data...")
    analysis = fetch_analysis()
    print(f"      Analyzed {len(analysis)} stocks")
    
    # Save to DB
    print("\n[3/5] Saving to database...")
    save_analysis(analysis)
    print("      OK")
    
    # Get signals
    print("\n[4/5] Generating signals...")
    signals = generate_trade_signals(analysis)
    print(f"      Found {len(signals)} signals (RSI < 40)")
    
    # Display results
    print("\n" + "=" * 70)
    print("  TRADING SIGNALS (RSI < 40)")
    print("=" * 70)
    
    if signals:
        print(f"\n  {'Symbol':<6} {'Name':<15} {'Price':>10} {'RSI':>6} {'Target':>10} {'Stop':>10}")
        print("  " + "-" * 65)
        for s in signals:
            print(f"  {s['symbol']:<6} {s['name']:<15} ${s['entry_price']:>9.2f} {s['entry_rsi']:>6.1f} ${s['target_price']:>9.2f} ${s['stop_loss']:>9.2f}")
    else:
        print("\n  No signals today (no stocks with RSI < 40)")
    
    # All stocks overview
    print("\n" + "=" * 70)
    print("  ALL STOCKS OVERVIEW")
    print("=" * 70)
    
    print(f"\n  {'Symbol':<6} {'Name':<15} {'Price':>10} {'RSI(14)':>8} {'Signal':<14} {'Trend':<10} {'Score':>5}")
    print("  " + "-" * 80)
    
    # Sort by tier then by score
    sorted_analysis = sorted(analysis, key=lambda x: (x.get('tier', 99), -x.get('score', 0)))
    
    buy_count = 0
    watch_count = 0
    overbought_count = 0
    
    for d in sorted_analysis:
        if 'error' in d:
            continue
        
        tier_marker = "*" if d.get('tier', 3) == 1 else " "
        print(f"  {tier_marker}{d['symbol']:<5} {d['name']:<15} ${d['price']:>9.2f} {d['rsi_14']:>8.1f} {d['signal']:<14} {d['trend']:<10} {d['score']:>5}")
        
        if d['signal'] in ['STRONG_BUY', 'BUY']:
            buy_count += 1
        elif d['signal'] == 'WATCH':
            watch_count += 1
        elif d['signal'] == 'OVERBOUGHT':
            overbought_count += 1
    
    print(f"\n  Summary: {buy_count} BUY | {watch_count} WATCH | {overbought_count} OVERBOUGHT")
    
    # Save report
    print("\n[5/5] Saving report...")
    report = {
        'date': datetime.now().isoformat(),
        'total_stocks': len(analysis),
        'signals': signals,
        'analysis': [d for d in analysis if 'error' not in d],
        'params': OPTIMAL_PARAMS,
        'summary': {
            'buy_count': buy_count,
            'watch_count': watch_count,
            'overbought_count': overbought_count
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
    # Tina 標準化入口
    std = ScriptStandard('us_ai_tech', 'US')
    
    try:
        # 執行前：讀取脈絡
        context = std.before_execute()
        print(f"[Brain-Aware] Execution ID: {context['execution_id']}")
        
        # 執行主要邏輯
        main()
        
        # 執行後：讀取報告檔案作為 signals
        report_file = DATA_DIR / f"daily_report_{datetime.now().strftime('%Y%m%d')}.json"
        if report_file.exists():
            with open(report_file, 'r', encoding='utf-8') as f:
                report = json.load(f)
            signals = report.get('signals', [])
            metrics = {
                'total_stocks': report.get('total_stocks', 0),
                'buy_count': report.get('summary', {}).get('buy_count', 0),
                'watch_count': report.get('summary', {}).get('watch_count', 0)
            }
        else:
            signals = []
            metrics = {}
        
        std.after_execute(success=True, signals=signals, metrics=metrics)
        
    except Exception as e:
        std.handle_error(e, 'us_ai_tech_daily.py 執行失敗')
        std.after_execute(success=False, signals=[], metrics={'error': str(e)})
        raise
    finally:
        health = std.finalize()
        print(f"[Health] status={health['status']}, duration={health['duration_ms']}ms")
