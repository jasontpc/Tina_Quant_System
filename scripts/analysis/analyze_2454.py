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

sym = '2454.TW'
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

# TWII
twii = yf.Ticker('^TWII').history(period='5d', interval='1d')
twii_cur = float(twii['Close'].iloc[-1])
twii_rsi_vals = calc_rsi(twii['Close'].dropna())
twii_rsi = float(twii_rsi_vals.iloc[-1])

ma_score = 2 if ma5 > ma20 else 1 if ma5 > ma10 else 0
macd_score = 2 if macd_val > sig_val else 0
kdj_score = 2 if k_cross_up else 1 if k_cur > d_cur else 0
rsi_score = 2 if rsi_cur < 40 else 1 if rsi_cur < 65 else 0
total = ma_score + macd_score + kdj_score + rsi_score
ma_diff = (ma20 - ma60) / ma60 * 100

# Analyst data
t = yf.Ticker(sym)
info = t.info
rec = info.get('recommendationKey', 'N/A')
target = info.get('targetMeanPrice', 'N/A')
eps = info.get('trailingEps', 'N/A')
pe = info.get('trailingPE', 'N/A')
wk52_high = info.get('fiftyTwoWeekHigh', 'N/A')
wk52_low = info.get('fiftyTwoWeekLow', 'N/A')
mcap = info.get('marketCap', 'N/A')

out = f"""============================================================
              2454 聯發科 個股三位一體深度分析
============================================================
Scan time: {datetime.now().strftime('%Y-%m-%d %H:%M')}

[PRICE]
  Price:      {cur:,.0f} ({chg:+.2f}% today)
  5-day:      {chg5:+.2f}% | 20-day: {chg20:+.2f}%
  52w High:   {wk52_high:,.0f} | 52w Low: {wk52_low:,.0f}
  From 52w High: {(cur/wk52_high-1)*100:+.1f}%

------------------------------------------------------------
[PRICE + MA SYSTEM]
  MA5:   {ma5:,.0f}  MA10: {ma10:,.0f}  MA20: {ma20:,.0f}  MA60: {ma60:,.0f}
  MA diff (MA20/MA60): {ma_diff:+.1f}%
  State: {'BULLISH (price above all MAs)' if cur > ma20 else 'NEUTRAL' if cur > ma10 else 'BEARISH'}

------------------------------------------------------------
[MACD SYSTEM]
  MACD:   {macd_val:.2f}  Signal: {sig_val:.2f}  Hist: {hist_val:.2f}
  State:  {'BULLISH' if macd_val > sig_val else 'BEARISH'}
  Score:  {macd_score}/2

------------------------------------------------------------
[KDJ SYSTEM]
  K: {k_cur:.1f}  D: {d_cur:.1f}  J: {j_cur:.1f}
  Cross: {'*** GOLDEN CROSS ***' if k_cross_up else ('*** DEAD CROSS ***' if k_cross_down else 'FLAT')}
  State:  {'UPTREND (K>D)' if k_cur > d_cur else 'DOWNTREND'}
  Score:  {kdj_score}/2

------------------------------------------------------------
[RSI SYSTEM]
  RSI(14):   {rsi_cur:.1f}  (prev: {rsi_prev:.1f})
  RSI MA20:   {rsi_ma20:.1f}
  State:     {'OVERBOUGHT (>65)' if rsi_cur > 65 else 'NEUTRAL (40-65)' if rsi_cur > 40 else 'OVERSOLD'}
  Score:     {rsi_score}/2

------------------------------------------------------------
[FUNDAMENTALS]
  P/E:         {pe:.1f}x
  EPS:         {eps:.2f}
  Market Cap:  {mcap/1e12:.2f}T TWD
  Analyst Rec: {rec}
  Target Price:{target:,.1f} (current upside: {(target/cur-1)*100:+.1f}%)

------------------------------------------------------------
[MARKET CONTEXT]
  TWII:       {twii_cur:,.0f}
  TWII RSI:   {twii_rsi:.1f} ({'OVERBOUGHT' if twii_rsi > 70 else 'NEUTRAL'})

============================================================
[TRINITY SCORE] {total}/8
  MA: {ma_score}  MACD: {macd_score}  KDJ: {kdj_score}  RSI: {rsi_score}
============================================================"""
print(out)

result = {
    'symbol': '2454', 'price': cur, 'chg': round(chg, 2),
    'chg5': round(chg5, 2), 'chg20': round(chg20, 2),
    'rsi': round(rsi_cur, 1), 'rsi_prev': round(rsi_prev, 1),
    'ma5': round(ma5, 0), 'ma10': round(ma10, 0),
    'ma20': round(ma20, 0), 'ma60': round(ma60, 0),
    'macd': round(macd_val, 2), 'signal': round(sig_val, 2), 'hist': round(hist_val, 2),
    'kdj_K': round(k_cur, 1), 'kdj_D': round(d_cur, 1), 'kdj_J': round(j_cur, 1),
    'kdj_cross': 'golden' if k_cross_up else 'dead' if k_cross_down else 'flat',
    'ma_score': ma_score, 'macd_score': macd_score,
    'kdj_score': kdj_score, 'rsi_score': rsi_score, 'total_score': total,
    'twii': round(twii_cur), 'twii_rsi': round(twii_rsi, 1),
    'pe': round(pe, 1), 'eps': eps,
    'rec': rec, 'target': target,
    'scan_time': datetime.now().strftime('%Y-%m-%d %H:%M'),
}
path = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\stores\short_term\2454_trinity.json'
with open(path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f'\nSaved: {path}')