import urllib.request, json

url = "https://ollama.com/api/tags"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=10) as resp:
    data = json.loads(resp.read().decode())

qwen = [m['name'] for m in data.get('models', []) if 'qwen' in m['name'].lower()]
for q in qwen:
    mb = next((m for m in data['models'] if m['name'] == q), {}).get('size', 0) // (1024**2)
    print(f"{q} ({mb:.0f} MB)")
