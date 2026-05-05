"""
Taiwan ETF Daily Report
台股 ETF 每日報告
"""

import sys
sys.path.insert(0, __file__.rsplit('\\', 1)[0] if '\\' in __file__ else '.')

from tw_etf_database import (
    init_db, fetch_analysis, save_analysis,
    generate_dca_signals, get_top_dca, TW_ETFS, OPTIMAL_PARAMS
)
import json
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent

def main():
    print("=" * 70)
    print("  Taiwan ETF Daily Report")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Init DB
    print("\n[1/5] Initializing database...")
    db_file = init_db()
    print(f"      OK: {db_file}")
    
    # Fetch
    print("\n[2/5] Fetching ETF data...")
    analysis = fetch_analysis()
    print(f"      Analyzed {len(analysis)} ETFs")
    
    # Save
    print("\n[3/5] Saving to database...")
    save_analysis(analysis)
    print("      OK")
    
    # DCA signals
    print("\n[4/5] Generating DCA signals...")
    signals = generate_dca_signals(analysis)
    print(f"      Generated {len(signals)} signals")
    
    # Display
    print("\n" + "=" * 70)
    print("  DCA SIGNALS (PRIORITY)")
    print("=" * 70)
    
    # Sort by DCA priority
    dca_priority = sorted([s for s in signals if s['dca_weight'] > 0], 
                         key=lambda x: (-x['dca_weight'], x['rsi_14']))
    
    print(f"\n  {'Symbol':<6} {'Name':<14} {'Price':>8} {'RSI':>6} {'Signal':<14} {'Weight':>6}")
    print("  " + "-" * 65)
    
    for s in dca_priority:
        print(f"  {s['symbol']:<6} {s['name']:<14} {s['price']:>8.0f} {s['rsi_14']:>6.1f} {s['recommendation']:<14} {s['dca_weight']:>6}%")
    
    # All ETFs
    print("\n" + "=" * 70)
    print("  ALL ETFs OVERVIEW")
    print("=" * 70)
    
    print(f"\n  {'Sym':<6} {'Name':<14} {'Price':>8} {'Chg':>7} {'RSI':>6} {'Signal':<14} {'Tier':>5}")
    print("  " + "-" * 70)
    
    for d in sorted(analysis, key=lambda x: (x.get('tier', 99), -x.get('score', 0))):
        if 'error' in d:
            continue
        tier_marker = "*" if d.get('tier', 3) == 1 else " "
        sign = '+' if d['change_pct'] > 0 else ''
        print(f"  {tier_marker}{d['symbol']:<5} {d['name']:<14} {d['price']:>8.0f} {sign}{d['change_pct']:>6.1f}% {d['rsi_14']:>6.1f} {d['signal']:<14} {d['tier']:>5}")
    
    # Summary
    buy_count = sum(1 for d in analysis if d.get('signal') in ['STRONG_BUY', 'BUY'])
    watch_count = sum(1 for d in analysis if d.get('signal') == 'WATCH')
    overbought = sum(1 for d in analysis if d.get('signal') == 'OVERBOUGHT')
    reduce_count = sum(1 for d in analysis if d.get('signal') == 'OVERBOUGHT')
    
    print(f"\n  Summary: {buy_count} BUY | {watch_count} WATCH | {overbought} OVERBOUGHT")
    
    # Best DCA picks
    top_dca = get_top_dca()
    print("\n  Top DCA Picks:")
    for i, d in enumerate(top_dca[:3], 1):
        print(f"    {i}. {d['name']} ({d['symbol']}) - RSI={d['rsi_14']:.1f}, Weight={d['dca_weight']}%")
    
    # Save report
    print("\n[5/5] Saving report...")
    report = {
        'date': datetime.now().isoformat(),
        'total_etfs': len(analysis),
        'signals': signals,
        'top_dca': top_dca,
        'analysis': [d for d in analysis if 'error' not in d],
        'params': OPTIMAL_PARAMS,
        'summary': {
            'buy_count': buy_count,
            'watch_count': watch_count,
            'overbought_count': overbought
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
