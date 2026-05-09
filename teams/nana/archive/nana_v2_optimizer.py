# -*- coding: utf-8 -*-
"""
Nana v2.0 - 動態優化版
=======================
目標:
1. 加大交易數量
2. 提高勝率
3. 動態出場
4. 自主回測優化
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np
import yfinance as yf
import sqlite3
import json
from datetime import datetime

DB_PATH = 'skills/stock-analyzer/scripts/tina_master.db'

# ==================== 動態參數空間 ====================

PARAM_SPACE = {
    'rsi_min': [30, 35, 40, 45],
    'rsi_max': [70, 75, 80],
    'atr_min': [0.002, 0.003, 0.004],
    'inst_min': [0, 5, 10],
    'total_min': [45, 50, 55, 60],
    'entry_min': [55, 60, 65],
    'hold_days': [5, 7, 10],
    # 動態出场
    'exit_rsi': [80, 85, 90],
    'exit_bias': [8, 10, 12],
    'use_trailing': [True, False],
    'trailing_mult': [2.0, 2.5, 3.0]
}

def inst_score(days):
    if days >= 11: return 20
    elif days >= 6: return 60
    elif days >= 4: return 50
    elif days == 3: return 40
    elif days == 2: return 15
    elif days == 1: return 10
    return 0

def get_rsi(closes):
    d = np.diff(closes)
    g = np.where(d > 0, d, 0)
    l = np.where(d > 0, 0, -d)
    ag = np.mean(g[-14:])
    al = np.mean(l[-14:])
    return 100 - (100 / (1 + ag / al)) if al != 0 else 50

def get_inst(symbol):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT foreign_net, trust_net FROM MarketData WHERE symbol = ? ORDER BY date DESC LIMIT 30', (symbol,))
    rows = cur.fetchall()
    conn.close()
    f_c = t_c = 0
    for f, t in rows:
        if f and f > 0: f_c += 1
        else: break
    for f, t in rows:
        if t and t > 0: t_c += 1
        else: break
    return f_c, t_c

def run_backtest(symbol, params, days=180):
    """完整回測 + 動態出场"""
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
    rsi_arr = 100 - (100 / (1 + rs))
    rsi_arr = np.where(np.isnan(rsi_arr), 50, rsi_arr)
    
    # MA
    ma20 = pd.Series(close).rolling(20).mean().values
    ma60 = pd.Series(close).rolling(60).mean().values
    
    # ATR
    tr = np.maximum(high - low, np.maximum(np.abs(high - np.roll(close, 1)), np.abs(low - np.roll(close, 1))))
    atr = pd.Series(tr).rolling(14).mean().values
    atr_pct = atr / close * 100
    
    # Bias
    bias_arr = (close - ma20) / ma20 * 100
    
    # 法人
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT date, foreign_net, trust_net FROM MarketData WHERE symbol = ? ORDER BY date DESC LIMIT ?', (symbol, days))
    rows = cur.fetchall()
    conn.close()
    inst_map = {str(r[0])[:10]: {'f': r[1] or 0, 't': r[2] or 0} for r in rows}
    
    # 參數
    rsi_min = params.get('rsi_min', 40)
    rsi_max = params.get('rsi_max', 75)
    atr_min = params.get('atr_min', 0.003)
    inst_min = params.get('inst_min', 0)
    total_min = params.get('total_min', 50)
    entry_min = params.get('entry_min', 60)
    hold_days = params.get('hold_days', 7)
    exit_rsi = params.get('exit_rsi', 85)
    exit_bias = params.get('exit_bias', 10)
    use_trailing = params.get('use_trailing', True)
    trailing_mult = params.get('trailing_mult', 2.5)
    
    trades = []
    position = None
    highest_since_entry = 0
    
    for i in range(60, len(dates)):
        price = close[i]
        r = rsi_arr[i]
        m20 = ma20[i]
        m60 = ma60[i]
        a = atr_pct[i]
        b = bias_arr[i] if not np.isnan(bias_arr[i]) else 0
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
            
            # 進場
            if rsi_min <= r <= rsi_max and m20 > m60 and a >= atr_min and inst_total >= inst_min and total >= entry_min:
                position = {
                    'entry_date': date, 'entry_price': price,
                    'shares': int(50000 / price / 100) * 100,
                    'fc': f_c, 'tc': t_c,
                    'atr': a, 'trail': 0
                }
                highest_since_entry = price
        else:
            # 更新最高價 (用於 trailing)
            if high[i] > highest_since_entry:
                highest_since_entry = high[i]
            
            # 計算 trailing stop
            if use_trailing:
                position['trail'] = highest_since_entry - (position['atr'] * trailing_mult)
            
            days_held = i - dates.index(position['entry_date'])
            
            # ====== 動態出场條件 ======
            should_exit = False
            exit_reason = 'time'
            
            # 1. 時間到了
            if days_held >= hold_days:
                should_exit = True
                exit_reason = 'time'
            
            # 2. RSI 過熱
            elif r >= exit_rsi:
                should_exit = True
                exit_reason = 'rsi'
            
            # 3. Bias 過大
            elif b >= exit_bias:
                should_exit = True
                exit_reason = 'bias'
            
            # 4. Trailing stop 觸發
            elif use_trailing and price <= position['trail']:
                should_exit = True
                exit_reason = 'trailing'
            
            # 5. 趨勢反轉
            elif m20 <= m60:
                should_exit = True
                exit_reason = 'ma_cross'
            
            if should_exit:
                ret_pct = (price / position['entry_price'] - 1) * 100
                trades.append({
                    'symbol': symbol, 'entry': date, 'exit': date,
                    'entry_px': position['entry_price'], 'exit_px': price,
                    'ret_pct': ret_pct,
                    'days': days_held,
                    'reason': exit_reason,
                    'fc': position['fc'], 'tc': position['tc']
                })
                position = None
    
    if position:
        price = close[-1]
        ret_pct = (price / position['entry_price'] - 1) * 100
        days_held = len(dates) - dates.index(position['entry_date']) - 1
        trades.append({
            'symbol': symbol, 'entry': position['entry_date'], 'exit': dates[-1],
            'entry_px': position['entry_price'], 'exit_px': price,
            'ret_pct': ret_pct, 'days': days_held,
            'reason': 'eod', 'fc': position['fc'], 'tc': position['tc']
        })
    
    return trades

def calc_metrics(trades):
    if not trades:
        return {'trades': 0, 'wr': 0, 'avg': 0, 'pf': 0, 'ret': 0}
    df = pd.DataFrame(trades)
    wins = df[df['ret_pct'] > 0]
    losses = df[df['ret_pct'] <= 0]
    wr = len(wins) / len(df) * 100
    avg = df['ret_pct'].mean()
    pf = wins['ret_pct'].sum() / abs(losses['ret_pct'].sum()) if len(losses) > 0 and losses['ret_pct'].sum() != 0 else 999
    ret = df['ret_pct'].sum()
    return {'trades': len(trades), 'wr': wr, 'avg': avg, 'pf': pf, 'ret': ret}

def score_params(metrics):
    """評估參數組合分數"""
    trades = metrics.get('trades', 0)
    wr = metrics.get('wr', 0)
    pf = metrics.get('pf', 0)
    ret = metrics.get('ret', 0)
    
    if trades == 0:
        return 0
    
    # 目標: 交易多 + 勝率高 + 報酬正
    # 分數 = 交易數 * 0.1 + 勝率 * 0.5 + PF * 2 + 報酬 * 0.5
    score = (min(trades, 50) * 0.1 + 
             wr * 0.5 + 
             min(pf, 5) * 2 + 
             max(min(ret, 30), -10) * 0.5)
    
    return score

def optimize_single_stock(symbol, max_combinations=200):
    """對單一股票優化參數"""
    import itertools
    
    # 生成所有組合
    keys = list(PARAM_SPACE.keys())
    values = [PARAM_SPACE[k] for k in keys]
    all_combos = list(itertools.product(*values))
    
    print(f'  {symbol}: {len(all_combos)} 種組合')
    
    # 限制組合數
    if len(all_combos) > max_combinations:
        indices = np.linspace(0, len(all_combos)-1, max_combinations, dtype=int)
        all_combos = [all_combos[i] for i in indices]
    
    best_score = 0
    best_params = None
    best_metrics = None
    results = []
    
    for combo in all_combos:
        params = dict(zip(keys, combo))
        trades = run_backtest(symbol, params)
        metrics = calc_metrics(trades)
        score = score_params(metrics)
        
        results.append({'params': params, 'metrics': metrics, 'score': score})
        
        if score > best_score:
            best_score = score
            best_params = params
            best_metrics = metrics
    
    return {
        'symbol': symbol,
        'best_params': best_params,
        'best_metrics': best_metrics,
        'best_score': best_score,
        'all_results': results
    }

def main():
    print()
    print('='*60)
    print(' Nana v2.0 動態優化系統')
    print('='*60)
    print()
    print('目標: 交易多 + 勝率高 + 動態出场')
    print()
    
    # 測試股票池 (精簡)
    test_stocks = ['2330', '2317', '2454', '3034', '2379']
    
    all_results = {}
    
    for symbol in test_stocks:
        print(f'優化 {symbol}...')
        result = optimize_single_stock(symbol, max_combinations=100)
        all_results[symbol] = result
        
        m = result['best_metrics']
        p = result['best_params']
        print(f'  最佳: {m["trades"]}筆, WR={m["wr"]:.1f}%, PF={m["pf"]:.2f}')
        print(f'  最優參數: RSI={p["rsi_min"]}-{p["rsi_max"]}, ATR={p["atr_min"]}, hold={p["hold_days"]}')
        print(f'  出場: RSI>{p["exit_rsi"]}, Bias>{p["exit_bias"]}, trailing={p["use_trailing"]}')
        print()
    
    # 總結
    print('='*60)
    print(' 總結')
    print('='*60)
    print()
    
    total_trades = sum(all_results[s]['best_metrics']['trades'] for s in test_stocks)
    avg_wr = np.mean([all_results[s]['best_metrics']['wr'] for s in test_stocks])
    avg_pf = np.mean([all_results[s]['best_metrics']['pf'] for s in test_stocks])
    
    print(f'總交易次數: {total_trades}')
    print(f'平均勝率: {avg_wr:.1f}%')
    print(f'平均盈虧比: {avg_pf:.2f}')
    print()
    
    # 最佳股票
    best_symbol = max(all_results.keys(), key=lambda s: all_results[s]['best_score'])
    print(f'最佳個股: {best_symbol}')
    print(f'  交易: {all_results[best_symbol]["best_metrics"]["trades"]}筆')
    print(f'  勝率: {all_results[best_symbol]["best_metrics"]["wr"]:.1f}%')
    print(f'  盈虧比: {all_results[best_symbol]["best_metrics"]["pf"]:.2f}')
    
    # 儲存
    with open('Tina_Quant_System/teams/nana/optimization_results.json', 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print()
    print('已儲存: optimization_results.json')

if __name__ == '__main__':
    main()