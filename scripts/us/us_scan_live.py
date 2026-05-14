# -*- coding: utf-8 -*-
"""
US Live Scan - Tina Architecture Edition
即時技術掃描：MA20/MA60 + RSI + MACD Hist + KDJ J

整合：RayDataCenter + 摩擦成本 + Sharpe/MDD 把關
- 只對 math_passed=True 的標的給 BUY 標籤
- 所有結果寫入 SQLite

Run: python us_scan_live.py
"""

import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import yfinance as yf
import numpy as np
from datetime import datetime
import warnings; warnings.filterwarnings("ignore")

from ray_data_center import RayDataCenter
from ray_engine import RayEngine

SHARPE_MIN = 1.5
MDD_MAX    = 0.15
WIN_MIN    = 0.45
COST_US    = 0.0015  # 0.15%

def ema(c, n):
    e = np.zeros(len(c)); e[0]=c[0]; a=2/(n+1)
    for i in range(1,len(c)): e[i]=c[i]*a+e[i-1]*(1-a)
    return e

def kdj(h, l, c, n=9):
    k=np.zeros_like(c); d=np.zeros_like(c)
    for i in range(n-1,len(c)):
        lo = np.min(l[max(0,i-n+1):i+1]); hi = np.max(h[max(0,i-n+1):i+1])
        k[i] = 50 if hi==lo else (c[i]-lo)/(hi-lo)*100
        d[i] = float(np.nanmean(k[max(n,i-n+1):i+1])) if i>=n else 50.0
    j = 3*k-2*d
    return j

def rsi_calc(c):
    d = np.diff(c, prepend=c[0])
    g = np.where(d>0,d,0.); l = np.where(d<0,-d,0.)
    ag=g.copy(); al=l.copy()
    for i in range(1,len(ag)): ag[i]=(ag[i-1]*13+g[i])/14; al[i]=(al[i-1]*13+l[i])/14
    return float(100-(100/(1+ag[-1]/max(al[-1],1e-10))))

def calc_rolling_stats(df, window=30):
    if len(df) < window: return {"sharpe": None, "mdd": None, "win_rate": None}
    c = df['Close'].values.astype(float)
    ret = np.diff(c)/c[:-1]; ret = np.insert(ret,0,0)
    cum = np.cumsum(ret); cummax = np.maximum.accumulate(cum)
    mdd = float(np.max(cummax - cum))
    mean_ret = float(np.mean(ret)); std_ret = float(np.std(ret))
    sharpe = (mean_ret/std_ret*np.sqrt(252)) if std_ret>1e-10 else 0.0
    win_rate = float(np.sum(ret>0)/len(ret))
    return {"sharpe": round(sharpe,3), "mdd": round(mdd,4), "win_rate": round(win_rate,4)}

SYMS = [
    "NVDA","AMD","AVGO","AMAT","LRCX","MU","INTC","QCOM","META","AAPL",
    "MSFT","GOOGL","AMZN","ASML","KLAC","TER","SNPS","CDNS","NXPI","MRVL","ADI","ON","QQQ","PANW","CRWD","NET","FTNT","NOW","SMCI","DELL"
]

def run():
    print(f"US Tech Live Scan | Tina Architecture  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Math Gate: Sharpe > {SHARPE_MIN}, MDD < {MDD_MAX*100}%, Win > {WIN_MIN*100}%")
    print(f"{'Ticker':<8}{'Price':>9}{'MA20':>9}{'MA60':>9}{'RSI':>7}{'MACD':>9}{'J':>8} Sharpe MDD     Signal")
    print("-"*90)

    db     = RayDataCenter()
    engine = RayEngine(market_type="US")
    res    = []

    for sym in SYMS:
        try:
            df6 = yf.Ticker(sym).history(period="6mo", interval="1d", auto_adjust=True, timeout=10)
            if df6 is None or len(df6) < 120: continue

            c = df6['Close'].values.astype(float)
            h = df6['High'].values.astype(float)
            l = df6['Low'].values.astype(float)

            m20 = ema(c,20); m60 = ema(c,60)
            ef = ema(c,12); es = ema(c,26)
            mac = ef-es; sigv = ema(mac,9); mh = mac-sigv
            j_arr = kdj(h,l,c)
            j0 = float(j_arr[-1]) if not np.isnan(j_arr[-1]) else 50.0
            j1 = float(j_arr[-2]) if len(j_arr)>=2 else j0
            rs = rsi_calc(c)
            p  = float(c[-1])

            if np.isnan(m20[-1]) or np.isnan(m60[-1]): continue

            stats = calc_rolling_stats(df6, 30)
            sharpe = stats.get("sharpe") or 0
            mdd    = stats.get("mdd")    or 999
            win_r  = stats.get("win_rate") or 0
            math_passed = (sharpe >= SHARPE_MIN and mdd <= MDD_MAX and win_r >= WIN_MIN)

            bull = 0
            if p > float(m20[-1]): bull += 1
            if p > float(m60[-1]): bull += 1
            if float(mh[-1]) > 0: bull += 1
            if j0 > j1 and 10 < j0 < 85: bull += 1

            tag = "🟢" if (bull>=3 and math_passed) else "🟡" if (bull>=2 and math_passed) else "⚪"

            print(f"{sym:<8}{p:>9.2f}{float(m20[-1]):>9.2f}{float(m60[-1]):>9.2f}"
                  f"{rs:>7.1f}{float(mh[-1]):>9.3f}{j0:>8.1f}"
                  f"{sharpe:>7.3f}{mdd:>8.2%} {tag}")

            res.append((sym, p, float(m20[-1]), float(m60[-1]), rs,
                        float(mh[-1]), j0, sharpe, mdd, win_r, bull, math_passed))

            db.log_signal(
                symbol=sym, source="live_scan", score=float(bull),
                sharpe=sharpe, mdd=mdd, win_rate=win_r,
                signal_tag="BUY" if (bull>=3 and math_passed) else ("WATCH" if math_passed else "NEUT"),
                note=f"MA20={float(m20[-1]):.2f} MACD={float(mh[-1]):.3f} J={j0:.0f}"
            )
        except Exception as e:
            print(f"{sym:<8} error: {e}")

        time.sleep(0.15)

    print()
    buy = sorted([x for x in res if x[11] and x[10]>=3], key=lambda x: -x[7])
    if buy:
        print(f"🟢 BUY ({len(buy)}):")
        for s,p,m20,m60,rs,mh,j0,sh,mdd,wr,b,mp in buy[:10]:
            print(f"  {s:<6} ${p:.2f} S={sh:.2f} MDD={mdd:.2%} RSI={rs:.0f} J={j0:.0f} MACD={mh:.3f}")

    watch = sorted([x for x in res if x[11] and x[10]==2], key=lambda x: -x[7])
    if watch:
        print(f"\n🟡 WATCH ({len(watch)}):")
        for s,p,m20,m60,rs,mh,j0,sh,mdd,wr,b,mp in watch[:8]:
            print(f"  {s:<6} ${p:.2f} S={sh:.2f} RSI={rs:.0f}")

if __name__ == "__main__":
    run()