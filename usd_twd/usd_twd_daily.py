"""
USD/TWD Daily Report
美元兌台幣每日報告
"""

import sys
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, __file__.rsplit('\\', 1)[0] if '\\' in __file__ else '.')

from usd_twd_tracker import (
    init_db, fetch_current_rate, fetch_historical_rates,
    analyze_rate_level, generate_signals, save_data
)

DATA_DIR = Path(__file__).parent

def main():
    print("=" * 60)
    print("  USD/TWD Daily Report")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Init
    print("\n[1/5] Initializing database...")
    init_db()
    print("      OK")
    
    # Fetch
    print("\n[2/5] Fetching USD/TWD rate...")
    rate = fetch_current_rate()
    if rate:
        sign = '+' if rate['change_pct'] > 0 else ''
        print(f"      USD/TWD: {rate['price']:.4f} ({sign}{rate['change_pct']:.4f}%)")
    
    # Historical
    print("\n[3/5] Fetching historical data...")
    hist = fetch_historical_rates()
    print(f"      Got {len(hist)} data points")
    
    # Signals
    print("\n[4/5] Generating signals...")
    signals = generate_signals(rate['price'] if rate else 0, 
                              rate['change_pct'] if rate else 0, 
                              hist)
    print(f"      Generated {len(signals)} signals")
    
    # Save
    print("\n[5/5] Saving data...")
    save_data(rate, hist, signals)
    print("      OK")
    
    # Display
    print("\n" + "=" * 60)
    print("  USD/TWD 分析")
    print("=" * 60)
    
    if rate:
        level, signal = analyze_rate_level(rate['price'])
        sign = '+' if rate['change_pct'] > 0 else ''
        print(f"\n  即期匯率: {rate['price']:.4f}")
        print(f"  單日變化: {sign}{rate['change_pct']:.2f}%")
        print(f"  區間判斷: {level}")
        
        # MA analysis
        if len(hist) >= 20:
            ma20 = sum([d['price'] for d in hist[-20:]]) / 20
            print(f"\n  MA20: {ma20:.4f}")
            if rate['price'] > ma20:
                print(f"  趨勢: USD 強勢 ↑")
            else:
                print(f"  趨勢: TWD 回升 ↓")
    
    print("\n  Signals:")
    for s in signals:
        print(f"    {s['signal']}: {s['interpretation']} → {s['action']}")
    
    # Save Report
    report = {
        'date': datetime.now().isoformat(),
        'rate': rate,
        'signals': signals,
        'level': level if rate else None,
        'signal': signal if rate else None
    }
    
    report_file = DATA_DIR / f"daily_report_{datetime.now().strftime('%Y%m%d')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 60)

if __name__ == '__main__':
    main()
