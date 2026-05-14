import json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def check_file(path):
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            raw = f.read()
        data = json.loads(raw)
        return data, None
    except Exception as e:
        return None, str(e)

files = [
    (r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\stores\backtest_report.json', 'stores/backtest_report.json'),
    (r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\nana\reports\nana_backtest_report.json', 'nana_backtest_report.json'),
    (r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\maggy\reports\full_backtest.json', 'maggy_full_backtest.json'),
    (r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\ray\reports\backtest_report.json', 'ray_backtest_report.json'),
    (r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\nana\archive_json\nana_backtest_learnings.json', 'nana_backtest_learnings.json'),
    (r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\backtest_results.json', 'data/backtest_results.json'),
    (r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\nana_backtest_results.json', 'data/nana_backtest_results.json'),
]

for path, name in files:
    print(f'=== {name} ===')
    data, err = check_file(path)
    if err:
        print(f'ERROR: {err}')
        print()
        continue

    if isinstance(data, dict):
        keys = list(data.keys())[:15]
        print(f'Type: dict, Keys: {keys}')
        # Try to find performance
        for k in ['performance', 'stats', 'summary']:
            if k in data:
                print(f'  {k}: {data[k]}')
        # Try trades count
        for k in ['total_trades', 'trades', 'n']:
            if k in data:
                v = data[k]
                if isinstance(v, list):
                    print(f'  {k}: {len(v)} items')
                else:
                    print(f'  {k}: {v}')
    elif isinstance(data, list):
        print(f'Type: list, len={len(data)}')
        if data:
            first = data[0]
            if isinstance(first, dict):
                print(f'  First item keys: {list(first.keys())[:10]}')
                # Try to get stats
                total = len(data)
                pcts = [t.get('pnl_pct', t.get('return', None)) for t in data[:50] if isinstance(t, dict)]
                pcts = [p for p in pcts if p is not None]
                if pcts:
                    wins = sum(1 for p in pcts if p > 0)
                    print(f'  Sample WR: {wins/len(pcts)*100:.1f}% ({wins}/{len(pcts)}), avg: {sum(pcts)/len(pcts):.3f}')
    print()