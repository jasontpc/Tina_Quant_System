import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests

# Test MiniMax
MINIMAX_TOKEN = 'sk-cp-d1DZZxzGpsijgC4bJaTl6_mrDJp376z9iwXyRnXRq8wYZOXBKRqFL2YVSE6nVwJ0yi14yjhh6fPCwvtLT5J53KNdfLMSJgLIjfcCqTHpja08L58oTe0wztg'

print("Test MiniMax...")
resp = requests.post(
    'https://api.minimax.chat/v1/text/chatcompletion_pro',
    headers={'Authorization': f'Bearer {MINIMAX_TOKEN}'},
    json={
        'model': 'MiniMax-Text-01',
        'messages': [{'role': 'user', 'content': 'Say hello in 3 words'}],
        'max_tokens': 100
    },
    timeout=30
)
print('Status:', resp.status_code)
print('Response:', resp.text[:500])