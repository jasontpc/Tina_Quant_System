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

sym = '2458.TW'
df = yf.Ticker(sym).history(period='6mo', interval='1d', auto_adjust=True)
closes = df['Close']; highs = df['High']; lows = df['Low']

rsi_vals = calc_rsi(closes)
rsi_cur = float(rsi_vals.iloc[-1])
rsi_prev = float(rsi_vals.iloc[-2])
rsi_ma20 = float(rsi_vals.rolling(20).mean().iloc[-1])

ma5 = float(closes.rolling(5).mean().iloc[-1])
ma10 = float(closes.rolling(10).mean().iloc[-1])
ma20 = float(closes.rolling(20).mean().iloc[-1])
ma60_vals = closes.rolling(60).mean().dropna()
ma60 = float(ma60_vals.iloc[-1])

cur = float(closes.iloc[-1])
prev = float(closes.iloc[-2])
chg = (cur - prev) / prev * 100
chg5 = (cur - float(closes.iloc[-6])) / float(closes.iloc[-6]) * 100
chg20 = (cur - float(closes.iloc[-21])) / float(closes.iloc[-21]) * 100

ema12 = closes.ewm(span=12).mean(); ema26 = closes.ewm(span=26).mean()
macd = ema12 - ema26; sig = macd.ewm(span=9).mean()
hist = macd - sig
macd_val = float(macd.iloc[-1]); sig_val = float(sig.iloc[-1]); hist_val = float(hist.iloc[-1])

n = 9; m1 = 3; m2 = 3
ll = lows.rolling(n).min(); hh = highs.rolling(n).max()
rsv = (closes - ll) / (hh - ll) * 100
K = rsv.ewm(com=m1-1, min_periods=0).mean()
D = K.ewm(com=m2-1, min_periods=0).mean()
J = K * 3 - D * 2
k_cur = float(K.iloc[-1]); d_cur = float(D.iloc[-1]); j_cur = float(J.iloc[-1])
k_prev = float(K.iloc[-2]); d_prev = float(D.iloc[-2])
k_cross_up = k_prev < d_prev and k_cur > d_cur
k_cross_down = k_prev > d_prev and k_cur < d_cur

# TWII for context
twii = yf.Ticker('^TWII').history(period='5d', interval='1d')
twii_cur = float(twii['Close'].iloc[-1])
twii_rsi = float(calc_rsi(twii['Close'].dropna()).iloc[-1])

# Score
ma_score = 2 if ma5 > ma20 else 1 if ma5 > ma10 else 0
macd_score = 2 if macd_val > sig_val else 0
kdj_score = 2 if k_cross_up else 1 if k_cur > d_cur else 0
rsi_score = 2 if rsi_cur < 40 else 1 if rsi_cur < 65 else 0
total = ma_score + macd_score + kdj_score + rsi_score

ma_diff = (ma20 - ma60) / ma60 * 100

out = f"""============================================================
              2458 聯發科 個股三位一體深度分析
============================================================
Scan time: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Stock: 2458.TW (MediaTek)
Price: {cur:.2f} ({chg:+.2f}% today)
5-day: {chg5:+.2f}% | 20-day: {chg20:+.2f}%

------------------------------------------------------------
[PRICE + MA SYSTEM]
  Price:   {cur:.2f}
  MA5:     {ma5:.2f}  ({'+' if ma5 > cur else '-'}{abs((ma5-cur)/cur*100):.1f}% from price)
  MA10:    {ma10:.2f}
  MA20:    {ma20:.2f}  ({'+' if ma20 < cur else '-'}{abs((ma20-cur)/cur*100):.1f}% from price)
  MA60:    {ma60:.2f}  ({'+' if ma60 < cur else '-'}{abs((ma60-cur)/cur*100):.1f}% from price)
  MA diff: {ma_diff:+.1f}%  (MA20 vs MA60)
  MA state: {'BULLISH (price above all MAs)' if cur > ma20 else 'NEUTRAL' if cur > ma10 else 'BEARISH'}

------------------------------------------------------------
[MACD SYSTEM]
  MACD:   {macd_val:.3f}
  Signal: {sig_val:.3f}
  Hist:   {hist_val:.3f}
  State:  {'BULLISH (MACD above signal)' if macd_val > sig_val else 'BEARISH'}
  Score:  {macd_score}/2

------------------------------------------------------------
[KDJ SYSTEM]
  K: {k_cur:.1f}  D: {d_cur:.1f}  J: {j_cur:.1f}
  Cross: {'*** GOLDEN CROSS ***' if k_cross_up else ('*** DEAD CROSS ***' if k_cross_down else 'FLAT (K>D)')}
  State:  {'Uptrend' if k_cur > d_cur else 'Downtrend'}
  Score:  {kdj_score}/2

------------------------------------------------------------
[RSI SYSTEM]
  RSI(14):    {rsi_cur:.1f}  (prev: {rsi_prev:.1f})
  RSI MA20:   {rsi_ma20:.1f}
  State:      {'OVERBOUGHT (>65)' if rsi_cur > 65 else 'NEUTRAL (40-65)' if rsi_cur > 40 else 'OVERSOLD (<40)'}
  Score:      {rsi_score}/2

------------------------------------------------------------
[MARKET CONTEXT]
  TWII:       {twii_cur:,.0f}
  TWII RSI:   {twii_rsi:.1f}  ({'OVERBOUGHT' if twii_rsi > 70 else 'NEUTRAL'})
  Beta info:  2458 is high-beta chip stock, amplify market moves

============================================================
[TRINITY SCORE] {total}/8
  MA: {ma_score}  MACD: {macd_score}  KDJ: {kdj_score}  RSI: {rsi_score}
============================================================
[SIGNAL] {'[STRONG BUY] - 3/4 conditions met' if total >= 5 else ('[BUY]' if k_cross_up else '[WATCH]')}
============================================================
"""
print(out)

# Save
result = {
    'symbol': '2458', 'price': cur, 'chg': round(chg, 2),
    'chg5': round(chg5, 2), 'chg20': round(chg20, 2),
    'rsi': round(rsi_cur, 1), 'rsi_prev': round(rsi_prev, 1),
    'ma5': round(ma5, 2), 'ma10': round(ma10, 2),
    'ma20': round(ma20, 2), 'ma60': round(ma60, 2),
    'macd': round(macd_val, 3), 'signal': round(sig_val, 3), 'hist': round(hist_val, 3),
    'kdj_K': round(k_cur, 1), 'kdj_D': round(d_cur, 1), 'kdj_J': round(j_cur, 1),
    'kdj_cross': 'golden' if k_cross_up else 'dead' if k_cross_down else 'flat',
    'ma_score': ma_score, 'macd_score': macd_score,
    'kdj_score': kdj_score, 'rsi_score': rsi_score, 'total_score': total,
    'twii': round(twii_cur), 'twii_rsi': round(twii_rsi, 1),
    'scan_time': datetime.now().strftime('%Y-%m-%d %H:%M'),
}
path = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\stores\short_term\2458_trinity.json'
with open(path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f'Saved: {path}')