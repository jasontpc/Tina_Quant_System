import requests, sys
sys.stdout.reconfigure(encoding='utf-8')

TAVILY_KEY = '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'
url = 'https://api.tavily.com/search'

queries = [
    '台股 分析 2026-05',
    'Taiwan stock market outlook May 2026',
    'Taiwan semiconductor AI stocks May 2026',
]

print('=== Tavily TW Stock Trends ===')
for q in queries:
    try:
        r = requests.post(url, json={'api_key': TAVILY_KEY, 'query': q, 'max_results': 5}, timeout=15)
        d = r.json()
        results = d.get('results', [])
        print(f'Query: {q}')
        for item in results[:3]:
            title = item.get('title', '')[:70]
            print(f'  {title}')
        print()
    except Exception as e:
        print(f'ERR: {e}')
