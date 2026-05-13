# -*- coding: utf-8 -*-

"""

Tina Scanner v3.0 - TW+US Stock Analysis | 1000 Tech Scoring + Institutional Data + Telegram

"""

import os

import sqlite3

import subprocess

import streamlit as st

import yfinance as yf

import numpy as np

import pandas as pd

import time

import urllib.request

import json

from datetime import datetime, timedelta

from pathlib import Path

from concurrent.futures import ThreadPoolExecutor, as_completed

import logging

from logging.handlers import RotatingFileHandler

# ── Debug Log Setup ──────────────────────────────────────────────────────
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
_log = logging.getLogger("tina_scanner")
_log.setLevel(logging.INFO)
if not _log.handlers:
    _h = RotatingFileHandler(LOG_DIR / "streamlit_debug.log", maxBytes=5*1024*1024, backupCount=3, encoding="utf-8")
    _h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"))
    _log.addHandler(_h)
    _log.info("=== Tina Scanner 啟動 ===")

# ── Shioaji Real-Time Data (優先 > yfinance) ────────────────────────
_SHIOAJI_AVAILABLE = False
try:
    import shioaji as sj
    _SHIOAJI_AVAILABLE = True
except ImportError:
    _SHIOAJI_AVAILABLE = False
    _log.warning("[Shioaji] Not available in this environment, using yfinance fallback")
_SJ_API = None
_SJ_READY = False

import threading as _threading
_SJ_LOGIN_LOCK = _threading.Lock()

def _get_shioaji_api():
    global _SJ_API, _SJ_READY
    if not _SHIOAJI_AVAILABLE:
        return None
    if _SJ_READY:
        return _SJ_API
    with _SJ_LOGIN_LOCK:
        if _SJ_READY:
            return _SJ_API
        try:
            _SJ_API = sj.Shioaji(simulation=False)
            _SJ_API.login(
                api_key=os.getenv("SJ_API_KEY", "3r6UGMUX7bnxhnbrZ92sSseGVzL3C63kkBxH3WkAPsgW"),
                secret_key=os.getenv("SJ_SECRET_KEY", "FCcefW9iatHvYyp3XgSYVM1VhdmZMawjQ49Mzp97WPBF")
            )
            _SJ_API.activate_ca(
                ca_path=os.getenv("SJ_CA_PATH", None),
                ca_passwd=os.getenv("SJ_CA_PASSWD", ""),
                subscription=Sj.Subscription("FK,OPT")
            )
            _SJ_READY = True
            _log.info(f"[Shioaji] Connected: {_SJ_API.stock_account.account_id}")
        except Exception as e:
            _SJ_READY = False
            _log.warning(f"[Shioaji] Connection failed: {e}")
        return _SJ_API

def sj_get_quote(code):
    try:
        api = _get_shioaji_api()
        if not api:
            return None
        c = api.Contracts.Stocks[code]
        snap = api.snapshots([c])[0]
        return {'close': float(snap.close), 'open': float(snap.open),
                'high': float(snap.high), 'low': float(snap.low),
                'volume': int(snap.total_volume),
                'change': float(snap.change_price), 'change_rate': float(snap.change_rate)}
    except Exception as e:
        _log.debug(f"[Shioaji] quote error {code}: {e}")
        return None

def sj_get_kbars(code, days=5):
    from datetime import datetime, timedelta
    try:
        api = _get_shioaji_api()
        if not api:
            return None
        c = api.Contracts.Stocks[code]
        end = datetime.now().strftime('%Y-%m-%d')
        start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        kb = api.kbars(c, start=start, end=end)
        return {'ts': kb.ts, 'Open': kb.Open, 'High': kb.High,
                'Low': kb.Low, 'Close': kb.Close, 'Volume': kb.Volume}
    except Exception as e:
        _log.debug(f"[Shioaji] kbars error {code}: {e}")
        return None


def _get_secret(key, default=""):
    """Extract string value from st.secrets TOML dict structure.
    TOML [section] creates st.secrets['section'] = {'section': value}
    so we need .get(key, {}).get(key, default) to unwrap it.
    
    Additionally handles json.loads unwrapping for edge cases where
    st.secrets returns dict-string representations."""
    val = st.secrets.get(key, {})
    if isinstance(val, dict):
        inner = val.get(key, default)
        # Defensive: if inner is STILL a dict (edge case), return default
        if isinstance(inner, dict):
            return default
        return inner if inner else default
    # Handle json-string edge case: st.secrets['key'] = "{'key': 'value'}"
    if isinstance(val, str) and val.startswith('{'):
        try:
            parsed = json.loads(val.replace("'", '"'))
            inner = parsed.get(key, default)
            if isinstance(inner, dict):
                return default
            return inner if inner else default
        except:
            pass
    return val if val else default

def _validate_chat_id(raw):
    """Robust chat_id extraction — handles dict/List/int/all edge cases on Streamlit Cloud.

    Streamlit Cloud st.secrets returns values as Python string repr of dicts,
    e.g. "{'tg_chat_id': '1616824689'}" instead of actual dicts.
    """
    if raw is None:
        return '1616824689'

    # STEP 1: If raw is a string that looks like dict-string repr, parse it first
    if isinstance(raw, str):
        s = raw.strip()
        if s.startswith('{') and 'chat_id' in s:
            try:
                import json
                parsed = json.loads(s.replace("'", '"'))
                if isinstance(parsed, dict):
                    raw = parsed.get('chat_id', parsed.get('tg_chat_id', parsed.get('value', raw)))
            except:
                pass
        # STEP 2: Strip 'telegram:' or 'tg_' prefixes (BEFORE isdigit check!)
        raw = raw.replace('telegram:', '').replace('tg_', '')

    # STEP 3: Unwrap nested dict/List layers
    while isinstance(raw, (dict, list)):
        if isinstance(raw, dict):
            raw = raw.get('chat_id', raw.get('tg_chat_id',
                              list(raw.values())[0] if raw else '1616824689'))
        else:
            raw = raw[0] if raw else '1616824689'

    # STEP 4: Final guard — strip prefixes again after all unwrapping
    if isinstance(raw, str):
        raw = raw.replace('telegram:', '').replace('tg_', '')

    return str(raw) if raw else '1616824689'

def _validate_token(raw):
    """Robust token extraction — rejects truncated/malformed tokens.
    Valid Telegram bot tokens are format: <digits>:<alphanum> (typically 40-50 chars).
    If token is a dict-string repr like "{'tg_bot_token': '...'}", parse it first."""
    if not raw:
        return ''
    raw_str = str(raw).strip()
    # If the token looks like a dict-string repr, parse it
    if raw_str.startswith('{'):
        try:
            import json as _json
            parsed = _json.loads(raw_str.replace("'", '"'))
            if isinstance(parsed, dict):
                raw_str = parsed.get('tg_bot_token', parsed.get('bot_token', parsed.get('value', '')))
        except:
            pass
    # Reject obviously truncated tokens (valid tokens are 40+ chars)
    if len(raw_str) < 20:
        print(f'[TOKEN WARNING] Token truncated ({len(raw_str)} chars): {repr(raw_str[:10])}... expecting 40+ chars')
        return ''  # Force fallback to empty
    return raw_str
# ═══════════════════════════════════════════════════════════
# Streamlit Cloud st.secrets BUG WORKAROUND
# ═══════════════════════════════════════════════════════════
# KNOWN BUG (Streamlit Cloud):
#   st.secrets.get('tg_chat_id') returns Python string repr of dict
#   e.g. "\{'tg_chat_id': '1616824689'\}" instead of \{'tg_chat_id': '1616824689'\}
#   or a DICT \{'tg_chat_id': '1616824689'} with string VALUES
#   or the raw string "\{'tg_chat_id': '1616824689'\}"
#
# SOLUTION: Hard-code known values + validation inside push_telegram()
# This eliminates all st.secrets parsing edge cases for these two known secrets.
# ═══════════════════════════════════════════════════════════

# Known working values (hard-coded as final fallback)
_KNOWN_CHAT_ID = '1616824689'
_KNOWN_BOT_TOKEN = '8614615741:AAHEMV6daIzF6J_MFUAm8KkhJYtOGVOM14Q'

def _try_get_chat_id():
    """Try to get chat_id from st.secrets, return known fallback on any failure."""
    try:
        raw = st.secrets.get('tg_chat_id', st.secrets.get('chat_id', None))
        if raw is None:
            return _KNOWN_CHAT_ID
        raw_type = type(raw).__name__
        # Already a plain digit string
        if isinstance(raw, str) and raw.isdigit():
            return raw
        # AttrDict (Streamlit Cloud custom class) — access via .get() or hasattr
        if hasattr(raw, 'get'):
            v = raw.get('chat_id') or raw.get('tg_chat_id') or raw.get('value')
            if isinstance(v, str) and v.isdigit():
                return v
            # AttrDict may have tg_chat_id as attribute
            if hasattr(raw, 'tg_chat_id') and str(raw.tg_chat_id).isdigit():
                return str(raw.tg_chat_id)
        # Dict with string values (plain dict, not AttrDict)
        if isinstance(raw, dict):
            v = raw.get('chat_id') or raw.get('tg_chat_id') or raw.get('value')
            if isinstance(v, str) and v.isdigit():
                return v
        # String repr of dict
        if isinstance(raw, str) and raw.startswith('{'):
            import json as _json
            try:
                parsed = _json.loads(raw.replace("'", '"'))
                if isinstance(parsed, dict):
                    v = parsed.get('chat_id') or parsed.get('tg_chat_id') or parsed.get('value')
                    if isinstance(v, str) and v.isdigit():
                        return v
            except:
                pass
        # Last resort: try to extract digit string via regex
        import re as _re
        m = _re.search(r'(\d{7,15})', str(raw))
        if m:
            return m.group(1)
        return _KNOWN_CHAT_ID
    except:
        return _KNOWN_CHAT_ID

def _try_get_bot_token():
    """Try to get bot token from st.secrets, return known fallback on any failure."""
    try:
        raw = st.secrets.get('tg_bot_token', st.secrets.get('bot_token', None))
        if raw is None:
            return _KNOWN_BOT_TOKEN
        if isinstance(raw, str) and len(raw) >= 20 and ':' in raw:
            return raw
        if isinstance(raw, dict):
            v = raw.get('tg_bot_token') or raw.get('bot_token') or raw.get('value')
            if isinstance(v, str) and len(v) >= 20 and ':' in v:
                return v
        if isinstance(raw, str) and raw.startswith('{'):
            import json as _json
            try:
                parsed = _json.loads(raw.replace("'", '"'))
                if isinstance(parsed, dict):
                    v = parsed.get('tg_bot_token') or parsed.get('bot_token') or parsed.get('value')
                    if isinstance(v, str) and len(v) >= 20 and ':' in v:
                        return v
            except:
                pass
        import re as _re
        m = _re.search(r'(\d+:[A-Za-z0-9_-]{30,})', str(raw))
        if m:
            return m.group(1)
        return _KNOWN_BOT_TOKEN
    except:
        return _KNOWN_BOT_TOKEN

TELEGRAM_CHAT_ID = _try_get_chat_id()
TELEGRAM_BOT_TOKEN = _try_get_bot_token()




# DEBUG: Log raw st.secrets on Streamlit Cloud (when no local secrets.toml)
_secrets_debug_file = os.path.join(os.path.dirname(__file__), '.streamlit', 'secrets.toml')
if not os.path.exists(_secrets_debug_file):
    import sys as _sys
    _raw_tg_bot = st.secrets.get('tg_bot_token', 'NOT_FOUND')
    _raw_tg_chat = st.secrets.get('tg_chat_id', 'NOT_FOUND')
    print(f'[SECRETS] tg_bot_token raw = {repr(_raw_tg_bot)[:80]}', file=_sys.stderr)
    print(f'[SECRETS] tg_chat_id raw   = {repr(_raw_tg_chat)[:80]}', file=_sys.stderr)
    print(f'[SECRETS] TOKEN after val  = {repr(TELEGRAM_BOT_TOKEN)[:60]}', file=_sys.stderr)
    print(f'[SECRETS] CHAT_ID after val= {repr(TELEGRAM_CHAT_ID)[:60]}', file=_sys.stderr)

def _parse_finmind_token(raw):
    """Parse FinMind token that may come as dict-string repr from Streamlit secrets."""
    if not raw:
        return ''
    raw_str = str(raw).strip()
    if raw_str.startswith('{'):
        try:
            import json as _json
            parsed = _json.loads(raw_str.replace("'", '"'))
            if isinstance(parsed, dict):
                raw_str = parsed.get('finmind_token', parsed.get('token', ''))
        except:
            pass
    return raw_str

FINMIND_TOKEN = _parse_finmind_token(os.getenv("FINMIND_TOKEN") or _get_secret("finmind_token", ""))



import json



def _to_json_safe(obj):

    """Recursively convert any object (including AttrDict/dict subclasses) to plain Python types."""

    if hasattr(obj, '__class__') and obj.__class__.__name__ == 'AttrDict':

        obj = dict(obj)

    if isinstance(obj, dict):

        return {k: _to_json_safe(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple)):

        return [_to_json_safe(x) for x in obj]

    if isinstance(obj, str):

        return obj

    try:

        json.dumps(obj)

        return obj

    except TypeError:

        return str(obj)



def push_telegram(message):
    # Clean and validate token before use — last-resort regex extraction
    import json, re, urllib.parse
    token_raw = TELEGRAM_BOT_TOKEN
    token_str = str(token_raw).strip()
    # If token looks like dict-string repr, do final regex extraction
    if token_str.startswith('{'):
        m = re.search(r'([0-9]+:[A-Za-z0-9_-]{30,})', token_str)
        token_clean = m.group(1) if m else ''
    elif isinstance(token_raw, str) and len(token_str) >= 20 and ':' in token_str:
        token_clean = token_str
    else:
        token_clean = ''
    if not token_clean:
        return False, f'Invalid token: {repr(token_raw)[:50]}'
    # Validate chat_id is a proper string
    chat_id_raw = TELEGRAM_CHAT_ID
    if isinstance(chat_id_raw, dict):
        # This should NOT happen if _validate_chat_id works, but double-check here
        chat_id = chat_id_raw.get('chat_id', chat_id_raw.get('tg_chat_id', '1616824689'))
    elif isinstance(chat_id_raw, str) and chat_id_raw.isdigit():
        chat_id = chat_id_raw
    else:
        chat_id = str(chat_id_raw)

    url = f'https://api.telegram.org/bot{token_clean}/sendMessage'
    safe_msg = str(message) if not isinstance(message, str) else message

    payload = {'chat_id': chat_id, 'text': safe_msg, 'parse_mode': 'Markdown'}
    payload = _to_json_safe(payload)
    data = json.dumps(payload).encode()

    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})

    try:

        with urllib.request.urlopen(req, timeout=10) as resp:

            return True, 'OK'

    except urllib.error.HTTPError as e:

        body = e.read().decode('utf-8', errors='replace')[:200]

        return False, f'HTTP {e.code}: {body}'

    except Exception as e:

        return False, str(e)[:200]



def format_telegram(results, title):

    if not results:

        return ["No results"]

    all_lines = [

        f"*{title}* | {datetime.now().strftime('%Y-%m-%d %H:%M')}",

        "=" * 40

    ]

    for r in results:

        tier_icon = {"A": "A", "B": "B", "C": "C", "D": "X"}.get(r.get('tier','?'), '?')

        ma_icon = "Y" if r.get('ma20_above_ma60') else "N"

        macd_icon = "+" if r.get('macd_hist', 0) > 0 else "-"

        bull = r.get('bullish', 'N')

        kd = "K+D+" if r.get('kd_golden') else ""

        inst = r.get('inst') or {}

        f_val = inst.get('foreign', 0)

        t_val = inst.get('trust', 0)

        d_val = inst.get('dealer', 0)

        inst_str = f" F:{f_val:+,} T:{t_val:+,} D:{d_val:,}" if inst else ""

        macd_hist = r.get('macd_hist', 0)

        macd_warn = ' [?]MACD-' if macd_hist < 0 else ''

        tier_display = tier_icon if not (tier_icon == 'A' and macd_hist < 0) else 'B'  # downgrade A if MACD<

        all_lines.append(

            f"[{tier_display}] {r['code']} {r['name'][:8]}"

            f" ${r['price']:.2f} ({r['chg']:+.2f}%)"

            f" 評分={r['score']:.0f}/1000 RSI={r['rsi']:.0f} K={r['k']:.0f} D={r['d']:.0f}"

            f" 布林={r['bb_pct']:.0f}% 偏離={r['bias5']:+.1f}% 量={r['vol_ratio']:.1f}x"

            f" 動={macd_icon} MACD={macd_hist:+.2f}{macd_warn} 均線={ma_icon} {bull} {kd}{inst_str}"

        )

    a = sum(1 for r in results if r.get('tier') == 'A')

    b = sum(1 for r in results if r.get('tier') == 'B')

    c = sum(1 for r in results if r.get('tier') == 'C')

    all_lines.append("=" * 40)

    all_lines.append(f"評級: A={a} B={b} C={c} | 合計={len(results)}")

    chunks = []

    chunk = []

    chunk_len = 0

    for line in all_lines:

        if chunk_len + len(line) + 1 > 4000 and chunk:

            chunks.append("\n".join(chunk))

            chunk = []

            chunk_len = 0

        chunk.append(line)

        chunk_len += len(line) + 1

    if chunk:

        chunks.append("\n".join(chunk))

    return chunks



# ── Short-lived In-Memory Cache (no persistent DB, auto-expire) ──

# SESSION_CACHE: stores 6mo price history per stock, TTL=300s

#   • No disk write — purely in-memory, cleared on app restart

#   • Every fetch checks TTL; expired entries are purged on access

#   • After TTL, MACD+RSI are recalculated from fresh yfinance data

#   • Cron jobs start with empty cache → always fresh calculation

#   • atexit handler clears expired entries on graceful shutdown

SESSION_CACHE = {}

CACHE_TTL = 60   # 60-second TTL — faster UI response, was 300s



INST_CACHE = {}
INST_CACHE_TTL = 1800  # 30 minutes

import atexit

def _clear_expired():

    now = time.time()

    expired = [k for k, (ts, _) in SESSION_CACHE.items() if now - ts > CACHE_TTL]

    for k in expired:

        del SESSION_CACHE[k]

    print(f"[Cache] Cleared {len(expired)} expired entries on shutdown.")



atexit.register(_clear_expired)



TW_CATS = {

    "熱門台股": ['2330', '2454', '2317', '2382', '3034', '3665', '2881', '2603', '2303', '1216', '2308', '2302', '2313', '2327', '2337', '2344', '2354', '2376', '2383', '2402'],

    "AI 供應鏈": ['2330', '2303', '6770', '6153', '6239', '6271', '8147', '8261', '8271', '2383', '6213', '3038', '3044', '5388', '5468', '4951', '2345', '2344', '2454', '3231', '3317', '3491', '2401', '2342', '6579', '6715', '6526', '6666', '8039', '8046', '8150', '8277', '8299', '8383'],

    "半導體": ['2303', '2311', '2325', '2363', '2379', '2473', '3035', '3041', '3063', '3257', '3443', '3474', '3519', '3534', '3536', '3579', '3598', '3686', '5280', '5305', '6239', '6271', '6415', '6451', '6515', '6525', '6526', '6531', '6552', '6695', '6719', '6756', '6770', '7769', '8081', '8131', '8150', '8261', '8271', '3105', '3122', '3141', '3169', '3178', '3227', '3228', '3259', '3260', '3264', '3265', '3268', '3317', '3372', '3374', '3438', '3467', '3527', '3529', '3555', '3556', '3567', '3581', '3675', '3680', '3707', '4749', '4923', '4945', '4951', '4966', '4971', '4973', '4991', '5236', '5272', '5274', '5299', '5302', '5344', '5347', '5351', '5425', '5443', '5468', '5483', '5487', '6103', '6104', '6129', '6138', '6147', '6182', '6187', '6208', '6223', '6229', '6233', '6237', '6261', '6287', '6291', '6411', '6423', '6435', '6457', '6462', '6485', '6488', '6494', '6510', '6532', '6548', '6568', '6594', '6640', '6643', '6651', '6679', '6683', '6684', '6693', '6708', '6716', '6720', '6732', '6788', '6823', '6829', '6895', '6907', '6953', '6996', '7556', '7704', '7712', '7734', '7751', '7770', '7810', '7828', '8024', '8040', '8054', '8086', '8088', '8091', '8102', '8227', '8277', '8299', '8383'],

    "電子工業": ['2302', '2312', '2314', '2315', '2316', '2317', '2321', '2323', '2327', '2328', '2329', '2330', '2332', '2336', '2337', '2338', '2340', '2342', '2344', '2345', '2349', '2350', '2351', '2354', '2359', '2362', '2369', '2373', '2374', '2376', '2377', '2384', '2388', '2390', '2391', '2393', '2396', '2397', '2401', '2404', '2406', '2408', '2409', '2411', '2412', '2418', '2419', '2423', '2424', '2426', '2427', '2428', '2430', '2434', '2436', '2438', '2439', '2441', '2446', '2447', '2449', '2450', '2451', '2452', '2453', '2454', '2458', '2459', '2462', '2463', '2464', '2466', '2468', '2469', '2471', '2474', '2477', '2479', '2480', '2481', '2482', '2485', '2486', '2488', '2489', '2491', '2492', '2493', '2495', '2498', '3006', '3007', '3008', '3014', '3016', '3018', '3019', '3020', '3022', '3024', '3025', '3027', '3028', '3029', '3030', '3031', '3034', '3043', '3045', '3049', '3050', '3051', '3055', '3059', '3061', '3062', '3094', '3135', '3138', '3142', '3149', '3150', '3168', '3189', '3214', '3271', '3296', '3305', '3311', '3356', '3367', '3380', '3413', '3419', '3437', '3447', '3450', '3481', '3494', '3501', '3504', '3518', '3530', '3532', '3535', '3543', '3545', '3559', '3563', '3576', '3583', '3584', '3588', '3591', '3592', '3596', '3605', '3607', '3614', '3622', '3638', '3661', '3665', '3669', '3673', '3679', '3694', '3697', '3702A', '3704', '3711', '3714', '3715', '4585', '4588', '4904', '4919', '4934', '4935', '4942', '4943', '4952', '4956', '4960', '4961', '4967', '4968', '4976', '4977', '4989', '5203', '5222', '5225', '5234', '5243', '5244', '5258', '5269', '5285', '5388', '5471', '5484', '6112', '6116', '6119', '6120', '6136', '6139', '6141', '6153', '6183', '6189', '6191', '6197', '6201', '6202', '6214', '6215', '6216', '6225', '6226', '6243', '6257', '6272', '6278', '6280', '6285', '6286', '6449', '6477', '6533', '6573', '6579', '6591', '6669', '6672', '6715', '6722', '6789', '6792', '6799', '6830', '6854', '6863', '6909', '6916', '6921', '6933', '6937', '6962', '7631', '7730', '7749', '7822', '8008', '8011', '8016', '8021', '8028', '8045', '8070', '8103', '8104', '8110', '8112A', '8114', '8162', '8163', '8199', '8201', '8213', '8215', '8249'],

    "電子零組件": ['1471', '1582', '2059', '2308', '2313', '2355', '2367', '2368', '2375', '2383', '2385', '2392', '2402', '2413', '2415', '2420', '2421', '2431', '2437', '2440', '2456', '2457', '2460', '2467', '2472', '2476', '2478', '2483', '2484', '3003', '3011', '3015', '3021', '3023', '3026', '3032', '3037', '3042', '3044', '3058', '3090', '3092', '3229', '3308', '3321', '3338', '3376', '3432', '3533', '3550', '3593', '3645', '3653', '4545', '4912', '4915', '4927', '4958', '4999', '5469', '6108', '6115', '6133', '6155', '6205', '6213', '6224', '6251', '6269', '6282', '6412', '6422', '6781', '6805', '6834', '6835', '6862', '6924', '7788', '7795', '8039', '8046', '1336', '1595', '1815', '3078', '3089', '3114', '3115', '3144', '3191', '3202', '3206', '3207', '3217', '3236', '3276', '3288', '3290', '3294', '3310', '3322', '3332', '3354', '3357', '3388', '3390', '3484', '3492', '3511', '3520', '3526', '3537', '3548', '3597', '3609', '3624', '3631', '3646', '3689', '3710', '4542', '4939', '4974', '5227', '5228', '5291', '5309', '5328', '5340', '5349', '5355', '5381', '5439', '5457', '5460', '5464', '5475', '5488', '5498', '6114', '6124', '6126', '6127', '6134', '6156', '6158', '6173', '6174', '6175', '6185', '6194', '6203', '6204', '6207', '6210', '6217', '6220', '6259', '6266', '6274', '6275', '6279', '6284', '6290', '6292', '6418', '6432', '6538', '6584', '6597', '6642', '6664', '6727', '6761', '6821', '6913', '6967', '7744', '8038', '8042', '8043', '8071', '8074', '8093', '8109', '8121', '8147', '8155', '8182', '8289', '8291', '8358'],

    "光電/顯示": ['2429', '2448', '2475', '2499', '3009', '3038', '3080', '3383', '3406', '3454', '3514', '3561', '3573', '3599', '3698', '4949', '5259', '6131', '6164', '6168', '6176', '6209', '6255', '6289', '6405', '6443', '6456', '6668', '6706', '6742', '8105', '3066', '3128', '3230', '3297', '3339', '3362', '3434', '3441', '3455', '3490', '3516', '3523', '3531', '3615', '3623', '3630', '3666', '3691', '4729', '4933', '4944', '4972', '4995', '5220', '5230', '5245', '5251', '5281', '5315', '5371', '5392', '6125', '6167', '6222', '6234', '6244', '6246', '6419', '6498', '6517', '6556', '6560', '6859', '6899', '7402', '7753', '8049', '8064', '8069', '8111', '8240'],

    "通信網路": ['2444', '2455', '2494', '3047', '3682', '4906', '4984', '6142', '6152', '6416', '6426', '6442', '6674', '8078', '8101', '3081', '3095', '3152', '3163', '3221', '3234', '3306', '3363', '3466', '3491', '3499', '3558', '3564', '3632', '3664', '3672', '3684', '4903', '4905', '4908', '4909', '4979', '5353', '6109', '6143', '6163', '6170', '6190', '6218', '6241', '6245', '6263', '6417', '6465', '6470', '6486', '6514', '6530', '6546', '6561', '6588', '7717', '8034', '8048', '8059', '8089', '8097', '8176'],

    "資料中心/記憶體": ['2330', '2382', '2401', '2454', '3034', '3044', '3217', '3356', '3592', '2342', '2344', '2440', '2483', '3021', '3038', '3189', '3317', '3443', '4915', '5225', '5471', '5483', '6153', '6208', '6239', '6488', '6579', '6708', '6715', '6770', '8039', '8046', '8150', '8299', '8383'],

    "金融": ['2801', '2807', '2809', '2812', '2816', '2820', '2823', '2827', '2831', '2832', '2833', '2833A', '2834', '2836', '2836A', '2837', '2838', '2838A', '2845', '2847', '2849', '2850', '2851', '2852', '2854', '2855', '2856', '2867', '2880', '2881', '2881A', '2881B', '2881C', '2882', '2882A', '2882B', '2883A', '2883', '2883B', '2884', '2885', '2886', '2887C', '2887', '2887E', '2887F', '2887G', '2887H', '2887I', '2887Z1', '2888B', '2888A', '2888', '2889', '2890', '2891A', '2891', '2891B', '2891C', '2892', '2897A', '2897', '2897B', '5854', '5876', '5880', '6004', '6005', '6012', '6024', '5820', '5864', '5878', '6015', '6016', '6020', '6021', '6023', '6026', '6028'],

    "傳產製造": ['1101', '1101B', '1102', '1103', '1104', '1108', '1109', '1110', '1230', '1301', '1303', '1304', '1305', '1307', '1308', '1309', '1310', '1311', '1312A', '1312', '1313', '1314', '1315', '1316', '1321', '1323', '1324', '1325', '1326', '1337', '1340', '1341', '1402', '1409', '1410', '1413', '1414', '1417', '1418', '1419', '1423', '1434', '1436', '1438', '1439', '1440', '1441', '1442', '1444', '1445', '1446', '1447', '1449', '1451', '1452', '1453', '1454', '1455', '1456', '1457', '1459', '1460', '1463', '1464', '1465', '1466', '1467', '1468', '1469', '1470', '1472', '1473', '1474', '1475', '1476', '1477', '1503', '1504', '1506', '1507', '1513', '1514', '1515', '1517', '1519', '1523', '1526', '1527', '1528', '1529', '1530', '1531', '1532', '1535', '1537', '1538', '1539', '1540', '1541', '1558', '1560', '1583', '1589', '1590', '1597', '1601', '1603', '1604', '1605', '1606', '1608', '1609', '1611', '1612', '1613', '1614', '1615', '1616', '1617', '1618', '1623', '1626', '1715', '1805', '1808', '2002', '2002A', '2006', '2007', '2008', '2009', '2010', '2012', '2013', '2014', '2015', '2017', '2020', '2022', '2023', '2024', '2025', '2027', '2028', '2029', '2030', '2031', '2032', '2033', '2034', '2038', '2049', '2069', '2101', '2102', '2103', '2104', '2105', '2106', '2107', '2108', '2109', '2114', '2211', '2371', '2442', '2501', '2504', '2505', '2506', '2509', '2511', '2515', '2516', '2520', '2524', '2526', '2527', '2528', '2530', '2534', '2535', '2536', '2537', '2538', '2539', '2540', '2542', '2543', '2545', '2546', '2547', '2548', '2597', '2841', '2923', '3004', '3052', '3056', '3167', '3266', '3703', '4306', '4414', '4426', '4438', '4439', '4440', '4441', '4526', '4532', '4540', '4552', '4555', '4560', '4562', '4564', '4566', '4571', '4572', '4576', '4583', '4590', '4930', '5007', '5283', '5288', '5515', '5519', '5521', '5522', '5525', '5531', '5533', '5534', '5538', '5546', '6177', '6582', '6606', '7750', '8222', '8374', '8996', '9906', '9946', '9958', '1570', '1580', '1586', '1591', '1599', '2035', '2061', '2063', '2064', '2065', '2066', '2067', '2070', '2073', '2230', '2235', '2596', '2718', '3162', '3188', '3226', '3379', '3426', '3489', '3512', '3521', '3685', '4113', '4303', '4304', '4305', '4401', '4402', '4406', '4413', '4416', '4417', '4420', '4429', '4432', '4433', '4442', '4502', '4503', '4506', '4510', '4513', '4523', '4527', '4528', '4533', '4534', '4535', '4538', '4543', '4549', '4550', '4558', '4561', '4563', '4568', '4580', '4584', '4907', '4950', '5009', '5011', '5013', '5014', '5015', '5016', '5102', '5206', '5213', '5324', '5455', '5508', '5511', '5512', '5514', '5516', '5520', '5523', '5529', '5543', '5547', '5548', '6122', '6171', '6186', '6198', '6212', '6219', '6248', '6264', '6425', '6506', '6603', '6609', '6843', '6982', '7642', '7709', '7718', '8027', '8080', '8083', '8107', '8255', '8349A', '8349', '8415', '8424', '8930', '9950', '9951', '9962'],

    "生技醫療": ['1701', '1704', '1707', '1708', '1709', '1710', '1711', '1712', '1713', '1714', '1716', '1717', '1718', '1720', '1721', '1722', '1723', '1724', '1725', '1726', '1727', '1729', '1730', '1731', '1733', '1734', '1735', '1752', '1760', '1762', '1773', '1776', '1783', '1786', '1789', '1795', '3164', '3705', '3716', '4104', '4106', '4108', '4119', '4133', '4137', '4141', '4142', '4144', '4148', '4155', '4164', '4169', '4178', '4190', '4720', '4722', '4725', '4736', '4737', '4739', '4746', '4755', '4763', '4764', '4766', '4770', '4771', '6431', '6446', '6452', '6472', '6491', '6534', '6541', '6550', '6589', '6598', '6645', '6657', '6666', '6782', '6794', '6796', '6838', '6861', '6885', '6918', '6919', '6931', '6934', '6936', '6949', '6955', '7799', '1565', '1777', '1781', '1784', '1788', '1799', '1813', '3118', '3176', '3205', '3218', '4102', '4105', '4107', '4109', '4111', '4114', '4116', '4120', '4121', '4123', '4126', '4127', '4128', '4129A', '4129', '4130', '4131', '4138', '4139', '4147', '4152', '4153', '4157', '4160', '4161', '4162', '4163', '4166', '4167', '4168', '4173', '4174', '4175', '4183', '4188', '4192', '4198', '4726', '4728', '4735', '4743', '4744', '4745', '4747', '4911', '5312', '6130', '6242', '6461', '6469', '6492', '6496', '6497', '6499', '6523', '6527', '6535', '6547', '6569', '6574', '6576', '6612', '6615', '6617', '6620', '6637', '6649', '6661', '6662', '6703', '6712', '6730', '6733', '6747', '6762', '6767', '6785', '6841', '6844', '6872', '6875', '6929', '7713', '8279', '8403', '8406', '8409', '8432', '8436'],

    "綠能/車電": ['1319', '1338', '1339', '1512', '1521', '1522', '1522A', '1524', '1525', '1533', '1536', '1563', '1568', '1587', '1592', '2072', '2115', '2201', '2204', '2206', '2207', '2227', '2228', '2231', '2233', '2236', '2239', '2241', '2243', '2247', '2248', '2250', '2254', '2258', '2497', '3346', '3708', '3717', '4551', '4557', '4569', '4581', '5292', '6288', '6581', '6605', '6641', '6771', '6806', '6869', '6873', '6887', '6923', '6944', '6951', '6969', '6988', '6994', '7610', '7732', '7736', '7740', '7786', '7821', '8341', '8422', '8438', '8473', '8476', '9930', '9955', '3073', '3551', '3713', '5205', '5432', '6624', '6692', '6803', '6894', '6971', '7715', '7820', '8087', '8171', '8390', '8423', '8440'],

    "ETF": ['0050', '0051', '0052', '0053', '0054', '0055', '0056', '0057', '0058', '0059', '0060', '0061', '0080', '0081', '00400A', '00401A', '00625K', '00631L', '00632R', '00633L', '00634R', '00635U', '00636K', '00636', '00637L', '00638R', '00639', '00640L', '00641R', '00642U', '00643', '00643K', '00645', '00646', '00647L', '00648R', '00649', '00650L', '00651R', '00652', '00653L', '00654R', '00655L', '00656R', '00657', '00657K', '00658L', '00659R', '00660', '00661', '00662', '00663L', '00664R', '00665L', '00666R', '00667', '00668', '00668K', '00669R', '00670L', '00671R', '00672L', '00673R', '00674R', '00675L', '00676R', '00677U', '00678', '00679B', '00680L', '00681R', '00682U', '00683L', '00684R', '00685L', '00686R', '00687C', '00687B', '00688L', '00689R', '00690', '00691R', '00692', '00693U', '00694B', '00695B', '00696B', '00697B', '00698L', '00699R', '00700', '00701', '00702', '00703', '00704L', '00705R', '00706L', '00707R', '00708L', '00709', '00710B', '00711B', '00712', '00713', '00714', '00715L', '00716R', '00717', '00718B', '00719B', '00720B', '00721B', '00722B', '00723B', '00724B', '00725B', '00726B', '00727B', '00728', '00729R', '00730', '00731', '00732', '00733', '00734B', '00735', '00736', '00737', '00738U', '00739', '00740B', '00741B', '00742', '00743', '00744B', '00745B', '00746B', '00747B', '00748B', '00749B', '00750B', '00751B', '00752', '00753L', '00754B', '00755B', '00756B', '00757', '00758B', '00759B', '00760B', '00761B', '00762', '00763U', '00764B', '00765B', '00766L', '00767', '00768B', '00770', '00771', '00772B', '00773B', '00774B', '00774C', '00775B', '00776', '00777B', '00778B', '00779B', '00780B', '00781B', '00782B', '00783', '00784B', '00785B', '00786B', '00787B', '00788B', '00789B', '00790B', '00791B', '00792B', '00793B', '00794B', '00795B', '00796B', '00798B', '00799B', '00830', '00831B', '00832B', '00833B', '00834B', '00835B', '00836B', '00837B', '00838B', '00839B', '00840B', '00841B', '00842B', '00843B', '00844B', '00845B', '00846B', '00847B', '00848B', '00849B', '00850', '00851', '00852L', '00853B', '00854B', '00855B', '00856B', '00857B', '00858', '00859B', '00860B', '00861', '00862B', '00863B', '00864B', '00865B', '00866', '00867B', '00868B', '00869B', '00870B', '00871B', '00872B', '00873B', '00874B', '00875', '00876', '00877', '00878', '00879B', '00880B', '00881', '00882', '00883B', '00884B', '00885', '00886', '00887', '00888', '00889B', '00890B', '00891', '00892', '00893', '00894', '00895', '00896', '00897', '00898', '00899', '00900', '00901', '00902', '00903', '00904', '00905', '00906', '00907', '00908', '00909', '00910', '00911', '00912', '00913', '00915', '00916', '00917', '00918', '00919', '00920', '00921', '00922', '00923', '00924', '00925', '00926', '00927', '00928', '00929', '00930', '00931B', '00932', '00933B', '00934', '00935', '00936', '00937B', '00938', '00939', '00940', '00941', '00942B', '00943', '00944', '00945B', '00946', '00947', '00948B', '00949', '00950B', '00951', '00952', '00953B', '00954', '00955', '00956', '00957B', '00958B', '00959B', '00960', '00961', '00962', '00963', '00964', '00965', '00966B', '00967B', '00968B', '00969B', '00970B', '00971', '00972', '00980T', '00980D', '00980B', '00980A', '00981D', '00981B', '00981A', '00981T', '00982B', '00982A', '00982D', '00982T', '00983B', '00983A', '00983D', '00984B', '00984D', '00984A', '00985D', '00985B', '00985A', '00986D', '00986B', '00986A', '00987B', '00987A', '00988B', '00988A', '00989B', '00989A', '00990A', '00991A', '00992A', '00993A', '00994A', '00995A', '00996A', '00997A', '00998A', '006201', '006203', '006204', '006205', '006206', '006207', '006208', '008201', '009800', '009801', '009802', '009803', '009804', '009805', '009806', '009807', '009808', '009809', '009810', '009811', '009812', '009813', '009814', '009815', '009816', '009817', '009818', '009819', '009820'],

    "觀光/消費": ['1201', '1203', '1210', '1213', '1215', '1216', '1217', '1218', '1219', '1220', '1225', '1227', '1229', '1231', '1232', '1233', '1234', '1235', '1236', '1256', '1432', '1598', '1702', '1736', '1737', '2062', '2601', '2701', '2702', '2704', '2705', '2706', '2707', '2712', '2722', '2723', '2727', '2731', '2739', '2748', '2753', '2762', '2901', '2903', '2905', '2906', '2908', '2910', '2911', '2912', '2913', '2915', '2929', '2936', '2939', '2945', '3054', '3557', '4536', '4807', '5306', '5706', '5906', '5907', '6670', '6671', '6754', '6768', '6807', '6890', '6965', '7705', '7760', '7780', '7791', '8429', '8443', '8462', '8464', '8467', '8478', '8482', '8940', '9801', '9802', '9904', '9910', '9911', '9914', '9921', '9924', '9934', '9935', '9943', '1258', '1259', '1264', '1268', '1294', '1295', '1593', '1796', '2719', '2726', '2729', '2732', '2734', '2736', '2740', '2743', '2745', '2751', '2752', '2754', '2755', '2756', '2916', '2924', '2928', '2937', '2941', '2947', '2948', '3171', '3252', '3522', '4205', '4207', '4419', '4530', '4609', '4702', '4712', '4804', '5301', '5348', '5364', '5701', '5703', '5704', '5902', '5903', '5904', '5905', '6195', '6616', '6629', '6728', '6804', '6846', '6961', '6968', '7708', '7723', '7743', '7757', '7782', '7794', '7811', '8066', '8077', '8420', '8433', '8924', '8928', '8933', '8938', '8941', '9960'],

    "其他電子/軟體": ['1107', '1262', '1342', '1416', '1435', '1437', '1443', '1516', '1520', '2301', '2305', '2324', '2331', '2341', '2348', '2348A', '2352', '2353', '2356', '2357', '2358', '2360', '2361', '2364', '2365', '2380', '2381', '2382', '2387', '2395', '2399', '2405', '2417', '2425', '2432', '2433', '2443', '2461', '2465', '2496', '2514', '2614', '2904', '3002', '3005', '3013', '3017', '3040', '3046', '3053', '3057', '3060', '3130', '3231', '3416', '3515', '3617', '3652', '3701', '3706', '3712', '4916', '4938', '4994', '5215', '5264', '5284', '5871', '5871A', '6117', '6128', '6165', '6166', '6172', '6184', '6192', '6196', '6206', '6230', '6235', '6277', '6283', '6409', '6414', '6438', '6464', '6504', '6558', '6585', '6592B', '6592A', '6592', '6614', '6625', '6655', '6658', '6689', '6691', '6698', '6743', '6831', '6901', '6902', '6906', '6914', '6928', '6952', '6957', '6958', '6958A', '7711', '7721', '7722', '7765', '7823', '8033', '8210', '8404', '8411', '8427', '8442', '8454', '8463', '8466', '8480', '8481', '8488', '8497', '8499', '9902', '9905', '9907', '9912', '9915', '9917', '9919', '9922', '9925', '9927', '9928', '9929', '9933', '9938', '9939', '9940', '9941A', '9941', '9942', '9944', '9945', '1569', '1584', '1785', '2221', '2640', '2724', '2949', '3067', '3071', '3085', '3088', '3093', '3131', '3147', '3158', '3211', '3213', '3219', '3272', '3284', '3285', '3287', '3289', '3303', '3313', '3323', '3324', '3325', '3349', '3373', '3402', '3465', '3479', '3483', '3498', '3508', '3540', '3541', '3552', '3570', '3577', '3580', '3587', '3594', '3611', '3625', '3628', '3642', '3663', '3687', '3693', '3709', '4154', '4430', '4529', '4541', '4554', '4556', '4577', '4760', '4924', '4931', '4953', '4987', '5201', '5202', '5209', '5210', '5211', '5212', '5223', '5276', '5278', '5287', '5289', '5304', '5310', '5314', '5321', '5345', '5356', '5383', '5386', '5398', '5403', '5410', '5426', '5438', '5450', '5452', '5465', '5474', '5481', '5489', '5490', '5493', '5530', '5536', '5604', '6121', '6123', '6140', '6146', '6148', '6150', '6151', '6160', '6161', '6179', '6188', '6199', '6221', '6228', '6231', '6236', '6238', '6240', '6247', '6276', '6404', '6441', '6512', '6516', '6570', '6577', '6590', '6593', '6613', '6654', '6667', '6680', '6690', '6697', '6721', '6725', '6735', '6739', '6741', '6751', '6752', '6763', '6791', '6811', '6840', '6855', '6865', '6870', '6874', '6877', '6881', '6884', '6903', '6904', '6910', '6922', '6925', '6997', '7547', '7703', '7714', '7728', '7738', '7747', '7767', '7777', '7792', '7805', '8044', '8047', '8050', '8076', '8085', '8092', '8099', '8183', '8234', '8272', '8284', '8342', '8354', '8401', '8410', '8416', '8418', '8421', '8426', '8431', '8435', '8437', '8444', '8455', '8472', '8477', '8489', '8905', '8906', '8916A', '8916', '8921', '8929', '8932', '8934', '8935', '8936', '8937', '8942'],

    "全部": ['0050', '0051', '0052', '0053', '0054', '0055', '0056', '0057', '0058', '0059', '0060', '0061', '0080', '0081', '1101', '1102', '1103', '1104', '1107', '1108', '1109', '1110', '1201', '1203', '1210', '1213', '1215', '1216', '1217', '1218', '1219', '1220', '1225', '1227', '1229', '1230', '1231', '1232', '1233', '1234', '1235', '1236', '1256', '1262', '1301', '1303', '1304', '1305', '1307', '1308', '1309', '1310', '1311', '1312', '1313', '1314', '1315', '1316', '1319', '1321', '1323', '1324', '1325', '1326', '1337', '1338', '1339', '1340', '1341', '1342', '1402', '1409', '1410', '1413', '1414', '1416', '1417', '1418', '1419', '1423', '1432', '1434', '1435', '1436', '1437', '1438', '1439', '1440', '1441', '1442', '1443', '1444', '1445', '1446', '1447', '1449', '1451', '1452', '1453', '1454', '1455', '1456', '1457', '1459', '1460', '1463', '1464', '1465', '1466', '1467', '1468', '1469', '1470', '1471', '1472', '1473', '1474', '1475', '1476', '1477', '1503', '1504', '1506', '1507', '1512', '1513', '1514', '1515', '1516', '1517', '1519', '1520', '1521', '1522', '1523', '1524', '1525', '1526', '1527', '1528', '1529', '1530', '1531', '1532', '1533', '1535', '1536', '1537', '1538', '1539', '1540', '1541', '1558', '1560', '1563', '1568', '1582', '1583', '1587', '1589', '1590', '1592', '1597', '1598', '1601', '1603', '1604', '1605', '1606', '1608', '1609', '1611', '1612', '1613', '1614', '1615', '1616', '1617', '1618', '1623', '1626', '1701', '1702', '1704', '1707', '1708', '1709', '1710', '1711', '1712', '1713', '1714', '1715', '1716', '1717', '1718', '1720', '1721', '1722', '1723', '1724', '1725', '1726', '1727', '1729', '1730', '1731', '1732', '1733', '1734', '1735', '1736', '1737', '1752', '1760', '1762', '1773', '1776', '1783', '1786', '1789', '1795', '1802', '1805', '1806', '1808', '1809', '1810', '1817', '1902', '1903', '1904', '1905', '1906', '1907', '1909', '2002', '2006', '2007', '2008', '2009', '2010', '2012', '2013', '2014', '2015', '2017', '2020', '2022', '2023', '2024', '2025', '2027', '2028', '2029', '2030', '2031', '2032', '2033', '2034', '2038', '2049', '2059', '2062', '2069', '2072', '2101', '2102', '2103', '2104', '2105', '2106', '2107', '2108', '2109', '2114', '2115', '2201', '2204', '2206', '2207', '2208', '2211', '2227', '2228', '2231', '2233', '2236', '2239', '2241', '2243', '2247', '2248', '2250', '2254', '2258', '2301', '2302', '2303', '2305', '1240', '1258', '1259', '1264', '1268', '1294', '1295', '1336', '1565', '1569', '1570', '1580', '1584', '1586', '1591', '1593', '1595', '1599', '1742', '1777', '1781', '1784', '1785', '1788', '1796', '1799', '1813', '1815', '2035', '2061', '2063', '2064', '2065', '2066', '2067', '2070', '2073', '2221', '2230', '2235', '2596', '2640', '2641', '2643', '2718', '2719', '2724', '2726', '2729', '2732', '2734', '2736', '2740', '2743', '2745', '2751', '2752', '2754', '2755', '2756', '2916', '2924', '2926', '2928', '2937', '2941', '2947', '2948', '2949', '3064', '3066', '3067', '3071', '3073', '3078', '3081', '3083', '3085', '3086', '3088', '3089', '3093', '3095', '3105', '3114', '3115', '3118', '3122', '3128', '3131', '3141', '3144', '3147', '3152', '3158', '3162', '3163', '3169', '3171', '3176', '3178', '3188', '3191', '3202', '3205', '3206', '3207', '3211', '3213', '3217', '3218', '3219', '3221', '3224', '3226', '3227', '3228', '3230', '3232', '3234', '3236', '3252', '3259', '3260', '3264', '3265', '3268', '3272', '3276', '3284', '3285', '3287', '3288', '3289', '3290', '3293', '3294', '3297', '3303', '3306', '3310', '3313', '3317', '3322', '3323', '3324', '3325', '3332', '3339', '3349', '3354', '3357', '3360', '3362', '3363', '3372', '3373', '3374', '3379', '3388', '3390', '3402', '3426', '3430', '3434', '3438', '3441', '3444', '3455', '3465', '3466', '3467', '3479', '3483', '3484', '3489', '3490', '3491', '3492', '3498', '3499', '3508', '3511', '3512', '3516', '3520', '3521', '3522', '3523', '3526', '3527', '3529', '3531', '3537', '3540', '3541', '3546', '3548', '3551', '3552'],

}



US_CATS = {

    'S&P 500': ['A','AAPL','ABBV','ABNB','ABT','ACGL','ACN','ADBE','ADI','ADM','ADP','ADSK','AEE','AEP','AES','AFL','AIG','AIZ','AJG','AKAM','ALB','ALGN','ALL','ALLE','AMAT','AMCR','AMD','AME','AMGN','AMP','AMT','AMZN','ANET','AON','AOS','APA','APD','APH','APO','APP','APTV','ARE','ARES','ATO','AVB','AVGO','AVY','AWK','AXON','AXP','AZO','B','BA','BAC','BALL','BAX','BBY','BDX','BEN','BG','BIIB','BK','BKNG','BKR','BLDR','BLK','BMY','BR','BRO','BSX','BX','BXP','C','CAG','CAH','CARR','CASY','CAT','CB','CBOE','CBRE','CCI','CCL','CDNS','CDW','CEG','CF','CFG','CHD','CHRW','CHTR','CI','CIEN','CINF','CL','CLX','CME','CMG','CMI','CMS','CNC','CNP','COF','COHR','COIN','COO','COP','COR','COST','CPAY','CPB','CPRT','CPT','CRH','CRL','CRM','CRWD','CSCO','CSGP','CSX','CTAS','CTRA','CTSH','CTVA','CVNA','CVS','CVX','D','DAL','DASH','DD','DDOG','DE','DECK','DELL','DG','DGX','DHI','DHR','DIS','DLR','DLTR','DOC','DOV','DOW','DPZ','DRI','DTE','DUK','DVA','DVN','DXCM','EA','EBAY','ECL','ED','EFX','EG','EIX','EL','ELV','EME','EMR','EOG','EPAM','EQIX','EQR','EQT','ERIE','ES','ESS','ETN','ETR','EVRG','EW','EXC','EXE','EXPD','EXPE','EXR','F','FANG','FAST','FCX','FDS','FDX','FE','FFIV','FICO','FIS','FISV','FITB','FIX','FOX','FOXA','FRT','FSLR','FTNT','FTV','GD','GDDY','GE','GEHC','GEN','GEV','GILD','GIS','GL','GLW','GM','GNRC','GOOG','GPC','GPN','GRMN','GS','GWW','HAL','HAS','HBAN','HCA','HD','HIG','HII','HLT','HON','HOOD','HPE','HPQ','HRL','HSIC','HST','HSY','HUBB','HUM','HWM','IBKR','IBM','ICE','IDXX','IEX','IFF','INCY','INTC','INTU','INVH','IP','IQV','IR','IRM','ISRG','IT','ITW','IVZ','J','JBHT','JBL','JCI','JKHY','JNJ','JPM','KDP','KEY','KEYS','KHC','KIM','KKR','KLAC','KMB','KMI','KO','KR','KVUE','L','LDOS','LEN','LH','LHX','LII','LIN','LITE','LLY','LMT','LNT','LOW','LRCX','LULU','LUV','LVS','LYB','LYV','MA','MAA','MAR','MAS','MCD','MCHP','MCK','MCO','MDLZ','MDT','MET','META','MGM','MKC','MLM','MMM','MNST','MO','MOS','MPC','MPWR','MRK','MRNA','MRSH','MS','MSCI','MSFT','MSI','MTB','MTD','MU','NCLH','NDAQ','NDSN','NEE','NEM','NFLX','NI','NKE','NOC','NOW','NRG','NSC','NTAP','NTRS','NUE','NVDA','NVR','NWS','NWSA','NXPI','O','ODFL','OKE','OMC','ON','ORCL','ORLY','OTIS','OXY','PANW','PAYX','PCAR','PCG','PEG','PEP','PFE','PFG','PG','PGR','PH','PHM','PKG','PLD','PLTR','PM','PNC','PNR','PNW','PODD','POOL','PPG','PPL','PRU','PSA','PSX','PTC','PWR','PYPL','Q','QCOM','RCL','REG','REGN','RF','RJF','RL','RMD','ROK','ROL','ROP','ROST','RSG','RTX','RVTY','SATS','SBAC','SBUX','SCHW','SHW','SJM','SLB','SMCI','SNA','SNDK','SNPS','SO','SOLV','SPG','SPGI','SRE','STE','STLD','STT','STX','STZ','SW','SWK','SWKS','SYF','SYK','SYY','T','TAP','TDG','TDY','TECH','TEL','TER','TFC','TGT','TJX','TKO','TMO','TMUS','TPL','TPR','TRGP','TRMB','TROW','TRV','TSCO','TSLA','TSN','TT','TTD','TTWO','TXN','TXT','TYL','UAL','UBER','UDR','UHS','ULTA','UNH','UNP','UPS','URI','USB','V','VICI','VLO','VLTO','VMC','VRSK','VRSN','VRT','VRTX','VST','VTR','VTRS','VZ','WAB','WAT','WBD','WDAY','WDC','WEC','WELL','WFC','WM','WMB','WMT','WRB','WSM','WST','WTW','WY','WYNN','XEL','XOM','XYL','XYZ','YUM','ZBH','ZBRA','ZTS'],

    # ─── S&P 500 GICS 產業分類 ───

    'IT - Information Technology': ['AAPL','ACN','ADBE','ADI','ADSK','AKAM','AMAT','AMD','ANET','APH','APP','AVGO','CDNS','CDW','CIEN','COHR','CRM','CRWD','CSCO','CTSH','DDOG','DELL','EPAM','FFIV','FICO','FSLR','FTNT','GDDY','GEN','GLW','HPE','HPQ','IBM','INTC','INTU','IT','JBL','KEYS','KLAC','LITE','LRCX','MCHP','MPWR','MSFT','MSI','MU','NOW','NTAP','NVDA','NXPI','ON','ORCL','PANW','PLTR','PTC','Q','QCOM','ROP','SMCI','SNDK','SNPS','STX','SWKS','TDY','TEL','TER','TRMB','TXN','TYL','VRSN','WDAY','WDC','ZBRA'],

    'HC - Health Care': ['A','ABBV','ABT','ALGN','AMGN','BAX','BDX','BIIB','BMY','BSX','CAH','CI','CNC','COO','COR','CRL','CVS','DGX','DHR','DVA','DXCM','ELV','EW','GEHC','GILD','HCA','HSIC','HUM','IDXX','INCY','IQV','ISRG','JNJ','LH','LLY','MCK','MDT','MRK','MRNA','MTD','PFE','PODD','REGN','RMD','RVTY','SOLV','STE','SYK','TECH','TMO','UHS','UNH','VRTX','VTRS','WAT','WST','ZBH','ZTS'],

    'FIN - Financials': ['ACGL','AFL','AIG','AIZ','AJG','ALL','AMP','AON','APO','ARES','AXP','BAC','BEN','BK','BLK','BRK.B','BRO','BX','C','CB','CFG','CINF','CME','COF','COIN','CPAY','EG','ERIE','FDS','FIS','FISV','FITB','GL','GPN','GS','HBAN','HIG','HOOD','IBKR','ICE','IVZ','JKHY','JPM','KEY','KKR','L','MA','MCO','MET','MRSH','MS','MSCI','MTB','NDAQ','NTRS','PFG','PGR','PNC','PRU','PYPL','RF','RJF','SCHW','SPGI','STT','SYF','TFC','TROW','TRV','USB','V','WFC','WRB','WTW','XYZ'],

    'CD - Consumer Discretionary': ['ABNB','AMZN','APTV','AZO','BBY','BKNG','CCL','CMG','CVNA','DASH','DECK','DHI','DPZ','DRI','EBAY','EXPE','F','GM','GPC','GRMN','HAS','HD','HLT','LEN','LOW','LULU','LVS','MAR','MCD','MGM','NCLH','NKE','NVR','ORLY','PHM','POOL','RCL','RL','ROST','SBUX','TJX','TPR','TSCO','TSLA','ULTA','WSM','WYNN','YUM'],

    'COMM - Communication Services': ['CHTR','CMCSA','DIS','EA','FOX','FOXA','GOOG','GOOGL','LYV','META','NFLX','NWS','NWSA','OMC','SATS','T','TKO','TMUS','TTD','TTWO','VZ','WBD'],

    'IND - Industrials': ['ADP','ALLE','AME','AOS','AXON','BA','BLDR','BR','CARR','CAT','CHRW','CMI','CPRT','CSX','CTAS','DAL','DE','DOV','EFX','EME','EMR','ETN','EXPD','FAST','FDX','FIX','FTV','GD','GE','GEV','GNRC','GWW','HII','HON','HUBB','HWM','IEX','IR','ITW','J','JBHT','JCI','LDOS','LHX','LII','LMT','LUV','MAS','MMM','NDSN','NOC','NSC','ODFL','OTIS','PAYX','PCAR','PH','PNR','PWR','ROK','ROL','RSG','RTX','SNA','SWK','TDG','TT','TXT','UAL','UBER','UNP','UPS','URI','VLTO','VRSK','VRT','WAB','WM','XYL'],

    'CST - Consumer Staples': ['ADM','BF.B','BG','CAG','CASY','CHD','CL','CLX','COST','CPB','DG','DLTR','EL','GIS','HRL','HSY','KDP','KHC','KMB','KO','KR','KVUE','MDLZ','MKC','MNST','MO','PEP','PG','PM','SJM','STZ','SYY','TAP','TGT','TSN','WMT'],

    'ENE - Energy': ['APA','BKR','COP','CTRA','CVX','DVN','EOG','EQT','EXE','FANG','HAL','KMI','MPC','OKE','OXY','PSX','SLB','TPL','TRGP','VLO','WMB','XOM'],

    'UTI - Utilities': ['AEE','AEP','AES','ATO','AWK','CEG','CMS','CNP','D','DTE','DUK','ED','EIX','ES','ETR','EVRG','EXC','FE','LNT','NEE','NI','NRG','PCG','PEG','PNW','PPL','SO','SRE','VST','WEC','XEL'],

    'RE - Real Estate': ['AMT','ARE','AVB','BXP','CBRE','CCI','CPT','CSGP','DLR','DOC','EQIX','EQR','ESS','EXR','FRT','HST','INVH','IRM','KIM','MAA','O','PLD','PSA','REG','SBAC','SPG','UDR','VICI','VTR','WELL','WY'],

    'MAT - Materials': ['ALB','AMCR','APD','AVY','BALL','CF','CRH','CTVA','DD','DOW','ECL','FCX','IFF','IP','LIN','LYB','MLM','MOS','NEM','NUE','PKG','PPG','SHW','STLD','SW','VMC'],

    # ─── 主題精選（跨 GICS 板塊）───

    'AI 基礎設施': ['NVDA','AMD','AVGO','MRVL','AMZN','MSFT','GOOGL','META','ANET','VRT','DELL','PLTR','NOW','ORCL','COHR','LITE','GLW','AMSC','NVT','SBGSY','EQIX','DLR','AMKR'],

    '費半指數 (SOX)': ['NVDA','AMD','AVGO','AMAT','LRCX','KLAC','MU','INTC','ASML','NXPI','QCOM','TSM','AMKR','ON','MPWR','MCHP','ADI','SWKS','ENTG','COHR','SNPS','CDNS','MRVL','SMCI','PTC','TER','QRVO','UMC','SMTC','LEDS','WDC','SE','NXGN','GFS','CE','QRVO','SWI','LSCC','MLNX','IDTI','MPWR','OLED','SMAR','VICR','DIOD','MEMC','FORM','LTHM','MAXR','NPTN','ASX','ATOM','PLAB','SOXX'],

    '金融科技': ['PYPL','SQ','AFRM','COIN','HOOD','DB','AFC','GREM','UPST','LC','RBLX','NU','SOFI'],

    '電動車/綠能': ['TSLA','RIVN','LCID','F','GM','HYLN','ENPH','SEDG','SPWR','FSLR','RUN','ALB','NIO','XPEV','CHPT','BLNK','CCID','NOVA'],

    # ─── 美股 ETF ───

    # ─── 美股熱門 ETF（Jo 提供，36 檔）───

    'ETF': ['VOO','IVV','SPY','VTI','QQQ','VUG','SOXX','SMH','SCHD','VYM','VTV','DGRO','BND','TLT','SHY','AGG','VT','VXUS','VWO','SSO','QLD','MVV','UWM','DDM','USD','ROM','UYG','DIG','UXI','UBT','UST','UUP','SDS','QID','TWM','DXD'],
    'NASDAQ-100': ['AAPL','ABNB','ADBE','ADP','ADSK','AEP','ALGN','AMAT','AMD','AMGN','AMZN','ASML','AVGO','AZO','BKNG','CDNS','CDW','CHTR','CMCSA','CRWD','CSX','CTAS','CTSH','DASH','DDOG','DLTR','DXCM','EA','EBAY','EXC','FAST','FISV','FTNT','GEHC','GEN','GOOG','GOOGL','HON','HPQ','IDXX','ILMN','INCY','INTC','INTU','ISRG','JD','JNJ','JPM','KDP','KLAC','LRCX','LULU','MAR','MDLZ','META','MNST','MO','MRVL','MSFT','MU','NFLX','NKE','NVDA','NXPI','ODFL','OKTA','ON','ORLY','PANW','PAYX','PCAR','PEP','PTC','PYPL','QCOM','RIVN','ROST','SBUX','SNPS','SOFI','SPLK','TEAM','TMUS','TRMB','TSLA','TTD','TTWO','TXN','UAL','UBER','V','VRSK','VRTX','WBA','WDAY','XEL'],

    '全部': [],

}











all_tw = []

seen = set()

for v in TW_CATS.values():

    for c in v:

        if c not in seen:

            seen.add(c)

            all_tw.append(c)

TW_CATS["全部"] = sorted(all_tw, key=lambda x: (0, int(x)) if x.isdigit() else (1, x))[:999]



all_us = []

seen = set()

for v in US_CATS.values():

    for c in v:

        if c not in seen:

            seen.add(c)

            all_us.append(c)

US_CATS["全部"] = sorted(all_us, key=lambda x: x)[:999]



TW_NAMES = {

    "2330": "台積電", "2454": "聯發科", "2317": "鴻海", "2382": "廣達",

    "3034": "緯穎", "3665": "穎崴", "2881": "富邦金", "2603": "長榮",

    "2303": "聯電", "1216": "統一", "0050": "元大台灣50", "0056": "元大高股息",

    "00646": "富邦S&P500", "00662": "富邦NASDAQ", "00713": "元大高息低波",

    "00757": "統一大FANG+", "00927": "統一手創未來", "00878": "國泰永續高股息",

    "00900": "富邦ESG", "00902": "兆豐藍籌", "00906": "凱基優選高股息",

    "3217": "3217", "2401": "2401", "3527": "3527", "4749": "美時",

    "6819": "6819", "6229": "6229", "6786": "6786", "6563": "6563",

    "5351": "5351", "4923": "4923", "3265": "3265",

}

US_NAMES = {

    # S&P 500 stocks

    "NVDA": "NVIDIA", "AVGO": "Broadcom", "AMD": "AMD", "MRVL": "Marvell", "MU": "Micron",

    "INTC": "Intel", "QCOM": "Qualcomm", "AMAT": "Applied Mat", "LRCX": "Lam Research",

    "KLAC": "KLA", "SNPS": "Synopsys", "CDNS": "Cadence", "NXPI": "NXP", "ASML": "ASML",

    "TSM": "TSM", "TXN": "Texas Instr", "ADI": "Analog Devices", "MPWR": "Monolithic Power",

    "TER": "Teradyne", "MCHP": "Microchip", "ON": "ON Semi", "CRDO": "Credo", "ALAB": "Astera Labs",

    "ENTG": "Entegris", "MTSI": "MACOM", "ASX": "ASE Tech",

    # XPU / Design

    "ARM": "ARM",

    # 光通訊 / CPO

    "ANET": "Arista", "CSCO": "Cisco", "COHR": "Coherent", "LITE": "Lumentum", "GLW": "Corning",

    # 記憶體 / 儲存

    "WDC": "Western Digital", "STX": "Seagate",

    # 電力 / 散熱

    "VRT": "Vertiv", "ETN": "Eaton", "AMSC": "AMSC", "SBGSY": "Schneider", "NVT": "nVent",

    # 先進封裝 / 雲端

    "AMKR": "Amkor", "EQIX": "Equinix", "DLR": "Digital Realty", "ORCL": "Oracle",

    # AI 雲端

    "AMZN": "Amazon", "MSFT": "Microsoft", "GOOGL": "Google", "META": "Meta", "DELL": "Dell",

    # 5G

    "NOK": "Nokia", "ERIC": "Ericsson", "SWKS": "Skyworks", "RF": "RF Micro",

    "VZ": "Verizon", "T": "AT&T", "TMUS": "T-Mobile",

    # 設備

    "CAMT": "Camtek",

    # FinTech

    "PYPL": "PayPal", "SQ": "Block", "AFRM": "Affirm", "COIN": "Coinbase", "HOOD": "Robinhood",

    "DB": "Deutsche Bank", "BAC": "Bank of America", "GS": "Goldman", "V": "Visa", "MA": "Mastercard",

    # 其他

    "SMCI": "SuperMicro", "AI": "C3.ai", "DT": "Dynatrace",

    # ─── ETF - 指數核心 ───

    'VOO': "Vanguard S&P 500", 'IVV': "iShares Core S&P 500", 'SPY': "SPDR S&P 500", 'VTI': "Vanguard 全美市場",

    # ─── ETF - 科技與成長 ───

    'QQQ': "Invesco QQQ", 'VUG': "Vanguard Growth", 'SOXX': "iShares 半導體", 'SMH': "VanEck 半導體",

    # ─── ETF - 股息與價值 ───

    'SCHD': "Schwab 高股息", 'VYM': "Vanguard 高殖利率", 'VTV': "Vanguard Value", 'DGRO': "iShares 股息增長",

    # ─── ETF - 債券與配置 ───

    'BND': "Vanguard 綜合債券", 'TLT': "iShares 長天期美債", 'SHY': "iShares 短天期美債", 'AGG': "iShares 綜合債",

    # ─── ETF - 全球與其他 ───

    'VT': "Vanguard 全球股票", 'VXUS': "Vanguard 非美股市", 'VWO': "Vanguard 新興市場",

    # 舊 ETF

    # ─── 2x Leveraged ETF ───

    'SSO': "ProShares 2x S&P500", 'QLD': "ProShares 2x QQQ", 'MVV': "ProShares 2x MidCap400", 'UWM': "ProShares 2x Russell2000", 'DDM': "ProShares 2x Dow30",

    'USD': "ProShares 2x 半導體", 'ROM': "ProShares 2x 科技", 'UYG': "ProShares 2x 金融", 'DIG': "ProShares 2x 油氣", 'UXI': "ProShares 2x 工業",

    'UBT': "ProShares 2x 長債", 'UST': "ProShares 2x 中債", 'UUP': "Invesco 美元指數",

    'SDS': "ProShares -2x S&P500", 'QID': "ProShares -2x QQQ", 'TWM': "ProShares -2x Russell2000", 'DXD': "ProShares -2x Dow30",

}



def calc_rsi(close, period=14):

    delta = close.diff()

    gain = delta.where(delta > 0, 0).rolling(period).mean()

    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()

    rs = gain / loss.replace(0, np.nan)

    return 100 - (100 / (1 + rs))



def calc_rsi_simple(close, period=14):

    delta = close.diff()

    gain = delta.where(delta > 0, 0).rolling(period).mean()

    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()

    rs = gain / loss.replace(0, np.nan)

    rsi_vals = 100 - (100 / (1 + rs))

    return float(rsi_vals.iloc[-1]) if len(rsi_vals) > 0 else 50



def get_tier(rsi):

    if rsi < 35: return "A"

    if rsi < 50: return "B"

    if rsi < 70: return "C"

    return "D"



def calc_macd(close):

    ema_fast = close.ewm(span=12, adjust=False).mean()

    ema_slow = close.ewm(span=26, adjust=False).mean()

    macd = ema_fast - ema_slow

    macd_signal = macd.ewm(span=9, adjust=False).mean()

    return float(macd.iloc[-1]), float(macd_signal.iloc[-1]), float((macd - macd_signal).iloc[-1])



# ── Vegas Tunnel (EMA 144/169/576/676 + EMA 12 Filter) ─────────────────────
def vegas_tunnel(code, market='TW'):
    import numpy as np
    try:
        sym = code + ".TW" if market == 'TW' else code
        try:
            df2 = yf.Ticker(sym).history(period="2y", interval="1d", auto_adjust=True)
        except Exception:
            df2 = yf.Ticker(sym).history(period="1y", interval="1d", auto_adjust=True)
        if df2 is None or df2.empty or len(df2) < 100:
            return None
        close = df2['Close'].astype(float).dropna()
        price = float(close.iloc[-1])
        prev  = float(close.iloc[-2]) if len(close) >= 2 else price
        chg   = (price - prev) / prev * 100
        for m in [12, 144, 169, 576, 676]:
            df2['EMA' + str(m)] = df2['Close'].ewm(span=m).mean()
        cur   = df2.iloc[-1]
        prev2 = df2.iloc[-2] if len(df2) > 1 else cur
        ema12  = float(cur['EMA12'])
        ema144 = float(cur['EMA144'])
        ema169 = float(cur['EMA169'])
        ema576 = float(cur['EMA576'])
        ema676 = float(cur['EMA676'])
        if any(np.isnan(x) for x in [ema12, ema144, ema169, ema576, ema676]):
            return None
        h1_above_h4 = (ema144 > ema576) and (ema169 > ema676)
        h1_below_h4 = (ema144 < ema576) and (ema169 < ema676)
        if h1_above_h4: bias = 'BULL'
        elif h1_below_h4: bias = 'BEAR'
        else: bias = 'NEUTRAL'
        price_above   = (price > ema144) and (price > ema169)
        ema12_above   = (ema12 > ema144) and (ema12 > ema169)
        ema12_cross_up = (float(prev2['EMA12']) <= float(prev2['EMA144'])) and (ema12 > ema144)
        ema12_inside   = (min(ema144, ema169) < ema12 < max(ema144, ema169))
        tunnel_w = abs(ema144 - ema169)
        tp1 = round(float(price + tunnel_w * 0.55), 2)
        tp2 = round(float(price + tunnel_w * 0.89), 2)
        tp3 = round(float(price + tunnel_w * 1.44), 2)
        tp4 = round(float(price + tunnel_w * 2.33), 2)
        sl_long = round(float(min(ema144, ema169)), 2)
        sl_pct  = round((price - sl_long) / price * 100, 2)
        if bias == 'NEUTRAL':
            signal, sig_color = 'NEUTRAL', 'gray'
        elif bias == 'BULL' and price_above and ema12_above:
            signal, sig_color = 'BUY', 'green'
        elif bias == 'BULL' and price_above and not ema12_above:
            signal, sig_color = 'PULLBACK', 'blue'
        elif bias == 'BULL' and ema12_inside:
            signal, sig_color = 'INSIDE_TUNNEL', 'orange'
        elif bias == 'BEAR' and not price_above:
            signal, sig_color = 'SELL', 'red'
        elif price_above and not ema12_above:
            signal, sig_color = 'FAKEOUT', 'orange'
        else:
            signal, sig_color = 'NO_SIGNAL', 'gray'
        bias_sc = 2 if bias == 'BULL' else (-2 if bias == 'BEAR' else 0)
        brk_sc  = 3 if (price_above and ema12_above) else (1 if price_above else 0)
        dist_sc = min(5, int((price / min(ema144, ema169) - 1) * 100 / 5))
        score   = int((bias_sc + brk_sc + dist_sc) * 10)
        return dict(
            price=price, chg=chg, bias=bias, signal=signal, sig_color=sig_color,
            score=score, ema12=ema12, ema144=ema144, ema169=ema169,
            ema576=ema576, ema676=ema676,
            price_vs_144=round((price/ema144-1)*100,2),
            price_vs_169=round((price/ema169-1)*100,2),
            ema12_vs_144=round((ema12/ema144-1)*100,2),
            tunnel_w=round(float(tunnel_w),2),
            sl_long=sl_long, sl_pct=sl_pct,
            tp1=tp1, tp2=tp2, tp3=tp3, tp4=tp4,
            price_above=price_above, ema12_above=ema12_above,
            ema12_cross_up=ema12_cross_up, ema12_inside=ema12_inside,
            h1_above_h4=h1_above_h4, h1_below_h4=h1_below_h4,
        )
    except Exception:
        return None


# ── Data Fetch ──────────────────────────────────────────────────────────────




def fetch_institutional(code):
    from datetime import datetime, timedelta
    """Fetch F/T/D from FinMind TaiwanStockInstitutionalInvestorsBuySell (30-min cache)"""
    # ── Check cache first ─────────────────────────────────────────────
    now = time.time()
    if code in INST_CACHE:
        ts, cached = INST_CACHE[code]
        if now - ts < INST_CACHE_TTL:
            _log.debug("[fetch_institutional] " + code + " CACHE HIT")
            return cached
        else:
            del INST_CACHE[code]
    _log.info("[fetch_institutional] " + str(code) + " cache miss, fetching... token_set=" + str(bool(FINMIND_TOKEN)))
    try:

        import urllib.request

        params = {

            'dataset': 'TaiwanStockInstitutionalInvestorsBuySell',

            'data_id': str(code).zfill(4),

            'start_date': (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'),

            'end_date': datetime.now().strftime('%Y-%m-%d'),

            'token': FINMIND_TOKEN

        }

        url = 'https://api.finmindtrade.com/api/v4/data?' + '&'.join(f'{k}={v}' for k, v in params.items())

        with urllib.request.urlopen(url, timeout=8) as resp:

            data = json.loads(resp.read())

            rows = data.get('data', [])

            if not rows:

                return None

            latest_date = max(r['date'] for r in rows)

            day_rows = [r for r in rows if r['date'] == latest_date]

            result = {'foreign': 0, 'trust': 0, 'dealer': 0}

            for r in day_rows:

                name = r.get('name', '')

                net = r.get('buy', 0) - r.get('sell', 0)

                if name == 'Foreign_Investor':

                    result['foreign'] = net

                elif name == 'Investment_Trust':

                    result['trust'] = net

                elif 'Dealer' in name:

                    result['dealer'] += net

            _log.info("[fetch_institutional] " + str(code) + " success=" + str(result))
            INST_CACHE[code] = (now, result)  # Cache for 30 min
            return result

    except Exception as e:
        _log.error("[fetch_institutional] " + str(code) + " error=" + str(e))
        return None



def fetch_price(code, market='TW'):
    cache_key = f"{market}:{code}"
    now = time.time()
    if cache_key in SESSION_CACHE:
        ts, cached_h = SESSION_CACHE[cache_key]
        if now - ts < CACHE_TTL:
            return cached_h
    # ── 優先：Shioaji kbars（TW only）──────────────────────────
    if market == 'TW':
        try:
            kb = sj_get_kbars(code, days=180)
            if kb and 'Close' in kb and len(kb['Close']) >= 30:
                import pandas as pd
                df = pd.DataFrame(kb)
                df['Datetime'] = pd.to_datetime(df['ts'], unit='ns')
                df = df.set_index('Datetime').sort_index()
                SESSION_CACHE[cache_key] = (now, df)
                _log.info("[fetch_price] " + code + " from Shioaji (rows=" + str(len(df)) + ")")
                return df
        except Exception as e:
            _log.debug("[fetch_price] Shioaji failed " + code + ": " + str(e))
    # ── 備援：yfinance ─────────────────────────────────────────
    try:
        if market == 'TW':
            code_str = str(code)
            has_letter = any(c.isalpha() for c in code_str)
            for suffix in ['.TW', '.TWO']:
                sym = code_str + suffix if has_letter else code_str.zfill(4) + suffix
                h = yf.Ticker(sym).history(period='6mo')
                if h is not None and len(h) >= 10:
                    SESSION_CACHE[cache_key] = (now, h)
                    return h
        else:
            h = yf.Ticker(code).history(period='6mo')
            if h is not None and len(h) >= 30:
                SESSION_CACHE[cache_key] = (now, h)
                return h
    except:
        pass
    return None



def analyze(code, market='TW'):

    name = (TW_NAMES if market == 'TW' else US_NAMES).get(code, code)

    price_hist = fetch_price(code, market)

    if price_hist is None:

        return None

    inst = fetch_institutional(code) if market == 'TW' else None

    try:

        close = price_hist['Close'].astype(float).dropna()

        if len(close) < 2:
            return None

        price = float(close.iloc[-1])

        prev = float(close.iloc[-2]) if len(close) >= 2 else price

        chg = (price - prev) / prev * 100

        rsi = float(calc_rsi(close).iloc[-1])

        if np.isnan(rsi): rsi = 50.0

        ma20 = float(close.rolling(20).mean().iloc[-1])

        ma60_val = float(close.rolling(60).mean().iloc[-1])

        ma60 = ma60_val if not np.isnan(ma60_val) else None

        ma_bull = bool(ma60 and ma20 > ma60)

        macd_val, macd_sig, macd_hist = calc_macd(close)

        macd_bull = macd_hist > 0

        low9 = close.rolling(9).min()

        high9 = close.rolling(9).max()

        rsv = (close - low9) / (high9 - low9 + 1e-9) * 100

        k_series = rsv.ewm(alpha=1/3).mean()

        d_series = k_series.ewm(alpha=1/3).mean()

        k_val = float(k_series.iloc[-1])

        d_val = float(d_series.iloc[-1])

        kd_golden = bool(k_val > d_val and k_val < 30)

        bb_ma20 = close.rolling(20).mean()

        bb_std = close.rolling(20).std()

        bb_upper = float((bb_ma20 + 2 * bb_std).iloc[-1])

        bb_lower = float((bb_ma20 - 2 * bb_std).iloc[-1])

        bb_pct = (price - bb_lower) / (bb_upper - bb_lower + 1e-9) * 100

        ma5 = close.rolling(5).mean()

        bias5 = float((close.iloc[-1] - ma5.iloc[-1]) / ma5.iloc[-1] * 100)

        vol = price_hist['Volume'] if 'Volume' in price_hist.columns else close * 0

        vol_ma5 = float(vol.rolling(5).mean().iloc[-1])

        vol_ratio = float(vol.iloc[-1] / vol_ma5) if vol_ma5 > 0 else 1.0

        bullish = "Y" if (ma_bull and macd_bull) else ("W" if macd_bull else "N")

        # ── Tina Brain v2.0 Scoring (1000 max) ─────────────────────

        # RSI: 200 | MACD: 200 | K: 150 | D: 100 | BB%: 150 | MA: 100 | Vol: 50 | Trend: 150

        # Key principle: reward STRENGTH not WEAKNESS



        # RSI: 200pts — reward moderate (45-55 = best), reduce oversold reward

        if 45 <= rsi <= 55:

            rsi_s = 200

        elif 40 <= rsi < 45:

            rsi_s = 150

        elif 55 < rsi <= 60:

            rsi_s = 130

        elif 35 <= rsi < 40:

            rsi_s = 100

        elif 60 < rsi <= 65:

            rsi_s = 80

        elif rsi < 30:

            rsi_s = 60   # oversold but NOT automatically a buy signal

        elif 30 <= rsi < 35:

            rsi_s = 80

        elif 65 < rsi <= 70:

            rsi_s = 30

        else:

            rsi_s = 0



        # MACD: 200pts — require STRENGTH, not just >0

        if macd_hist > 2:

            macd_s = 200

        elif macd_hist > 1.5:

            macd_s = 170

        elif macd_hist > 1.0:

            macd_s = 140

        elif macd_hist > 0.5:

            macd_s = 100

        elif macd_hist > 0:

            macd_s = 50    # just positive = marginal

        elif macd_hist > -1:

            macd_s = 20

        else:

            macd_s = 0



        # K: 150pts — reward MOMENTUM (40-70 = strongest), low K = weakness

        if 45 <= k_val <= 70:

            k_s = 150

        elif 35 <= k_val < 45:

            k_s = 110

        elif 70 < k_val <= 80:

            k_s = 100

        elif 25 <= k_val < 35:

            k_s = 60

        elif k_val < 25:

            k_s = 20    # low K = weak momentum

        else:

            k_s = 0



        # D: 100pts — same logic, mid-range = strong

        if 45 <= d_val <= 70:

            d_s = 100

        elif 35 <= d_val < 45:

            d_s = 70

        elif 70 < d_val <= 80:

            d_s = 60

        elif 25 <= d_val < 35:

            d_s = 40

        elif d_val < 25:

            d_s = 10

        else:

            d_s = 0



        # BB%: 150pts — reward NORMAL range (20-45), extremes get less

        if 20 <= bb_pct <= 45:

            bb_s = 150

        elif 10 <= bb_pct < 20:

            bb_s = 100

        elif 45 < bb_pct <= 60:

            bb_s = 100

        elif 5 <= bb_pct < 10:

            bb_s = 50

        elif 60 < bb_pct <= 80:

            bb_s = 50

        else:

            bb_s = 20



        # MA multi-tier: 100pts

        ma5_val = float(ma5.iloc[-1]) if not np.isnan(float(ma5.iloc[-1])) else price

        if ma5_val > ma20 > (ma60 or 0):

            ma_s = 100   # 3-tier bullish

        elif ma20 > (ma60 or 0):

            ma_s = 60    # 2-tier bullish

        else:

            ma_s = 0



        # Vol: 50pts — add finer granularity

        if vol_ratio >= 2.5:

            vol_s = 50

        elif vol_ratio >= 2.0:

            vol_s = 45

        elif vol_ratio >= 1.5:

            vol_s = 35

        elif vol_ratio >= 1.2:

            vol_s = 25

        elif vol_ratio >= 1.0:

            vol_s = 15

        elif vol_ratio >= 0.8:

            vol_s = 5

        else:

            vol_s = 0

        score = rsi_s + macd_s + k_s + d_s + bb_s + ma_s + vol_s

        # Grade from score (v2.0 — stricter thresholds)

        if score >= 750:

            tier = "A"

        elif score >= 550:

            tier = "B"

        elif score >= 350:

            tier = "C"

        else:

            tier = "D"

        return {

            'code': code, 'name': name,

            'price': price, 'chg': chg, 'rsi': rsi,

            'macd': macd_val, 'macd_sig': macd_sig, 'macd_hist': macd_hist,

            'ma20': ma20, 'ma60': ma60, 'ma20_above_ma60': ma_bull,

            'k': k_val, 'd': d_val, 'kd_golden': kd_golden,

            'bb_upper': bb_upper, 'bb_lower': bb_lower, 'bb_pct': bb_pct,

            'bias5': bias5, 'vol_ratio': vol_ratio,

            'bullish': bullish,

            'inst': inst,

            'score': score, 'tier': tier,

            'score_breakdown': {'rsi': rsi_s, 'macd': macd_s, 'k': k_s, 'd': d_s, 'bb': bb_s, 'ma': ma_s, 'vol': vol_s},

        }

    except:

        return None



# ── Page Setup ──────────────────────────────────────────────────────────────

st.markdown(""""
<style>
.metric-card { background-color:white; padding:20px; border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,0.08); border-left:5px solid #1E88E5; }
[data-testid="stMainBlockContainer"] { padding-top:1rem; }
</style>
""", unsafe_allow_html=True)

st.set_page_config(page_title="Tina Scanner v3.1", page_icon="📈", layout="wide")

st.title("[UP] Tina Scanner v3.1 — TW+US Tech Scoring")
_log.info("[UI] Page setup complete")



tw_tab, us_tab = st.tabs(["📊 Taiwan", "🇺🇸 US"])

# ── Market Overview ──────────────────────────────────────────────────────

try:

    twii = yf.Ticker("^TWII")

    twii_hist = twii.history(period="1mo")

    spy = yf.Ticker("^GSPC")

    spy_hist = spy.history(period="1mo")

    if not twii_hist.empty and not spy_hist.empty:

        # TW market

        twii_close = twii_hist['Close'].iloc[-1]

        twii_prev = twii_hist['Close'].iloc[-2]

        twii_chg = (twii_close - twii_prev) / twii_prev * 100

        twii_rsi = None

        if len(twii_hist) >= 15:

            d = twii_hist['Close'].diff()

            g = d.clip(lower=0).rolling(14).mean()

            l = (-d.clip(upper=0)).rolling(14).mean()

            rs = g / l.replace(0, np.nan)

            twii_rsi_val = 100 - (100 / (1 + rs))
            twii_rsi = float(twii_rsi_val.iloc[-1]) if len(twii_rsi_val) > 0 and not twii_rsi_val.iloc[-1] != twii_rsi_val.iloc[-1] else None

        # US market (S&P 500)

        spy_close = spy_hist['Close'].iloc[-1]

        spy_prev = spy_hist['Close'].iloc[-2]

        spy_chg = (spy_close - spy_prev) / spy_prev * 100

        spy_rsi = None

        if len(spy_hist) >= 15:

            d2 = spy_hist['Close'].diff()

            g2 = d2.clip(lower=0).rolling(14).mean()

            l2 = (-d2.clip(upper=0)).rolling(14).mean()

            rs2 = g2 / l2.replace(0, np.nan)

            spy_rsi_val = 100 - (100 / (1 + rs2))
            spy_rsi = float(spy_rsi_val.iloc[-1]) if len(spy_rsi_val) > 0 and not spy_rsi_val.iloc[-1] != spy_rsi_val.iloc[-1] else None

        rsi_label_tw = "[ERR] 過熱" if twii_rsi and twii_rsi > 70 else ("[Y] 偏多" if twii_rsi and twii_rsi > 50 else "[G] 中性")

        rsi_label_us = "[ERR] 過熱" if spy_rsi and spy_rsi > 70 else ("[Y] 偏多" if spy_rsi and spy_rsi > 50 else "[G] 中性")

        m = st.columns(6)

        m[0].metric("TWII", f"{twii_close:,.0f}", f"{twii_chg:+.2f}%")

        m[1].metric("TWII RSI", f"{twii_rsi:.0f}" if twii_rsi else "N/A")

        m[2].metric("TW狀態", rsi_label_tw)

        m[3].metric("S&P500", f"{spy_close:,.0f}", f"{spy_chg:+.2f}%")

        m[4].metric("SPY RSI", f"{spy_rsi:.0f}" if spy_rsi else "N/A")

        m[5].metric("US狀態", rsi_label_us)

except Exception:

    pass



# ═══════════════════════════ TW TAB ═══════════════════════════

with tw_tab:

    col_side, col_main = st.columns([1, 4], vertical_alignment="top")

    with col_side:

        st.header("Filters")

        tw_cat = st.selectbox("Category", list(TW_CATS.keys()), key="tw_cat")

        with st.form(key="grade_filter_tw"):
            st.markdown("**評級**")
            g1, g2, g3, g4, gall = st.columns([1,1,1,1,1])
            g_a = g1.checkbox("A", value=True, key="tw_grade_a")
            g_b = g2.checkbox("B", value=True, key="tw_grade_b")
            g_c = g3.checkbox("C", value=True, key="tw_grade_c")
            g_d = g4.checkbox("D", value=True, key="tw_grade_d")
            if gall.form_submit_button("全", help="Select All", width='stretch'):
                pass  # Checkbox values are auto-managed by Streamlit via key=
            tw_grade = [g for g, on in zip(["A","B","C","D"], [g_a, g_b, g_c, g_d]) if on]

        tw_score_min = st.slider("Score Min", 0, 1000, 0, key="tw_score")
        tw_rsi_max = st.slider("RSI Max", 30, 100, 100, key="tw_rsi")

        tw_macd_filter = st.checkbox("排除 MACD < 0", value=False, key="tw_macd_filter")

        codes = TW_CATS.get(tw_cat, [])

        st.info(f"{len(codes)} stocks")

        analyze_tw = st.button("Analyze", type="primary", width='stretch', key="btn_tw_analyze")
        _log.info("[UI] TW Analyze button ready")



    if 'tw_results' not in st.session_state:

        st.session_state.tw_results = None

        st.session_state.tw_filtered = None

        st.session_state.tw_cat_saved = None



    if analyze_tw:

        with st.spinner("Analyzing + Fetching Institutional..."):

            def _analyze_one(idx_code):

                i, code = idx_code

                return i, analyze(code, 'TW')

            results = []

            bar = st.progress(0)

            total = len(codes)

            with ThreadPoolExecutor(max_workers=8) as pool:

                futures = {pool.submit(_analyze_one, (i, code)): i for i, code in enumerate(codes)}

                for future in as_completed(futures):

                    try:

                        i, r = future.result()

                        if r:

                            results.append((i, r))

                    except Exception:

                        pass

                    bar.progress(min(len(results) + 1, total) / total)

            results.sort(key=lambda x: x[0])

            results = [r for _, r in results]

            bar.empty()
            _log.info(f"[batch] TW done total={len(results)}")

            filtered = [r for r in results

                        if r['rsi'] <= tw_rsi_max

                        and r['tier'] in tw_grade

                        and r['score'] >= tw_score_min

                        and (not tw_macd_filter or r['macd_hist'] >= 0)]

            filtered.sort(key=lambda x: x['score'], reverse=True)

            st.session_state.tw_results = results

            st.session_state.tw_filtered = filtered

            st.session_state.tw_cat_saved = tw_cat



    results = st.session_state.tw_results

    filtered = st.session_state.tw_filtered

    cat_saved = st.session_state.tw_cat_saved



    if results:

        a = sum(1 for r in filtered if r['tier'] == 'A')

        b = sum(1 for r in filtered if r['tier'] == 'B')

        c = sum(1 for r in filtered if r['tier'] == 'C')

        d = sum(1 for r in filtered if r['tier'] == 'D')

        bull = sum(1 for r in filtered if r['bullish'] == 'Y')

        kd = sum(1 for r in filtered if r['kd_golden'])

        m = st.columns(6)

        m[0].metric("A", a)

        m[1].metric("B", b)

        m[2].metric("C", c)

        m[3].metric("D", d)

        m[4].metric("BULL", bull)

        m[5].metric("KD+", kd)

        st.success(f"{len(results)} stocks | {len(filtered)} after filter")
        st.toast(f"掃描完成！ {len(results)} 檔 ({len(filtered)} 通過篩選)", icon="✅")



    if filtered:

        rows = []

        for r in filtered:

            inst = r.get('inst') or {}

            f_val = inst.get('foreign', 0)

            t_val = inst.get('trust', 0)

            d_val = inst.get('dealer', 0)

            rows.append({

                "Score": f"{r['score']:.0f}",

                "Code": r['code'],

                "Name": r['name'],

                "Price": f"${r['price']:.2f}",

                "Chg%": f"{r['chg']:+.2f}%",

                "RSI": f"{r['rsi']:.0f}",

                "K": f"{r['k']:.0f}",

                "D": f"{r['d']:.0f}",

                "BB%": f"{r['bb_pct']:.0f}%",

                "BIAS5": f"{r['bias5']:+.1f}%",

                "Vol": f"{r['vol_ratio']:.1f}x",

                "MA": "Y" if r['ma20_above_ma60'] else "N",

                "F": f"{f_val:+,}" if f_val != 0 else "-",

                "T": f"{t_val:+,}" if t_val != 0 else "-",

                "D": f"{d_val:+,}" if d_val != 0 else "-",

                "Tier": r['tier'],

            })

        df = pd.DataFrame(rows)

        st.dataframe(
            df,
            column_config={
                "Score": st.column_config.NumberColumn("評分", format="%.0f", min_value=0, max_value=1000),
                "Chg%": st.column_config.TextColumn("漲跌%"),
                "RSI":  st.column_config.TextColumn("RSI"),
                "Tier": st.column_config.TextColumn("評級"),
                "Code": st.column_config.TextColumn("代碼"),
                "Price": st.column_config.NumberColumn("現價", format="%.2f"),
                "MA":   st.column_config.TextColumn("MA20>60"),
                "F":    st.column_config.TextColumn("外資"),
                "T":    st.column_config.TextColumn("投信"),
                "Vol":  st.column_config.TextColumn("量比"),
            },
            use_container_width=True,
            hide_index=True,
        )



        with st.expander("Send to Telegram"):

            grade_filter = st.multiselect("Grade Filter", ["A","B","C","D"], default=["A","B","C","D"], key="tw_grade_send")

            grade_filtered = [r for r in filtered if r['tier'] in grade_filter]

            sel = st.multiselect("Select", [f"[{r['tier']}] S={r['score']:.0f} {r['code']} ${r['price']:.0f}" for r in grade_filtered], key="tw_sel")

            sel_rows = [r for r in grade_filtered if f"[{r['tier']}] S={r['score']:.0f} {r['code']} ${r['price']:.0f}" in sel]

            sc = len(sel_rows)

            r1, r2 = st.columns(2)

            if r1.button(f"Send ({sc}) Grade {','.join(grade_filter)}", disabled=(sc==0), width='stretch', key="tw_batch_send"):

                with st.spinner("Sending..."):

                    chunks = format_telegram(sel_rows, f"TW-{cat_saved} ({','.join(grade_filter)})")

                    ok_all = True

                    for chunk in chunks:

                        ok, err = push_telegram(chunk)

                        if not ok:

                            ok_all = False

                            st.error(f"Error: {err}")

                            break

                    if ok_all:

                        st.success(f"Sent {sc} stocks ({len(chunks)} msgs)")
                        st.toast(f"已發送 {sc} 檔分析到 Telegram", icon="📤")

            if r2.button(f"Send All ({len(grade_filtered)}) Grade {','.join(grade_filter)}", width='stretch'):

                with st.spinner("Sending..."):

                    chunks = format_telegram(grade_filtered, f"TW-{cat_saved} ({','.join(grade_filter)})")

                    ok_all = True

                    for chunk in chunks:

                        ok, err = push_telegram(chunk)

                        if not ok:

                            ok_all = False

                            st.error(f"Error: {err}")

                            break

                    if ok_all:

                        st.success(f"Sent {len(grade_filtered)} stocks ({len(chunks)} msgs)")
                        st.toast(f"已發送 {len(grade_filtered)} 檔到 Telegram", icon="📤")



        if results:

            csv = pd.DataFrame(results).to_csv(index=False).encode('utf-8-sig')

            st.download_button("CSV", csv, f"tw_{cat_saved}_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", key="tw_csv")



    # --- Auto-Send Toggle ---

    if 'tw_auto_send' not in st.session_state:

        st.session_state['tw_auto_send'] = False

    auto_col, spacer = st.columns([2, 1])

    with auto_col:

        st.session_state['tw_auto_send'] = st.toggle('分析後自動發送 Telegram', value=st.session_state['tw_auto_send'], key='tw_auto_send_toggle')

    with spacer:

        st.caption('ON = 自動發送' if st.session_state.get('tw_auto_send') else 'OFF = 手動發送')



    # --- Single Stock Deep Analysis ---

    st.divider()

    st.subheader("Single Stock Deep Analysis")

    col_code, col_btn = st.columns([2, 1])

    with col_code:

        single_code = st.text_input("Stock Code", "2330", key="tw_single_code").strip().upper()

    with col_btn:

        st.write(" ")

        do_single = st.button("Analyze", type="primary", width='stretch', key="btn_tw_single")

    if do_single or st.session_state.get('tw_analyzed', False):

        if do_single:
            with st.spinner(f"Analyzing {single_code}..."):
                r = analyze(single_code, "TW")
            st.session_state['tw_analyzed'] = True
        elif 'single_result' in st.session_state:
            r = st.session_state['single_result']
        else:
            r = None

        if r:

            st.session_state['single_result'] = r
            bd = r.get('score_breakdown', {})

            # ═══════════════════════════════════════
            #  ACTION BAR
            # ═══════════════════════════════════════
            score = r['score']
            tier  = r['tier']
            rsi_v = r['rsi']
            bb_v  = r['bb_pct']
            macd_v = r['macd_hist']
            ma_bull = r['ma20_above_ma60']
            kd_ok   = r['kd_golden']

            pos = (kd_ok*200)+(ma_bull*150)+((35<=rsi_v<=60)*100)+((macd_v>0)*140)+((20<=bb_v<=80)*100)
            pct = min(100, max(0, int(pos*100/690)))
            bar = "█"*(pct//10) + "░"*(10-pct//10)

            if kd_ok and ma_bull and macd_v>0 and rsi_v<65:
                act,col,trend = "強力买入","green","多頭"
            elif score>=700 and rsi_v<70:
                act,col,trend = "买入","blue","多頭"
            elif score>=400:
                act,col,trend = "觀望","gray","中性"
            elif rsi_v>80 or bb_v>90:
                act,col,trend = "過熱觀望","orange","警覺"
            else:
                act,col,trend = "減持","red","空頭"

            st.markdown(
                f"<big><b>「{r['code']} {r['name'][:8]}」</b></big>"
                f"&nbsp;&nbsp;Score {score}"
                f"&nbsp;&nbsp;<b>:color[{col}][{bar} {act}]</b>"
                f"&nbsp;&nbsp;{trend}趨勢",
                unsafe_allow_html=True)

            # ── Signal Badges ──
            sigs = []
            if r['kd_golden']:      sigs.append(("KD Golden","green"))
            if r['ma20_above_ma60']: sigs.append(("MA Bull","green"))
            if r['macd_hist']>0:    sigs.append(("MACD+","green"))
            if r['bb_pct']<20:     sigs.append(("BB Oversold","blue"))
            if r['bb_pct']>80:     sigs.append(("BB Overbought","red"))
            if r['rsi']<35:         sigs.append(("RSI Oversold","blue"))
            if r['rsi']>70:         sigs.append(("RSI Overbought","red"))
            if r['vol_ratio']>2.0: sigs.append(("Vol Surge","orange"))

            if sigs:
                tags = "  ".join([f":{c}[{l}]" for l,c in sigs])
                st.markdown(tags)
            else:
                st.caption("No signals")

            # ── Row 1: Price + RSI + K/D + BB% ──
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Price", f"${r['price']:.2f}", f"{r['chg']:+.2f}%")
            rsi_delta = rsi_v-50
            if rsi_v>70:       rsi_st = "過熱"
            elif rsi_v<35:    rsi_st = "超賣"
            else:              rsi_st = f"正常 {rsi_v:.0f}"
            c2.metric("RSI", f"{rsi_v:.0f}", f"{rsi_delta:+.0f}", help=f"Status: {rsi_st}")

            k_val,d_val = r['k'],r['d']
            kd_lbl = "Golden!" if kd_ok else f"{k_val:.0f}/{d_val:.0f}"
            c3.metric("K/D", kd_lbl, f"{k_val-d_val:+.0f}", help="K above D=bullish")

            bb_delta = bb_v-50
            if bb_v<20:       bb_st = "超賣"
            elif bb_v>80:     bb_st = "過熱"
            else:             bb_st = f"中立 {bb_v:.0f}%"
            c4.metric("BB%", f"{bb_v:.0f}%", f"{bb_delta:+.0f}", help=f"Status: {bb_st}")

            # ── Row 2: MA20 vs MA60 + MACD + Vol + BIAS ──
            d1,d2,d3,d4 = st.columns(4)
            ma_diff = r['ma20']-r['ma60'] if r.get('ma60') else 0
            ma_lbl = "MA Bull" if ma_bull else "MA Bear"
            d1.metric("MA20 vs MA60", ma_lbl, f"{ma_diff:+.1f}" if r.get('ma60') else "N/A")

            d2.metric("MACD Hist", f"{macd_v:+.2f}", f"{macd_v:+.2f}")

            vol_v = r['vol_ratio']
            vol_st = "高量" if vol_v>1.5 else "低量" if vol_v<0.8 else "正常"
            d3.metric("Vol Ratio", f"{vol_v:.1f}x", help=f"Status: {vol_st}")

            bias_v = r['bias5']
            bias_st = "偏離大" if abs(bias_v)>3 else "正常"
            d4.metric("BIAS5", f"{bias_v:+.1f}%", help=f"Status: {bias_st}")

            # ── Score Breakdown (color-coded inline) ──
            bd = r.get('score_breakdown', {})
            items = [
                ('RSI',  bd.get('rsi',0),  (35<=rsi_v<=60)),
                ('MACD', bd.get('macd',0), (macd_v>0)),
                ('K',    bd.get('k',0),    kd_ok),
                ('D',    bd.get('d',0),    not kd_ok),
                ('BB',   bd.get('bb',0),   (20<=bb_v<=80)),
                ('MA',   bd.get('ma',0),   ma_bull),
                ('Vol',  bd.get('vol',0),  (0.8<=vol_v<=1.5)),
            ]
            sb_parts = []
            for k,v,good in items:
                color = 'green' if good else 'gray'
                sb_parts.append(f":{color}[{k} {v}]")
            st.markdown("  ".join(sb_parts))

            # ── 📊 Technical Detail Button ──
            detail_key = f"detail_{single_code}"
            show_detail = st.button("📊 技術分析詳細解讀", key=f"btn_{detail_key}")

            if show_detail or st.session_state.get('detail_shown_' + single_code, False):
                st.session_state['detail_shown_' + single_code] = True

                def _s(tag, val, unit="", good=None):
                    col = "green" if good else ("orange" if good is False else "gray")
                    return f":{col}[{tag} {val}{unit}]"

                st.markdown("---")
                st.markdown("### 📈 技術指標詳細解析")

                # RSI Detail
                rsi_v = r['rsi']
                rsi_status = "過熱" if rsi_v > 70 else ("超賣" if rsi_v < 30 else ("偏低" if rsi_v < 40 else ("偏高" if rsi_v > 60 else "正常")))
                rsi_meaning = "動能過強，小心回調" if rsi_v > 70 else ("可能出現反彈機會" if rsi_v < 30 else ("評分偏低" if rsi_v < 40 else ("動能偏強" if rsi_v > 60 else "位於中性區間")))
                st.markdown(f"**RSI (相對強弱指標)** — 當前 `{rsi_v:.0f}` | 狀態: `{rsi_status}`")
                st.caption(f"📌 RSI 衡量價格變動頻率。>70超買（過熱），<30超賣。{rsi_meaning}。")
                st.progress(min(rsi_v / 100, 1.0), text=f"RSI: {rsi_v:.0f}/100")
                st.markdown("---")

                # MACD Detail
                macd_hist = r['macd_hist']
                macd_sig = r.get('macd_sig', 0)
                macd_status = "多頭" if macd_hist > 0 else "空頭"
                macd_color = "green" if macd_hist > 0 else "red"
                st.markdown(f"**MACD (平滑異同移動平均線)** — 柱狀 `{macd_hist:+.2f}` | 訊號線 `{macd_sig:+.2f}` | :{macd_color}[{macd_status}]")
                st.caption(f"📌 MACD = EMA12-EMA26。柱狀正值代表多頭動能，負值代表空頭動能。{'MACD > 0 = 上漲趨勢' if macd_hist > 0 else 'MACD < 0 = 下跌趨勢'}。")
                st.markdown("---")

                # K/D Detail
                k_val, d_val = r['k'], r['d']
                kd_ok = r['kd_golden']
                kd_status = "黃金交叉（多頭）" if kd_ok else ("死亡交叉（空頭）" if k_val < d_val else "整理中")
                st.markdown(f"**K/D (隨機指標)** — K=`{k_val:.0f}` D=`{d_val:.0f}` | 狀態: `{kd_status}`")
                st.caption(f"📌 K反映近期收盤價相對高低區間位置。K>D為多頭；K<30且K>D為黃金交叉預示反轉。{'K>D 且 K<30 = 即將反轉上漲' if kd_ok else ('K<D = 短線偏空' if k_val < d_val else 'K、D膠著中')}。")
                st.markdown("---")

                # MA Detail
                ma20_val = r['ma20']
                ma60_val = r.get('ma60', 0) or 0
                ma_status = "多頭排列" if r['ma20_above_ma60'] else "空頭排列"
                ma_color = "green" if r['ma20_above_ma60'] else "red"
                diff = ma20_val - ma60_val
                diff_pct = diff / ma60_val * 100 if ma60_val > 0 else 0
                st.markdown(f"**MA (均線多頭)** — MA20=`{ma20_val:.0f}` MA60=`{ma60_val:.0f}` | 差: `{diff:+.1f}` ({diff_pct:+.1f}%) | :{ma_color}[{ma_status}]")
                st.caption(f"📌 MA20>MA60代表中長期趨勢向上；MA20<MA60代表中長期趨勢向下。差超過2%代表趨勢明顯。{'完美多頭排列' if r['ma20_above_ma60'] else '空頭排列，中期趨勢向下'}。")
                st.markdown("---")

                # BB% Detail
                bb_v = r['bb_pct']
                bb_upper, bb_lower = r.get('bb_upper',0), r.get('bb_lower',0)
                bb_status = "超賣區間" if bb_v < 20 else ("過熱區間" if bb_v > 80 else "中立區間")
                st.markdown(f"**BB% (布林帶百分比)** — 當前 `{bb_v:.0f}%` (帶: {bb_lower:.0f}~{bb_upper:.0f}) | 狀態: `{bb_status}`")
                st.caption(f"📌 BB% = (現價-下軌)/(上軌-下軌)*100%。<20%超賣（支撐），>80%超買（回調風險）。{'價格接近下緣，可能有支撐' if bb_v < 20 else ('價格接近上緣，留意回調' if bb_v > 80 else '價格在布林帶中軸附近')}。")
                st.progress(min(bb_v / 100, 1.0), text=f"BB%: {bb_v:.0f}%")
                st.markdown("---")

                # BIAS5 Detail
                bias_v = r['bias5']
                bias_status = "偏離大" if abs(bias_v) > 3 else "正常"
                st.markdown(f"**BIAS5 (5日乖離率)** — 當前 `{bias_v:+.1f}%` | 狀態: `{bias_status}`")
                st.caption(f"📌 BIAS5 = (現價-MA5)/MA5*100%。>3%代表偏離均線過多遲早回調；<-3%代表嚴重超賣。{'價格偏離MA5過大，遲早回歸' if abs(bias_v) > 3 else '偏離程度正常'}。")
                st.markdown("---")

                # Vol Ratio Detail
                vol_v = r['vol_ratio']
                vol_status = "巨量" if vol_v > 2.5 else ("高量" if vol_v > 1.5 else ("低量" if vol_v < 0.8 else "正常量"))
                st.markdown(f"**Vol Ratio (量比)** — 當前 `{vol_v:.1f}x` | 狀態: `{vol_status}`")
                st.caption(f"📌 量比 = 今日量/5日均量。>1.5x為高量通常伴隨趨勢；<0.8x為低量動能不足。{'高量動能強' if vol_v > 1.5 else ('低量缺乏方向' if vol_v < 0.8 else '量能正常')}。")
                st.markdown("---")

                # Score / Tier
                score = r['score']
                tier = r['tier']
                tier_color = {"A":"green","B":"blue","C":"gray","D":"orange","F":"red"}.get(tier,"gray")
                st.markdown(f"**評分 / 等級** — Score: `{score}/1000` | 等級: :{tier_color}[{tier}]")
                thresholds = {"A":800,"B":600,"C":400,"D":200}
                next_tier = next((k for k,v in sorted(thresholds.items(), key=lambda x:x[1]) if score < v), "MAX")
                st.caption(f"📌 等級：A≥800 B≥600 C≥400 D≥200。距離{tier}需{abs(score - thresholds.get(tier, 0))}分，距{next_tier}還差{abs(score - thresholds.get(next_tier, 1000))}分。")
                st.markdown("---")

                # Overall Assessment
                st.markdown("### 🎯 綜合進場評估")
                bullish_count = sum([1 for sig in sigs if sig[1]=='green'])
                total_signals = len(sigs) if sigs else 0
                if total_signals == 0:
                    assessment = "⚠️ 無明確技術信號，建議觀望"
                    assessment_col = "gray"
                elif bullish_count >= 4:
                    assessment = "✅ 多項技術指標支撐，上漲機率高"
                    assessment_col = "green"
                elif bullish_count >= 2:
                    assessment = "🟡 部分指標支撐，可謹慎關注"
                    assessment_col = "blue"
                else:
                    assessment = "🔴 多數指標偏空，建議觀望或減持"
                    assessment_col = "red"
                st.markdown(f":{assessment_col}[{assessment}] ({bullish_count}/{total_signals} 項多頭信號)")

                # Risk warnings
                risks = []
                if rsi_v > 75: risks.append("RSI 過熱，回調風險高")
                if bb_v > 85: risks.append("BB% 接近上緣，過熱風險")
                if macd_hist < 0: risks.append("MACD 負值，空頭動能")
                if vol_v < 0.6: risks.append("成交量過低，動能不足")
                if not r['ma20_above_ma60']: risks.append("均線空頭排列，中期趨勢向下")
                if risks:
                    st.markdown("### ⚠️ 風險提示")
                    for risk in risks:
                        st.warning(f"⚠️ {risk}")

            # ── Institutional (TW only) ──
            inst = r.get("inst") or {}
            f_v = inst.get("foreign",0); t_v = inst.get("trust",0); d_v = inst.get("dealer",0)
            i1,i2,i3 = st.columns(3)
            i1.metric("Foreign", f"{f_v:+,.0f}")
            i2.metric("Trust",   f"{t_v:+,.0f}")
            i3.metric("Dealer",  f"{d_v:+,.0f}")

        if not r:
            st.warning("Please analyze a stock first")
        else:
            tier_icon = {"A": "A", "B": "B", "C": "C", "D": "X"}.get(r.get("tier","?"), "?")
            macd_hist = r.get("macd_hist", 0)
            tier_display = tier_icon if not (tier_icon == "A" and macd_hist < 0) else "B"
            score_detail = f"RSI={r['rsi']:.0f}/250 MACD={macd_hist:+.2f}/200 K={r['k']:.0f}/150 D={r['d']:.0f}/100 BB%={r['bb_pct']:.0f}/150 MA={'Y' if r['ma20_above_ma60'] else 'N'}/100 Vol={r['vol_ratio']:.1f}x/50"
            inst = r.get("inst") or {}
            f_val = inst.get("foreign",0); t_val = inst.get("trust",0); d_val = inst.get("dealer",0)
            msg = (
                f"[CHART] **{single_code} {r['name'][:12]}** Deep Analysis\n"
                f"-------------------\n"
                f"[MONEY] ${r['price']:.2f} ({r['chg']:+.2f}%)\n"
                f"[TROPHY] Tier: [{tier_display}] | Score: {r['score']:.0f}/1000\n"
                f"[UP] {score_detail}\n"
                f"[DWN] BIAS5={r['bias5']:+.1f}% Vol={r['vol_ratio']:.1f}x\n"
                f"[CHART] MA20={r['ma20']:.0f} MA60={r['ma60'] if r['ma60'] else 'N/A'}\n"
                f"[BOX] {r.get('bullish','N')} | {'KD Golden' if r['kd_golden'] else 'KD OK'}\n"
                f"Foreign:{f_val:+,} Trust:{t_val:+,} Dealer:{d_val:,}")

            # ── Vegas Tunnel Section ─────────────────────────────────────────────
            st.divider()
            st.subheader("Vegas Tunnel (EMA 144/169/576/676)")

            vegas_btn = st.button("Vegas 分析", key="btn_vegas_tw")
            if vegas_btn:
                with st.spinner("Computing Vegas Tunnel..."):
                    v = vegas_tunnel(single_code, "TW")
                if v:
                    st.session_state['vegas_result'] = v
                else:
                    st.error("無法取得 Vega 資料，請確認股票代碼")

            if 'vegas_result' in st.session_state:
                v = st.session_state['vegas_result']
                bias_icon = "BU" if v['bias'] == 'BULL' else ("RD" if v['bias'] == 'BEAR' else "YL")
                trend_str = v['bias'] + " Trend"
                st.markdown('**' + bias_icon + ' ' + trend_str + '** &nbsp;&nbsp; **:' + v['sig_color'] + '[' + v['signal'] + ']** &nbsp;&nbsp; Score ' + str(v['score']))

                e1, e2, e3, e4, e5 = st.columns(5)
                e1.metric("EMA12", str(round(v['ema12'],2)), str(round(v['ema12_vs_144'],2)) + "% vs 144")
                e2.metric("EMA144", str(round(v['ema144'],2)), str(round(v['price_vs_144'],1)) + "%")
                e3.metric("EMA169", str(round(v['ema169'],2)), str(round(v['price_vs_169'],1)) + "%")
                e4.metric("EMA576", str(round(v['ema576'],2)))
                e5.metric("EMA676", str(round(v['ema676'],2)))

                s1, s2, s3, s4 = st.columns(4)
                s1.metric("Price above", "Y" if v['price_above'] else "N")
                s2.metric("EMA12 above", "Y" if v['ema12_above'] else "N")
                s3.metric("EMA12 cross", "Y" if v['ema12_cross_up'] else "N")
                s4.metric("EMA12 inside", "Y" if v['ema12_inside'] else "N")

                t1, t2, t3, t4 = st.columns(4)
                t1.metric("Tunnel W", str(round(v['tunnel_w'],2)))
                t2.metric("Long SL", str(round(v['sl_long'],2)), "-" + str(round(v['sl_pct'],1)) + "%")
                t3.metric("TP1", str(round(v['tp1'],2)))
                t4.metric("TP2", str(round(v['tp2'],2)))

                t5, t6, t7, t8 = st.columns(4)
                t5.metric("TP3", str(round(v['tp3'],2)))
                t6.metric("TP4", str(round(v['tp4'],2)))
                t7.metric("H1>H4", "Y" if v['h1_above_h4'] else "N")
                t8.metric("Bias", v['bias'])

                sig_map = {
                    'BUY':          'BUY - 價格突破隧道且EMA12確認，多頭動能強，建議進場',
                    'PULLBACK':     'PULLBACK - 價格突破隧道但EMA12未確認，等待回調再進',
                    'INSIDE_TUNNEL':'INSIDE - 價格在隧道內震盪，觀望等待突破',
                    'FAKEOUT':      'FAKEOUT - 假突破！勿追單',
                    'SELL':         'SELL - 空頭趨勢，避免做多',
                    'NEUTRAL':      'NEUTRAL - 隧道糾結，觀望不交易',
                    'NO_SIGNAL':    'NO SIGNAL - 無明確信號，等待市場表態',
                }
                sig_txt = sig_map.get(v['signal'], v['signal'])
                st.info(sig_txt)
            else:
                st.caption("點擊「Vegas 分析」執行隧道分析")

            with st.form(key="tw_single_tg_form", clear_on_submit=False):
                st.write("DEBUG: TW Send form rendering")
                col1, _ = st.columns([1, 4])
                submitted = st.form_submit_button("Send Telegram", width='stretch')
                st.write(f"DEBUG: submitted={submitted}")
                if submitted:
                    st.info("TW form submitted!")
                    st.info(f"DEBUG chat_id={TELEGRAM_CHAT_ID} token_len={len(TELEGRAM_BOT_TOKEN)}")
                    try:
                        ok, err = push_telegram(msg)
                        st.info(f"ok={ok} err={err}")
                    except Exception as ex:
                        st.error(f"ex={ex}")
                    else:
                        if ok:
                            st.success("Telegram sent!")
                            st.toast("已發送單一股票分析到 Telegram", icon="📤")
                        else:
                            st.error(f"Failed: {err}")


# ═══════════════════════════ US TAB ═══════════════════════════

with us_tab:

    col_side, col_main = st.columns([1, 4], vertical_alignment="top")

    with col_side:

        st.header("Filters")

        us_cat = st.selectbox("Category", list(US_CATS.keys()), key="us_cat")

        with st.form(key="grade_filter_us"):
            st.markdown("**評級**")
            u1, u2, u3, u4, uall = st.columns([1,1,1,1,1])
            u_a = u1.checkbox("A", value=True, key="us_grade_a")
            u_b = u2.checkbox("B", value=True, key="us_grade_b")
            u_c = u3.checkbox("C", value=True, key="us_grade_c")
            u_d = u4.checkbox("D", value=True, key="us_grade_d")
            if uall.form_submit_button("全", help="Select All", width='stretch'):
                pass  # Checkbox values are auto-managed by Streamlit via key=
            us_grade = [g for g, on in zip(["A","B","C","D"], [u_a, u_b, u_c, u_d]) if on]

        us_score_min = st.slider("Score Min", 0, 1000, 0, key="us_score")
        us_rsi_max = st.slider("RSI Max", 30, 100, 100, key="us_rsi")

        us_macd_filter = st.checkbox("排除 MACD < 0", value=False, key="us_macd_filter")

        codes = US_CATS.get(us_cat, [])

        st.info(f"{len(codes)} stocks")

        analyze_us = st.button("Analyze", type="primary", width='stretch', key="btn_us_analyze")



    if 'us_results' not in st.session_state:

        st.session_state.us_results = None

        st.session_state.us_filtered = None

        st.session_state.us_cat_saved = None



    if analyze_us:

        with st.spinner("Analyzing..."):

            def _analyze_one(idx_code):

                i, code = idx_code

                return i, analyze(code, 'US')

            results = []

            bar = st.progress(0)

            total = len(codes)

            with ThreadPoolExecutor(max_workers=8) as pool:

                futures = {pool.submit(_analyze_one, (i, code)): i for i, code in enumerate(codes)}

                for future in as_completed(futures):

                    try:

                        i, r = future.result()

                        if r:

                            results.append((i, r))

                    except Exception:

                        pass

                    bar.progress(min(len(results) + 1, total) / total)

            results.sort(key=lambda x: x[0])

            results = [r for _, r in results]

            bar.empty()
            _log.info(f"[batch] TW done total={len(results)}")

            filtered = [r for r in results

                        if r['rsi'] <= us_rsi_max

                        and r['tier'] in us_grade

                        and r['score'] >= us_score_min

                        and (not us_macd_filter or r['macd_hist'] >= 0)]

            filtered.sort(key=lambda x: x['score'], reverse=True)

            st.session_state.us_results = results

            st.session_state.us_filtered = filtered

            st.session_state.us_cat_saved = us_cat



    results = st.session_state.us_results

    filtered = st.session_state.us_filtered

    cat_saved = st.session_state.us_cat_saved



    if results:

        a = sum(1 for r in filtered if r['tier'] == 'A')

        b = sum(1 for r in filtered if r['tier'] == 'B')

        c = sum(1 for r in filtered if r['tier'] == 'C')

        d = sum(1 for r in filtered if r['tier'] == 'D')

        bull = sum(1 for r in filtered if r['bullish'] == 'Y')

        kd = sum(1 for r in filtered if r['kd_golden'])

        avg_score = sum(r['score'] for r in filtered) / len(filtered) if filtered else 0

        m = st.columns(7)

        m[0].metric("A", a)

        m[1].metric("B", b)

        m[2].metric("C", c)

        m[3].metric("D", d)

        m[4].metric("BULL", bull)

        m[5].metric("KD+", kd)

        m[6].metric("Avg Score", f"{avg_score:.0f}")

        st.success(f"{len(results)} stocks | {len(filtered)} after filter")
        st.toast(f"掃描完成！ {len(results)} 檔 ({len(filtered)} 通過篩選)", icon="✅")



    if filtered:

        rows = []

        for r in filtered:

            rows.append({

                "Score": f"{r['score']:.0f}",

                "Code": r['code'],

                "Name": r['name'],

                "Price": f"${r['price']:.2f}",

                "Chg%": f"{r['chg']:+.2f}%",

                "RSI": f"{r['rsi']:.0f}",

                "K": f"{r['k']:.0f}",

                "D": f"{r['d']:.0f}",

                "BB%": f"{r['bb_pct']:.0f}%",

                "BIAS5": f"{r['bias5']:+.1f}%",

                "Vol": f"{r['vol_ratio']:.1f}x",

                "MA": "Y" if r['ma20_above_ma60'] else "N",

                "Tier": r['tier'],

            })

        df = pd.DataFrame(rows)

        st.dataframe(
            df,
            column_config={
                "Score": st.column_config.NumberColumn("評分", format="%.0f", min_value=0, max_value=1000),
                "Chg%": st.column_config.TextColumn("漲跌%"),
                "RSI":  st.column_config.TextColumn("RSI"),
                "Tier": st.column_config.TextColumn("評級"),
                "Code": st.column_config.TextColumn("代碼"),
                "Price": st.column_config.NumberColumn("現價", format="%.2f"),
                "MA":   st.column_config.TextColumn("MA20>60"),
                "F":    st.column_config.TextColumn("外資"),
                "T":    st.column_config.TextColumn("投信"),
                "Vol":  st.column_config.TextColumn("量比"),
            },
            use_container_width=True,
            hide_index=True,
        )



        with st.expander("Send to Telegram"):

            grade_filter = st.multiselect("Grade Filter", ["A","B","C","D"], default=["A","B","C","D"], key="us_grade_send")

            grade_filtered = [r for r in filtered if r['tier'] in grade_filter]

            sel = st.multiselect("Select", [f"[{r['tier']}] S={r['score']:.0f} {r['code']} ${r['price']:.0f}" for r in grade_filtered], key="us_sel")

            sel_rows = [r for r in grade_filtered if f"[{r['tier']}] S={r['score']:.0f} {r['code']} ${r['price']:.0f}" in sel]

            sc = len(sel_rows)

            r1, r2 = st.columns(2)

            if r1.button(f"Send ({sc}) Grade {','.join(grade_filter)}", disabled=(sc==0), width='stretch', key="us_batch_send"):

                with st.spinner("Sending..."):

                    chunks = format_telegram(sel_rows, f"US-{cat_saved} ({','.join(grade_filter)})")

                    ok_all = True

                    for chunk in chunks:

                        ok, err = push_telegram(chunk)

                        if not ok:

                            ok_all = False

                            st.error(f"Error: {err}")

                            break

                    if ok_all:

                        st.success(f"Sent {sc} stocks ({len(chunks)} msgs)")
                        st.toast(f"已發送 {sc} 檔分析到 Telegram", icon="📤")

            if r2.button(f"Send All ({len(grade_filtered)}) Grade {','.join(grade_filter)}", width='stretch'):

                with st.spinner("Sending..."):

                    chunks = format_telegram(grade_filtered, f"US-{cat_saved} ({','.join(grade_filter)})")

                    ok_all = True

                    for chunk in chunks:

                        ok, err = push_telegram(chunk)

                        if not ok:

                            ok_all = False

                            st.error(f"Error: {err}")

                            break

                    if ok_all:

                        st.success(f"Sent {len(grade_filtered)} stocks ({len(chunks)} msgs)")
                        st.toast(f"已發送 {len(grade_filtered)} 檔到 Telegram", icon="📤")



        if results:

            csv = pd.DataFrame(results).to_csv(index=False).encode('utf-8-sig')

            st.download_button("CSV", csv, f"us_{cat_saved}_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", key="us_csv")



    # --- Auto-Send Toggle (US) ---

    if 'us_auto_send' not in st.session_state:

        st.session_state['us_auto_send'] = False

    auto_col, spacer = st.columns([2, 1])

    with auto_col:

        st.session_state['us_auto_send'] = st.toggle('分析後自動發送 Telegram', value=st.session_state['us_auto_send'], key='us_auto_send_toggle')

    with spacer:

        st.caption('ON = 自動發送' if st.session_state.get('us_auto_send') else 'OFF = 手動發送')



    # --- Single Stock Deep Analysis ---

    st.divider()

    st.subheader("Single Stock Deep Analysis")

    col_code, col_btn = st.columns([2, 1])

    with col_code:

        us_single_code = st.text_input("Stock Code", "NVDA", key="us_single_code").strip().upper()

    with col_btn:

        st.write(" ")

        do_us_single = st.button("Analyze", type="primary", width='stretch', key="btn_us_single")

    if do_us_single or st.session_state.get('us_analyzed', False):

        if do_us_single:
            with st.spinner("Analyzing " + us_single_code + "..."):
                r = analyze(us_single_code, "US")
            st.session_state['us_analyzed'] = True
        elif 'us_single_result' in st.session_state:
            r = st.session_state['us_single_result']
        else:
            r = None

        if r:

            st.session_state['us_single_result'] = r
            bd = r.get('score_breakdown', {})

            # ═══════════════════════════════════════
            #  ACTION BAR
            # ═══════════════════════════════════════
            score = r['score']
            tier  = r['tier']
            rsi_v = r['rsi']
            bb_v  = r['bb_pct']
            macd_v = r['macd_hist']
            ma_bull = r['ma20_above_ma60']
            kd_ok   = r['kd_golden']

            pos = (kd_ok*200)+(ma_bull*150)+((35<=rsi_v<=60)*100)+((macd_v>0)*140)+((20<=bb_v<=80)*100)
            pct = min(100, max(0, int(pos*100/690)))
            bar = "█"*(pct//10) + "░"*(10-pct//10)

            if kd_ok and ma_bull and macd_v>0 and rsi_v<65:
                act,col,trend = "強力买入","green","多頭"
            elif score>=700 and rsi_v<70:
                act,col,trend = "买入","blue","多頭"
            elif score>=400:
                act,col,trend = "觀望","gray","中性"
            elif rsi_v>80 or bb_v>90:
                act,col,trend = "過熱觀望","orange","警覺"
            else:
                act,col,trend = "減持","red","空頭"

            st.markdown(
                f"<big><b>「{us_single_code} {r['name'][:8]}」</b></big>"
                f"&nbsp;&nbsp;Score {score}"
                f"&nbsp;&nbsp;<b>:color[{col}][{bar} {act}]</b>"
                f"&nbsp;&nbsp;{trend}趨勢",
                unsafe_allow_html=True)

            # ── Signal Badges ──
            sigs = []
            if r['kd_golden']:      sigs.append(("KD Golden","green"))
            if r['ma20_above_ma60']: sigs.append(("MA Bull","green"))
            if r['macd_hist']>0:    sigs.append(("MACD+","green"))
            if r['bb_pct']<20:     sigs.append(("BB Oversold","blue"))
            if r['bb_pct']>80:     sigs.append(("BB Overbought","red"))
            if r['rsi']<35:         sigs.append(("RSI Oversold","blue"))
            if r['rsi']>70:         sigs.append(("RSI Overbought","red"))
            if r['vol_ratio']>2.0: sigs.append(("Vol Surge","orange"))

            if sigs:
                tags = "  ".join([f":{c}[{l}]" for l,c in sigs])
                st.markdown(tags)
            else:
                st.caption("No signals")

            # ── Row 1: Price + RSI + K/D + BB% ──
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Price", f"${r['price']:.2f}", f"{r['chg']:+.2f}%")
            rsi_delta = rsi_v-50
            if rsi_v>70:       rsi_st = "過熱"
            elif rsi_v<35:    rsi_st = "超賣"
            else:              rsi_st = f"正常 {rsi_v:.0f}"
            c2.metric("RSI", f"{rsi_v:.0f}", f"{rsi_delta:+.0f}", help=f"Status: {rsi_st}")

            k_val,d_val = r['k'],r['d']
            kd_lbl = "Golden!" if kd_ok else f"{k_val:.0f}/{d_val:.0f}"
            c3.metric("K/D", kd_lbl, f"{k_val-d_val:+.0f}", help="K above D=bullish")

            bb_delta = bb_v-50
            if bb_v<20:       bb_st = "超賣"
            elif bb_v>80:     bb_st = "過熱"
            else:             bb_st = f"中立 {bb_v:.0f}%"
            c4.metric("BB%", f"{bb_v:.0f}%", f"{bb_delta:+.0f}", help=f"Status: {bb_st}")

            # ── Row 2: MA20 vs MA60 + MACD + Vol + BIAS ──
            d1,d2,d3,d4 = st.columns(4)
            ma_diff = r['ma20']-r['ma60'] if r.get('ma60') else 0
            ma_lbl = "MA Bull" if ma_bull else "MA Bear"
            d1.metric("MA20 vs MA60", ma_lbl, f"{ma_diff:+.1f}" if r.get('ma60') else "N/A")

            d2.metric("MACD Hist", f"{macd_v:+.2f}", f"{macd_v:+.2f}")

            vol_v = r['vol_ratio']
            vol_st = "高量" if vol_v>1.5 else "低量" if vol_v<0.8 else "正常"
            d3.metric("Vol Ratio", f"{vol_v:.1f}x", help=f"Status: {vol_st}")

            bias_v = r['bias5']
            bias_st = "偏離大" if abs(bias_v)>3 else "正常"
            d4.metric("BIAS5", f"{bias_v:+.1f}%", help=f"Status: {bias_st}")

            # ── Score Breakdown (color-coded inline) ──
            bd = r.get('score_breakdown', {})
            items = [
                ('RSI',  bd.get('rsi',0),  (35<=rsi_v<=60)),
                ('MACD', bd.get('macd',0), (macd_v>0)),
                ('K',    bd.get('k',0),    kd_ok),
                ('D',    bd.get('d',0),    not kd_ok),
                ('BB',   bd.get('bb',0),   (20<=bb_v<=80)),
                ('MA',   bd.get('ma',0),   ma_bull),
                ('Vol',  bd.get('vol',0),  (0.8<=vol_v<=1.5)),
            ]
            sb_parts = []
            for k,v,good in items:
                color = 'green' if good else 'gray'
                sb_parts.append(f":{color}[{k} {v}]")
            st.markdown("  ".join(sb_parts))

            # ── 📊 Technical Detail Button (US) ──
            detail_key_us = f"detail_{us_single_code}"
            show_us_detail = st.button("📊 技術分析詳細解讀", key=f"btn_{detail_key_us}")

            if show_us_detail or st.session_state.get('us_detail_shown_' + us_single_code, False):
                st.session_state['us_detail_shown_' + us_single_code] = True

                st.markdown("---")
                st.markdown("### 📈 技術指標詳細解析 (US)")

                rsi_v = r['rsi']
                rsi_status = "過熱" if rsi_v > 70 else ("超賣" if rsi_v < 30 else ("偏低" if rsi_v < 40 else ("偏高" if rsi_v > 60 else "正常")))
                st.markdown(f"**RSI (相對強弱指標)** — 當前 `{rsi_v:.0f}` | 狀態: `{rsi_status}`")
                st.caption(f"📌 RSI衡量價格變動頻率。>70超買（過熱），<30超賣。{'動能過強，小心回調' if rsi_v > 70 else ('可能出現反彈機會' if rsi_v < 30 else ('評分偏低' if rsi_v < 40 else ('動能偏強' if rsi_v > 60 else '位於中性區間')))}。")
                st.progress(min(rsi_v / 100, 1.0), text=f"RSI: {rsi_v:.0f}/100")
                st.markdown("---")

                macd_hist = r['macd_hist']
                macd_sig = r.get('macd_sig', 0)
                macd_color = "green" if macd_hist > 0 else "red"
                st.markdown(f"**MACD** — 柱狀 `{macd_hist:+.2f}` | 訊號線 `{macd_sig:+.2f}` | :{macd_color}['多頭' if macd_hist > 0 else '空頭']")
                st.caption(f"📌 MACD柱狀正值代表多頭動能。{'上漲趨勢' if macd_hist > 0 else '下跌趨勢'}。")
                st.markdown("---")

                k_val, d_val = r['k'], r['d']
                kd_ok = r['kd_golden']
                kd_status = "黃金交叉（多頭）" if kd_ok else ("死亡交叉（空頭）" if k_val < d_val else "整理中")
                st.markdown(f"**K/D (隨機指標)** — K=`{k_val:.0f}` D=`{d_val:.0f}` | 狀態: `{kd_status}`")
                st.caption(f"📌 K>D為多頭；K<30且K>D為黃金交叉預示反轉。{'即將反轉上漲' if kd_ok else ('短線偏空' if k_val < d_val else 'K、D膠著中')}。")
                st.markdown("---")

                ma20_val = r['ma20']
                ma60_val = r.get('ma60', 0) or 0
                ma_color = "green" if r['ma20_above_ma60'] else "red"
                diff = ma20_val - ma60_val
                diff_pct = diff / ma60_val * 100 if ma60_val > 0 else 0
                st.markdown(f"**MA (均線多頭)** — MA20=`{ma20_val:.0f}` MA60=`{ma60_val:.0f}` | 差: `{diff:+.1f}` ({diff_pct:+.1f}%) | :{ma_color}['多頭排列' if r['ma20_above_ma60'] else '空頭排列']")
                st.caption(f"📌 MA20>MA60代表中長期趨勢向上。{'完美多頭排列' if r['ma20_above_ma60'] else '空頭排列，中期趨勢向下'}。")
                st.markdown("---")

                bb_v = r['bb_pct']
                bb_upper, bb_lower = r.get('bb_upper',0), r.get('bb_lower',0)
                bb_status = "超賣區間" if bb_v < 20 else ("過熱區間" if bb_v > 80 else "中立區間")
                st.markdown(f"**BB% (布林帶百分比)** — 當前 `{bb_v:.0f}%` (帶: {bb_lower:.0f}~{bb_upper:.0f}) | 狀態: `{bb_status}`")
                st.caption(f"📌 BB% <20%超賣（支撐），>80%超買（回調風險）。{'接近下緣可能有支撐' if bb_v < 20 else ('接近上緣留意回調' if bb_v > 80 else '在布林帶中軸附近')}。")
                st.progress(min(bb_v / 100, 1.0), text=f"BB%: {bb_v:.0f}%")
                st.markdown("---")

                bias_v = r['bias5']
                bias_status = "偏離大" if abs(bias_v) > 3 else "正常"
                st.markdown(f"**BIAS5 (5日乖離率)** — 當前 `{bias_v:+.1f}%` | 狀態: `{bias_status}`")
                st.caption(f"📌 BIAS5 = (現價-MA5)/MA5*100%。>3%偏離均線過多遲早回調。{'偏離過大' if abs(bias_v) > 3 else '偏離正常'}。")
                st.markdown("---")

                vol_v = r['vol_ratio']
                vol_status = "巨量" if vol_v > 2.5 else ("高量" if vol_v > 1.5 else ("低量" if vol_v < 0.8 else "正常量"))
                st.markdown(f"**Vol Ratio (量比)** — 當前 `{vol_v:.1f}x` | 狀態: `{vol_status}`")
                st.caption(f"📌 量比 >1.5x為高量通常伴隨趨勢；<0.8x為低量動能不足。{'高量動能強' if vol_v > 1.5 else ('低量缺乏方向' if vol_v < 0.8 else '量能正常')}。")
                st.markdown("---")

                score = r['score']
                tier = r['tier']
                tier_color = {"A":"green","B":"blue","C":"gray","D":"orange","F":"red"}.get(tier,"gray")
                st.markdown(f"**評分 / 等級** — Score: `{score}/1000` | 等級: :{tier_color}[{tier}]")
                thresholds = {"A":800,"B":600,"C":400,"D":200}
                next_tier = next((k for k,v in sorted(thresholds.items(), key=lambda x:x[1]) if score < v), "MAX")
                st.caption(f"📌 等級：A≥800 B≥600 C≥400 D≥200。距離{tier}需{abs(score - thresholds.get(tier, 0))}分，距{next_tier}還差{abs(score - thresholds.get(next_tier, 1000))}分。")
                st.markdown("---")

                st.markdown("### 🎯 綜合進場評估")
                us_bullish_count = sum([1 for sig in sigs if sig[1]=='green'])
                us_total_signals = len(sigs) if sigs else 0
                if us_total_signals == 0:
                    assessment = "⚠️ 無明確技術信號，建議觀望"
                    assessment_col = "gray"
                elif us_bullish_count >= 4:
                    assessment = "✅ 多項技術指標支撐，上漲機率高"
                    assessment_col = "green"
                elif us_bullish_count >= 2:
                    assessment = "🟡 部分指標支撐，可謹慎關注"
                    assessment_col = "blue"
                else:
                    assessment = "🔴 多數指標偏空，建議觀望或減持"
                    assessment_col = "red"
                st.markdown(f":{assessment_col}[{assessment}] ({us_bullish_count}/{us_total_signals} 項多頭信號)")

                risks = []
                if rsi_v > 75: risks.append("RSI 過熱，回調風險高")
                if bb_v > 85: risks.append("BB% 接近上緣，過熱風險")
                if macd_hist < 0: risks.append("MACD 負值，空頭動能")
                if vol_v < 0.6: risks.append("成交量過低，動能不足")
                if not r['ma20_above_ma60']: risks.append("均線空頭排列，中期趨勢向下")
                if risks:
                    st.markdown("### ⚠️ 風險提示")
                    for risk in risks:
                        st.warning(f"⚠️ {risk}")


        if not r:
            st.warning("Please analyze a stock first")
        else:
            tier_icon = {"A": "A", "B": "B", "C": "C", "D": "X"}.get(r.get('tier','?'), '?')
            macd_h = r.get('macd_hist', 0)
            tier_d = tier_icon if not (tier_icon == 'A' and macd_h < 0) else 'B'
            inst = r.get('inst') or {}
            f_v = inst.get('foreign',0); t_v = inst.get('trust',0); d_v = inst.get('dealer',0)
            ma60_val = r.get('ma60', None)
            ma60_str = f"${ma60_val:.0f}" if ma60_val else "N/A"
            msg = (
                f"[CHART] **{us_single_code} {r['name'][:12]}** Deep Analysis\n"
                f"─────────────────────\n"
                f"[MONEY] ${r['price']:.2f} ({r['chg']:+.2f}%)\n"
                f"[TROPHY] Tier: [{tier_d}] | Score: {r['score']:.0f}/1000\n"
                f"[UP] RSI={r['rsi']:.0f} K={r['k']:.0f} D={r['d']:.0f} BB%={r['bb_pct']:.0f}%\n"
                f"[DWN] BIAS5={r['bias5']:+.1f}% MACD={macd_h:+.2f}\n"
                f"[CHART] MA20=${r['ma20']:.0f} MA60={ma60_str}\n"
                f"[BOX] Vol: {r['vol_ratio']:.1f}x | {r.get('bullish','N')}\n"
                f"法人: F={f_v:+,} T={t_v:+,} D={d_v:,}")
            st.write("DEBUG: US Send button rendering now")
            col1, _ = st.columns([1, 4])

            # ── Vegas Tunnel Section (US) ───────────────────────────────────────
            st.divider()
            st.subheader("Vegas Tunnel (EMA 144/169/576/676)")

            vegas_btn_us = st.button("Vegas 分析", key="btn_vegas_us")
            if vegas_btn_us:
                with st.spinner("Computing Vegas Tunnel..."):
                    v_us = vegas_tunnel(us_single_code, "US")
                if v_us:
                    st.session_state['vegas_result_us'] = v_us
                else:
                    st.error("無法取得 Vega 資料，請確認股票代碼")

            if 'vegas_result_us' in st.session_state:
                v_us = st.session_state['vegas_result_us']
                bias_icon = "BU" if v_us['bias'] == 'BULL' else ("RD" if v_us['bias'] == 'BEAR' else "YL")
                trend_str = v_us['bias'] + " Trend"
                st.markdown('**' + bias_icon + ' ' + trend_str + '** &nbsp;&nbsp; **:' + v_us['sig_color'] + '[' + v_us['signal'] + ']** &nbsp;&nbsp; Score ' + str(v_us['score']))

                e1, e2, e3, e4, e5 = st.columns(5)
                e1.metric("EMA12", str(round(v_us['ema12'],2)), str(round(v_us['ema12_vs_144'],2)) + "% vs 144")
                e2.metric("EMA144", str(round(v_us['ema144'],2)), str(round(v_us['price_vs_144'],1)) + "%")
                e3.metric("EMA169", str(round(v_us['ema169'],2)), str(round(v_us['price_vs_169'],1)) + "%")
                e4.metric("EMA576", str(round(v_us['ema576'],2)))
                e5.metric("EMA676", str(round(v_us['ema676'],2)))

                s1, s2, s3, s4 = st.columns(4)
                s1.metric("Price above", "Y" if v_us['price_above'] else "N")
                s2.metric("EMA12 above", "Y" if v_us['ema12_above'] else "N")
                s3.metric("EMA12 cross", "Y" if v_us['ema12_cross_up'] else "N")
                s4.metric("EMA12 inside", "Y" if v_us['ema12_inside'] else "N")

                t1, t2, t3, t4 = st.columns(4)
                t1.metric("Tunnel W", str(round(v_us['tunnel_w'],2)))
                t2.metric("Long SL", str(round(v_us['sl_long'],2)), "-" + str(round(v_us['sl_pct'],1)) + "%")
                t3.metric("TP1", str(round(v_us['tp1'],2)))
                t4.metric("TP2", str(round(v_us['tp2'],2)))

                t5, t6, t7, t8 = st.columns(4)
                t5.metric("TP3", str(round(v_us['tp3'],2)))
                t6.metric("TP4", str(round(v_us['tp4'],2)))
                t7.metric("H1>H4", "Y" if v_us['h1_above_h4'] else "N")
                t8.metric("Bias", v_us['bias'])

                sig_map = {
                    'BUY':          'BUY - 價格突破隧道且EMA12確認，多頭動能強，建議進場',
                    'PULLBACK':     'PULLBACK - 價格突破隧道但EMA12未確認，等待回調再進',
                    'INSIDE_TUNNEL':'INSIDE - 價格在隧道內震盪，觀望等待突破',
                    'FAKEOUT':      'FAKEOUT - 假突破！勿追單',
                    'SELL':         'SELL - 空頭趨勢，避免做多',
                    'NEUTRAL':      'NEUTRAL - 隧道糾結，觀望不交易',
                    'NO_SIGNAL':    'NO SIGNAL - 無明確信號，等待市場表態',
                }
                sig_txt = sig_map.get(v_us['signal'], v_us['signal'])
                st.info(sig_txt)
            else:
                st.caption("點擊「Vegas 分析」執行隧道分析")

            with st.form(key="us_single_tg_form", clear_on_submit=False):
                submitted = st.form_submit_button("Send Telegram", width='stretch')
                st.write(f"DEBUG: submitted={submitted}")
                if submitted:
                    st.info("US form submitted!")
                    st.info(f"DEBUG chat_id={TELEGRAM_CHAT_ID} token_len={len(TELEGRAM_BOT_TOKEN)}")
                    try:
                        ok, err = push_telegram(msg)
                        st.info(f"ok={ok} err={err}")
                    except Exception as ex:
                        st.error(f"ex={ex}")
                    else:
                        if ok:
                            st.success("Telegram sent!")
                            st.toast("已發送單一股票分析到 Telegram", icon="📤")
                        else:
                            st.error(f"Failed: {err}")


# ═══════════════════════════ BRAIN TAB ═══════════════════════════

