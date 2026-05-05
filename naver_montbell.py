# -*- coding: utf-8 -*-
"""Try Naver Shopping API for Montbell at Shinsegae Centum City"""
import sys, requests, re
sys.stdout.reconfigure(encoding='utf-8')

headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'ko-KR,ko;q=0.9',
}

# Try Naver Shopping search for Montbell at Shinsegae Centum
search_urls = [
    'https://search.shopping.naver.com/search/all?query=몽벨%20신세계센텀',
    'https://search.shopping.naver.com/search/all?query=montbell%20센텀',
    'https://m.shopping.naver.com/search?query=montbell%20신세계',
]

for url in search_urls:
    print(f'\n--- {url[:80]} ---')
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f'Status: {r.status_code}, Len: {len(r.text)}')
        if r.status_code == 200 and len(r.text) > 1000:
            text = r.text
            # Look for store references
            if '센텀' in text or '신세계' in text:
                print('Found Centum City reference!')
                # Extract product names
                products = re.findall(r'"productName"\s*:\s*"([^"]+)"', text)
                for p in products[:10]:
                    print(f'  Product: {p}')
    except Exception as e:
        print(f'ERR: {e}')

# Try Naver Place search for Montbell
print('\n\n--- Naver Place Montbell ---')
place_urls = [
    'https://m.place.naver.com/place/search?query=montbell%20센텀',
    'https://m.place.naver.com/place/search?query=몽벨%20부산',
]
for url in place_urls:
    print(f'\n{url[:80]}')
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f'Status: {r.status_code}, Len: {len(r.text)}')
    except Exception as e:
        print(f'ERR: {e}')