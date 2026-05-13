import yfinance as yf
import numpy as np

df = yf.Ticker('VICR').history(period='6mo', interval='1d', auto_adjust=True, timeout=15)
c = df['Close'].values.astype(float)
h = df['High'].values.astype(float)
l = df['Low'].values.astype(float)

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

m20 = ema(c,20); m60 = ema(c,60)
ef = ema(c,12); es = ema(c,26)
mac = ef - es; sig = ema(mac,9); mh = mac - sig
j_arr = kdj(h, l, c)
j0 = float(j_arr[-1]); j1 = float(j_arr[-2]) if len(j_arr)>=2 else j0
rs = rsi_calc(c)
p = c[-1]; chg = (p/c[-2]-1)*100
stats = calc_stats(df, 30)
sh = stats['sharpe'] or 0; mdd = stats['mdd'] or 999; wr = stats['win_rate'] or 0
bull = 0
if p > float(m20[-1]): bull += 1
if p > float(m60[-1]): bull += 1
if float(mh[-1]) > 0: bull += 1
if j0 > j1 and 10 < j0 < 85: bull += 1
mp = (sh >= 1.5 and mdd <= 0.15 and wr >= 0.45)
tag = 'BUY' if (bull>=3 and mp) else ('WATCH' if mp else 'NEUT')

print(f'VICR  ${p:.2f}')
print(f'MA20={m20[-1]:.2f}  MA60={m60[-1]:.2f}  價差={p-float(m20[-1]):+.2f}/{p-float(m60[-1]):+.2f}')
print(f'RSI={rs:.1f}  MACD hist={mh[-1]:.3f}  KDJ J={j0:.1f}/{j1:.1f}')
print(f'Sharpe={sh}  MDD={mdd:.2%}  Win={wr:.2%}')
d5 = (p/c[-6]-1)*100 if len(c)>=6 else 0
d20 = (p/c[-21]-1)*100 if len(c)>=21 else 0
print(f'1D={chg:+.2f}%  5D={d5:+.2f}%  20D={d20:+.2f}%')
print(f'信號: {tag}  bull={bull}/4')
print()
print('--- 近10日K線 ---')
for i in range(-10, 0):
    row = df.iloc[i]
    d = df.index[i]
    date_str = d.strftime('%m/%d')
    print(f'{date_str}  O={row["Open"]:.2f}  H={row["High"]:.2f}  L={row["Low"]:.2f}  C={row["Close"]:.2f}  V={int(row["Volume"]):,}')
