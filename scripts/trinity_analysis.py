import yfinance as yf, numpy as np, json
from datetime import datetime

def rsi14(closes):
    deltas = np.diff(closes, prepend=closes[0])
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    p = 14
    ag = np.zeros(len(closes)); al = np.zeros(len(closes))
    ag[p] = np.mean(gains[1:p+1]); al[p] = np.mean(losses[1:p+1])
    for i in range(p+1, len(closes)):
        ag[i] = (ag[i-1]*(p-1)+gains[i])/p
        al[i] = (al[i-1]*(p-1)+losses[i])/p
    rs = np.divide(ag, np.maximum(al, 1e-10), where=np.maximum(al,1e-10)!=0)
    return 100-(100/(1+rs))

def kdj(high, low, close, n=9, m1=3, m2=3):
    ll = np.zeros(len(close)); hh = np.zeros(len(close))
    for i in range(n-1, len(close)):
        ll[i] = np.min(low[i-n+1:i+1])
        hh[i] = np.max(high[i-n+1:i+1])
    rsv = (close - ll) / np.maximum(hh - ll, 1e-10) * 100
    rsv = np.nan_to_num(rsv, nan=50)
    K = np.zeros(len(close)); D = np.zeros(len(close))
    K[n-1] = 50; D[n-1] = 50
    for i in range(n, len(close)):
        K[i] = (K[i-1]*m1 + rsv[i]) / (m1+1)
        D[i] = (D[i-1]*m2 + K[i]) / (m2+1)
    J = K*3 - D*2
    return K, D, J

stocks = [
    ('2376.TW', 301, 664, '技嘉'),
    ('3034.TW', 442, 336, '緯穎'),
    ('2379.TW', 543, 367, '環球晶'),
]

# TWII
twii = yf.Ticker('^TWII').history(period='2d', interval='1h')
twii_closes = twii['Close'].dropna()
twii_rsi = rsi14(twii_closes)[-1]
twii_cur = twii_closes.iloc[-1]
print(f'TWII: {twii_cur:.0f} | RSI: {twii_rsi:.1f}')
print()

results = {}
for sym, cost, shares, name in stocks:
    try:
        df = yf.Ticker(sym).history(period='3mo', interval='1d', auto_adjust=True)
        if df is None or len(df) < 60:
            print(f'{sym}: insufficient data')
            continue
        closes = df['Close'].dropna()
        highs = df['High']; lows = df['Low']
        
        rsi_cur = rsi14(closes)[-1]
        ma20 = closes.rolling(20).mean().iloc[-1]
        ma60 = closes.rolling(60).mean().iloc[-1]
        K, D, J = kdj(highs.values, lows.values, closes.values)
        k_cur = K[-1]; d_cur = D[-1]; j_cur = J[-1]
        k_prev = K[-2]; d_prev = D[-2]
        kd_cross_up = k_prev < d_prev and k_cur > d_cur
        kd_cross_down = k_prev > d_prev and k_cur < d_cur
        
        ema12 = closes.ewm(span=12, adjust=False).mean()
        ema26 = closes.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        macd_sig = macd_line.ewm(span=9, adjust=False).mean()
        hist = macd_line - macd_sig
        hist_now = hist.iloc[-1]
        
        price = closes.iloc[-1]
        pnl = (price - cost) / cost * 100
        
        ma_ok = ma20 > ma60
        macd_ok = hist_now > 0
        kdj_ok = kd_cross_up
        rsi_ok = rsi_cur < 65
        
        score = sum([ma_ok, macd_ok, kdj_ok, rsi_ok])
        
        if pnl > 10 or rsi_cur > 68:
            action = 'TAKE_PROFIT'
        elif score >= 3 and rsi_ok:
            action = 'BUY'
        elif rsi_cur > 70:
            action = 'REDUCE'
        else:
            action = 'HOLD'
        
        print(f'{sym} {name}')
        print(f'  Price: {price:.0f} | PnL: {pnl:+.1f}%')
        print(f'  RSI: {rsi_cur:.1f} | MA20: {ma20:.1f} | MA60: {ma60:.1f}')
        macd_dir = 'UP' if hist_now > 0 else 'DOWN'
        print(f'  MACD: {macd_dir} (hist={hist_now:.2f})')
        kd_sig = 'GOLDEN_CROSS' if kd_cross_up else ('DEAD_CROSS' if kd_cross_down else 'FLAT')
        print(f'  KDJ: K={k_cur:.1f} D={d_cur:.1f} J={j_cur:.1f} [{kd_sig}]')
        print(f'  三位一體: MA={"OK" if ma_ok else "NG"} MACD={"OK" if macd_ok else "NG"} KDJ={"OK" if kdj_ok else "NG"}')
        print(f'  Score: {score}/4 | Action: {action}')
        print()
        
        results[sym] = {
            'name': name, 'price': round(price, 1), 'cost': cost,
            'shares': shares, 'pnl_pct': round(pnl, 2),
            'rsi': round(rsi_cur, 1), 'ma20': round(ma20, 1), 'ma60': round(ma60, 1),
            'macd_hist': round(hist_now, 2),
            'kdj': {'K': round(k_cur, 1), 'D': round(d_cur, 1), 'J': round(j_cur, 1), 'signal': kd_sig},
            '三位一體': {'MA_OK': ma_ok, 'MACD_OK': macd_ok, 'KDJ_OK': kdj_ok},
            'score': score, 'action': action,
            'updated': datetime.now().strftime('%Y-%m-%d %H:%M')
        }
    except Exception as e:
        print(f'{sym} Error: {e}')
        print()

# Save
output = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\stores\short_term\trinity_analysis.json'
with open(output, 'w', encoding='utf-8') as f:
    json.dump({
        'TWII': {'price': round(twii_cur, 1), 'rsi': round(twii_rsi, 1)},
        'positions': results,
        'generated': datetime.now().strftime('%Y-%m-%d %H:%M')
    }, f, ensure_ascii=False, indent=2)
print(f'Saved: {output}')