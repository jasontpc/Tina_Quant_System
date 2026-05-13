# -*- coding: utf-8 -*-
import json, requests, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

cfg = json.load(open(r"C:\Users\USER\.openclaw\openclaw.json", encoding='utf-8'))
API_KEY = cfg.get("env", {}).get("GEMINI_API_KEY", "")
print(f"Key: {API_KEY[:8]}..." if API_KEY else "No key found")

# Check model list (free endpoint)
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
resp = requests.get(url, timeout=10)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    models = data.get("models", [])
    emb_models = [m["name"] for m in models if "embedding" in m["name"].lower()]
    print(f"Embedding models: {emb_models}")
    print(f"Total models: {len(models)}")
else:
    print(resp.text[:300])