# Taiwan ETF Trinity Live Scan
import yfinance as yf
import json
from datetime import datetime

def calc_rsi(closes, period=14):
    delta = closes.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))
    avg_gain = gain.ewm(com=period-1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period-1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

ETFS = [
    ('0050', 'YuanDa Taiwan50'),
    ('0056', 'YuanDa HighDiv'),
    ('00713', 'YuanDa HiDivLowVol'),
    ('00646', 'Fubon S&P500'),
    ('00662', 'Fubon Nasdaq100'),
    ('00757', 'TongYi FANG+'),
    ('00727', 'FH China5G'),
    ('00891', 'CTBC Semi'),
    ('00892', 'Fubon Taiwan5G+'),
    ('00929', 'FH TaiwanTechDiv'),
    ('00927', 'TongYi Inno'),
    ('00937', 'ESGCarbon'),
    ('00878', 'Cathay SustHiDiv'),
    ('00741', 'Capco ESGLowCarb'),
]

results = []
for sym, name in ETFS:
    try:
        df = yf.Ticker(f'{sym}.TW').history(period='5d', interval='1d', auto_adjust=True, timeout=5)
        if df is None or len(df) < 2:
            continue
        closes = df['Close']
        cur = float(closes.iloc[-1])
        prev = float(closes.iloc[-2])
        chg = (cur - prev) / prev * 100

        df6 = yf.Ticker(f'{sym}.TW').history(period='6mo', interval='1d', auto_adjust=True, timeout=5)
        c6 = df6['Close']; h6 = df6['High']; l6 = df6['Low']

        rsi_cur = float(calc_rsi(c6).iloc[-1])
        ma20 = float(c6.rolling(20).mean().iloc[-1])
        ma60_v = c6.rolling(60).mean().dropna()
        ma60 = float(ma60_v.iloc[-1]) if len(ma60_v) > 0 else None
        ma_ok = ma60 is not None and ma20 > ma60

        ema12 = c6.ewm(span=12).mean(); ema26 = c6.ewm(span=26).mean()
        macd = ema12 - ema26; sig = macd.ewm(span=9).mean()
        hist = macd - sig
        hist_now = float(hist.iloc[-1])
        macd_ok = hist_now > 0

        n = 9; m1 = 3; m2 = 3
        ll = l6.rolling(n).min(); hh = h6.rolling(n).max()
        rsv = (c6 - ll) / (hh - ll) * 100
        K = rsv.ewm(com=m1-1, min_periods=0).mean()
        D = K.ewm(com=m2-1, min_periods=0).mean()
        k_cur = float(K.iloc[-1]); d_cur = float(D.iloc[-1])
        k_prev = float(K.iloc[-2]); d_prev = float(D.iloc[-2])
        kd_cross_up = k_prev < d_prev and k_cur > d_cur
        kd_ok = kd_cross_up

        rsi_ok = rsi_cur < 65
        score = sum([ma_ok, macd_ok, kd_ok, rsi_ok])
        ma_diff = (ma20 - ma60) / ma60 * 100 if ma60 else 0

        results.append({
            'symbol': sym, 'name': name, 'price': cur, 'chg': round(chg, 2),
            'rsi': round(rsi_cur, 1),
            'ma20': round(ma20, 2),
            'ma60': round(ma60, 2) if ma60 else None,
            'ma_diff': round(ma_diff, 1),
            'macd_hist': round(hist_now, 2),
            'kdj': 'GOLDEN_CROSS' if kd_cross_up else 'FLAT',
            'score': score, 'signal': 'BUY' if score >= 3 else 'WATCH'
        })
    except Exception as e:
        pass

results.sort(key=lambda x: (-x['score'], x['rsi']))

# TWII
twii = yf.Ticker('^TWII').history(period='3d', interval='1d')
twii_cur = float(twii['Close'].iloc[-1])
twii_rsi = float(calc_rsi(twii['Close'].dropna()).iloc[-1])

print(f'TWII: {twii_cur:,.0f} | RSI: {twii_rsi:.1f}')
print()
header = '  # Code  Name              Price    Day%   RSI     MA20     MA60  MA%   MACD KDJ            Sc Signal'
print(header)
print('-' * 115)
for i, r in enumerate(results, 1):
    icon = '[BUY]' if r['signal'] == 'BUY' else '[WATCH]'
    ma60_s = f"{r['ma60']:.2f}" if r['ma60'] else 'N/A'
    print(f"{i:2}. {r['symbol']:5} {r['name']:16} {r['price']:8.2f} ({r['chg']:+.2f}%) RSI:{r['rsi']:5.1f} MA20:{r['ma20']:9.2f} MA60:{ma60_s:>9} ({r['ma_diff']:+.1f}%) MACD:{r['macd_hist']:+.2f} {r['kdj']:13} {r['score']}/4 {icon}")

path = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\stores\short_term\tw_etf_trinity.json'
with open(path, 'w', encoding='utf-8') as f:
    json.dump({
        'TWII': round(twii_cur), 'twii_rsi': round(twii_rsi, 1),
        'scan_time': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'results': results
    }, f, ensure_ascii=False, indent=2)
print(f'\nSaved: {path}')