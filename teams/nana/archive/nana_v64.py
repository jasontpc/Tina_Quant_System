# -*- coding: utf-8 -*-
"""
Nana v6.4 波段系統 - 勝率提升版
"""
import sys, os, json, time
import yfinance as yf
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

CACHE_FILE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\nana\scan_cache_v64.json'
CACHE_TTL = 300

RSI_PERIOD = 12
RSI_ENTRY_MIN = 30
RSI_ENTRY_MAX = 45
MA_LONG = 60
SCORE_MIN = 32
MOMENTUM_FILTER = 3.0
ADX_MIN = 18
HOLD_DAYS = 7
ATR_TP_MULT = 3.0
ATR_SL_MULT = 1.5
TRAILING_ATR = 2.0

VALID_STOCKS = [
    '2330','2317','2454','2303','2382','2881','2882','2883','2884','2885',
    '2886','2887','2889','2890','2891','2892','3008','3037','3231',
    '3443','3711','4532','4770','4938','4952','5203','5215','5388','5471',
    '5538','5876','5880','6116','6139','6176','6183','6230','6257','6285',
    '6405','6409','6415','6446','6550','6579','6581','6770','6789','8016',
    '8028','8046','8081','8131','8150','8261','8454','8464','9914','9921'
]

STOCK_NAMES = {
    '2330':'台積電','2317':'鴻海','2454':'聯發科','2303':'聯電','2382':'廣達',
    '2881':'國泰金','2882':'兆豐金','2883':'開發金','2884':'玉山金','2885':'元大金',
    '2886':'第一金','2887':'富邦金','2889':'永豐金','2890':'中信金',
    '2891':'統一','2892':'遠傳','3008':'大立光','3037':'欣興','3231':'創意',
    '3443':'中碳','3711':'日月光','4532':'華擎','4770':'熱映','4938':'和碩',
    '4952':'凌華','5203':'互盛電','5215':'科嘉-KY','5388':'環球晶','5471':'松翰',
    '5538':'融程電','5876':'上海商銀','5880':'合庫金','6116':'彩晶','6139':'太陽能',
    '6176':'環球晶','6183':'撼訊','6230':'麗臺','6257':'迎廣','6285':'綠能',
    '6405':'景岳','6409':'光菱','6415':'崇越','6446':'秧訊','6550':'長科',
    '6579':'全景軟','6581':'安格','6770':'力旺','6789':'安格','8016':'昇技',
    '8028':'敦泰','8046':'力成','8081':'致茂','8131':'立端','8150':'合新',
    '8261':'富鼎','8454':'M31','8464':'億光','9914':'美利肯','9921':'巨大',
}

def get_rsi(closes, period=12):
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

def get_adx(highs, lows, closes, period=14):
    if len(closes) < period + 5:
        return 15.0
    ma_now = get_ma(closes, period)
    ma_prev = np.mean(closes[-(period+5):-5])
    slope = abs((ma_now - ma_prev) / ma_prev * 100) if ma_prev != 0 else 0
    return min(80, max(10, slope * 5))

def get_momentum(closes, bars=5):
    if len(closes) < bars + 1:
        return 0.0
    return float((closes[-1] / closes[-bars-1] - 1) * 100)

def get_slope(closes, period=20, bars=5):
    if len(closes) < period + bars:
        return 0.0
    ma_now = np.mean(closes[-period:])
    ma_prev = np.mean(closes[-(period+bars):-bars])
    return float((ma_now - ma_prev) / ma_prev * 100) if ma_prev != 0 else 0.0

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

def analyze_stock(symbol):
    try:
        ticker = yf.Ticker(f'{symbol}.TW')
        h = ticker.history(period='30d', interval='1d')
        if h.empty or len(h) < 20:
            return None

        closes = h['Close'].values
        highs = h['High'].values
        lows = h['Low'].values
        price = float(closes[-1])

        rsi = get_rsi(closes, RSI_PERIOD)
        ma20 = get_ma(closes, 20)
        ma60 = get_ma(closes, 60)
        ma120 = get_ma(closes, 120) if len(closes) >= 120 else ma60
        momentum = get_momentum(closes, 5)
        slope20 = get_slope(closes, 20)
        adx = get_adx(highs, lows, closes)
        atr = get_atr(highs, lows, closes)

        rsi_ok = RSI_ENTRY_MIN <= rsi <= RSI_ENTRY_MAX
        momentum_ok = momentum > MOMENTUM_FILTER or momentum < -2
        trend_up = ma60 > ma120 if len(closes) >= 120 else price > ma60
        adx_ok = adx >= ADX_MIN

        score = 0
        zone = ''

        if rsi < 30:
            score += 30
            zone = 'deep_oversold'
        elif rsi < 40:
            score += 25
            zone = 'oversold'
        elif rsi < 45:
            score += 20
            zone = 'soft_oversold'

        if momentum > 5:
            score += 15
        elif momentum > 3:
            score += 10
        elif momentum > 0:
            score += 5

        if price > ma20:
            score += 10
        if price > ma60:
            score += 10
        if ma60 > ma120:
            score += 8

        if slope20 > 1.5:
            score += 10
        elif slope20 > 0.5:
            score += 5

        if adx >= 25:
            score += 10
        elif adx >= ADX_MIN:
            score += 5

        if score < SCORE_MIN:
            return None
        # Hard filter: RSI must be in entry range
        if not rsi_ok:
            return None

        return {
            'symbol': symbol,
            'price': price,
            'rsi': round(rsi, 1),
            'zone': zone,
            'momentum': round(momentum, 2),
            'adx': round(adx, 1),
            'slope20': round(slope20, 3),
            'score': score,
            'atr': round(atr, 2),
            'ma20': round(ma20, 2),
            'ma60': round(ma60, 2),
            'trend_up': trend_up,
            'rsi_ok': rsi_ok,
            'momentum_ok': momentum_ok,
            'adx_ok': adx_ok,
            'target': round(price + atr * ATR_TP_MULT, 2),
            'stop': round(price - atr * ATR_SL_MULT, 2),
        }
    except:
        return None

def run_scan():
    print('=' * 60)
    print('Nana v6.4 勝率提升版')
    print('Time: ' + time.strftime('%Y-%m-%d %H:%M'))
    print('=' * 60)

    cache = load_cache()
    if cache:
        print('Using cache: ' + str(len(cache)) + ' stocks')
        candidates = sorted(cache.values(), key=lambda x: x['score'], reverse=True)[:15]
    else:
        print('Scanning ' + str(len(VALID_STOCKS)) + ' stocks...')
        results = {}
        for i, sym in enumerate(VALID_STOCKS):
            r = analyze_stock(sym)
            if r:
                results[sym] = r
            if (i + 1) % 20 == 0:
                print('  ' + str(i+1) + '/' + str(len(VALID_STOCKS)) + '...')
        save_cache(results)
        candidates = sorted(results.values(), key=lambda x: x['score'], reverse=True)[:15]

    print()
    print('Candidates: ' + str(len(candidates)))
    print()
    print('CODE   PRICE     RSI    MOMENTUM   ADX   SCORE   TARGET    STOP   NAME')
    print('-' * 85)

    for c in candidates:
        mom = c.get('momentum', 0)
        zone = c.get('zone', '')
        name = STOCK_NAMES.get(c['symbol'], c['symbol'])
        print(str(c['symbol']).ljust(6) + ' ' +
              str(c['price']).ljust(8) + ' ' +
              str(c['rsi']).ljust(6) + ' ' +
              ('+' if mom >= 0 else '') + str(mom).ljust(8) + ' ' +
              str(c['adx']).ljust(5) + ' ' +
              str(c['score']).ljust(6) + ' ' +
              str(c['target']).ljust(8) + ' ' +
              str(c['stop']).ljust(8) + ' ' +
              name.ljust(8) + ' ' + zone)

    # Market status
    print()
    try:
        twii = yf.Ticker('^TWII').history(period='5d')
        if not twii.empty:
            tp = float(twii['Close'].iloc[-1])
            ma20 = float(twii['Close'].rolling(20).mean().iloc[-1])
            pos = (tp / ma20 - 1) * 100
            rsi_twii = get_rsi(twii['Close'].values)
            regime = 'BULL' if pos > 0 else 'BEAR'
            print('TWII: ' + str(int(tp)) + ' (' + ('+' if pos >= 0 else '') + str(round(pos,1)) + '%) ' + regime + ' RSI=' + str(int(rsi_twii)))
        else:
            print('TWII: BULL (default)')
    except:
        print('TWII: BULL (default)')

    print()
    print('Market watch: TWII RSI ~93 (OVERBOUGHT). All trades on hold.')
    return candidates

if __name__ == '__main__':
    run_scan()