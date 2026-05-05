"""
TW ETF Return, Yield & EPS Daily Report
台股 ETF 殖利率 & 年化報酬率 & EPS 每日報告
"""

import sys
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, __file__.rsplit('\\', 1)[0] if '\\' in __file__ else '.')

from tw_etf_return_database import (
    init_db, fetch_return_data, fetch_yield_data, fetch_eps_data,
    save_return_data, save_yield_data, save_eps_data,
    generate_rankings, ETF_POOL
)

DATA_DIR = Path(__file__).parent

def main():
    print("=" * 70)
    print("  TW ETF Return, Yield & EPS Daily Report")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Init
    print("\n[1/7] Initializing database...")
    init_db()
    print("      OK")
    
    # Fetch Return Data
    print("\n[2/7] Fetching return data (3Y)...")
    ret_data = fetch_return_data()
    valid_ret = [r for r in ret_data if 'error' not in r and r.get('ann_1y')]
    print(f"      Fetched {len(ret_data)} ETFs ({len(valid_ret)} valid with ann_1y)")
    
    # Fetch Yield Data
    print("\n[3/7] Fetching yield data...")
    yld_data = fetch_yield_data()
    print(f"      Fetched {len(yld_data)} ETFs")
    
    # Fetch EPS Data
    print("\n[4/7] Fetching EPS data...")
    eps_data = fetch_eps_data()
    print(f"      Fetched {len(eps_data)} ETFs")
    
    # Save
    print("\n[5/7] Saving to database...")
    save_return_data(ret_data)
    save_yield_data(yld_data)
    save_eps_data(eps_data)
    print("      OK")
    
    # Rankings
    rankings = generate_rankings(ret_data, yld_data, eps_data)
    
    # Top Ann Return
    print("\n" + "=" * 70)
    print("  TOP 10 BY ANNUALIZED RETURN (1Y)")
    print("=" * 70)
    
    top_ann = sorted([r for r in rankings if r['ann_1y']], key=lambda x: -x['ann_1y'])[:10]
    print(f"\n  {'Rank':<5} {'Symbol':<6} {'Name':<15} {'Ann 1Y':>8} {'Sharpe':>6} {'MaxDD':>8}")
    print("  " + "-" * 55)
    for i, r in enumerate(top_ann, 1):
        ann = f"{r['ann_1y']:+.1f}%"
        shp = f"{r['sharpe_1y']:.2f}" if r['sharpe_1y'] else "N/A"
        mdd = f"{r['maxdd_1y']:.1f}%" if r['maxdd_1y'] else "N/A"
        print(f"  {i:<5} {r['symbol']:<6} {r['name']:<15} {ann:>8} {shp:>6} {mdd:>8}")
    
    # Top Sharpe
    print("\n" + "=" * 70)
    print("  TOP 10 BY SHARPE RATIO")
    print("=" * 70)
    
    top_sharpe = sorted([r for r in rankings if r['sharpe_1y']], key=lambda x: -x['sharpe_1y'])[:10]
    print(f"\n  {'Rank':<5} {'Symbol':<6} {'Name':<15} {'Sharpe':>6} {'Ann 1Y':>8} {'Yield':>6}")
    print("  " + "-" * 55)
    for i, r in enumerate(top_sharpe, 1):
        shp = f"{r['sharpe_1y']:.2f}" if r['sharpe_1y'] else "N/A"
        ann = f"{r['ann_1y']:+.1f}%" if r['ann_1y'] else "N/A"
        yld = f"{r['yield']:.2f}%" if r['yield'] else "N/A"
        print(f"  {i:<5} {r['symbol']:<6} {r['name']:<15} {shp:>6} {ann:>8} {yld:>6}")
    
    # DCA Recommendations
    print("\n" + "=" * 70)
    print("  DCA RECOMMENDATIONS")
    print("=" * 70)
    
    dca_recs = [r for r in rankings if r['dca_weight'] > 0 and r['tier'] in [1, 2]]
    dca_recs = sorted(dca_recs, key=lambda x: (-x['ann_1y'] if x['ann_1y'] else 0, -x['sharpe_1y'] if x['sharpe_1y'] else 0))
    
    print(f"\n  {'Symbol':<6} {'Name':<15} {'Weight':>7} {'Ann 1Y':>8} {'Sharpe':>6} {'Yield':>6} {'Rec':<12}")
    print("  " + "-" * 75)
    for r in dca_recs[:15]:
        ann = f"{r['ann_1y']:+.1f}%" if r['ann_1y'] else "N/A"
        shp = f"{r['sharpe_1y']:.2f}" if r['sharpe_1y'] else "N/A"
        yld = f"{r['yield']:.2f}%" if r['yield'] else "N/A"
        print(f"  {r['symbol']:<6} {r['name']:<15} {r['dca_weight']:>6}% {ann:>8} {shp:>6} {yld:>6} {r['recommendation']:<12}")
    
    # Save Report
    print("\n[6/7] Saving report...")
    
    report = {
        'date': datetime.now().isoformat(),
        'total_etfs': len(valid_ret),
        'rankings': rankings,
        'top_ann_return': top_ann,
        'top_sharpe': top_sharpe,
        'dca_recommendations': dca_recs[:15]
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
