"""
Taiwan AI Tech Stocks Daily Report
台股 AI 科技股每日報告
"""

import sys
sys.path.insert(0, __file__.rsplit('\\', 1)[0] if '\\' in __file__ else '.')

from tw_ai_tech_database import (
    init_db, fetch_analysis, save_analysis,
    generate_trade_signals, TW_AI_STOCKS, OPTIMAL_PARAMS,
    fetch_us_correlation
)
import json
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent

def main():
    print("=" * 70)
    print("  Taiwan AI Tech Stocks - Daily Report")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Initialize DB
    print("\n[1/6] Initializing database...")
    db_file = init_db()
    print(f"      OK: {db_file}")
    
    # Fetch analysis
    print("\n[2/6] Fetching Taiwan market data...")
    analysis = fetch_analysis()
    print(f"      Analyzed {len(analysis)} stocks")
    
    # Save to DB
    print("\n[3/6] Saving to database...")
    save_analysis(analysis)
    print("      OK")
    
    # Get US correlation
    print("\n[4/6] Fetching US ADP correlation...")
    correlations = []
    for sym, info in list(TW_AI_STOCKS.items())[:5]:  # Top 5
        corr = fetch_us_correlation(sym, info['us_adp'])
        if corr and 'error' not in corr:
            correlations.append(corr)
            print(f"      {sym} vs {info['us_adp']}: RSI TW={corr['tw_rsi']:.1f} US={corr['us_rsi']:.1f}")
    
    # Get signals
    print("\n[5/6] Generating signals...")
    signals = generate_trade_signals(analysis)
    print(f"      Found {len(signals)} signals (RSI < 40)")
    
    # Display results
    print("\n" + "=" * 70)
    print("  TRADING SIGNALS (RSI < 40)")
    print("=" * 70)
    
    if signals:
        print(f"\n  {'Symbol':<6} {'Name':<10} {'Price':>10} {'RSI':>6} {'Target':>10} {'Stop':>10}")
        print("  " + "-" * 60)
        for s in signals:
            print(f"  {s['symbol']:<6} {s['name']:<10} ${s['entry_price']:>9.0f} {s['entry_rsi']:>6.1f} ${s['target_price']:>9.0f} ${s['stop_loss']:>9.0f}")
    else:
        print("\n  No signals today (no stocks with RSI < 40)")
    
    # All stocks overview
    print("\n" + "=" * 70)
    print("  ALL STOCKS OVERVIEW")
    print("=" * 70)
    
    print(f"\n  {'Sym':<6} {'Name':<10} {'Price':>10} {'Chg':>7} {'RSI':>6} {'Signal':<14} {'US ADP':<8}")
    print("  " + "-" * 75)
    
    sorted_analysis = sorted(analysis, key=lambda x: (x.get('tier', 99), -x.get('score', 0)))
    
    buy_count = 0
    watch_count = 0
    overbought_count = 0
    
    for d in sorted_analysis:
        if 'error' in d:
            continue
        
        tier_marker = "*" if d.get('tier', 3) == 1 else " "
        sign = '+' if d['change_pct'] > 0 else ''
        us_adp = d.get('us_adp', '')
        print(f"  {tier_marker}{d['symbol']:<5} {d['name']:<10} {d['price']:>10.0f} {sign}{d['change_pct']:>6.1f}% {d['rsi_14']:>6.1f} {d['signal']:<14} {us_adp:<8}")
        
        if d['signal'] in ['STRONG_BUY', 'BUY']:
            buy_count += 1
        elif d['signal'] == 'WATCH':
            watch_count += 1
        elif d['signal'] == 'OVERBOUGHT':
            overbought_count += 1
    
    print(f"\n  Summary: {buy_count} BUY | {watch_count} WATCH | {overbought_count} OVERBOUGHT")
    
    # US Correlation section
    if correlations:
        print("\n" + "=" * 70)
        print("  US ADP CORRELATION")
        print("=" * 70)
        print(f"\n  {'TW':<6} {'US':<8} {'TW Price':>10} {'US Price':>10} {'TW RSI':>8} {'US RSI':>8}")
        print("  " + "-" * 60)
        for c in correlations:
            print(f"  {c['tw_symbol']:<6} {c['us_symbol']:<8} {c['tw_price']:>10.2f} ${c['us_price']:>9.2f} {c['tw_rsi']:>8.1f} {c['us_rsi']:>8.1f}")
    
    # Save report
    print("\n[6/6] Saving report...")
    report = {
        'date': datetime.now().isoformat(),
        'total_stocks': len(analysis),
        'signals': signals,
        'analysis': [d for d in analysis if 'error' not in d],
        'correlations': correlations,
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
    main()
