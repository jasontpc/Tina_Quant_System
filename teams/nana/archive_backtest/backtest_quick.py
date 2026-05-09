# -*- coding: utf-8 -*-
"""
Nana Backtest - Quick Test
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np
import yfinance as yf
import sqlite3
import json

DB_PATH = 'skills/stock-analyzer/scripts/tina_master.db'

def fetch_data(symbol):
    df = yf.download(symbol + '.TW', period='365d', auto_adjust=True, progress=False)
    if df is None or len(df) < 60:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    return df

def get_inst(symbol):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT date, foreign_net, trust_net FROM MarketData WHERE symbol = ? ORDER BY date DESC LIMIT 60', (symbol,))
    rows = cur.fetchall()
    conn.close()
    return {(str(r[0])[:10]): {'f': r[1] or 0, 't': r[2] or 0} for r in rows}

def inst_score(days):
    if days >= 11: return 20
    elif days >= 6: return 60
    elif days >= 4: return 50
    elif days == 3: return 40
    elif days == 2: return 15
    elif days == 1: return 10
    return 0

def run_backtest(symbol, params):
    df = fetch_data(symbol)
    if df is None:
        return None
    
    inst_map = get_inst(symbol)
    
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
    
    # Bias
    bias = (close - ma20) / ma20 * 100
    
    # 法人連續
    f_cons = np.zeros(len(dates))
    t_cons = np.zeros(len(dates))
    f_count = t_count = 0
    
    for i in range(len(dates) - 1, -1, -1):
        inst = inst_map.get(dates[i], {'f': 0, 't': 0})
        if inst['f'] > 0: f_count += 1
        else: f_count = 0
        if inst['t'] > 0: t_count += 1
        else: t_count = 0
        f_cons[i] = f_count
        t_cons[i] = t_count
    
    # 回測
    trades = []
    position = None
    
    rsi_min = params.get('rsi_min', 40)
    rsi_max = params.get('rsi_max', 75)
    atr_min = params.get('atr_min', 0.3)
    inst_min = params.get('inst_min', 10)
    entry_min = params.get('entry_min', 65)
    hold_days = params.get('hold_days', 7)
    
    for i in range(60, len(dates)):
        date = dates[i]
        price = close[i]
        r = rsi[i]
        b = bias[i]
        a = atr_pct[i]
        m20 = ma20[i]
        m60 = ma60[i]
        fc = f_cons[i]
        tc = t_cons[i]
        
        if position is None:
            # 進場評分
            f_s = inst_score(fc)
            t_s = inst_score(tc)
            base = max(f_s, t_s)
            if fc >= 3 and tc >= 3: base += 10
            inst_total = min(70, base)
            
            rsi_s = 15 if 50 <= r <= 70 else (10 if 30 <= r < 50 else 5)
            bias_s = 15 if -2 <= b <= 3 else (10 if 3 < b <= 6 else 0)
            total = inst_total + rsi_s + bias_s
            
            # 進場條件
            if rsi_min <= r <= rsi_max and m20 > m60 and a >= atr_min and inst_total >= inst_min and total >= entry_min:
                shares = int(100000 * 0.1 / price / 100) * 100
                if shares >= 100:
                    position = {'entry_date': date, 'entry_price': price, 'shares': shares}
        else:
            days_held = i - dates.index(position['entry_date'])
            if days_held >= hold_days:
                pnl = (price - position['entry_price']) * position['shares']
                pnl_pct = (price / position['entry_price'] - 1) * 100
                trades.append({
                    'entry': position['entry_date'], 'exit': date,
                    'entry_px': position['entry_price'], 'exit_px': price,
                    'pnl': pnl, 'pnl_pct': pnl_pct, 'days': days_held
                })
                position = None
    
    if position:
        pnl = (close[-1] - position['entry_price']) * position['shares']
        pnl_pct = (close[-1] / position['entry_price'] - 1) * 100
        trades.append({
            'entry': position['entry_date'], 'exit': dates[-1],
            'entry_px': position['entry_price'], 'exit_px': close[-1],
            'pnl': pnl, 'pnl_pct': pnl_pct, 'days': 0
        })
    
    return trades

def calc_metrics(trades):
    if not trades:
        return {'trades': 0, 'wr': 0, 'avg': 0, 'pf': 0, 'ret': 0}
    df = pd.DataFrame(trades)
    wins = df[df['pnl'] > 0]
    losses = df[df['pnl'] <= 0]
    wr = len(wins) / len(df) * 100
    avg = df['pnl_pct'].mean()
    pf = wins['pnl'].sum() / abs(losses['pnl'].sum()) if len(losses) > 0 and losses['pnl'].sum() != 0 else 999
    ret = df['pnl_pct'].sum()
    return {'trades': len(trades), 'wr': wr, 'avg': avg, 'pf': pf, 'ret': ret}

# 測試
symbol = '2330'

v1 = {'rsi_min': 40, 'rsi_max': 70, 'atr_min': 0.3, 'inst_min': 0, 'entry_min': 60, 'hold_days': 5}
v11 = {'rsi_min': 40, 'rsi_max': 75, 'atr_min': 0.3, 'inst_min': 10, 'entry_min': 65, 'hold_days': 7}

print('='*50)
print(' Nana Backtest - Quick Test')
print('='*50)
print()

print(f'Testing {symbol}...')
print()

t1 = run_backtest(symbol, v1)
m1 = calc_metrics(t1)
print(f'v1.0: Trades={m1["trades"]}, WR={m1["wr"]:.1f}%, Avg={m1["avg"]:.2f}%, PF={m1["pf"]:.2f}, Ret={m1["ret"]:.1f}%')

t2 = run_backtest(symbol, v11)
m2 = calc_metrics(t2)
print(f'v1.1: Trades={m2["trades"]}, WR={m2["wr"]:.1f}%, Avg={m2["avg"]:.2f}%, PF={m2["pf"]:.2f}, Ret={m2["ret"]:.1f}%')

print()
if m2['wr'] > m1['wr']:
    print(f'v1.1 較好: WR +{m2["wr"]-m1["wr"]:.1f}%')
elif m1['wr'] > m2['wr']:
    print(f'v1.0 較好: WR +{m1["wr"]-m2["wr"]:.1f}%')
else:
    print('兩者相同')

# 儲存
result = {'symbol': symbol, 'v1': m1, 'v11': m2, 'v1_trades': t1, 'v11_trades': t2}
with open('Tina_Quant_System/teams/nana/backtest_result.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print()
print('Saved: backtest_result.json')