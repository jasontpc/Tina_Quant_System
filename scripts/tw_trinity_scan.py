# Taiwan Trinity Watchlist — parallel scan with correct data length
import yfinance as yf, json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np

def calc_rsi(closes, period=14):
    delta = closes.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))
    avg_gain = gain.ewm(com=period-1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period-1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

ACTIVE_TW = [
    '2330','2454','2317','2376','2379','2382','3034','2303','3008','2458',
    '2408','2357','4958','2308','2492','2401','2449','2441','3022','3189',
    '3231','3419','3532','3686','3704','3714','4551','4746','4938','5388',
    '5515','5530','5566','5871','5880','6116','6128','6147','6165','6214',
    '6288','6409','6412','6426','6515','6533','6541','6572','6581','6754',
    '6770','8011','8016','8028','8032','8046','8070','8101','8105','8112',
    '8150','8163','8173','8192','8200','8255','8281','8306','8358','8369',
    '8409','8410','8427','8473','8481','8499','8577','8709','2327','2345',
    '2356','2360','2371','2377','2402','2405','2412','2431','2444','2451',
    '2455','2464','2474','2478','2481','2485','2491','2504','2511','2521',
]

def analyze(sym_id):
    sym = f'{sym_id}.TW'
    try:
        # Use 6mo to get ~120 rows (enough for MA60)
        df = yf.Ticker(sym).history(period='6mo', interval='1d', auto_adjust=True, timeout=5)
        if df is None or len(df) < 65: return None
        closes = df['Close']; highs = df['High']; lows = df['Low']

        rsi_vals = calc_rsi(closes)
        rsi_cur = float(rsi_vals.iloc[-1])
        if rsi_cur != rsi_cur or rsi_cur >= 65: return None

        ma20 = float(closes.rolling(20).mean().iloc[-1])
        ma60_vals = closes.rolling(60).mean().dropna()
        if len(ma60_vals) < 5: return None
        ma60 = float(ma60_vals.iloc[-1])
        if ma20 <= ma60: return None

        n, m1, m2 = 9, 3, 3
        ll = lows.rolling(n).min(); hh = highs.rolling(n).max()
        rsv = (closes - ll) / (hh - ll) * 100
        K = rsv.ewm(com=m1-1, min_periods=0).mean()
        D = K.ewm(com=m2-1, min_periods=0).mean()
        k_cur = float(K.iloc[-1]); d_cur = float(D.iloc[-1])
        k_prev = float(K.iloc[-2]); d_prev = float(D.iloc[-2])
        kd_cross_up = k_prev < d_prev and k_cur > d_cur
        kd_sig = 'GOLDEN_CROSS' if kd_cross_up else 'FLAT'

        ema12 = closes.ewm(span=12).mean(); ema26 = closes.ewm(span=26).mean()
        macd = ema12 - ema26; sig = macd.ewm(span=9).mean()
        hist = macd - sig
        hist_now = float(hist.iloc[-1])
        if hist_now <= 0: return None

        price = float(closes.iloc[-1])
        prev = float(closes.iloc[-2]) if len(closes) > 1 else price
        chg = (price - prev) / prev * 100
        ma_diff = (ma20 - ma60) / ma60 * 100
        score = 3 if kd_cross_up else 2
        action = 'BUY' if score >= 3 else 'WATCH'

        return {
            'symbol': sym_id, 'market': 'TW',
            'price': round(price, 2), 'chg': round(chg, 2), 'rsi': round(rsi_cur, 1),
            'ma20': round(ma20, 2), 'ma60': round(ma60, 2), 'ma_diff': round(ma_diff, 2),
            'macd_hist': round(hist_now, 2), 'macd_dir': 'UP',
            'kdj_K': round(k_cur, 1), 'kdj_D': round(d_cur, 1), 'kdj_sig': kd_sig,
            'score': score, 'action': action,
        }
    except Exception as e:
        return None

# TWII
twii = yf.Ticker('^TWII').history(period='5d', interval='1d')
twii_closes = twii['Close'].dropna()
twii_rsi = float(calc_rsi(twii_closes).iloc[-1])
twii_cur = float(twii_closes.iloc[-1])
print(f'TWII: {twii_cur:.0f} | RSI: {twii_rsi:.1f}')

results = []
with ThreadPoolExecutor(max_workers=10) as exe:
    futures = {exe.submit(analyze, s): s for s in ACTIVE_TW}
    done = 0
    for fut in as_completed(futures):
        r = fut.result()
        if r: results.append(r)
        done += 1
        if done % 20 == 0: print(f'  {done}/{len(ACTIVE_TW)}... ({len(results)} passed)')

results.sort(key=lambda x: (-x['score'], x['rsi']))

print(f'\n=== 三位一體觀察名單 ({len(results)} 檔通過) ===')
print(f'{"#":2} {"代碼":6} {"價格":>9} {"日%":>7} {"RSI":>5} {"MA20":>9} {"MA60":>9} {"偏離":>6} {"MACD":>8} {"KDJ":12} {"分":2} {"建議"}\n')
for i, r in enumerate(results, 1):
    icon = '[BUY]' if r['action'] == 'BUY' else '[WATCH]'
    print(f"{i:2}. {r['symbol']:6} {r['price']:9.2f} ({r['chg']:+.2f}%) RSI:{r['rsi']:5.1f} MA20:{r['ma20']:9.2f} MA60:{r['ma60']:9.2f} ({r['ma_diff']:+.1f}%) MACD:UP({r['macd_hist']:+.2f}) KDJ:{r['kdj_sig']:12} {r['score']}/4 {icon}")

path = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\stores\short_term\tw_trinity_watchlist.json'
with open(path, 'w', encoding='utf-8') as f:
    json.dump({
        'TWII': {'price': round(twii_cur, 1), 'rsi': round(twii_rsi, 1)},
        'scan_time': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'total_scanned': len(ACTIVE_TW), 'passed': len(results), 'results': results
    }, f, ensure_ascii=False, indent=2)
print(f'\nSaved: {path}')