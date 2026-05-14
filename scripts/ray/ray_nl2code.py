# -*- coding: utf-8 -*-
"""
ray_nl2code.py — JSON 提取包裝器 for Qwen3.5-4B (ray-v3.5)
功能：自動去除 thinking block，提取乾淨 JSON
"""

import re, json
from typing import Optional

def extract_json(raw_text: str) -> Optional[dict]:
    if not raw_text:
        return None
    # Remove thinking blocks
    text = re.sub(r'<\|think\|>.*?<\|/think\|>', '', raw_text, flags=re.DOTALL)
    text = re.sub(r'<think>.*?<\|/', '', text, flags=re.DOTALL)
    text = text.strip()
    if '{' not in text:
        return None
    start = text.index('{')
    last_brace = text.rindex('}')
    json_str = text[start:last_brace+1]
    try:
        return json.loads(json_str)
    except:
        try:
            # Fix unquoted keys: {action:...} -> {"action":...}
            fixed = re.sub(r'([{,])\s*(\w+):', r'\1"\2":', json_str)
            return json.loads(fixed)
        except:
            return None

def parse_ray_response(raw: str) -> dict:
    result = extract_json(raw)
    if result:
        return {
            'commander': 'ray-v3.5',
            'status': 'online',
            'data': result,
            'raw_length': len(raw)
        }
    return {
        'commander': 'ray-v3.5',
        'status': 'parse_failed',
        'raw': raw[:300],
        'raw_length': len(raw)
    }

def call_ray_v35(prompt: str, temperature: float = 0.3, num_predict: int = 300) -> dict:
    """標準化呼叫 ray-v3.5"""
    import requests
    resp = requests.post('http://localhost:11434/api/generate', json={
        'model': 'ray-v3.5',
        'prompt': prompt,
        'stream': False,
        'options': {'temperature': temperature, 'num_predict': num_predict}
    }, timeout=30)
    raw = resp.json().get('response', '')
    return parse_ray_response(raw)

if __name__ == '__main__':
    import requests
    print("=== ray-v3.5 JSON 提取測試 ===")
    resp = requests.post('http://localhost:11434/api/generate', json={
        'model': 'ray-v3.5',
        'prompt': 'TSLA 245 RSI65 VIX18. JSON: {action,confidence,reason}',
        'stream': False,
        'options': {'num_predict': 400, 'temperature': 0.3}
    }, timeout=30)
    raw = resp.json().get('response', '')
    print(f"Raw length: {len(raw)}")
    result = parse_ray_response(raw)
    if result.get('data'):
        d = result['data']
        action_key = 'action' if 'action' in d else 'a'
        conf_key = 'confidence' if 'confidence' in d else 'c'
        reason_key = 'reason' if 'reason' in d else 'r'
        print(f"\n✅ Action: {d.get(action_key, '?')}")
        print(f"✅ Confidence: {d.get(conf_key, '?')}")
        reason = d.get(reason_key, d.get('reason', ''))
        if isinstance(reason, str):
            print(f"✅ Reason: {reason[:80]}...")
        else:
            print(f"✅ Reason: {reason}")
    else:
        print(f"❌ Parse failed")
        print(f"Raw[:200]: {raw[:200]}")