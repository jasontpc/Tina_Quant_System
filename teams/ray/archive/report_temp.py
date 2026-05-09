import json
with open(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\ray\autonomous_trades.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
trades = data['trades']
dca = [t for t in trades if t.get('type') == 'DCA']
bh = [t for t in trades if t.get('type') == 'BUY&HOLD']
dates = sorted(set(t['timestamp'][:10] for t in trades))
total_dca = sum(t.get('amount',0) for t in dca)
total_bh = sum(t.get('amount',0) for t in bh)
print('=== Ray 自主交易模擬報告 ===')
print(f'報告時間: 2026-04-25 07:49')
print(f'總交易筆數: {len(trades)} (含重複執行)')
print(f'DCA 執行: {len(dca)} 筆')
print(f'BH 建倉: {len(bh)} 筆')
print(f'資料期間: {dates[0]} ~ {dates[-1]}')
print(f'DCA 投入: NT${total_dca:,.0f}')
print(f'BH 投入: NT${total_bh:,.0f}')
print()
etfs = {}
for t in trades:
    e = t.get('etf_id','?')
    if e not in etfs:
        etfs[e] = {'dca':0,'bh':0,'count':0}
    etfs[e]['count'] += 1
    if t.get('type') == 'DCA':
        etfs[e]['dca'] += t.get('amount',0)
    elif t.get('type') == 'BUY&HOLD':
        etfs[e]['bh'] += t.get('amount',0)
print('=== ETF 執行摘要 ===')
for e, v in sorted(etfs.items()):
    print(f'{e}: DCA NT${v["dca"]:,.0f} | BH NT${v["bh"]:,.0f} | {v["count"]}次')