# -*- coding: utf-8 -*-
"""Verify streamlit v3.0 scoring patches"""
from pathlib import Path

file = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\streamlit_tw_stock.py')
src = file.read_text(encoding='utf-8')

checks = [
    ('Tina Brain v3.0 Scoring', 'v3.0 scoring comment'),
    ('RSI: 200', 'RSI section'),
    ('TREND: 150', 'TREND section'),
    ('trend_s = 0', 'trend variable init'),
    ('rs_s = 0', 'rel strength var'),
    ('f_s = 0', 'funda var'),
    ('score = rsi_s + macd_s + trend_s + kd_s + bb_s + rs_s + vol_s + f_s', 'v3.0 formula'),
    ('tier = "A"', 'new tier A'),
    ('score >= 800', 'new tier threshold'),
    ('score_breakdown', 'score breakdown'),
    ('Rel.Str', 'rel strength display'),
    ('Funda', 'funda display'),
    ("'kd': kd_s", 'kd merged field'),
    ("'rel_str': rs_s", 'rel_str field'),
    ("'funda': f_s", 'funda field'),
]

for text, label in checks:
    if text in src:
        print(f'OK: {label}')
    else:
        print(f'MISSING: {label}')

print('\nDone')