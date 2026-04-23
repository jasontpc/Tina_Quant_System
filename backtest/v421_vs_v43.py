# -*- coding: utf-8 -*-
"""
v4.21 vs v4.3 完整回測對比
180天回測
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import warnings
warnings.filterwarnings('ignore')
import yfinance as yf
yf.suppress_errors=True
import numpy as np
import sqlite3
import pandas as pd
import time

DB = 'skills/stock-analyzer/scripts/tina_master.db'

STOCKS = ['2330','2454','3034','2002','1301','1326','1216','2610','2891','2881',
    '5871','6505','3665','3017','2345','6230','3583','2360','6139','3189',
    '2308','2474','3033','3338','3702','4938','5880','6770','8046','8454',
    '8478','8499','3711','4961','2379','2451','2201','2207','2231','2352',
    '2353','2354','2356','2371','2373','2376','2383','2385','2392','2393',
    '2401','2402','2404','2412','2420','2423','2425','2426','2427','2428',
    '2429','2430','2431','2432','2433','2434','2436','2438','2439','4952',
    '6415','6183','2618','2630','2892','2884','2886','2887','2890']

BLACKLIST = ['2615','1590','2382','2317','2303','3008','3231','2408','3443','6446','6669','2597']
STOCKS = [s for s in STOCKS if s not in BLACKLIST][:100]

def load_inst():
    inst = {}
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('SELECT symbol, date, foreign_net, trust_net FROM MarketData')
    for sym, date, f, t in cur.fetchall():
        if sym not in inst: inst[sym] = {}
        inst[sym][date] = (f or 0, t or 0)
    conn.close()
    return inst

def rsi(p):
    d = np.diff(p)
    g = np.where(d > 0, d, 0)
    l = np.where(d > 0, 0, -d)
    ag = np.mean(g[-14:])
    al = np.mean(l[-14:])
    return 100 - (100 / (1 + ag / al)) if al != 0 else 50

def calc_atr(h, i):
    high = list(h['High'].iloc[max(0,i-14):i+1])
    low = list(h['Low'].iloc[max(0,i-14):i+1])
    close = list(h['Close'].iloc[max(0,i-14):i+1])
    tr = [max(high[j]-low[j], abs(high[j]-close[j-1]), abs(low[j]-close[j-1])) for j in range(1, len(high))]
    return np.mean(tr[-14:]) if len(tr) >= 14 else 30

def kdj(h, i, n=9):
    if i < n: return 50, 50, 50
    low_n = h['Low'].iloc[i-n:i+1].min()
    high_n = h['High'].iloc[i-n:i+1].max()
    close = h['Close'].iloc[i]
    if high_n == low_n: return 50, 50, 50
    rsv = (close - low_n) / (high_n - low_n) * 100
    k = 2/3 * 50 + 1/3 * rsv
    d = 2/3 * 50 + 1/3 * k
    j = 3 * k - 2 * d
    return k, d, j

def macd(p):
    if len(p) < 26: return 0, 0
    ema12 = pd.Series(list(p)).ewm(span=12).mean().iloc[-1]
    ema26 = pd.Series(list(p)).ewm(span=26).mean().iloc[-1]
    macd_val = ema12 - ema26
    signal = pd.Series([macd_val]).ewm(span=9).mean().iloc[-1]
    return macd_val if not pd.isna(macd_val) else 0, signal if not pd.isna(signal) else 0

def backtest_v421(inst_map, days=180):
    """v4.21: MA Trend + Inst Any"""
    end = '2026-04-23'
    start = (pd.to_datetime(end) - pd.Timedelta(days=days)).strftime('%Y-%m-%d')
    
    all_trades = []
    for code in STOCKS:
        try:
            h = yf.Ticker(code+'.TW').history(start=start, end=end)
            if len(h) < 60: continue
            cl = list(h['Close'])
            vol = list(h['Volume'])
            
            for i in range(30, len(cl)-6):
                rs = rsi(cl[:i+1])
                ma20 = np.mean(cl[i-19:i+1])
                ma60 = np.mean(cl[i-59:i+1])
                atr = calc_atr(h, i)
                atr_pct = atr / cl[i] * 100 if cl[i] > 0 else 0
                k, d, j = kdj(h, i)
                macd_val, signal_val = macd(cl[:i+1])
                date_str = str(h.index[i])[:10]
                
                # v4.21 條件
                if rs >= 70: continue
                if cl[i] < ma20: continue
                if ma20 <= ma60: continue
                if atr_pct < 0.5: continue
                
                # 法人 任一買超
                if code in inst_map:
                    f_days = t_days = 0
                    for dd in range(1, 4):
                        dt = (pd.to_datetime(date_str) - pd.Timedelta(days=dd)).strftime('%Y-%m-%d')
                        if dt in inst_map[code]:
                            if inst_map[code][dt][0] > 0: f_days += 1
                            if inst_map[code][dt][1] > 0: t_days += 1
                    if max(f_days, t_days) < 1: continue
                
                entry = h['Open'].iloc[i+1] if i+1 < len(h) else cl[i]
                exit_p = cl[min(i+6, len(cl)-1)]
                ret = (exit_p / entry - 1) * 100 - 0.45
                all_trades.append({'ret': ret, 'code': code, 'rsi': rs, 'atr': atr_pct})
        except:
            pass
        time.sleep(0.05)
    return all_trades

def backtest_v43(inst_map, days=180):
    """v4.3: MA Trend + Inst Sync"""
    end = '2026-04-23'
    start = (pd.to_datetime(end) - pd.Timedelta(days=days)).strftime('%Y-%m-%d')
    
    all_trades = []
    for code in STOCKS:
        try:
            h = yf.Ticker(code+'.TW').history(start=start, end=end)
            if len(h) < 60: continue
            cl = list(h['Close'])
            vol = list(h['Volume'])
            
            for i in range(30, len(cl)-6):
                rs = rsi(cl[:i+1])
                ma20 = np.mean(cl[i-19:i+1])
                ma60 = np.mean(cl[i-59:i+1])
                atr = calc_atr(h, i)
                atr_pct = atr / cl[i] * 100 if cl[i] > 0 else 0
                k, d, j = kdj(h, i)
                macd_val, signal_val = macd(cl[:i+1])
                date_str = str(h.index[i])[:10]
                
                # v4.3 條件
                if not (40 <= rs <= 70): continue
                if cl[i] < ma20: continue
                if ma20 <= ma60: continue
                if atr_pct < 0.3: continue
                
                # 法人 同步買超
                if code in inst_map:
                    f_days = t_days = 0
                    for dd in range(1, 4):
                        dt = (pd.to_datetime(date_str) - pd.Timedelta(days=dd)).strftime('%Y-%m-%d')
                        if dt in inst_map[code]:
                            if inst_map[code][dt][0] > 0: f_days += 1
                            if inst_map[code][dt][1] > 0: t_days += 1
                    # Inst Sync: 兩者都要有買超
                    if not (f_days >= 1 and t_days >= 1): continue
                
                entry = h['Open'].iloc[i+1] if i+1 < len(h) else cl[i]
                exit_p = cl[min(i+6, len(cl)-1)]
                ret = (exit_p / entry - 1) * 100 - 0.45
                all_trades.append({'ret': ret, 'code': code, 'rsi': rs, 'atr': atr_pct})
        except:
            pass
        time.sleep(0.05)
    return all_trades

def analyze(trades):
    if not trades: return None
    wins = [t for t in trades if t['ret'] > 0]
    losses = [t for t in trades if t['ret'] <= 0]
    gross_profit = sum([t['ret'] for t in wins])
    gross_loss = abs(sum([t['ret'] for t in losses]))
    pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    mdd = min([t['ret'] for t in trades]) if trades else 0
    avg = np.mean([t['ret'] for t in trades]) if trades else 0
    wr = len(wins)/len(trades)*100
    avg_win = np.mean([t['ret'] for t in wins]) if wins else 0
    avg_loss = abs(np.mean([t['ret'] for t in losses])) if losses else 0
    expectancy = (wr/100 * avg_win) - ((100-wr)/100 * avg_loss)
    return {
        'total': len(trades), 'wins': len(wins), 'losses': len(losses),
        'wr': wr, 'avg': np.mean([t['ret'] for t in trades]),
        'pf': pf, 'mdd': mdd, 'expectancy': expectancy
    }

print('='*70)
print(' v4.21 vs v4.3 完整回測對比')
print(' 股票池: 台股市值前100大')
print(' 回測區間: 最近180天')
print('='*70)

inst_map = load_inst()

print('\n[ 回測 v4.21... ]')
t1 = backtest_v421(inst_map)
r1 = analyze(t1)

print('\n[ 回測 v4.3... ]')
t2 = backtest_v43(inst_map)
r2 = analyze(t2)

print('\n'+'='*70)
print(' 回測結果對比')
print('='*70)
print()
print('         | v4.21        | v4.3')
print('-'*40)
print(' 勝利    | %d           | %d' % (r1['wins'], r2['wins']) if r1 and r2 else '')
print(' 失敗    | %d           | %d' % (r1['losses'], r2['losses']) if r1 and r2 else '')
print(' 勝率    | %.1f%%        | %.1f%%' % (r1['wr'], r2['wr']) if r1 and r2 else '')
print(' 信號數  | %d           | %d' % (r1['total'], r2['total']) if r1 and r2 else '')
print(' 平均報酬| %+.2f%%       | %+.2f%%' % (r1['avg'], r2['avg']) if r1 and r2 else '')
print(' 期望值  | %.2f          | %.2f' % (r1['expectancy'], r2['expectancy']) if r1 and r2 else '')
print(' PF      | %.2f          | %.2f' % (r1['pf'], r2['pf']) if r1 and r2 else '')
print(' MDD     | %+.2f%%       | %+.2f%%' % (r1['mdd'], r2['mdd']) if r1 and r2 else '')
print('-'*40)
print()
print('='*70)
print(' 進場條件差異')
print('='*70)
print('         | v4.21              | v4.3')
print('-'*40)
print(' RSI     | <70                | 40-70')
print(' ATR     | >=0.5%             | >=0.3%')
print(' MA      | MA20>MA60          | MA20>MA60')
print(' 法人    | 任一買超           | 同步買超')
print('='*70)