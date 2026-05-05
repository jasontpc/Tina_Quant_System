# -*- coding: utf-8 -*-
import sys, requests, json
sys.stdout.reconfigure(encoding='utf-8')

# Try to find Shinsegae API
headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'ko-KR,ko;q=0.9',
    'Referer': 'http://m.shinsegae.cn/m/',
    'Origin': 'http://m.shinsegae.cn',
}

# Try different API patterns
test_urls = [
    'https://www.shinsegae.com/store/BUSAN_CENTUM/floor.do',
    'https://www.shinsegae.com/store/busan-centum/floor.do',
    'https://www.shinsegae.com/inter家的/shopping/BUSAN_CENTUM/guide/floor.do',
]

for url in test_urls:
    try:
        r = requests.get(url, headers=headers, timeout=5)
        print(f'Status: {r.status_code}, Len: {len(r.text)}, URL: {url}')
        if r.status_code == 200 and len(r.text) > 500:
            print('Content:', r.text[:300])
    except Exception as e:
        print(f'ERR: {e}')

# Also try with session
session = requests.Session()
session.headers.update(headers)

# Try to get main page and extract links
print('\n--- Trying main page ---')
try:
    r = session.get('http://m.shinsegae.cn/m/', timeout=10)
    print(f'Status: {r.status_code}, Final URL: {r.url}')
    print(f'History: {r.history}')
    if r.status_code == 200:
        print('Content:', r.text[:500])
except Exception as e:
    print(f'ERR: {e}')