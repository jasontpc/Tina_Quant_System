import requests, json

# Quick connectivity test
try:
    r = requests.post("http://localhost:11434/api/chat", json={
        "model": "ray-v1",
        "messages": [{"role": "user", "content": "hi"}],
        "stream": False,
        "options": {"num_predict": 10}
    }, timeout=15)
    print("ray-v1 OK:", r.json()["message"]["content"][:50])
except Exception as e:
    print("ray-v1 FAIL:", e)

try:
    r = requests.post("http://localhost:11434/api/chat", json={
        "model": "ray-deep-v1",
        "messages": [{"role": "user", "content": "hi"}],
        "stream": False,
        "options": {"num_predict": 10}
    }, timeout=30)
    print("ray-deep-v1 OK:", r.json()["message"]["content"][:50])
except Exception as e:
    print("ray-deep-v1 FAIL:", e)