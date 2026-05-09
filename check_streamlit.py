# -*- coding: utf-8 -*-
with open('streamlit_tw_stock.py', encoding='utf-8') as f:
    src = f.read()

markers = [
    ('v3.0 scoring comment', '# ── Tina Brain v3.0 Scoring', 1),
    ('v3.0 formula', 'score = rsi_s + macd_s + trend_s', 1),
    ('score_breakdown', "'score_breakdown'", 1),
    ('tier A threshold', 'score >= 800', 1),
    ('Rel.Str display', 'Rel.Str', 2),
    ('Funda display', 'Funda', 2),
    ('KD merged', "'kd': kd_s", 1),
    ('rel_str field', "'rel_str': rs_s", 1),
    ('funda field', "'funda': f_s", 1),
    ('TREND section', '# ── Trend: 150pts', 1),
]

all_ok = True
for name, marker, expected in markers:
    count = src.count(marker)
    status = 'OK' if count >= expected else 'MISSING'
    if status == 'MISSING':
        all_ok = False
    print(f'{status}: {name} = {count} (expected >={expected})')

print()
if all_ok:
    print('All v3.0 markers confirmed!')
else:
    print('Some markers missing!')
