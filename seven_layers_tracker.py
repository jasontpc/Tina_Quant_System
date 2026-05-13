"""
七層蛋糕個股追蹤系統
AI 產業鏈七層股：每日技術掃描 + 動能追蹤
"""

import sys, sqlite3, json, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import yfinance as yf
import numpy as np
from datetime import datetime

DB = 'ray_wisdom.db'

layers = [
    ("L1-能源", ["CEG","BE","VST"]),
    ("L2-半導體", ["NVDA","INTC","AMD"]),
    ("L3-記憶體", ["MU","SNDK","WDC","STX"]),
    ("L4-網路", ["AVGO","MRVL","ANET"]),
    ("L5-系統散熱", ["VRT","SMCI"]),
    ("L6-模型平台", ["MSFT","META","GOOGL"]),
    ("L7-代理應用", ["PLTR","CRWD","NOW"]),
]

def ema(c, n):
    e = np.zeros(len(c)); e[0] = c[0]; a = 2/(n+1)
    for i in range(1, len(c)): e[i] = c[i]*a + e[i-1]*(1-a)
    return e

def kdj(h, l, c, n=9):
    k = np.zeros_like(c); d = np.zeros_like(c)
    for i in range(n-1, len(c)):
        lo = np.min(l[max(0,i-n+1):i+1]); hi = np.max(h[max(0,i-n+1):i+1])
        k[i] = 50 if hi==lo else (c[i]-lo)/(hi-lo)*100
        d[i] = float(np.nanmean(k[max(n,i-n+1):i+1])) if i>=n else 50.0
    return 3*k-2*d

def rsi_calc(c):
    d = np.diff(c, prepend=c[0])
    g = np.where(d>0, d, 0.); l = np.where(d<0, -d, 0.)
    ag = g.copy(); al = l.copy()
    for i in range(1, len(ag)): ag[i] = (ag[i-1]*13+g[i])/14; al[i] = (al[i-1]*13+l[i])/14
    return float(100-(100/(1+ag[-1]/max(al[-1], 1e-10))))

def calc_stats(df, w=30):
    c = df['Close'].values.astype(float)
    ret = np.diff(c)/c[:-1]; ret = np.insert(ret, 0, 0)
    cum = np.cumsum(ret); cummax = np.maximum.accumulate(cum)
    mdd = float(np.max(cummax - cum))
    mean_ret = float(np.mean(ret)); std_ret = float(np.std(ret))
    sharpe = (mean_ret/std_ret*np.sqrt(252)) if std_ret>1e-10 else 0.0
    win_rate = float(np.sum(ret>0)/len(ret))
    return {'sharpe': round(sharpe,3), 'mdd': round(mdd,4), 'win_rate': round(win_rate,4)}

def save_to_db(rows):
    """寫入 signals_log"""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    for r in rows:
        try:
            c.execute('''INSERT INTO signals_log
                (symbol, source, score, sharpe_30d, mdd_30d, win_rate_30d, signal_tag, note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                (r['symbol'], 'seven_layers', r['score'], r['sharpe'], r['mdd'],
                 r['win_rate'], r['tag'], r['note']))
        except Exception as e:
            pass
    conn.commit()
    conn.close()

def run():
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"=== AI 七層蛋糕追蹤 {today} ===\n")
    all_rows = []

    for layer_name, syms in layers:
        print(f"### {layer_name}")
        for sym in syms:
            try:
                df = yf.Ticker(sym).history(period="6mo", interval="1d", auto_adjust=True, timeout=10)
                if df is None or len(df) < 60: continue
                c = df['Close'].values.astype(float)
                h = df['High'].values.astype(float)
                l = df['Low'].values.astype(float)
                m20 = ema(c,20); m60 = ema(c,60)
                ef = ema(c,12); es = ema(c,26)
                mac = ef-es; sig = ema(mac,9); mh = mac-sig
                j_arr = kdj(h,l,c)
                j0 = float(j_arr[-1]) if not np.isnan(j_arr[-1]) else 50.0
                j1 = float(j_arr[-2]) if len(j_arr)>=2 else j0
                rs = rsi_calc(c)
                p = float(c[-1])
                chg1 = (p/c[-2]-1)*100
                chg5 = (p/c[-6]-1)*100 if len(c)>=6 else 0
                chg20 = (p/c[-21]-1)*100 if len(c)>=21 else 0
                stats = calc_stats(df, 30)
                sh = stats['sharpe'] or 0; mdd_v = stats['mdd'] or 999; wr = stats['win_rate'] or 0
                bull = 0
                if p > float(m20[-1]): bull += 1
                if p > float(m60[-1]): bull += 1
                if float(mh[-1]) > 0: bull += 1
                if j0>j1 and 10<j0<85: bull += 1
                mp = (sh >= 1.5 and mdd_v <= 0.15 and wr >= 0.45)
                tag = "BUY" if (bull>=3 and mp) else ("WATCH" if mp else "NEUT")
                note = f"RSI={rs:.0f} MACD={float(mh[-1]):.2f} J={j0:.0f} 1D={chg1:+.1f}% 5D={chg5:+.1f}%"
                print(f"  {sym:<6} ${p:.2f} RSI={rs:.0f} MACD={float(mh[-1]):+.2f} J={j0:.0f} | {chg1:+.1f}% | {chg5:+.1f}% | {chg20:+.1f}% | S={sh:.2f} MDD={mdd_v:.0%} [{tag}]")
                all_rows.append({
                    'symbol': sym, 'layer': layer_name,
                    'price': round(p,2), 'rsi': round(rs,1),
                    'macd': round(float(mh[-1]),2), 'j': round(j0,1),
                    'chg1': round(chg1,2), 'chg5': round(chg5,2), 'chg20': round(chg20,2),
                    'sharpe': sh, 'mdd': mdd_v, 'win_rate': wr,
                    'score': bull, 'tag': tag, 'note': note
                })
            except Exception as e:
                print(f"  {sym:<6} error: {e}")
            time.sleep(0.15)
        print()

    save_to_db(all_rows)
    return all_rows

if __name__ == "__main__":
    run()
