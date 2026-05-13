import requests, re, json

print("=== Final Test: Extract clean JSON from ray-v3.5 ===")
resp = requests.post('http://localhost:11434/api/generate', json={
    'model': 'ray-v3.5',
    'prompt': 'TSLA 245 RSI65 VIX18. JSON: {action,confidence,reason}',
    'stream': False,
    'options': {'num_predict': 400, 'temperature': 0.3}
}, timeout=30)

raw = resp.json().get('response', '')
print(f"Raw length: {len(raw)}")
print(f"Raw content:\n{raw}\n")

# Find the JSON block
match = re.search(r'\{[\s\S]+?"reason"[^}]+\}', raw)
if match:
    try:
        data = json.loads(match.group())
        print("Parsed JSON:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Parse error: {e}")
        print("Matched text:", match.group()[:200])
else:
    print("No JSON found")
    print("Last 400 chars:", raw[-400:])