import requests, re, json

def extract_json(raw_text):
    """Extract JSON from ray-v3.5 response, stripping thinking blocks."""
    # Step 1: Remove thinking blocks
    text = re.sub(r'<\|think\|>.*?<\|/think\|>', '', raw_text, flags=re.DOTALL)
    text = re.sub(r'<think>.*?', '', text, flags=re.DOTALL)
    # Step 2: Find first { and last }
    if '{' in text:
        start = text.index('{')
        end = text.rindex('}') + 1
        return json.loads(text[start:end])
    return None

# Final verification
print("=== ray-v3.5 Final Verification ===")
resp = requests.post('http://localhost:11434/api/generate', json={
    'model': 'ray-v3.5',
    'prompt': 'TSLA 245 RSI65 VIX18. JSON: {action,confidence,reason}',
    'stream': False,
    'options': {'num_predict': 400, 'temperature': 0.3}
}, timeout=30)

raw = resp.json().get('response', '')
result = extract_json(raw)

if result:
    print(f"✅ Action: {result.get('action','?')}")
    print(f"✅ Confidence: {result.get('confidence','?')}")
    print(f"✅ Reason: {result.get('reason','?')[:80]}...")
else:
    print("❌ No JSON extracted")
    print("Raw:", raw[:300])