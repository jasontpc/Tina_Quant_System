import sys
sys.path.insert(0, 'C:/Users/USER/.openclaw/workspace/Tina_Quant_System')
sys.path.insert(0, 'C:/Users/USER/.openclaw/workspace/Tina_Quant_System/teams/nana')

import os
os.chdir('C:/Users/USER/.openclaw/workspace/Tina_Quant_System')

from teams.nana.nana_v5 import NanaSystem

print('Running NanaSystem backtest...')
ns = NanaSystem()
ns.scan_universe()
print(f'\nScan complete: {len(ns.results)} stocks, {len(ns.top_picks)} tradeable')

if ns.top_picks:
    print('\nTop picks:')
    for r in ns.top_picks[:5]:
        print(f"  {r['symbol']} {r['name']} Score={r['score']:.1f} RSI={r['rsi']:.1f} can_trade={r['can_trade']}")

wr, avg, total = ns.backtest_all()
print(f'\nBacktest Result: WR={wr:.1f}%, Avg={avg:.2f}%, Total={total} trades')
