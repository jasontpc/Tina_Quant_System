# -*- coding: utf-8 -*-
import sys, requests
sys.stdout.reconfigure(encoding='utf-8')

headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    'Accept-Language': 'ko-KR,ko;q=0.9',
}

urls = [
    'http://m.shinsegae.cn/m/store/busan-centum/floor.do',
    'http://m.shinsegae.cn/m/store/busan-centum/guide/floor.do',
    'http://m.shinsegae.cn/m/shopping/BUSAN_CENTUM/guide/floor.do',
    'http://m.shinsegae.cn/m/shopping/BUSAN_CENTUM/storeInfo.do',
]

for url in urls:
    try:
        r = requests.get(url, headers=headers, timeout=10, allow_redirects=False)
        loc = r.headers.get('location', '')
        print(f'{r.status_code} [{len(r.text)}] loc={loc[:50]} | {url}')
        if r.status_code == 200 and len(r.text) > 1000:
            print('  Content preview:', r.text[:300])
    except Exception as e:
        print(f'ERR {url}: {e}')