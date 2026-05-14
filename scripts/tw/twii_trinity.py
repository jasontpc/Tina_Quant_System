# -*- coding: utf-8 -*-
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

twii = yf.Ticker('^TWII').history(period='3mo', interval='1d')
closes = twii['Close'].dropna()
highs = twii['High']; lows = twii['Low']

rsi_cur = float(calc_rsi(closes).iloc[-1])
rsi_prev = float(calc_rsi(closes).iloc[-2])

ma5 = float(closes.rolling(5).mean().iloc[-1])
ma10 = float(closes.rolling(10).mean().iloc[-1])
ma20 = float(closes.rolling(20).mean().iloc[-1])
ma60_vals = closes.rolling(60).mean().dropna()
ma60 = float(ma60_vals.iloc[-1]) if len(ma60_vals) > 0 else None

cur = float(closes.iloc[-1])
prev = float(closes.iloc[-2])

ema12 = closes.ewm(span=12).mean(); ema26 = closes.ewm(span=26).mean()
macd = ema12 - ema26; sig = macd.ewm(span=9).mean()
hist = macd - sig
macd_val = float(macd.iloc[-1]); sig_val = float(sig.iloc[-1]); hist_val = float(hist.iloc[-1])

n = 9
ll = lows.rolling(n).min(); hh = highs.rolling(n).max()
rsv = (closes - ll) / (hh - ll) * 100
K = rsv.ewm(com=2).mean(); D = K.ewm(com=2).mean()
J = K * 3 - D * 2
k_cur = float(K.iloc[-1]); d_cur = float(D.iloc[-1]); j_cur = float(J.iloc[-1])
k_prev = float(K.iloc[-2]); d_prev = float(D.iloc[-2])
k_cross_up = k_prev < d_prev and k_cur > d_cur
k_cross_down = k_prev > d_prev and k_cur < d_cur

ma_score = 2 if ma5 > ma20 else 1 if ma5 > ma10 else 0
macd_score = 2 if macd_val > sig_val else 0
kdj_score = 2 if k_cross_up else 1 if k_cur > d_cur else 0
rsi_score = 2 if rsi_cur < 40 else 1 if rsi_cur < 65 else 0
total = ma_score + macd_score + kdj_score + rsi_score

if ma5 > ma20 and macd_val > sig_val and rsi_cur < 65:
    phase = "BULL TREND"
elif ma5 < ma20 and macd_val < sig_val and rsi_cur > 65:
    phase = "BEAR TREND"
else:
    phase = "CONSOLIDATION"

result = {
    "TWII": round(cur),
    "daily_chg_pct": round((cur-prev)/prev*100, 2),
    "RSI": round(rsi_cur, 1),
    "RSI_prev": round(rsi_prev, 1),
    "MA5": round(ma5, 0),
    "MA10": round(ma10, 0),
    "MA20": round(ma20, 0),
    "MA60": round(ma60, 0) if ma60 else None,
    "MA_state": "bullish" if ma5 > ma20 else "neutral" if ma5 > ma10 else "bearish",
    "MACD": round(macd_val, 2),
    "MACD_signal": round(sig_val, 2),
    "MACD_hist": round(hist_val, 2),
    "MACD_state": "bullish" if macd_val > sig_val else "bearish",
    "KDJ_K": round(k_cur, 1),
    "KDJ_D": round(d_cur, 1),
    "KDJ_J": round(j_cur, 1),
    "KDJ_cross": "golden" if k_cross_up else "dead" if k_cross_down else "flat",
    "ma_score": ma_score,
    "macd_score": macd_score,
    "kdj_score": kdj_score,
    "rsi_score": rsi_score,
    "total_score": total,
    "phase": phase,
    "scan_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
}

path = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\stores\short_term\twii_trinity.json"
with open(path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

ma60_disp = f"{ma60:,.0f}" if ma60 else "N/A"

out = f"""======================================================
         TWII TRINITY ANALYSIS
======================================================
TWII: {cur:,.0f}  ({((cur-prev)/prev*100):+.2f}% today)

[MA SYSTEM]
  MA5={ma5:,.0f}  MA10={ma10:,.0f}  MA20={ma20:,.0f}  MA60={ma60_disp}
  State: {phase}
  Score: {ma_score}/2

[MACD SYSTEM]
  MACD={macd_val:.2f}  Signal={sig_val:.2f}  Hist={hist_val:.2f}
  State: {'BULLISH' if macd_val > sig_val else 'BEARISH'}
  Score: {macd_score}/2

[KDJ SYSTEM]
  K={k_cur:.1f}  D={d_cur:.1f}  J={j_cur:.1f}
  Cross: {'GOLDEN CROSS' if k_cross_up else 'DEAD CROSS' if k_cross_down else 'FLAT'}
  Score: {kdj_score}/2

[RSI]
  RSI(14)={rsi_cur:.1f}  (prev={rsi_prev:.1f})
  State: {'OVERBOUGHT' if rsi_cur > 70 else 'OVERSOLD' if rsi_cur < 40 else 'NEUTRAL'}
  Score: {rsi_score}/2

======================================================
[TRINITY SCORE] {total}/8 = {phase}
  MA:{ma_score}  MACD:{macd_score}  KDJ:{kdj_score}  RSI:{rsi_score}
======================================================"""
print(out)