# -*- coding: utf-8 -*-
import json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
with open(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\stores\short_term\tina_cron_v2_output.json', 'r', encoding='utf-8', errors='replace') as f:
    d = json.load(f)
print('Layer3 positions:')
for p in d['layer3_positions']:
    sym = p['symbol']
    rsi = p['current_rsi']
    pnl = p['pnl_pct']
    print(f'  {sym}: RSI={rsi:.1f}, PnL={pnl}')
print()
print('Layer2 risk:')
l2 = d['layer2_risk']
print(f"  Zone: {l2['risk_level']} {l2.get('zone_desc','')}")
us = l2.get('us_macro', {})
print(f"  WTI={us.get('WTI')}, SPX={us.get('SPX')}, NDX={us.get('NDX')}, TNX={us.get('TNX')}")
zf = l2.get('zone_factors', {})
print(f"  Factors: {zf}")