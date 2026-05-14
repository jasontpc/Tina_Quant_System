import json

# Check sim_trades.json (largest file, likely real backtest data)
sim = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leo\reports\sim_trades.json'
with open(sim, 'r', encoding='utf-8') as f:
    data = json.load(f)

print('=== sim_trades.json ===')
if isinstance(data, dict):
    print('Keys:', list(data.keys())[:10])
    for k in list(data.keys())[:3]:
        v = data[k]
        if isinstance(v, list):
            print(f'  {k}: {len(v)} items')
        elif isinstance(v, dict):
            print(f'  {k}: dict with keys {list(v.keys())[:5]}')
        else:
            print(f'  {k}: {v}')
elif isinstance(data, list):
    print(f'List: {len(data)} items')
    if data:
        print('Sample:', data[0])

# Check leo_best_params
params = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leo\reports\leo_best_params.json'
with open(params, 'r', encoding='utf-8') as f:
    p = json.load(f)
print('\n=== leo_best_params.json ===')
print(p)

# Check leo_evolutions
evo = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leo\reports\leo_evolutions.json'
with open(evo, 'r', encoding='utf-8') as f:
    e = json.load(f)
print('\n=== leo_evolutions.json ===')
print(json.dumps(e, ensure_ascii=False, indent=2)[:1000])