# -*- coding: utf-8 -*-
"""
tw_trinity_watchlist.py — 台股三位一體觀察名單（精簡版）
使用確認有效的股票代碼
"""

import yfinance as yf, json
from datetime import datetime

def calc_rsi(closes, period=14):
    delta = closes.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))
    avg_gain = gain.ewm(com=period-1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period-1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# Confirmed valid TW major stocks
VALID = [
    ('2330','TW'),('2454','TW'),('2317','TW'),('2379','TW'),('2376','TW'),
    ('2382','TW'),('3034','TW'),('2303','TW'),('3008','TW'),('2458','TW'),
    ('2408','TW'),('2357','TW'),('4958','TW'),('2308','TW'),('2492','TW'),
    ('2401','TW'),('2449','TW'),('2441','TW'),('3022','TW'),('3189','TW'),
    ('3231','TW'),('3419','TW'),('3532','TW'),('3686','TW'),('3704','TW'),
    ('3714','TW'),('4551','TW'),('4746','TW'),('4938','TW'),('5274','TW'),
    ('5388','TW'),('5455','TW'),('5515','TW'),('5530','TW'),('5566','TW'),
    ('5871','TW'),('5880','TW'),('6116','TW'),('6128','TW'),('6147','TW'),
    ('6165','TW'),('6170','TW'),('6214','TW'),('6288','TW'),('6409','TW'),
    ('6412','TW'),('6426','TW'),('6515','TW'),('6533','TW'),('6541','TW'),
    ('6572','TW'),('6581','TW'),('6702','TW'),('6754','TW'),('6770','TW'),
    ('8011','TW'),('8016','TW'),('8028','TW'),('8032','TW'),('8046','TW'),
    ('8070','TW'),('8101','TW'),('8105','TW'),('8112','TW'),('8121','TW'),
    ('8150','TW'),('8163','TW'),('8173','TW'),('8192','TW'),('8200','TW'),
    ('8255','TW'),('8281','TW'),('8306','TW'),('8358','TW'),('8369','TW'),
    ('8409','TW'),('8410','TW'),('8427','TW'),('8473','TW'),('8481','TW'),
    ('8499','TW'),('8577','TW'),('8709','TW'),
    # TW TWO
    ('2347','TWO'),('2383','TWO'),('2430','TWO'),('2464','TWO'),('2649','TWO'),
    ('3128','TWO'),('3217','TWO'),('3228','TWO'),('3273','TWO'),('3317','TWO'),
    ('3324','TWO'),('3434','TWO'),('3438','TWO'),('3465','TWO'),('3521','TWO'),
    ('3522','TWO'),('3550','TWO'),('3570','TWO'),('3615','TWO'),('3628','TWO'),
    ('3646','TWO'),('3680','TWO'),('3781','TWO'),('4164','TWO'),('4205','TWO'),
    ('4406','TWO'),('4426','TWO'),('4440','TWO'),('4529','TWO'),('4544','TWO'),
    ('4648','TWO'),('4725','TWO'),('4755','TWO'),('4804','TWO'),('4944','TWO'),
    ('4955','TWO'),('5228','TWO'),('5244','TWO'),('5259','TWO'),('5272','TWO'),
    ('5314','TWO'),('5324','TWO'),('5364','TWO'),('5398','TWO'),('5416','TWO'),
    ('5498','TWO'),('5604','TWO'),('5609','TWO'),('5615','TWO'),('5722','TWO'),
    ('5761','TWO'),('5927','TWO'),('5965','TWO'),('6016','TWO'),('6056','TWO'),
    ('6100','TWO'),('6186','TWO'),('6225','TWO'),('6255','TWO'),('6303','TWO'),
    ('6334','TWO'),('6527','TWO'),('6547','TWO'),('6573','TWO'),('6576','TWO'),
    ('6670','TWO'),('6683','TWO'),('6713','TWO'),('6756','TWO'),('6764','TWO'),
    ('6779','TWO'),('6790','TWO'),('6817','TWO'),('8044','TWO'),('8092','TWO'),
    ('8155','TWO'),('8177','TWO'),('8202','TWO'),('8227','TWO'),('8249','TWO'),
    ('8261','TWO'),('8277','TWO'),('8284','TWO'),('8297','TWO'),('8341','TWO'),
    ('8367','TWO'),('8436','TWO'),('8478','TWO'),('8728','TWO'),('8733','TWO'),
    ('8941','TWO'),('8951','TWO'),('8999','TWO'),('9103','TWO'),('9443','TWO'),
    ('9479','TWO'),('9503','TWO'),('9508','TWO'),('9514','TWO'),('9762','TWO'),
]

def analyze(symbol, market):
    try:
        sym = f'{symbol}.{market}'
        df = yf.Ticker(sym).history(period='3mo', interval='1d', auto_adjust=True, timeout=8)
        if df is None or len(df) < 60:
            return None
        closes = df['Close']
        highs = df['High']; lows = df['Low']
        
        rsi_cur = float(calc_rsi(closes).iloc[-1])
        if rsi_cur != rsi_cur: return None
        
        ma20 = float(closes.rolling(20).mean().iloc[-1])
        ma60_vals = closes.rolling(60).mean().dropna()
        if len(ma60_vals) < 5: return None
        ma60 = float(ma60_vals.iloc[-1])
        
        n = 9; m1 = 3; m2 = 3
        ll = lows.rolling(n).min(); hh = highs.rolling(n).max()
        rsv = (closes - ll) / (hh - ll) * 100
        K = rsv.ewm(com=m1-1, min_periods=0).mean()
        D = K.ewm(com=m2-1, min_periods=0).mean()
        J = K * 3 - D * 2
        k_cur = float(K.iloc[-1]); d_cur = float(D.iloc[-1])
        k_prev = float(K.iloc[-2]); d_prev = float(D.iloc[-2])
        kd_cross_up = k_prev < d_prev and k_cur > d_cur
        kd_cross_down = k_prev > d_prev and k_cur < d_cur
        
        ema12 = closes.ewm(span=12).mean(); ema26 = closes.ewm(span=26).mean()
        macd = ema12 - ema26; sig = macd.ewm(span=9).mean()
        hist = macd - sig
        hist_now = float(hist.iloc[-1])
        
        price = float(closes.iloc[-1])
        prev = float(closes.iloc[-2]) if len(closes) > 1 else price
        chg = (price - prev) / prev * 100
        
        ma_ok = ma20 > ma60
        macd_ok = hist_now > 0
        kdj_ok = kd_cross_up
        rsi_ok = rsi_cur < 65
        
        score = sum([ma_ok, macd_ok, kdj_ok, rsi_ok])
        if score < 2 or not rsi_ok: return None
        
        action = 'BUY' if score >= 3 else 'WATCH'
        kd_sig = 'GOLDEN_CROSS' if kd_cross_up else ('DEAD_CROSS' if kd_cross_down else 'FLAT')
        macd_dir = 'UP' if hist_now > 0 else 'DOWN'
        ma_diff = (ma20 - ma60) / ma60 * 100
        
        return {
            'symbol': symbol, 'market': market, 'price': round(price, 2),
            'chg': round(chg, 2), 'rsi': round(rsi_cur, 1),
            'ma20': round(ma20, 2), 'ma60': round(ma60, 2), 'ma_diff': round(ma_diff, 2),
            'macd_hist': round(hist_now, 2), 'macd_dir': macd_dir,
            'kdj_K': round(k_cur, 1), 'kdj_D': round(d_cur, 1), 'kdj_sig': kd_sig,
            'score': score, 'action': action,
        }
    except: return None

# TWII
twii = yf.Ticker('^TWII').history(period='5d', interval='1d')
twii_closes = twii['Close'].dropna()
twii_rsi = float(calc_rsi(twii_closes).iloc[-1])
twii_cur = float(twii_closes.iloc[-1])
print(f'TWII: {twii_cur:.0f} | RSI: {twii_rsi:.1f}')

results = []
total = len(VALID)

for i, (sym, market) in enumerate(VALID, 1):
    r = analyze(sym, market)
    if r: results.append(r)
    if i % 30 == 0: print(f'  {i}/{total}...')

results.sort(key=lambda x: (-x['score'], x['rsi']))

print(f'\n=== 三位一體觀察名單 ({len(results)} 檔通過) ===\n')
for i, r in enumerate(results[:30], 1):
    icon = '[BUY]' if r['action'] == 'BUY' else '[WATCH]'
    print(f"{i:2}. {r['symbol']:6} {r['market']} {r['price']:8.2f} ({r['chg']:+.2f}%) RSI:{r['rsi']:5.1f} MA20:{r['ma20']:8.2f} MA60:{r['ma60']:8.2f} ({r['ma_diff']:+.1f}%) MACD:{r['macd_dir']}({r['macd_hist']:+.2f}) KDJ:{r['kdj_sig']:12} {r['score']}/4 {icon}")

path = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\stores\short_term\tw_trinity_watchlist.json'
with open(path, 'w', encoding='utf-8') as f:
    json.dump({
        'TWII': {'price': round(twii_cur, 1), 'rsi': round(twii_rsi, 1)},
        'scan_time': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'total_scanned': total, 'passed': len(results), 'results': results[:50]
    }, f, ensure_ascii=False, indent=2)
print(f'\nSaved: {path}')