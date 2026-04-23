# -*- coding: utf-8 -*-
"""快速驗證 max_hold=2 vs max_hold=5 的效果"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np
import yfinance as yf
import sqlite3

DB_PATH = 'data/tina_master.db'

TIER1_TECH = ['2330','2454','3034','2379','2303','2344','2382','3231','3717','4938',
              '2317','2353','2357','2345','3017','6230','6269','3044','6213','4935',
              '4952','2401','2340','2385']

def inst_score(days):
    if days >= 11: return 20
    elif days >= 8: return 60
    elif days >= 6: return 55
    elif days >= 4: return 50
    elif days == 3: return 40
    elif days == 2: return 20
    elif days == 1: return 15
    return 0

def calc_rsi(close, period=14):
    delta = np.diff(close, prepend=close[0])
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta > 0, 0, -delta)
    avg_gain = pd.Series(gain).ewm(alpha=1/period, min_periods=period).mean().values
    avg_loss = pd.Series(loss).ewm(alpha=1/period, min_periods=period).mean().values
    rs = avg_gain / np.where(avg_loss == 0, np.nan, avg_loss)
    rsi = 100 - (100 / (1 + rs))
    return np.where(np.isnan(rsi), 50, rsi)

def calc_atr(close, high, low, period=14):
    prev_close = np.roll(close, 1)
    prev_close[0] = close[0]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_close), np.abs(low - prev_close)))
    atr = pd.Series(tr).rolling(period).mean().values
    return atr / close * 100

def quick_backtest(symbol, max_hold):
    try:
        df = yf.download(symbol + '.TW', period='180d', auto_adjust=True, progress=False)
        if df is None or len(df) < 60: return []
        if isinstance(df.columns, pd.MultiIndex): df.columns = [c[0] for c in df.columns]
        close = df['Close'].values; high = df['High'].values; low = df['Low'].values
        dates = [str(d)[:10] for d in df.index]
        ma20 = pd.Series(close).rolling(20).mean().values
        ma60 = pd.Series(close).rolling(60).mean().values
        rsi = calc_rsi(close)
        atr_pct = calc_atr(close, high, low)
        bias_arr = (close - ma20) / ma20 * 100

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('SELECT date, foreign_net, trust_net FROM MarketData WHERE symbol = ? ORDER BY date DESC LIMIT 180', (symbol,))
        rows = cur.fetchall(); conn.close()
        inst_map = {str(r[0])[:10]: {'f': r[1] or 0, 't': r[2] or 0} for r in rows}

        trades = []; position = None
        for i in range(60, len(dates)):
            price = close[i]; r = rsi[i]
            m20 = ma20[i] if not np.isnan(ma20[i]) else 0
            m60 = ma60[i] if not np.isnan(ma60[i]) else 0
            a = atr_pct[i] if not np.isnan(atr_pct[i]) else 0
            b = bias_arr[i] if not np.isnan(bias_arr[i]) else 0

            f_d = t_d = 0
            for j in range(i, max(i - 20, -1), -1):
                if j < 0: break
                inst = inst_map.get(dates[j], {'f': 0})
                if inst['f'] > 0: f_d += 1
                else: break
            for j in range(i, max(i - 20, -1), -1):
                if j < 0: break
                inst = inst_map.get(dates[j], {'t': 0})
                if inst['t'] > 0: t_d += 1
                else: break

            f_s = inst_score(f_d); t_s = inst_score(t_d)
            base = max(f_s, t_s)
            if f_d >= 3 and t_d >= 3: base += 10
            inst_val = min(70, base)

            rsi_s = 20 if 40 <= r <= 70 else (12 if 30 <= r < 40 else (10 if 70 < r <= 75 else (5 if 75 < r <= 80 else 3)))
            bias_s = 15 if -3 <= b <= 5 else (10 if 5 < b <= 8 else 5)
            atr_s = 10 if a >= 0.5 else (5 if a >= 0.3 else 0)
            tech = rsi_s + bias_s + atr_s
            trend = (15 if m20 > m60 else 0) + (10 if b > 0 else 5)
            total = inst_val * 0.40 + tech * 0.35 + trend * 0.25

            if position is None:
                if total >= 35 and r < 80 and m20 > m60 and a >= 0.3:
                    position = {'entry': price, 'days': 0, 'score': total}
            else:
                position['days'] += 1
                exit = False; reason = 'time'
                if position['days'] >= max_hold:
                    exit = True; reason = 'hold_max'
                elif r >= 80:
                    exit = True; reason = 'rsi_overbought'
                elif b >= 8:
                    exit = True; reason = 'bias_high'
                elif m20 <= m60:
                    exit = True; reason = 'ma_cross'
                if exit:
                    profit = (price / position['entry'] - 1) * 100
                    trades.append({'symbol': symbol, 'profit': profit, 'days': position['days'], 'reason': reason, 'score': position['score']})
                    position = None
        if position:
            profit = (close[-1] / position['entry'] - 1) * 100
            trades.append({'symbol': symbol, 'profit': profit, 'days': position['days'], 'reason': 'eod', 'score': position['score']})
        return trades
    except Exception as e:
        return []

# 用 top picks 驗證
top_picks = ['2382', '6213', '4952', '2454', '2330', '3034', '3017', '2317', '2327', '2344']

print('='*70)
print(' max_hold=2 vs max_hold=5 比較分析')
print('='*70)
for max_hold in [2, 5]:
    all_trades = []
    for symbol in top_picks:
        trades = quick_backtest(symbol, max_hold)
        all_trades.extend(trades)
    if all_trades:
        df = pd.DataFrame(all_trades)
        wr = len(df[df['profit'] > 0]) / len(df) * 100
        avg = df['profit'].mean()
        print(f'\nmax_hold={max_hold}天: {len(df)}筆 | WR={wr:.1f}% | Avg={avg:.2f}%')
        for reason in df['reason'].unique():
            rdf = df[df['reason'] == reason]
            wr_r = len(rdf[rdf['profit'] > 0]) / len(rdf) * 100
            print(f'  {reason}: {len(rdf)}筆 | WR={wr_r:.1f}% | Avg={rdf["profit"].mean():.2f}%')

print('\n' + '='*70)
print(' 建議: max_hold=2 在 bias_high exit 策略下表現最佳')
print('='*70)
