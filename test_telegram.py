"""Test _get_secret logic with simulated Cloud secrets behavior."""
import json, re

def _get_secret_simulated(key, default=""):
    """Replicate the actual _get_secret from streamlit_tw_stock.py."""
    # Simulate: st.secrets['tg_bot_token'] = {'tg_bot_token': '...'} on Cloud
    st_secrets_fake = {'tg_bot_token': '8614615741:AAHEMV6daIzF6J_MFUAm8KkhJYtOGVOM14Q'}
    raw = st_secrets_fake.get(key, default)
    if isinstance(raw, dict):
        inner = raw.get(key, default)
        if isinstance(inner, str):
            return inner if inner else default
        return default
    if isinstance(raw, str):
        s = raw.strip()
        if s.startswith("{") and s.endswith("}"):
            try:
                parsed = json.loads(s)
                if isinstance(parsed, dict):
                    inner = parsed.get(key, default)
                    if isinstance(inner, str) and inner:
                        return inner
            except:
                pass
        return s if s else default
    return default

token = _get_secret_simulated("tg_bot_token", "")
print(f"Token length: {len(token)}")
print(f"Token prefix: {token[:20]}")
print(f"Contains colon: {':' in token}")

# Now simulate push_telegram token extraction
token_raw = token
if not isinstance(token_raw, str) or not token_raw or ':' not in str(token_raw):
    print("TAKEN: fallback branch (broken token)")
    token_str = str(token_raw).strip()
    if token_str.startswith('{') and ':' in token_str:
        m = re.search(r'([0-9]+:[A-Za-z0-9_-]+)', token_str)
        if m:
            token_str = m.group(1)
    if not token_str or ':' not in token_str:
        print(f"Invalid token: {repr(token_raw)[:50]}")
    token_clean = token_str
else:
    token_clean = token_raw.strip()
    print(f"TAKEN: clean branch (token ok)")
print(f"Final token: {token_clean[:30]}")

url = f'https://api.telegram.org/bot{token_clean}/sendMessage'
print(f"URL: {url[:80]}")