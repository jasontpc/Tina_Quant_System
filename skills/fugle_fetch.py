# -*- coding: utf-8 -*-
"""
Fugle API 即時行情工具 v2.1 — 含安全 Time Sleep + Rate Limit 保護
用途：取得台股即時分鐘K線、技術指標
注意：/intraday/quote 需要更高權限，目前使用 candles 取得即時價格
"""
import os, json, sys, requests, time
from datetime import datetime
from functools import wraps

sys.stdout.reconfigure(encoding='utf-8')

# ========== .env 讀取 ==========
ENV_FILE = os.path.join(os.path.dirname(__file__), '.env')
FUGLE_API_KEY = None

if os.path.exists(ENV_FILE):
    for line in open(ENV_FILE):
        if line.startswith('FUGLE_API_KEY='):
            FUGLE_API_KEY = line.split('=', 1)[1].strip()

if not FUGLE_API_KEY:
    FUGLE_API_KEY = os.getenv('FUGLE_API_KEY', 'ZjEwNWVkNjMtMWNmNi00ZmI0LWI5MzEtZmQyZDJmNGM4M2E1')

BASE_URL = 'https://api.fugle.tw/marketdata/v1.0/stock'
HEADERS = {'X-API-Key': FUGLE_API_KEY}

# ========== Rate Limit 保護 ==========
MIN_REQUEST_INTERVAL = 1.0   # 秒（避免觸發 rate limit，富果建議每分鐘60次以下）
MAX_RETRIES = 3
RETRY_DELAY = 5             # 秒（遇到 429 或 5xx 時重試前等待）
_RATE_LAST_TIME = 0.0       # 上次請求時間（全域追蹤）


def _wait_interval():
    """確保請求間隔至少 MIN_REQUEST_INTERVAL 秒"""
    global _RATE_LAST_TIME
    elapsed = time.time() - _RATE_LAST_TIME
    if elapsed < MIN_REQUEST_INTERVAL:
        time.sleep(MIN_REQUEST_INTERVAL - elapsed)
    _RATE_LAST_TIME = time.time()


def safe_request(method, url, headers=None, params=None, body=None, timeout=8):
    """
    安全 HTTP 請求，含：
    - Rate limit 保護（每秒最多1次）
    - 429 / 5xx 重試機制（最多 MAX_RETRIES 次）
    - 逾時處理
    """
    if not headers:
        headers = HEADERS

    for attempt in range(MAX_RETRIES):
        try:
            _wait_interval()

            if method.upper() == 'GET':
                resp = requests.get(url, headers=headers, params=params, timeout=timeout)
            else:
                resp = requests.post(url, headers=headers, json=body, timeout=timeout)

            # Rate limit 觸發
            if resp.status_code == 429:
                retry_after = int(resp.headers.get('Retry-After', RETRY_DELAY))
                print(f'  [Fugle] 429 Rate limit, waiting {retry_after}s...')
                time.sleep(retry_after)
                continue

            # 5xx 伺服器錯誤
            if resp.status_code >= 500:
                print(f'  [Fugle] Server error {resp.status_code}, retry {attempt+1}/{MAX_RETRIES}...')
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue

            return resp

        except requests.exceptions.Timeout:
            print(f'  [Fugle] Timeout, retry {attempt+1}/{MAX_RETRIES}...')
            time.sleep(RETRY_DELAY)
        except requests.exceptions.ConnectionError as e:
            print(f'  [Fugle] Connection error: {e}, retry {attempt+1}/{MAX_RETRIES}...')
            time.sleep(RETRY_DELAY * (attempt + 1))
        except Exception as e:
            print(f'  [Fugle] Error: {e}')
            break

    print(f'  [Fugle] Failed after {MAX_RETRIES} attempts')
    return None


# ========== API 函式 ==========
def get_ticker(symbol):
    """取得股票基本資料"""
    url = f'{BASE_URL}/intraday/ticker/{symbol}'
    resp = safe_request('GET', url, headers=HEADERS)
    if resp and resp.status_code == 200:
        return resp.json()
    return None


def get_candles(symbol, offset=0):
    """取得分鐘K線"""
    url = f'{BASE_URL}/intraday/candles/{symbol}'
    params = {'offset': offset} if offset else None
    resp = safe_request('GET', url, headers=HEADERS, params=params)
    if resp and resp.status_code == 200:
        return resp.json()
    return None


def get_trades(symbol, limit=50):
    """取得成交明細"""
    url = f'{BASE_URL}/intraday/trades/{symbol}'
    params = {'limit': limit}
    resp = safe_request('GET', url, headers=HEADERS, params=params)
    if resp and resp.status_code == 200:
        return resp.json()
    return None


def get_technical(symbol, indicator, **params):
    """取得技術指標（sma/rsi/kdj/macd/bb）"""
    url = f'{BASE_URL}/technical/{indicator}/{symbol}'
    resp = safe_request('GET', url, headers=HEADERS, params=params if params else None)
    if resp and resp.status_code == 200:
        return resp.json()
    return None


def get_realtime_price(symbol):
    """取得即時報價（最後一根K棒收盤價）"""
    data = get_candles(symbol)
    if data and 'data' in data and len(data['data']) > 0:
        last_bar = data['data'][-1]
        return {
            'symbol': symbol,
            'date': last_bar['date'],
            'close': last_bar['close'],
            'open': last_bar['open'],
            'high': last_bar['high'],
            'low': last_bar['low'],
            'volume': last_bar['volume'],
        }
    return None


def get_batch_technical(symbol):
    """一次取得所有技術指標（RSI/SMA/KDJ/MACD/BB）"""
    results = {}
    indicators = [
        ('rsi', {'period': 14}),
        ('sma', {'period': 20}),
        ('sma', {'period': 60}),
        ('kdj', {'rPeriod': 9, 'kPeriod': 3, 'dPeriod': 3}),
        ('macd', {}),
        ('bb', {'period': 20}),
    ]
    for ind, params in indicators:
        data = get_technical(symbol, ind, **params)
        if data and 'data' in data and len(data['data']) > 0:
            results[ind] = data['data'][-1]
        time.sleep(MIN_REQUEST_INTERVAL)
    return results


def get_market_quote(symbol):
    """一次取得完整市場報價（ticker + 即時價格 + 技術指標）"""
    print(f'  [Fugle] Fetching {symbol}...')

    ticker = get_ticker(symbol)
    if ticker is None:
        print(f'  [Fugle] Failed to fetch ticker for {symbol}')
        return None
    time.sleep(MIN_REQUEST_INTERVAL)

    price = get_realtime_price(symbol)
    time.sleep(MIN_REQUEST_INTERVAL)

    tech = get_batch_technical(symbol)
    time.sleep(MIN_REQUEST_INTERVAL)

    return {
        'ticker': ticker,
        'price': price,
        'technical': tech,
        'fetched_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }


if __name__ == '__main__':
    import sys
    symbol = sys.argv[1] if len(sys.argv) > 1 else '2330'

    print(f'=== Fugle 即時行情 — {symbol} ===')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print()

    quote = get_market_quote(symbol)
    if not quote:
        print('取得失敗')
        sys.exit(1)

    t = quote.get('ticker', {})
    name = t.get('name', '').encode('utf-8', 'ignore').decode('utf-8', 'ignore')
    print(f'股票: {t.get("symbol")} {name}')
    print(f'昨收: {t.get("previousClose")} | 漲停: {t.get("limitUpPrice")} | 跌停: {t.get("limitDownPrice")}')
    print()

    p = quote.get('price', {})
    if p:
        print(f'即時價格: {p["close"]} @ {p["date"]}')
        print()

    tech = quote.get('technical', {})
    if tech:
        print('技術指標（最新）:')
        for k, v in tech.items():
            print(f'  {k.upper()}: {v}')
