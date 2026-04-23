# -*- coding: utf-8 -*-
"""
Nana v1.0 vs v1.1 回測 - 百分比報酬版本
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import sqlite3
import numpy as np
import pandas as pd
import json

DB_PATH = 'skills/stock-analyzer/scripts/tina_master.db'

def inst_score(days):
    if days >= 11: return 20
    elif days >= 6: return 60
    elif days >= 4: return 50
    elif days == 3: return 40
    elif days == 2: return 15
    elif days == 1: return 10
    return 0

def run_backtest(symbol, params, days=180):
    df = yf.download(symbol + '.TW', period=f'{days}d', auto_adjust=True, progress=False)
    if df is None or len(df) < 60:
        return []
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    
    close = df['Close'].values
    high = df['High'].values
    low = df['Low'].values
    dates = [str(d)[:10] for d in df.index]
    
    # RSI
    delta = np.diff(close, prepend=close[0])
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta > 0, 0, -delta)
    avg_gain = pd.Series(gain).rolling(14).mean().values
    avg_loss = pd.Series(loss).rolling(14).mean().values
    rs = avg_gain / np.where(avg_loss == 0, np.nan, avg_loss)
    rsi = 100 - (100 / (1 + rs))
    rsi = np.where(np.isnan(rsi), 50, rsi)
    
    # MA
    ma20 = pd.Series(close).rolling(20).mean().values
    ma60 = pd.Series(close).rolling(60).mean().values
    
    # ATR
    tr = np.maximum(high - low, np.maximum(np.abs(high - np.roll(close, 1)), np.abs(low - np.roll(close, 1))))
    atr = pd.Series(tr).rolling(14).mean().values
    atr_pct = atr / close * 100
    
    # 法人
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT date, foreign_net, trust_net FROM MarketData WHERE symbol = ? ORDER BY date DESC LIMIT ?', (symbol, days))
    rows = cur.fetchall()
    conn.close()
    inst_map = {str(r[0])[:10]: {'f': r[1] or 0, 't': r[2] or 0} for r in rows}
    
    rsi_min = params.get('rsi_min', 40)
    rsi_max = params.get('rsi_max', 75)
    atr_min = params.get('atr_min', 0.3)
    inst_min = params.get('inst_min', 10)
    entry_min = params.get('entry_min', 65)
    hold_days = params.get('hold_days', 7)
    
    trades = []
    position = None
    
    for i in range(60, len(dates)):
        price = close[i]
        r = rsi[i]
        m20 = ma20[i]
        m60 = ma60[i]
        a = atr_pct[i]
        b = (price - m20) / m20 * 100 if m20 else 0
        date = dates[i]
        
        # 法人
        f_c = t_c = 0
        for j in range(i, min(i+20, len(dates))):
            inst = inst_map.get(dates[j], {'f': 0, 't': 0})
            if inst['f'] > 0: f_c += 1
            else: break
        for j in range(i, min(i+20, len(dates))):
            inst = inst_map.get(dates[j], {'f': 0, 't': 0})
            if inst['t'] > 0: t_c += 1
            else: break
        
        if position is None:
            f_s = inst_score(f_c)
            t_s = inst_score(t_c)
            base = max(f_s, t_s)
            if f_c >= 3 and t_c >= 3: base += 10
            inst_total = min(70, base)
            
            rsi_s = 15 if 50 <= r <= 70 else (10 if 30 <= r < 50 else 5)
            bias_s = 15 if -2 <= b <= 3 else (10 if 3 < b <= 6 else 0)
            total = inst_total + rsi_s + bias_s
            
            if rsi_min <= r <= rsi_max and m20 > m60 and a >= atr_min and inst_total >= inst_min and total >= entry_min:
                # 進場，用 10% 資金
                position = {'entry_date': date, 'entry_price': price, 'fc': f_c, 'tc': t_c, 'pct': 10}
        else:
            days_held = i - dates.index(position['entry_date'])
            if days_held >= hold_days:
                ret_pct = (price / position['entry_price'] - 1) * 100
                pnl_pct = ret_pct * (position['pct'] / 100)
                trades.append({
                    'symbol': symbol, 'entry': position['entry_date'], 'exit': date,
                    'entry_px': position['entry_price'], 'exit_px': price,
                    'pnl_pct': pnl_pct, 'ret_pct': ret_pct, 'days': days_held,
                    'fc': position['fc'], 'tc': position['tc']
                })
                position = None
    
    if position:
        price = close[-1]
        ret_pct = (price / position['entry_price'] - 1) * 100
        pnl_pct = ret_pct * (position['pct'] / 100)
        days_held = len(dates) - dates.index(position['entry_date']) - 1
        trades.append({
            'symbol': symbol, 'entry': position['entry_date'], 'exit': dates[-1],
            'entry_px': position['entry_price'], 'exit_px': price,
            'pnl_pct': pnl_pct, 'ret_pct': ret_pct, 'days': days_held,
            'fc': position['fc'], 'tc': position['tc']
        })
    
    return trades

def calc_metrics(trades):
    if not trades:
        return {'trades': 0, 'wr': 0, 'avg': 0, 'pf': 0, 'ret': 0, 'mdd': 0}
    df = pd.DataFrame(trades)
    wins = df[df['ret_pct'] > 0]
    losses = df[df['ret_pct'] <= 0]
    wr = len(wins) / len(df) * 100
    avg = df['ret_pct'].mean()
    pf = wins['ret_pct'].sum() / abs(losses['ret_pct'].sum()) if len(losses) > 0 and losses['ret_pct'].sum() != 0 else 999
    ret = df['ret_pct'].sum()
    
    cum = df['ret_pct'].cumsum()
    peak = cum.cummax()
    dd = peak - cum
    mdd = dd.max()
    
    return {'trades': len(trades), 'wr': wr, 'avg': avg, 'pf': pf, 'ret': ret, 'mdd': mdd}

stocks = ['2330', '2317', '2454']
v1 = {'rsi_min': 40, 'rsi_max': 70, 'atr_min': 0.3, 'inst_min': 0, 'entry_min': 60, 'hold_days': 5}
v11 = {'rsi_min': 40, 'rsi_max': 75, 'atr_min': 0.3, 'inst_min': 10, 'entry_min': 65, 'hold_days': 7}

print()
print('='*60)
print(' Nana v1.0 vs v1.1 Backtest Report')
print('='*60)
print()

all_results = {}

for symbol in stocks:
    print(f'Testing {symbol}...')
    t1 = run_backtest(symbol, v1)
    m1 = calc_metrics(t1)
    t2 = run_backtest(symbol, v11)
    m2 = calc_metrics(t2)
    all_results[symbol] = {'v1': m1, 'v11': m2, 'v1_trades': t1, 'v11_trades': t2}
    print(f'  v1.0: {m1["trades"]} trades, WR={m1["wr"]:.1f}%, PF={m1["pf"]:.2f}, Ret={m1["ret"]:.1f}%')
    print(f'  v1.1: {m2["trades"]} trades, WR={m2["wr"]:.1f}%, PF={m2["pf"]:.2f}, Ret={m2["ret"]:.1f}%')
    print()

print('='*60)
print(' Summary')
print('='*60)
print()

avg_v1_wr = np.mean([all_results[s]['v1']['wr'] for s in stocks])
avg_v11_wr = np.mean([all_results[s]['v11']['wr'] for s in stocks])
avg_v1_ret = np.mean([all_results[s]['v1']['ret'] for s in stocks])
avg_v11_ret = np.mean([all_results[s]['v11']['ret'] for s in stocks])
avg_v1_pf = np.mean([all_results[s]['v1']['pf'] for s in stocks])
avg_v11_pf = np.mean([all_results[s]['v11']['pf'] for s in stocks])

print(f'{"Metric":<12} {"v1.0":>12} {"v1.1":>12} {"Diff":>10}')
print('-'*40)
print(f'{"Win Rate":<12} {avg_v1_wr:>11.1f}% {avg_v11_wr:>11.1f}% {(avg_v11_wr-avg_v1_wr):>+9.1f}%')
print(f'{"Total Ret":<12} {avg_v1_ret:>11.1f}% {avg_v11_ret:>11.1f}% {(avg_v11_ret-avg_v1_ret):>+9.1f}%')
print(f'{"Profit F.":<12} {avg_v1_pf:>12.2f} {avg_v11_pf:>12.2f} {(avg_v11_pf-avg_v1_pf):>+9.2f}')
print()

winner = 'v1.1' if avg_v11_wr > avg_v1_wr else 'v1.0' if avg_v1_wr > avg_v11_wr else 'TIE'
print(f'Winner: {winner}')

with open('Tina_Quant_System/teams/nana/backtest_final.json', 'w', encoding='utf-8') as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2)
print()
print('Saved: backtest_final.json')