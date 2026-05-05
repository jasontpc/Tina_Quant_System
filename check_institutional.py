import sys, os, json
sys.path.insert(0, r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\skills')

try:
    from fetch_institutional_finmind import fetch_institutional_summary
    result = fetch_institutional_summary()
    if result:
        print(result)
except Exception as e:
    print('FinMind API error:', e)

# Fallback: read cached data
cache = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\nana\market_scan_report.json'
if os.path.exists(cache):
    with open(cache, encoding='utf-8') as f:
        d = json.load(f)
    print(json.dumps(d, ensure_ascii=False, indent=2))
else:
    print('No cache available')