# -*- coding: utf-8 -*-
"""
ray_minimax_token.py — MiniMax API Token 測試
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests

TOKEN = os.environ.get('MINIMAX_TOKEN', 'sk-cp-d1DZZxzGpsijgC4bJaTl6_mrDJp376z9iwXyRnXRq8wYZOXBKRqFL2YVSE6nVwJ0yi14yjhh6fPCwvtLT5J53KNdfLMSJgLIjfcCqTHpja08L58oTe0wztg')

print("=== MiniMax API Token 測試 ===")
print()
print(f"Token: {TOKEN[:15]}...{TOKEN[-10:]}")
print()

# 測試不同端點
endpoints = [
    ('GET', 'https://api.minimax.chat/v1/models', None),
    ('POST', 'https://api.minimax.chat/v1/text/chatcompletion_pro', {'model': 'MiniMax-Text-01', 'messages': [{'role': 'user', 'content': 'hi'}]}),
]

for method, url, json_data in endpoints:
    print(f"測試: {method} {url}")
    try:
        if method == 'GET':
            resp = requests.get(url, headers={'Authorization': f'Bearer {TOKEN}'}, timeout=10)
        else:
            resp = requests.post(url, headers={'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}, json=json_data, timeout=10)
        print(f"  Status: {resp.status_code}")
        print(f"  Response: {resp.text[:200]}")
    except Exception as e:
        print(f"  Error: {e}")
    print()

print("=== 測試完成 ===")