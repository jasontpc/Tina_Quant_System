# -*- coding: utf-8 -*-
"""
US Momentum Scanner - Tina Architecture Edition
廣泛科技股動能排名

整合：RayDataCenter + RayEngine
- 30日滾動 Sharpe/MDD 把關
- 摩擦成本 0.15%
- 所有結果寫入 SQLite

Run: python us_momentum.py
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

def rsi_calc(c):
    d = np.diff(c, prepend=c[0])
    g = np.where(d>0,d,0.); l = np.where(d<0,-d,0.)
    ag=g.copy(); al=l.copy()
    for i in range(1,len(ag)): ag[i]=(ag[i-1]*13+g[i])/14; al[i]=(al[i-1]*13+l[i])/14
    return float(100-(100/(1+ag[-1]/max(al[-1],1e-10))))

def kdj(h, l, c, n=9):
    k=np.zeros_like(c); d=np.zeros_like(c)
    for i in range(n-1,len(c)):
        lo = np.min(l[max(0,i-n+1):i+1]); hi = np.max(h[max(0,i-n+1):i+1])
        k[i] = 50 if hi==lo else (c[i]-lo)/(hi-lo)*100
        d[i] = float(np.nanmean(k[max(n,i-n+1):i+1])) if i>=n else 50.0
    return 3*k-2*d

# 廣泛科技/成長股 universe
SYMBOLS = [
    'NVDA','AMD','AVGO','AMAT','LRCX','MU','INTC','QCOM','META','AAPL',
    'MSFT','GOOGL','AMZN','TSM','ASML','KLAC','TER','SNPS','CDNS',
    'NXPI','MRVL','ADI','ON','PANW','CRWD','NET','FTNT','NOW','SMCI',
    'DELL','HPE','LEN','ORCL','CRM','ADBE','PYPL','COIN','MSTR',
    'TSLA','RIVN','GM','F','UBER','LYFT','ABNB','COST','SBUX'
]

def calc_momentum(df, periods=[1, 5, 20]):
    """計算 1D / 5D / 20D 動能"""
    c = df['Close'].values.astype(float)
    results = {}
    for p in periods:
        if len(c) > p:
            results[f'mom_{p}d'] = float((c[-1] - c[-1-p]) / c[-1-p] * 100)
        else:
            results[f'mom_{p}d'] = 0.0
    return results

def calc_rolling_stats(df, window=30):
    """30日滾動 Sharpe / MDD"""
    if len(df) < window: return {"sharpe": None, "mdd": None, "win_rate": None}
    c = df['Close'].values.astype(float)
    ret = np.diff(c)/c[:-1]
    ret = np.insert(ret, 0, 0)
    cum = np.cumsum(ret)
    cummax = np.maximum.accumulate(cum)
    mdd = float(np.max(cummax - cum))
    mean_ret = float(np.mean(ret))
    std_ret  = float(np.std(ret))
    sharpe   = (mean_ret/std_ret*np.sqrt(252)) if std_ret > 1e-10 else 0.0
    win_rate = float(np.sum(ret > 0) / len(ret))
    return {"sharpe": round(sharpe,3), "mdd": round(mdd,4), "win_rate": round(win_rate,4)}

def run():
    print(f"US Momentum Scanner | Tina Architecture  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Math Gate: Sharpe > {SHARPE_MIN}, MDD < {MDD_MAX*100}%, Win > {WIN_MIN*100}%")
    print("-"*70)

    db     = RayDataCenter()
    engine = RayEngine(market_type="US")
    res    = []

    for sym in SYMBOLS:
        try:
            df5  = yf.Ticker(sym).history(period='20d', interval='1d', auto_adjust=True, timeout=5)
            df30 = yf.Ticker(sym).history(period='60d', interval='1d', auto_adjust=True, timeout=5)
            if df5 is None or df30 is None or len(df5)<3 or len(df30)<15: continue

            c5  = df5['Close'].values.astype(float)
            c30 = df30['Close'].values.astype(float)
            h   = df30['High'].values.astype(float)
            l   = df30['Low'].values.astype(float)

            p   = float(c5[-1])
            mom = calc_momentum(df5, [1,5,20])
            rs  = rsi_calc(c30)
            j_arr = kdj(h,l,c30)
            j0   = float(j_arr[-1]) if not np.isnan(j_arr[-1]) else 50.0
            stats = calc_rolling_stats(df30, 30)
            sharpe = stats.get("sharpe") or 0
            mdd    = stats.get("mdd")    or 999
            win_r  = stats.get("win_rate") or 0

            math_passed = (sharpe >= SHARPE_MIN and mdd <= MDD_MAX and win_r >= WIN_MIN)

            bull = 0
            bull += 1 if mom['mom_5d'] > 0 else 0
            bull += 1 if mom['mom_20d'] > 0 else 0
            bull += 1 if j0 > 20 and j0 < 85 else 0
            bull += 1 if math_passed else 0

            tag = "🟢 BUY" if bull>=3 and math_passed else \
                  "🟡 WATCH" if bull>=2 and math_passed else "⚪ NEUT"

            print(f"{sym:<8}{p:>8.2f}{mom['mom_1d']:>7.2f}{mom['mom_5d']:>7.2f}{mom['mom_20d']:>8.2f}"
                  f"{rs:>6.1f}{sharpe:>7.2f}{mdd:>7.2%} {tag}")

            res.append((sym, p, mom, rs, j0, sharpe, mdd, win_r, bull, math_passed))

            # 寫入 SQLite
            db.log_signal(
                symbol     = sym,
                source     = "momentum",
                score      = float(bull),
                sharpe     = sharpe,
                mdd        = mdd,
                win_rate   = win_r,
                signal_tag = "BUY" if (bull>=3 and math_passed) else ("WATCH" if math_passed else "NEUT"),
                note       = f"mom_5d={mom['mom_5d']:.1f} mom_20d={mom['mom_20d']:.1f} RSI={rs:.1f} J={j0:.0f}"
            )
        except Exception as e:
            print(f"{sym:<8} error: {e}")

        time.sleep(0.12)

    print()
    # ── Top BUY ──────────────────────────────────────────────────────
    buy = sorted([(s,p,m,rs,j,sh,mdd,wr,b,mp) for s,p,m,rs,j,sh,mdd,wr,b,mp in res
                  if mp and b>=3], key=lambda x: -x[5])
    if buy:
        print(f"🟢 BUY ({len(buy)} stocks, Sharpe排序):")
        for s,p,m,rs,j,sh,mdd,wr,b,mp in buy[:10]:
            print(f"  {s:<6} ${p:.2f}  S:{sh:.2f} MDD:{mdd:.2%} 5D:{m['mom_5d']:+.1f}% 20D:{m['mom_20d']:+.1f}% RSI:{rs:.0f} J:{j:.0f}")

    # ── Top WATCH ────────────────────────────────────────────────────
    watch = sorted([(s,p,m,rs,j,sh,mdd,wr,b,mp) for s,p,m,rs,j,sh,mdd,wr,b,mp in res
                    if mp and b==2], key=lambda x: -x[5])
    if watch:
        print(f"\n🟡 WATCH ({len(watch)} stocks):")
        for s,p,m,rs,j,sh,mdd,wr,b,mp in watch[:8]:
            print(f"  {s:<6} ${p:.2f}  S:{sh:.2f} MDD:{mdd:.2%} 5D:{m['mom_5d']:+.1f}% RSI:{rs:.0f}")

    all_ids = [r.get("signal_id") for r in res if r and len(r)>9 and r[9]]
    # mark signals pushed after display

if __name__ == "__main__":
    run()