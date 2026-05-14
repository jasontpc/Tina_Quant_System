# -*- coding: utf-8 -*-
"""
Step E: 7B 預熱腳本
每日 07:50 執行（美股开盘前 40 分鐘）
預熱 ray-deep-v1，避免冷啟動延遲
"""

import requests, time, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_URL = "http://localhost:11434/api/chat"
MODEL = "ray-deep-v1"

print("=== 7B Warmup Script ===")
print(f"Model: {MODEL}")
print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print()

# 預熱請求
print("Warming up ray-deep-v1...")
t0 = time.time()
try:
    resp = requests.post(BASE_URL, json={
        "model": MODEL,
        "messages": [{"role": "user", "content": "OK"}],
        "stream": False
    }, timeout=300)
    elapsed = time.time() - t0
    print(f"Warmup done in {elapsed:.1f}s")
    print(f"Response: {resp.json().get('message', {}).get('content', '')[:50]}")
except Exception as e:
    print(f"Warmup error: {e}")
    print("Daily run may experience cold start delays")

# 7B 快取後應該 < 5s 回應
# 預熱完成後，Ray Tina Daily 的 7B 分析將在 2-5s 內完成
print()
print("=== Warmup Complete ===")