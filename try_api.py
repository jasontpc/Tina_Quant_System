# -*- coding: utf-8 -*-
import sys, requests, re
sys.stdout.reconfigure(encoding='utf-8')

# Try API endpoints directly
headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'ko-KR',
}

# Try Shinsegae API
api_urls = [
    'https://www.shinsegae.com/api/store/busan-centum/floor',
    'https://www.shinsegae.com/api/store/busan-centum/brand',
    'https://www.shinsegae.com/api/shopping/BUSAN_CENTUM/floor',
    'https://www.shinsegae.com/inter家的/api/store/13067134',
]

for url in api_urls:
    try:
        r = requests.get(url, headers=headers, timeout=5)
        print(f'{r.status_code} [{len(r.text)}] {url}')
        if r.status_code == 200 and len(r.text) > 100:
            print(f'  Content: {r.text[:300]}')
    except Exception as e:
        print(f'ERR {url}: {e}')

# Try the m.shinsegae.cn API
m_urls = [
    'http://m.shinsegae.cn/m/store/busan-centum',
    'http://m.shinsegae.cn/m/store/busan-centum/floor',
    'http://m.shinsegae.cn/m/store/list?storeCode=BUSAN_CENTUM',
]

print()
for url in m_urls:
    try:
        r = requests.get(url, headers=headers, timeout=5, allow_redirects=True)
        print(f'{r.status_code} [{len(r.text)}] {r.url[:80]}')
        if r.status_code == 200 and len(r.text) > 500:
            print(f'  Content: {r.text[:500]}')
    except Exception as e:
        print(f'ERR {url}: {e}')