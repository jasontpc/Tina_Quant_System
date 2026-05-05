# -*- coding: utf-8 -*-
"""
Nana v6.3 波段系統 — 輕量版（每20分鐘執行）
避免 Timeout：使用緩存、限制股票數、加快速度
"""
import sys, os, json, time
import yfinance as yf
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

# 快取檔案
CACHE_FILE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\nana\scan_cache.json'
CACHE_TTL = 300  # 5分鐘快取

# 核心參數（Grid Search 優化）
ENTRY_RSI_MIN = 35
ENTRY_RSI_MAX = 55
ENTRY_SCORE_MIN = 35
HOLD_DAYS = 7
ATR_TP_MULT = 3.0
ATR_SL_MULT = 2.0
TRAILING_ATR = 2.0

VALID_STOCKS = [
    '2330','2317','2454','2303','2382','2881','2882','2883','2884','2885',
    '2886','2887','2889','2890','2891','2892','3008','3037','3231',
    '3443','3711','4532','4770','4938','4952','5203','5215','5388','5471',
    '5538','5876','5880','6116','6139','6176','6183','6230','6257','6285',
    '6405','6409','6415','6446','6550','6579','6581','6770','6789','8016',
    '8028','8046','8081','8131','8150','8261','8454','8464','9914','9921'
]

def get_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50.0
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0:
        return 100.0
    return float(100 - (100 / (1 + avg_gain / avg_loss)))

def get_ma(closes, period):
    if len(closes) < period:
        return 0.0
    return float(np.mean(closes[-period:]))

def get_atr(highs, lows, closes, period=14):
    if len(closes) < period + 1:
        return 5.0
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        trs.append(tr)
    return float(np.mean(trs[-period:])) if trs else 5.0

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                data = json.load(f)
            if time.time() - data.get('ts', 0) < CACHE_TTL:
                return data.get('results', {})
        except:
            pass
    return {}

def save_cache(results):
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump({'ts': time.time(), 'results': results}, f)
    except:
        pass

def scan_stock(symbol):
    try:
        ticker = yf.Ticker(f'{symbol}.TW')
        h = ticker.history(period='10d', interval='1d')
        if h.empty or len(h) < 5:
            return None
        closes = h['Close'].values
        highs = h['High'].values
        lows = h['Low'].values

        rsi = get_rsi(closes)
        ma20 = get_ma(closes, 20)
        ma60 = get_ma(closes, 60) if len(closes) >= 60 else get_ma(closes, len(closes)//2)
        ma120 = get_ma(closes, 120) if len(closes) >= 120 else ma60

        price = float(closes[-1])
        ma20_diff = ((price - ma20) / ma20 * 100) if ma20 != 0 else 0
        ma60_diff = ((price - ma60) / ma60 * 100) if ma60 != 0 else 0

        momentum = float((closes[-1] / closes[-5] - 1) * 100) if len(closes) >= 5 else 0
        slope20 = float((ma20 - np.mean(closes[-25:-5])) / np.mean(closes[-25:-5]) * 100) if len(closes) >= 25 else 0

        # 評分
        score = 0
        if ENTRY_RSI_MIN <= rsi <= ENTRY_RSI_MAX:
            if 40 <= rsi <= 50: score += 20
            elif 30 <= rsi < 40 or 50 < rsi <= 55: score += 10
        if abs(ma20_diff) < 2: score += 15
        elif abs(ma20_diff) < 3: score += 10
        if momentum > 3: score += 10
        elif momentum > 0: score += 5
        if slope20 > 1.0: score += 8
        elif slope20 > 0.5: score += 5
        if ma60_diff > 0: score += 5

        if score < ENTRY_SCORE_MIN:
            return None

        atr = get_atr(highs, lows, closes)
        return {
            'symbol': symbol, 'price': price, 'rsi': round(rsi, 1),
            'ma20_diff': round(ma20_diff, 2), 'ma60_diff': round(ma60_diff, 2),
            'score': score, 'momentum': round(momentum, 2),
            'slope20': round(slope20, 3), 'atr': round(atr, 2),
            'target': round(price + atr * ATR_TP_MULT, 2),
            'stop': round(price - atr * ATR_SL_MULT, 2),
        }
    except:
        return None

def run_scan():
    print('=== Nana v6.3 輕量掃描 ===')
    print(f'時間: {time.strftime("%Y-%m-%d %H:%M")}')

    cache = load_cache()
    if cache:
        print(f'使用快取: {len(cache)} 檔')
        candidates = sorted(cache.values(), key=lambda x: x['score'], reverse=True)[:10]
    else:
        print(f'掃描 {len(VALID_STOCKS)} 檔...')
        results = {}
        for i, sym in enumerate(VALID_STOCKS):
            r = scan_stock(sym)
            if r:
                results[sym] = r
            if (i + 1) % 20 == 0:
                print(f'  {i+1}/{len(VALID_STOCKS)}...')
        save_cache(results)
        candidates = sorted(results.values(), key=lambda x: x['score'], reverse=True)[:10]

    print(f'發現 {len(candidates)} 檔進場候選')
    for i, c in enumerate(candidates[:5]):
        print(f'  {i+1}. {c["symbol"]}: ${c["price"]} RSI={c["rsi"]} Score={c["score"]} Momentum={c["momentum"]}%')

    # Regime 簡查
    try:
        twii = yf.Ticker('^TWII').history(period='5d')
        if not twii.empty:
            twii_price = twii['Close'].iloc[-1]
            twii_ma20 = twii['Close'].rolling(20).mean().iloc[-1]
            pos = (twii_price / twii_ma20 - 1) * 100
            regime = 'BULL' if pos > 0 else 'BEAR'
            print(f'大盤: {twii_price:.0f} ({pos:+.1f}%) Regime={regime}')
    except:
        print('大盤: BULL（預設）')

    return candidates

if __name__ == '__main__':
    run_scan()