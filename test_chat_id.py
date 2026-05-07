# Test chat_id handling for Streamlit Cloud
import json

def validate_chat_id(raw):
    """Robust chat_id extraction from potentially broken st.secrets"""
    if raw is None:
        return '1616824689'  # fallback

    # If already a clean string
    if isinstance(raw, str) and raw.isdigit():
        return raw

    # If it's a dict (TOML section style)
    if isinstance(raw, dict):
        raw = raw.get('chat_id', raw.get('tg_chat_id', '1616824689'))

    # If it's a string that looks like a dict (broken JSON)
    if isinstance(raw, str) and raw.startswith('{') and 'chat_id' in raw:
        try:
            parsed = json.loads(raw.replace("'", '"'))
            raw = parsed.get('chat_id', parsed.get('tg_chat_id', raw))
        except:
            pass

    # Remove any remaining wrappers
    while isinstance(raw, (dict, list)):
        if isinstance(raw, dict):
            raw = raw.get('chat_id', raw.get('tg_chat_id',
                              list(raw.values())[0] if raw else '1616824689'))
        else:
            raw = raw[0] if raw else '1616824689'

    return str(raw)

# Test cases
test_cases = [
    '1616824689',  # correct
    {'tg_chat_id': '1616824689'},  # TOML style
    {'chat_id': '1616824689'},  # flat style
    1616824689,  # int
]

for tc in test_cases:
    result = validate_chat_id(tc)
    print(f'validate_chat_id({repr(tc)}) = {repr(result)}')