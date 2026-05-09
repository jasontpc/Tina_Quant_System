# -*- coding: utf-8 -*-
"""
全系統歷史回測 + 策略優化系統 v1.0
功能：
  1. 對所有團隊進行歷史回測
  2. 找出最優參數組合
  3. 自動優化策略參數
  4. 記錄最優參數並套用
"""

import sys, os, json, yfinance as yf, pandas as pd, numpy as np, subprocess
from datetime import datetime, date
from itertools import product
from typing import Dict, List, Tuple

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams'
OUTPUT_DIR = os.path.join(BASE_DIR, '..', 'automation', 'backtest_results')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── 市場數據獲取 ───────────────────────────────
def get_market_data(ticker='^TWII', period='5y') -> pd.DataFrame:
    """獲取市場數據"""
    print(f'  獲取 {ticker} {period} 歷史數據...')
    h = yf.Ticker(ticker).history(period=period)
    return h['Close'].dropna() if len(h) > 0 else None

def add_indicators(closes: pd.Series) -> pd.DataFrame:
    """添加技術指標"""
    df = pd.DataFrame({'close': closes})
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma60'] = df['close'].rolling(60).mean()
    df['ma120'] = df['close'].rolling(120).mean()
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + gain / loss))
    df['bias'] = (df['close'] - df['ma20']) / df['ma20'] * 100
    h = yf.Ticker('^TWII').history(period='5y')
    vol = h['Volume'].dropna() if len(h) > 0 else None
    if vol is not None:
        df['vol_ma20'] = vol.rolling(20).mean()
    else:
        df['vol_ma20'] = 1
    return df

# ── 全系統回測函式 ───────────────────────────────
def backtest_nana_strategy(closes: pd.Series, params: Dict) -> Dict:
    """回測Nana波段策略"""
    df = add_indicators(closes)
    
    entry_rsi_max = params['entry_rsi_max']
    entry_score_min = params['entry_score_min']
    entry_bias_max = params['entry_bias_max']
    bias_exit = params['bias_exit']
    atr_stop = params['atr_stop']
    atr_target = params['atr_target']
    
    trades = []
    position = None
    entry_price = 0
    entry_date = None
    
    for i in range(120, len(df)):
        if pd.isna(df['rsi'].iloc[i]) or pd.isna(df['ma20'].iloc[i]):
            continue
        
        rsi = df['rsi'].iloc[i]
        bias = df['bias'].iloc[i]
        cur = df['close'].iloc[i]
        atr = (df['close'].iloc[i] - df['close'].iloc[i-14:i].min()) if i >= 14 else cur * 0.02
        
        if position is None:
            # 進場條件
            if rsi < entry_rsi_max and abs(bias) < entry_bias_max:
                score = 0
                if 40 <= rsi < 50: score += 30
                elif 50 <= rsi < entry_rsi_max: score += 20
                if abs(bias) < 3: score += 15
                elif abs(bias) < entry_bias_max: score += 10
                
                if score >= entry_score_min:
                    position = {
                        'entry_price': cur,
                        'entry_date': df.index[i],
                        'entry_rsi': rsi,
                        'atr': atr,
                    }
        else:
            # 出場條件
            stop = position['entry_price'] - (atr * atr_stop)
            target = position['entry_price'] + (atr * atr_target)
            ret = (cur - position['entry_price']) / position['entry_price'] * 100
            
            exit_reason = None
            if cur <= stop:
                exit_reason = 'stop_loss'
            elif cur >= target:
                exit_reason = 'take_profit'
            elif bias > bias_exit:
                exit_reason = 'bias_exit'
            
            if exit_reason:
                trades.append({
                    'entry_price': position['entry_price'],
                    'exit_price': cur,
                    'return_pct': ret,
                    'exit_reason': exit_reason,
                    'entry_rsi': position['entry_rsi'],
                })
                position = None
    
    if not trades:
        return {'total_trades': 0, 'win_rate': 0, 'avg_return': 0}
    
    wins = [t for t in trades if t['return_pct'] > 0]
    return {
        'total_trades': len(trades),
        'win_rate': len(wins) / len(trades) * 100,
        'avg_return': sum(t['return_pct'] for t in trades) / len(trades),
        'max_gain': max(t['return_pct'] for t in trades),
        'max_loss': min(t['return_pct'] for t in trades),
    }

def backtest_leo_strategy(closes: pd.Series, params: Dict) -> Dict:
    """回測Leo波段策略"""
    df = add_indicators(closes)
    
    entry_rsi_max = params['entry_rsi_max']
    take_profit_pct = params['take_profit_pct']
    stop_loss_pct = params['stop_loss_pct']
    
    trades = []
    position = None
    
    for i in range(120, len(df)):
        if pd.isna(df['rsi'].iloc[i]):
            continue
        
        rsi = df['rsi'].iloc[i]
        cur = df['close'].iloc[i]
        bias = df['bias'].iloc[i]
        
        if position is None:
            if rsi < entry_rsi_max and abs(bias) < 15:
                position = {'entry_price': cur, 'entry_rsi': rsi}
        else:
            ret = (cur - position['entry_price']) / position['entry_price'] * 100
            exit_reason = None
            if ret <= -stop_loss_pct:
                exit_reason = 'stop_loss'
            elif ret >= take_profit_pct:
                exit_reason = 'take_profit'
            elif rsi > 85:
                exit_reason = 'overheat'
            
            if exit_reason:
                trades.append({
                    'entry_price': position['entry_price'],
                    'exit_price': cur,
                    'return_pct': ret,
                    'exit_reason': exit_reason,
                })
                position = None
    
    if not trades:
        return {'total_trades': 0, 'win_rate': 0, 'avg_return': 0}
    
    wins = [t for t in trades if t['return_pct'] > 0]
    return {
        'total_trades': len(trades),
        'win_rate': len(wins) / len(trades) * 100,
        'avg_return': sum(t['return_pct'] for t in trades) / len(trades),
        'max_gain': max(t['return_pct'] for t in trades),
        'max_loss': min(t['return_pct'] for t in trades),
    }

def backtest_ray_dca(closes: pd.Series, params: Dict) -> Dict:
    """回測Ray DCA策略"""
    yr_high = closes.rolling(252).max()
    yr_low = closes.rolling(252).min()
    
    investment = 0
    shares = 0
    trades = []
    
    entry_threshold = params['entry_threshold']
    low_threshold = params['low_threshold']
    dca_amount = params['dca_amount']
    
    for i in range(252, len(closes)):
        pos = (closes.iloc[i] - yr_low.iloc[i]) / (yr_high.iloc[i] - yr_low.iloc[i]) * 100 if yr_high.iloc[i] > yr_low.iloc[i] else 50
        
        if pos < low_threshold:
            amount = dca_amount * 1.5
        elif pos < entry_threshold:
            amount = dca_amount
        else:
            amount = 0
        
        if amount > 0:
            sh = amount / closes.iloc[i]
            shares += sh
            investment += amount
            trades.append({'date': closes.index[i], 'price': closes.iloc[i], 'shares': sh, 'amount': amount})
    
    if investment == 0 or shares == 0:
        return {'total_trades': 0, 'total_return': 0}
    
    final_value = shares * closes.iloc[-1]
    total_return = (final_value - investment) / investment * 100
    avg_cost = investment / shares
    
    return {
        'total_trades': len(trades),
        'total_investment': investment,
        'final_value': final_value,
        'total_return': total_return,
        'avg_cost': avg_cost,
    }

# ── 參數網格搜尋 ───────────────────────────────
def grid_search_nana(closes: pd.Series) -> Tuple[Dict, Dict]:
    """Nana參數網格搜尋"""
    print('\n[Step 1] Nana 參數網格搜尋...')
    
    param_grid = {
        'entry_rsi_max': [45, 50, 55, 60, 65],
        'entry_score_min': [25, 30, 35, 40],
        'entry_bias_max': [3, 5, 8, 10],
        'bias_exit': [4, 5, 6],
        'atr_stop': [1.5],
        'atr_target': [3.0],
    }
    
    best_params = None
    best_result = None
    best_score = 0
    
    results = []
    keys = list(param_grid.keys())
    values = [param_grid[k] for k in keys]
    
    total = 1
    for v in values:
        total *= len(v)
    print(f'  總測試組合: {total}')
    
    count = 0
    for combo in product(*values):
        params = dict(zip(keys, combo))
        result = backtest_nana_strategy(closes, params)
        
        # 評分：勝率×50 + avg_return×10（勝率權重更高）
        score = result['win_rate'] * 0.5 + result['avg_return'] * 10
        
        results.append({
            'params': params,
            'result': result,
            'score': score,
        })
        
        if score > best_score and result['total_trades'] >= 10:
            best_score = score
            best_params = params
            best_result = result
        
        count += 1
        if count % 100 == 0:
            print(f'  進度: {count}/{total}')
    
    results.sort(key=lambda x: x['score'], reverse=True)
    
    print(f'  最佳: 勝率={best_result["win_rate"]:.1f}%, 均報酬={best_result["avg_return"]:.2f}%')
    print(f'  最佳參數: RSI≤{best_params["entry_rsi_max"]}, Score≥{best_params["entry_score_min"]}, BIAS<{best_params["entry_bias_max"]}%')
    
    return best_params, best_result, results[:10]

def grid_search_leo(closes: pd.Series) -> Tuple[Dict, Dict]:
    """Leo參數網格搜尋"""
    print('\n[Step 2] Leo 參數網格搜尋...')
    
    param_grid = {
        'entry_rsi_max': [50, 55, 60, 65, 70],
        'take_profit_pct': [15, 20, 25],
        'stop_loss_pct': [6, 8, 10],
    }
    
    best_params = None
    best_result = None
    best_score = 0
    
    results = []
    keys = list(param_grid.keys())
    values = [param_grid[k] for k in keys]
    
    total = 1
    for v in values:
        total *= len(v)
    print(f'  總測試組合: {total}')
    
    count = 0
    for combo in product(*values):
        params = dict(zip(keys, combo))
        result = backtest_leo_strategy(closes, params)
        
        score = result['win_rate'] * 0.5 + result['avg_return'] * 10
        
        results.append({
            'params': params,
            'result': result,
            'score': score,
        })
        
        if score > best_score and result['total_trades'] >= 10:
            best_score = score
            best_params = params
            best_result = result
        
        count += 1
    
    results.sort(key=lambda x: x['score'], reverse=True)
    
    print(f'  最佳: 勝率={best_result["win_rate"]:.1f}%, 均報酬={best_result["avg_return"]:.2f}%')
    print(f'  最佳參數: RSI≤{best_params["entry_rsi_max"]}, 目標+{best_params["take_profit_pct"]}%, 停損-{best_params["stop_loss_pct"]}%')
    
    return best_params, best_result, results[:10]

def grid_search_ray(closes: pd.Series) -> Tuple[Dict, Dict]:
    """Ray DCA參數網格搜尋"""
    print('\n[Step 3] Ray DCA 參數網格搜尋...')
    
    param_grid = {
        'entry_threshold': [40, 45, 50, 55, 60],
        'low_threshold': [20, 25, 30, 35],
        'dca_amount': [5000, 10000],
    }
    
    best_params = None
    best_result = None
    best_score = 0
    
    results = []
    keys = list(param_grid.keys())
    values = [param_grid[k] for k in keys]
    
    total = 1
    for v in values:
        total *= len(v)
    print(f'  總測試組合: {total}')
    
    count = 0
    for combo in product(*values):
        params = dict(zip(keys, combo))
        result = backtest_ray_dca(closes, params)
        
        score = result['total_return'] * 2  # DCA以總報酬為主
        
        results.append({
            'params': params,
            'result': result,
            'score': score,
        })
        
        if score > best_score and result['total_trades'] >= 10:
            best_score = score
            best_params = params
            best_result = result
        
        count += 1
    
    results.sort(key=lambda x: x['score'], reverse=True)
    
    print(f'  最佳: 報酬={best_result["total_return"]:.1f}%, {best_result["total_trades"]}筆投資')
    print(f'  最佳參數: threshold={best_params["entry_threshold"]}, low={best_params["low_threshold"]}')
    
    return best_params, best_result, results[:10]

# ── 主循環 ───────────────────────────────
def main():
    print('=' * 65)
    print('  全系統歷史回測 + 策略優化系統 v1.0')
    print(f'  時間: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('=' * 65)
    
    # 獲取市場數據
    print('\n[Step 0] 獲取歷史數據...')
    closes = get_market_data('^TWII', '5y')
    if closes is None or len(closes) < 500:
        print('  錯誤: 市場數據不足')
        return
    
    print(f'  數據: {len(closes)}天 ({closes.index[0].date()} ~ {closes.index[-1].date()})')
    
    # 各團隊回測優化
    nana_params, nana_result, nana_top = grid_search_nana(closes)
    leo_params, leo_result, leo_top = grid_search_leo(closes)
    ray_params, ray_result, ray_top = grid_search_ray(closes)
    
    # 整合結果
    all_results = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'data_period': f'{closes.index[0].date()} ~ {closes.index[-1].date()}',
        'nana': {
            'best_params': nana_params,
            'best_result': nana_result,
            'top10': nana_top,
        },
        'leo': {
            'best_params': leo_params,
            'best_result': leo_result,
            'top10': leo_top,
        },
        'ray': {
            'best_params': ray_params,
            'best_result': ray_result,
            'top10': ray_top,
        },
    }
    
    # 儲存
    output_file = os.path.join(OUTPUT_DIR, 'full_backtest_optimization.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    # 寫入最優參數到各團隊
    nana_opt_file = os.path.join(BASE_DIR, 'nana', 'nana_optimized_params.json')
    with open(nana_opt_file, 'w', encoding='utf-8') as f:
        json.dump({'params': nana_params, 'result': nana_result}, f, ensure_ascii=False, indent=2)
    
    leo_opt_file = os.path.join(BASE_DIR, 'leo', 'scripts', 'leo_optimized_params.json')
    with open(leo_opt_file, 'w', encoding='utf-8') as f:
        json.dump({'params': leo_params, 'result': leo_result}, f, ensure_ascii=False, indent=2)
    
    ray_opt_file = os.path.join(BASE_DIR, 'ray', 'ray_optimized_params.json')
    with open(ray_opt_file, 'w', encoding='utf-8') as f:
        json.dump({'params': ray_params, 'result': ray_result}, f, ensure_ascii=False, indent=2)
    
    # 總結
    print('\n' + '=' * 65)
    print('  回測優化完成')
    print('=' * 65)
    print(f'\n📊 Nana 最佳策略:')
    print(f'   勝率: {nana_result["win_rate"]:.1f}%')
    print(f'   均報酬: {nana_result["avg_return"]:.2f}%')
    print(f'   參數: RSI≤{nana_params["entry_rsi_max"]}, Score≥{nana_params["entry_score_min"]}')
    
    print(f'\n📊 Leo 最佳策略:')
    print(f'   勝率: {leo_result["win_rate"]:.1f}%')
    print(f'   均報酬: {leo_result["avg_return"]:.2f}%')
    print(f'   參數: RSI≤{leo_params["entry_rsi_max"]}, +{leo_params["take_profit_pct"]}%, -{leo_params["stop_loss_pct"]}%')
    
    print(f'\n📊 Ray 最佳策略:')
    print(f'   總報酬: {ray_result["total_return"]:.1f}%')
    print(f'   參數: threshold={ray_params["entry_threshold"]}, low={ray_params["low_threshold"]}')
    
    print(f'\n💾 已寫入最優參數到各團隊目錄')
    
    return all_results

if __name__ == '__main__':
    main()