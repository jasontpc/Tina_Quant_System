# -*- coding: utf-8 -*-
import sys, json, os, sqlite3
import yfinance as yf
import numpy as np
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

POSITIONS_FILE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\position_tracker.json'

def get_rsi(c, p=12):
    if len(c) < p + 1:
        return 50.0
    d = np.diff(c)
    g = np.where(d > 0, d, 0)
    l = np.where(d < 0, -d, 0)
    ag = np.mean(g[-p:])
    al = np.mean(l[-p:])
    return 100 - (100 / (1 + ag / al)) if al != 0 else 50.0

with open(POSITIONS_FILE, 'r', encoding='utf-8', errors='replace') as f:
    data = json.load(f)

if isinstance(data, dict):
    positions = data.get('positions', [])
else:
    positions = data

# simulate Layer 2 pos_rsis computation
twii_rsi = 74.1
vix = 17.99
wti_val = 100.89
pos_rsis = []
for p in positions:
    sym = p.get('symbol','?')
    print(f'Fetching {sym}...')
    h = yf.Ticker(sym).history(period='20d')
    if h is None or h.empty:
        rsi_val = 50.0
        print(f'  -> No data, default RSI=50')
    else:
        rsi_val = get_rsi(h['Close'].values)
        print(f'  -> RSI={rsi_val:.2f}, bars={len(h)}')
    pos_rsis.append(rsi_val)

print()
print('pos_rsis:', [round(r,1) for r in pos_rsis])

def calc_risk_zone(twii_rsi, vix, wti, pos_rsis):
    factors = {
        'TWII_RSI': twii_rsi <= 90,
        'VIX': vix is not None and vix < 25,
        'WTI': wti is not None and wti < 100,
        'STOCK_RSI': all(r < 80 for r in pos_rsis if r)
    }
    green = sum(1 for v in factors.values() if v)
    red_count = sum(1 for v in factors.values() if not v)
    if red_count >= 2:
        return '🔴 RED', factors, f'{red_count}因子達Red Zone'
    elif red_count == 1:
        return '🟡 YELLOW', factors, f'{red_count}因子警告'
    else:
        return '🟢 GREEN', factors, '全因子正常'

zone_icon, zone_factors, zone_desc = calc_risk_zone(twii_rsi, vix, wti_val, pos_rsis)
print(f'Risk Zone: {zone_icon} {zone_desc}')
for k, v in zone_factors.items():
    print(f'  {k}: {"OK" if v else "FAIL"}')