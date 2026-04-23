# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
os.chdir(os.path.dirname(__file__))

# Import the module
from teams.nana.nana_v5 import NanaSystem, backtest, ALL_STOCKS

print("Testing NanaSystem v5.3...")
ns = NanaSystem()
ns.scan_universe()
print(f"Scanned: {len(ns.results)} | Tradeable: {len(ns.top_picks)}")

# Show top picks with Kelly sizing
print("\n--- Top Picks ---")
for r in ns.top_picks[:5]:
    shares = r.get('suggested_shares', 0)
    cap = r.get('suggested_capital', 0)
    print(f"  {r['symbol']} {r['name']}: score={r['score']}, bias={r['bias']}, can_trade={r['can_trade']}, Kelly={shares}股/${cap/10000:.1f}萬")

# Run backtest
wr, avg, total = ns.backtest_all()
print(f"\nBacktest Results: WR={wr:.1f}%, Avg={avg:.2f}%, Total={total}")

if ns.trades:
    import pandas as pd
    df = pd.DataFrame(ns.trades)
    print("\n--- Exit Reasons ---")
    for reason, cnt in df['reason'].value_counts().items():
        rdf = df[df['reason'] == reason]
        wr_r = len(rdf[rdf['profit'] > 0]) / len(rdf) * 100
        print(f"  {reason}: {cnt}筆, WR={wr_r:.1f}%, Avg={rdf['profit'].mean():.2f}%")
    
    # inst_reversal count
    inst_rev = df[df['reason'] == 'inst_reversal']
    print(f"\n  inst_reversal exits: {len(inst_rev)}")
    if len(inst_rev) > 0:
        print(f"  inst_reversal WR: {len(inst_rev[inst_rev['profit'] > 0])/len(inst_rev)*100:.1f}%")
