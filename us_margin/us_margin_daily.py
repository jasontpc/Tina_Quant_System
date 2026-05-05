"""
US Margin Daily Report
美股 Margin 每日報告
"""

import sys
sys.path.insert(0, __file__.rsplit('\\', 1)[0] if '\\' in __file__ else '.')

from us_margin_database import (
    init_db, fetch_daily_data, save_daily_data,
    analyze_margin_risk, get_high_risk_stocks,
    get_short_squeeze_candidates, MARGIN_STOCKS, MARGIN_PARAMS
)
import json
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent

def main():
    print("=" * 70)
    print("  US Margin Daily Report")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Init
    print("\n[1/6] Initializing database...")
    init_db()
    print("      OK")
    
    # Fetch
    print("\n[2/6] Fetching margin data...")
    data = fetch_daily_data()
    print(f"      Fetched {len(data)} stocks")
    
    # Save
    print("\n[3/6] Saving to database...")
    save_daily_data(data)
    print("      OK")
    
    # Analyze
    print("\n[4/6] Analyzing margin risk...")
    alerts = analyze_margin_risk(data)
    print(f"      Found {len(alerts)} risk alerts")
    
    # High Risk Stocks
    print("\n" + "=" * 70)
    print("  HIGH RISK STOCKS (RSI > 70)")
    print("=" * 70)
    
    high_risk = get_high_risk_stocks()
    if high_risk:
        print(f"\n  {'Symbol':<8} {'Name':<15} {'Price':>10} {'RSI':>6} {'Short%':>8} {'Days':>6}")
        print("  " + "-" * 60)
        for s in high_risk:
            print(f"  {s['symbol']:<8} {s['name']:<15} ${s['price']:>9.2f} {s['rsi_14']:>6.1f} {s['short_ratio']:>7.1f}% {s['days_to_cover']:>6.1f}")
    else:
        print("\n  None - All stocks in safe zone")
    
    # Short Squeeze Candidates
    print("\n" + "=" * 70)
    print("  SHORT SQUEEZE CANDIDATES")
    print("=" * 70)
    
    squeeze = get_short_squeeze_candidates()
    if squeeze:
        print(f"\n  {'Symbol':<8} {'Name':<15} {'Price':>10} {'ShortRatio':>10} {'DaysCover':>10} {'Score':>6}")
        print("  " + "-" * 65)
        for s in squeeze:
            print(f"  {s['symbol']:<8} {s['name']:<15} ${s['price']:>9.2f} {s['short_ratio']:>10.1f} {s['days_to_cover']:>10.1f} {s['squeeze_score']:>6.1f}")
    else:
        print("\n  No high short interest stocks found")
    
    # Alerts Summary
    print("\n" + "=" * 70)
    print("  MARGIN ALERTS")
    print("=" * 70)
    
    high_alerts = [a for a in alerts if a['severity'] == 'HIGH']
    med_alerts = [a for a in alerts if a['severity'] == 'MEDIUM']
    
    print(f"\n  HIGH: {len(high_alerts)} | MEDIUM: {len(med_alerts)}")
    
    if high_alerts:
        print("\n  HIGH SEVERITY:")
        for a in high_alerts:
            print(f"    ! {a['symbol']}: {a['reason']}")
    
    if med_alerts:
        print("\n  MEDIUM SEVERITY:")
        for a in med_alerts[:5]:
            print(f"    - {a['symbol']}: {a['reason']}")
    
    # Save report
    print("\n[5/6] Saving report...")
    
    report = {
        'date': datetime.now().isoformat(),
        'total_stocks': len(data),
        'high_risk_count': len(high_risk),
        'alerts_count': len(alerts),
        'high_risk': high_risk,
        'short_squeeze': squeeze,
        'alerts': alerts,
        'params': MARGIN_PARAMS,
        'summary': {
            'high_severity': len(high_alerts),
            'medium_severity': len(med_alerts),
        }
    }
    
    report_file = DATA_DIR / f"daily_report_{datetime.now().strftime('%Y%m%d')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"      Saved: {report_file}")
    
    # Recommendations
    print("\n[6/6] Margin Recommendations:")
    print("-" * 70)
    
    # Calculate margin recommendations
    margin_buy = [d for d in data if d.get('rsi_14', 0) < 40 and d.get('trend') == 'bullish']
    margin_sell = [d for d in data if d.get('rsi_14', 0) > 70]
    
    print(f"\n  MARGIN BUY (RSI < 40, Bullish):")
    if margin_buy:
        for s in margin_buy[:5]:
            print(f"    {s['symbol']}: ${s['price']:.2f}, RSI={s['rsi_14']:.1f}")
    else:
        print("    None - Market overbought")
    
    print(f"\n  MARGIN SHORT (RSI > 70, Bearish):")
    if margin_sell:
        for s in margin_sell[:5]:
            print(f"    {s['symbol']}: ${s['price']:.2f}, RSI={s['rsi_14']:.1f}")
    else:
        print("    None")
    
    print("\n" + "=" * 70)
    print("  COMPLETE")
    print("=" * 70)

if __name__ == '__main__':
    main()
