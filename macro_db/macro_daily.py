"""
Macro Database Daily Report
宏觀資料庫每日報告
"""

import sys
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, __file__.rsplit('\\', 1)[0] if '\\' in __file__ else '.')

from macro_database import (
    init_db, fetch_macro_data, fetch_taiwan_data,
    classify_regime, generate_macro_signals, save_data, analyze_current_state
)

DATA_DIR = Path(__file__).parent

def main():
    print("=" * 70)
    print("  Macro Database - Daily Report")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Init
    print("\n[1/5] Initializing database...")
    init_db()
    print("      OK")
    
    # Fetch & Analyze
    print("\n[2/5] Fetching macro data...")
    macro_data, tw_data, regime, signals = analyze_current_state()
    print(f"      Fetched {len(macro_data)} macro indicators")
    print(f"      Fetched {len(tw_data)} Taiwan indicators")
    
    # Market Regime
    print("\n" + "=" * 70)
    print("  MARKET REGIME CLASSIFICATION")
    print("=" * 70)
    
    print(f"\n  【Regime】: {regime['regime']}")
    print(f"  【VIX Level】: {regime['vix_level']}")
    print(f"  【Dollar】: {regime['dxy_level']}")
    print(f"  【Yield】: {regime['yield_level']}")
    print(f"  【Sentiment】: {regime['sentiment']}")
    
    # Macro Signals
    print("\n" + "=" * 70)
    print("  MACRO SIGNALS & ACTIONS")
    print("=" * 70)
    
    for s in signals:
        print(f"\n  {s['signal_type']} - {s['macro_factor']}")
        print(f"    Signal: {s['interpretation']}")
        print(f"    Value: {s['value']:.2f} (Threshold: {s['threshold']})")
        print(f"    Action: {s['action']}")
    
    # Key Indicators
    print("\n" + "=" * 70)
    print("  KEY MACRO INDICATORS")
    print("=" * 70)
    
    print(f"\n  {'Indicator':<30} {'Value':>12} {'Change':>10}")
    print("  " + "-" * 55)
    
    for d in sorted(macro_data, key=lambda x: -abs(x.get('change_pct', 0))):
        sign = '+' if d['change_pct'] > 0 else ''
        print(f"  {d['name']:<30} {d['value']:>12.2f} {sign}{d['change_pct']:>6.2f}%")
    
    # Taiwan Data
    print("\n" + "=" * 70)
    print("  TAIWAN MARKET INDICATORS")
    print("=" * 70)
    
    print(f"\n  {'Symbol':<20} {'Value':>12} {'Change':>10}")
    print("  " + "-" * 45)
    
    for d in tw_data:
        sign = '+' if d['change_pct'] > 0 else ''
        print(f"  {d['name']:<20} {d['value']:>12.2f} {sign}{d['change_pct']:>6.2f}%")
    
    # ETF Implications
    print("\n" + "=" * 70)
    print("  ETF INVESTMENT IMPLICATIONS")
    print("=" * 70)
    
    # Determine ETF signals based on regime
    implications = []
    
    if regime['vix_level'] in ['EXTREME_FEAR', 'FEAR']:
        implications.append(("0050", "台灣50", "REDUCE", "VIX elevated, risk off"))
        implications.append(("00757", "FANG+", "REDUCE", "Risk off environment"))
    else:
        implications.append(("0050", "台灣50", "HOLD", "Risk on environment"))
        implications.append(("00757", "FANG+", "HOLD", "Neutral environment"))
    
    if regime['yield_level'] in ['HIGH', 'VERY_HIGH']:
        implications.append(("00757", "FANG+", "REDUCE", "High rates pressure tech"))
        implications.append(("00830", "半導體", "REDUCE", "High rates"))
    else:
        implications.append(("00830", "半導體", "HOLD", "Normal rates"))
    
    if regime['dxy_level'] in ['VERY_STRONG', 'STRONG']:
        implications.append(("0050", "台灣50", "WATCH", "Strong dollar = Taiwan pressure"))
    
    print(f"\n  {'ETF':<8} {'Name':<12} {'Signal':<10} {'Reason'}")
    print("  " + "-" * 60)
    for etf, name, signal, reason in implications:
        print(f"  {etf:<8} {name:<12} {signal:<10} {reason}")
    
    # Save Report
    print("\n[4/5] Saving report...")
    
    report = {
        'date': datetime.now().isoformat(),
        'regime': regime,
        'signals': signals,
        'macro_data': macro_data,
        'tw_data': tw_data,
        'implications': implications,
        'summary': {
            'regime': regime['regime'],
            'vix': next((d['value'] for d in macro_data if d['symbol'] == '^VIX'), None),
            'yield_10y': next((d['value'] for d in macro_data if d['symbol'] == '^TNX'), None),
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
