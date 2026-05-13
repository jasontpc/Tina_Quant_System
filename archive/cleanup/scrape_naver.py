# -*- coding: utf-8 -*-
"""Naver Place Scraper for 13067134"""
import requests, re, json, sys
sys.stdout.reconfigure(encoding='utf-8')

url = 'https://m.place.naver.com/place/13067134/home'
headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15',
    'Accept-Language': 'ko-KR,ko;q=0.9',
    'Accept': 'text/html,application/xhtml+xml'
}

print(f'Fetching: {url}')
r = requests.get(url, headers=headers, timeout=15)
print(f'Status: {r.status_code}')
text = r.text
print(f'Length: {len(text)}')

# Extract JSON data from __NEXT_DATA__ or similar
next_data = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', text, re.DOTALL)
if next_data:
    try:
        data = json.loads(next_data.group(1))
        print('NEXT_DATA found, keys:', list(data.keys())[:5])
    except:
        pass

# Try to find business info in meta tags
metas = re.findall(r'<meta[^>]+content="([^"]+)"[^>]*>', text)
for m in metas[:20]:
    if any(k in m for k in ['신세계', '화장품', '매장', '제품', '주소']):
        print(f'Meta: {m[:100]}')

# Try JSON-LD
ld_json = re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.DOTALL)
if ld_json:
    try:
        ld = json.loads(ld_json.group(1))
        print('JSON-LD:', json.dumps(ld, ensure_ascii=False, indent=2)[:1000])
    except:
        pass

# Extract key phrases
patterns = [
    r'"name"\s*:\s*"([^"]+)"',
    r'"category"\s*:\s*"([^"]+)"',
    r'"address"\s*:\s*"([^"]+)"',
    r'roadAddress["\s:]+([^\s",}+]+)',
    r'lat\s*:\s*([0-9.]+)',
    r'lng\s*:\s*([0-9.]+)',
]
for p in patterns:
    matches = re.findall(p, text)
    if matches:
        print(f'Pattern {p[:30]}: {matches[:5]}')

print('\n--- Raw text sample ---')
print(text[:2000])