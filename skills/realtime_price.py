# -*- coding: utf-8 -*-
"""
市場報價優先取得器 — 自動選擇最快可用資料來源
優先順序：yfinance → FinMind → Fugle

用於 Nana/Leo/Ray 即時行情掃描
"""
import sys, time, requests
import yfinance as yf
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

# FinMind Token
FINMIND_TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSJ9.oCdQO1qNRUCYxHZSVuRQCqlF7X2DbQ77wury5ARCKzM'

# Fugle API
FUGLE_API_KEY = 'ZjEwNWVkNjMtMWNmNi00ZmI0LWI5MzEtZmQyZDJmNGM4M2E1'
FUGLE_BASE = 'https://api.fugle.tw/marketdata/v1.0/stock'
FUGLE_HEADERS = {'X-API-Key': FUGLE_API_KEY}

MIN_INTERVAL = 1.0   # Fugle rate limit protection
_last_fugle_time = 0.0


def _fugle_wait():
    global _last_fugle_time
    elapsed = time.time() - _last_fugle_time
    if elapsed < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - elapsed)
    _last_fugle_time = time.time()


# ========== 1. yfinance（最快，優先使用）==========
def get_price_yf(symbol):
    """使用 yfinance 取得最新價格（日線）"""
    try:
        ticker = yf.Ticker(f'{symbol}.TW')
        h = ticker.history(period='5d', interval='1d')
        if h.empty or len(h) < 1:
            return None
        closes = h['Close'].values
        highs = h['High'].values
        lows = h['Low'].values
        volumes = h['Volume'].values
        dates = h.index.tolist()
        return {
            'symbol': symbol,
            'source': 'yfinance',
            'close': float(closes[-1]),
            'open': float(h['Open'].iloc[-1]),
            'high': float(highs[-1]),
            'low': float(lows[-1]),
            'volume': int(volumes[-1]),
            'date': dates[-1].strftime('%Y-%m-%d') if hasattr(dates[-1], 'strftime') else str(dates[-1]),
            'bars': len(closes),
        }
    except:
        return None


def get_rsi_yf(symbol, period=14):
    """使用 yfinance 計算 RSI"""
    try:
        ticker = yf.Ticker(f'{symbol}.TW')
        h = ticker.history(period='60d')
        if len(h) < period + 1:
            return None
        closes = h['Close'].values
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return float(100 - (100 / (1 + rs)))
    except:
        return None


# ========== 2. FinMind（法人資料豐富）==========
def get_price_finmind(symbol, days=5):
    """使用 FinMind 取得最新價格"""
    try:
        from FinMind.data import DataLoader
        dl = DataLoader()
        dl.token = FINMIND_TOKEN
        end = (time.strftime('%Y-%m-%d'))
        start = '2020-01-01'  # FinMind needs start date
        data = dl.taiwan_stock_daily(stock_id=symbol, start_date=start, end_date=end)
        if data is None or len(data) < 1:
            return None
        latest = data.iloc[-1]
        return {
            'symbol': symbol,
            'source': 'finmind',
            'close': float(latest.get('close', 0)),
            'date': str(latest.get('date', '')),
        }
    except:
        return None


# ========== 3. Fugle（即時分鐘K線，最接近盤中實時）==========
def _fugle_safe_get(path, params=None):
    """Fugle 安全請求"""
    global _last_fugle_time
    for attempt in range(3):
        try:
            _fugle_wait()
            resp = requests.get(FUGLE_BASE + path, headers=FUGLE_HEADERS, params=params, timeout=8)
            if resp.status_code == 429:
                time.sleep(5)
                continue
            if resp.status_code >= 500:
                time.sleep(3)
                continue
            if resp.status_code == 200:
                return resp.json()
            return None
        except:
            time.sleep(2)
    return None


def get_price_fugle(symbol):
    """使用 Fugle 取得即時分鐘K線最後收盤價"""
    global _last_fugle_time
    data = _fugle_safe_get(f'/intraday/candles/{symbol}')
    if data and 'data' in data and len(data['data']) > 0:
        last_bar = data['data'][-1]
        return {
            'symbol': symbol,
            'source': 'fugle',
            'close': float(last_bar.get('close', 0)),
            'date': last_bar.get('date', ''),
            'open': float(last_bar.get('open', 0)),
            'high': float(last_bar.get('high', 0)),
            'low': float(last_bar.get('low', 0)),
            'volume': int(last_bar.get('volume', 0)),
        }
    return None


def get_technical_fugle(symbol):
    """使用 Fugle 取得技術指標"""
    global _last_fugle_time
    result = {}
    indicators = [
        ('rsi', {'period': 14}),
        ('sma', {'period': 20}),
        ('kdj', {'rPeriod': 9, 'kPeriod': 3, 'dPeriod': 3}),
        ('macd', {}),
        ('bb', {'period': 20}),
    ]
    for ind, params in indicators:
        d = _fugle_safe_get(f'/technical/{ind}/{symbol}', params)
        if d and 'data' in d and len(d['data']) > 0:
            result[ind] = d['data'][-1]
        time.sleep(MIN_INTERVAL)
    return result


# ========== 統一報價介面（自動選擇）==========
def get_realtime_price(symbol):
    """
    自動選擇最快可用資料來源
    優先順序：yfinance → FinMind → Fugle
    """
    # 1. yfinance（最快，首選）
    price = get_price_yf(symbol)
    if price:
        return price

    # 2. FinMind
    price = get_price_finmind(symbol)
    if price:
        return price

    # 3. Fugle（最後備援）
    price = get_price_fugle(symbol)
    if price:
        return price

    return None


def get_full_quote(symbol):
    """取得完整報價：價格 + RSI + 技術指標"""
    result = {'symbol': symbol}

    # 價格（yfinance）
    price = get_price_yf(symbol)
    if price:
        result['price'] = price
        result['rsi'] = get_rsi_yf(symbol)
    else:
        # Fallback Fugle
        pf = get_price_fugle(symbol)
        if pf:
            result['price'] = pf

    time.sleep(MIN_INTERVAL)

    # 技術指標（Fugle）
    tech = get_technical_fugle(symbol)
    if tech:
        result['technical'] = tech

    return result


if __name__ == '__main__':
    import sys
    sym = sys.argv[1] if len(sys.argv) > 1 else '2330'

    print(f'=== 即時報價測試 — {sym} ===')
    print()

    p = get_realtime_price(sym)
    if p:
        print(f'來源: {p.get("source")}')
        print(f'價格: {p.get("close")}')
        print(f'日期: {p.get("date")}')
        print()
    else:
        print('取得失敗')
