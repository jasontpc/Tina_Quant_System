# -*- coding: utf-8 -*-
"""
Gemini Embedding Demo
使用官方 google-genai SDK
"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

API_KEY = os.environ.get("GEMINI_API_KEY", "")
if not API_KEY:
    cfg_path = os.path.expanduser("~/.openclaw/openclaw.json")
    if os.path.exists(cfg_path):
        with open(cfg_path) as f:
            import json
            cfg = json.load(f)
        API_KEY = cfg.get("env", {}).get("GEMINI_API_KEY", "")

if not API_KEY:
    print("GEMINI_API_KEY not found")
    sys.exit(1)

print(f"Key OK: {API_KEY[:4]}...")

from google.genai import Client

client = Client(api_key=API_KEY)

result = client.models.embed_content(
    model="gemini-embedding-2",
    contents="What is the meaning of life?"
)

vec = result.embeddings
print(f"Embedding dim: {len(vec.values[0].values)}")
print(f"First 5 values: {vec.values[0].values[:5]}")
print("OK")