# -*- coding: utf-8 -*-
import json
from datetime import datetime

with open('autonomous_trades.json', encoding='utf-8') as f:
    d = json.load(f)

trades = d.get('trades', [])
bh = [t for t in trades if t.get('type') == 'BUY&HOLD']
dca = [t for t in trades if t.get('type') == 'DCA']

di = {}
for t in dca:
    eid = t['etf_id']
    if eid not in di:
        di[eid] = {'count': 0, 'amount': 0, 'multiplier': 0}
    di[eid]['count'] += 1
    di[eid]['amount'] += t.get('amount', 0)
    di[eid]['multiplier'] = t.get('kline_multiplier', 1.0)

def grade(m):
    if m >= 2.0: return 'S'
    elif m >= 1.5: return 'A'
    elif m >= 1.2: return 'B'
    elif m >= 1.0: return 'C'
    else: return 'D'

def label(g):
    return {'S':'極佳買點','A':'良好買點','B':'普通','C':'觀望','D':'離譜'}[g]

sc = {'S':0,'A':0,'B':0,'C':0,'D':0}
for v in di.values():
    sc[grade(v['multiplier'])] += 1

print('=== DCA Score 評估報告 ===')
print('時間:', d.get('last_update','未知'))
print('總記錄:', len(trades), '(BH=', len(bh), ', DCA=', len(dca), ')')
print()
print('ETF      倍數  評分  月預算')
print('-' * 45)
for eid, v in sorted(di.items(), key=lambda x: x[1]['multiplier'], reverse=True):
    g = grade(v['multiplier'])
    print(f'{eid:<8}  x{v["multiplier"]:<4.1f}  {g}    NT${v["amount"]:,}/月')

print()
print('評分分佈:')
for g in ['S','A','B','C','D']:
    print(f'  {g} ({label(g)}): {sc[g]} 檔')

print()
total = sum(v['amount'] for v in di.values())
print(f'DCA 月總預算: NT${total:,}')
print(f'BH 本輪進場: NT$100,000 (2檔 HYBRID)')
favorable = sc['S'] + sc['A']
print(f'極佳/良好買點: {favorable} 檔')