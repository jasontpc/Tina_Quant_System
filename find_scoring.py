# -*- coding: utf-8 -*-
"""Find 1000pt scoring logic in streamlit"""
import re

with open(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\streamlit_tw_stock.py', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')

# Find scoring/evaluation related functions and sections
scoring_keywords = ['score', '評分', '1000', 'total', 'weight', 'rating', 'rank', 'sort']

results = []
for i, line in enumerate(lines, 1):
    low = line.lower()
    if any(k in low for k in ['score', '評分', '1000', 'total_score', 'calc_score']):
        results.append(f'{i}: {line[:120]}')

print(f'Total lines: {len(lines)}')
print(f'Scoring-related: {len(results)}')
for r in results[:50]:
    print(r)