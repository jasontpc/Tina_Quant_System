import json
with open('teams/leadtrades/leos/leos_trades.json', encoding='utf-8') as f:
    data = json.load(f)
print('Stats:', data['stats'])
us_open = [t for t in data['trades'] if t.get('market') == 'US' and t.get('status') == 'open']
print('US open:', len(us_open))
for t in us_open[:5]:
    print(f'  {t["symbol"]}: entry={t.get("entry_price")}, current={t.get("current_price", "N/A")}, pnl_pct={t.get("pnl_pct", "N/A")}')
