# -*- coding: utf-8 -*-
"""快速回測 Core ETF"""
from teams.ray.scripts.dca_backtest import dca_backtest

core = ['0050', '0056', '00878', '00919']
results = []
for etf in core:
    r = dca_backtest(etf, 5000, 52)
    if r:
        results.append(r)

print()
print('=' * 65)
print(' Ray DCA Core 持股回測摘要 (52週)')
print('=' * 65)
for r in results:
    winner = 'DCA' if r['dca_vs_bh'] > 0 else 'B&H'
    pos = r['period_pos']
    avg = r['dca_avg_cost']
    dca_ret = r['dca_return_pct']
    bh_ret = r['bh_return_pct']
    diff = abs(r['dca_vs_bh'])
    print(f'  {r["name"]}({r["etf_id"]}):')
    print(f'    DCA報酬: {dca_ret:+.1f}% | B&H報酬: {bh_ret:+.1f}%')
    print(f'    差異: {diff:.1f}% ({winner}勝)')
    print(f'    期末位置: {pos:.0f}% | 平均成本: ${avg:.2f}')
    print()