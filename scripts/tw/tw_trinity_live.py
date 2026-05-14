# Fresh scan of watchlist stocks with live data
import yfinance as yf
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

def calc_rsi(closes, period=14):
    delta = closes.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))
    avg_gain = gain.ewm(com=period-1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period-1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

WATCHLIST = ['2458','5388','2485','8499','2441','2412','8150','2360','3704','2382','2455','2464']
EXTRA = ['2330','2454','2317','2376','3034','2303','4958']

def analyze(sym_id):
    sym = f'{sym_id}.TW'
    try:
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
            'symbol': sym_id,
            'price': round(price, 2),
            'chg': round(chg, 2),
            'rsi': round(rsi_cur, 1),
            'ma20': round(ma20, 2),
            'ma60': round(ma60, 2),
            'ma_diff': round(ma_diff, 2),
            'macd_hist': round(hist_now, 2),
            'kdj_K': round(k_cur, 1),
            'kdj_D': round(d_cur, 1),
            'kdj_sig': kd_sig,
            'score': score,
            'action': action,
        }
    except: return None

results = []
with ThreadPoolExecutor(max_workers=10) as exe:
    futures = {exe.submit(analyze, s): s for s in WATCHLIST + EXTRA}
    for fut in as_completed(futures):
        r = fut.result()
        if r: results.append(r)

results.sort(key=lambda x: (-x['score'], x['rsi']))

# Load TWII from saved scan
twii_data = {}
try:
    with open(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\stores\short_term\twii_trinity.json') as f:
        twii_data = json.load(f)
except: pass

print(f"TWII: {twii_data.get('TWII', 'N/A')} | RSI: {twii_data.get('RSI', 'N/A')}")
print(f"Scan time: {datetime.now().strftime('%H:%M')}\n")
header = "  # Code      Price    Day%   RSI     MA20     MA60  MAdiff   MACD KDJ            Sc Signal"
print(header)
print("-" * 100)
for i, r in enumerate(results, 1):
    icon = '[BUY]' if r['action'] == 'BUY' else '[WATCH]'
    kdj = r['kdj_sig']
    line = f"{i:2}. {r['symbol']:6} {r['price']:8.2f} ({r['chg']:+.2f}%) RSI:{r['rsi']:5.1f} MA20:{r['ma20']:8.2f} MA60:{r['ma60']:8.2f} ({r['ma_diff']:+.1f}%) MACD:{r['macd_hist']:+.2f} {kdj:13} {r['score']}/4 {icon}"
    print(line)

path = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\stores\short_term\tw_trinity_watchlist_live.json'
with open(path, 'w', encoding='utf-8') as f:
    json.dump({'scan_time': datetime.now().strftime('%Y-%m-%d %H:%M'), 'results': results}, f, ensure_ascii=False, indent=2)
print(f"\nSaved: {path}")