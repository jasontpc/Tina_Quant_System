# -*- coding: utf-8 -*-
"""
Nana Backtest Engine v1.0 - 自主回測系統
========================================

功能:
1. 完整回測引擎 (向後測試)
2. 多策略比較 (v1.0 vs v1.1)
3. 參數優化 (Grid Search)
4. 失敗模式分析
5. 自動優化迭代

自主流程:
1. 抓取歷史資料
2. 產生進場/出場訊號
3. 計算績效指標
4. 比較策略表現
5. 找出最優參數
6. 輸出報告
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np
import yfinance as yf
import sqlite3
import json
import itertools
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

DB_PATH = 'skills/stock-analyzer/scripts/tina_master.db'

# ==================== 參數空間 ====================

PARAM_GRID = {
    'rsi_min': [30, 40, 50],
    'rsi_max': [65, 70, 75, 80],
    'atr_min': [0.003, 0.005, 0.007],
    'inst_min_score': [0, 10, 20],
    'total_min': [40, 50, 60],
    'entry_min': [55, 60, 65, 70],
    'hold_days': [5, 7, 10]
}

# ==================== 資料抓取 ====================

def fetch_history(symbol, days=365):
    """抓取歷史股價"""
    try:
        df = yf.download(symbol + '.TW', period=f'{days}d', auto_adjust=True, progress=False)
        if df is None or len(df) < 60:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        return df
    except:
        return None

def get_institutional(symbol, dates):
    """取得法人資料 (對應日期)"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    placeholders = ','.join(['?'] * len(dates))
    query = f'SELECT date, foreign_net, trust_net FROM MarketData WHERE symbol = ? AND date IN ({placeholders})'
    params = [symbol] + dates
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    
    inst_map = {}
    for date, f, t in rows:
        inst_map[str(date)] = {'foreign': f or 0, 'trust': t or 0}
    return inst_map

# ==================== 指標計算 ====================

def calculate_indicators(df):
    """計算技術指標"""
    close = df['Close'].values
    high = df['High'].values
    low = df['Low'].values
    volume = df['Volume'].values
    
    # MA
    ma20 = pd.Series(close).rolling(20).mean().values
    ma60 = pd.Series(close).rolling(60).mean().values
    
    # RSI
    delta = np.diff(close, prepend=close[0])
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta > 0, 0, -delta)
    avg_gain = pd.Series(gain).rolling(14).mean().values
    avg_loss = pd.Series(loss).rolling(14).mean().values
    rs = avg_gain / np.where(avg_loss == 0, np.nan, avg_loss)
    rsi = 100 - (100 / (1 + rs))
    rsi = np.where(np.isnan(rsi), 50, rsi)
    
    # ATR
    tr1 = high - low
    tr2 = np.abs(high - np.roll(close, 1))
    tr3 = np.abs(low - np.roll(close, 1))
    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    atr = pd.Series(tr).rolling(14).mean().values
    atr_pct = atr / close * 100
    
    # Bias
    bias = (close - ma20) / ma20 * 100
    
    # Volume MA
    vol_ma5 = pd.Series(volume).rolling(5).mean().values
    
    return {
        'close': close,
        'high': high,
        'low': low,
        'ma20': ma20,
        'ma60': ma60,
        'rsi': rsi,
        'atr_pct': atr_pct,
        'bias': bias,
        'volume': volume,
        'vol_ma5': vol_ma5
    }

def calculate_consecutive(df, dates, inst_map):
    """計算法人連續買超天數"""
    f_consec = np.zeros(len(dates))
    t_consec = np.zeros(len(dates))
    
    f_count = t_count = 0
    
    for i in range(len(dates) - 1, -1, -1):
        date_str = str(dates[i])[:10]
        inst = inst_map.get(date_str, {'foreign': 0, 'trust': 0})
        
        if inst['foreign'] > 0:
            f_count += 1
        else:
            f_count = 0
        
        if inst['trust'] > 0:
            t_count += 1
        else:
            t_count = 0
        
        f_consec[i] = f_count
        t_consec[i] = t_count
    
    return f_consec, t_consec

# ==================== 評分系統 ====================

def inst_score(days):
    if days >= 11: return 20
    elif days >= 6: return 60
    elif days >= 4: return 50
    elif days == 3: return 40
    elif days == 2: return 15
    elif days == 1: return 10
    return 0

def calculate_score(rsi, bias, f_consec, t_consec):
    """計算 Nana 評分"""
    # RSI 評分
    if 50 <= rsi <= 70: rsi_score = 15
    elif 30 <= rsi < 50: rsi_score = 10
    else: rsi_score = 5
    
    # Bias 評分
    if -2 <= bias <= 3: bias_score = 15
    elif 3 < bias <= 6: bias_score = 10
    elif bias > 10: bias_score = 0
    else: bias_score = 5
    
    # 法人評分
    f_s = inst_score(f_consec)
    t_s = inst_score(t_consec)
    base = max(f_s, t_s)
    if f_consec >= 3 and t_consec >= 3:
        base += 10
    inst_total = min(70, base)
    
    return inst_total + rsi_score + bias_score

# ==================== 回測引擎 ====================

def run_backtest(symbol, params, start_date=None, end_date=None, initial_capital=1000000):
    """
    執行單一策略回測
    
    返回:
        Dict with trades, metrics
    """
    # 抓資料
    df = fetch_history(symbol, days=500)
    if df is None:
        return None
    
    dates = df.index.values
    close = df['Close'].values
    
    # 計算指標
    ind = calculate_indicators(df)
    
    # 取得法人資料
    date_strs = [str(d)[:10] for d in dates]
    inst_map = get_institutional(symbol, date_strs)
    f_consec, t_consec = calculate_consecutive(df, dates, inst_map)
    
    # 過濾日期範圍
    if start_date:
        start_idx = 0
        for i, d in enumerate(dates):
            if str(d)[:10] >= start_date:
                start_idx = i
                break
    else:
        start_idx = 60  # 預設從有MA60後開始
    
    if end_date:
        end_idx = len(dates)
        for i, d in enumerate(dates):
            if str(d)[:10] > end_date:
                end_idx = i
                break
    else:
        end_idx = len(dates)
    
    # 參數
    rsi_min = params.get('rsi_min', 40)
    rsi_max = params.get('rsi_max', 75)
    atr_min = params.get('atr_min', 0.003) * 100  # 轉百分比
    inst_min = params.get('inst_min_score', 10)
    total_min = params.get('total_min', 50)
    entry_min = params.get('entry_min', 65)
    hold_days = params.get('hold_days', 5)
    
    # 交易記錄
    trades = []
    position = None
    
    for i in range(start_idx, end_idx):
        date = str(dates[i])[:10]
        price = close[i]
        rsi = ind['rsi'][i]
        bias = ind['bias'][i]
        atr = ind['atr_pct'][i]
        ma20 = ind['ma20'][i]
        ma60 = ind['ma60'][i]
        fc = f_consec[i]
        tc = t_consec[i]
        
        # 進場條件
        if position is None:
            score = calculate_score(rsi, bias, fc, tc)
            
            # 基本進場條件
            rsi_ok = rsi_min <= rsi <= rsi_max
            ma_ok = ma20 > ma60 if not np.isnan(ma20) and not np.isnan(ma60) else False
            atr_ok = atr >= atr_min
            inst_ok = fc > 0 or tc > 0
            
            score_ok = score >= entry_min
            
            if rsi_ok and ma_ok and atr_ok and inst_ok and score_ok:
                # 計算進場量
                shares = int(initial_capital * 0.1 / price / 100) * 100  # 10%倉位
                if shares >= 100:
                    position = {
                        'entry_date': date,
                        'entry_price': price,
                        'shares': shares,
                        'score': score,
                        'rsi': rsi,
                        'fc': fc,
                        'tc': tc
                    }
        
        # 出場條件
        else:
            days_held = i - np.where(dates == np.datetime64(position['entry_date']))[0][0]
            
            # 出場: 持有期滿
            if days_held >= hold_days:
                pnl = (price - position['entry_price']) * position['shares']
                pnl_pct = (price / position['entry_price'] - 1) * 100
                
                trades.append({
                    'symbol': symbol,
                    'entry_date': position['entry_date'],
                    'exit_date': date,
                    'entry_price': position['entry_price'],
                    'exit_price': price,
                    'shares': position['shares'],
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'days': days_held,
                    'reason': 'time'
                })
                position = None
    
    # 如果還有持仓，平倉
    if position is not None:
        price = close[-1]
        pnl = (price - position['entry_price']) * position['shares']
        pnl_pct = (price / position['entry_price'] - 1) * 100
        trades.append({
            'symbol': symbol,
            'entry_date': position['entry_date'],
            'exit_date': str(dates[-1])[:10],
            'entry_price': position['entry_price'],
            'exit_price': price,
            'shares': position['shares'],
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'days': 0,
            'reason': 'eod'
        })
    
    return trades

def calculate_metrics(trades, initial_capital=1000000):
    """計算績效指標"""
    if not trades:
        return {
            'total_trades': 0,
            'win_rate': 0,
            'avg_return': 0,
            'profit_factor': 0,
            'max_drawdown': 0,
            'total_return': 0,
            'sharpe': 0
        }
    
    df = pd.DataFrame(trades)
    
    wins = df[df['pnl'] > 0]
    losses = df[df['pnl'] <= 0]
    
    total_pnl = df['pnl'].sum()
    total_return = total_pnl / initial_capital * 100
    
    win_rate = len(wins) / len(df) * 100 if len(df) > 0 else 0
    avg_return = df['pnl_pct'].mean()
    
    gross_profit = wins['pnl'].sum() if len(wins) > 0 else 0
    gross_loss = abs(losses['pnl'].sum()) if len(losses) > 0 else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    # Max Drawdown
    cumulative = df['pnl'].cumsum()
    peak = cumulative.cummax()
    drawdown = peak - cumulative
    max_drawdown = drawdown.max() / initial_capital * 100
    
    # Sharpe (simplified)
    daily_returns = df['pnl_pct'] / 100
    sharpe = daily_returns.mean() / daily_returns.std() * np.sqrt(252) if daily_returns.std() > 0 else 0
    
    return {
        'total_trades': len(trades),
        'win_rate': win_rate,
        'avg_return': avg_return,
        'profit_factor': profit_factor,
        'max_drawdown': max_drawdown,
        'total_return': total_return,
        'sharpe': sharpe,
        'avg_win': wins['pnl_pct'].mean() if len(wins) > 0 else 0,
        'avg_loss': losses['pnl_pct'].mean() if len(losses) > 0 else 0
    }

# ==================== 策略比較 ====================

def compare_strategies(symbol, v1_params, v11_params, start_date='2025-01-01'):
    """比較 v1.0 和 v1.1 策略"""
    print()
    print('='*60)
    print(f' 策略比較: {symbol}')
    print('='*60)
    print()
    
    # v1.0
    print('執行 v1.0...')
    v1_trades = run_backtest(symbol, v1_params, start_date=start_date)
    v1_metrics = calculate_metrics(v1_trades) if v1_trades else {}
    
    # v1.1
    print('執行 v1.1...')
    v11_trades = run_backtest(symbol, v11_params, start_date=start_date)
    v11_metrics = calculate_metrics(v11_trades) if v11_trades else {}
    
    print()
    print(f'{"指標":<15} {"v1.0":>12} {"v1.1":>12} {"差異":>10}')
    print('-'*50)
    
    metrics = ['total_trades', 'win_rate', 'avg_return', 'profit_factor', 'max_drawdown', 'total_return']
    for m in metrics:
        v1_val = v1_metrics.get(m, 0)
        v11_val = v11_metrics.get(m, 0)
        diff = v11_val - v1_val
        if m == 'win_rate' or m == 'avg_return' or m == 'total_return':
            diff_str = f'{diff:+.1f}%'
        elif m == 'profit_factor':
            diff_str = f'{diff:+.2f}'
        else:
            diff_str = f'{diff:+.0f}'
        print(f'{m:<15} {v1_val:>12.2f} {v11_val:>12.2f} {diff_str:>10}')
    
    # 找出哪個更好
    v1_score = v1_metrics.get('win_rate', 0) * 0.4 + v1_metrics.get('profit_factor', 0) * 30
    v11_score = v11_metrics.get('win_rate', 0) * 0.4 + v11_metrics.get('profit_factor', 0) * 30
    
    print()
    if v11_score > v1_score:
        print(f'結論: v1.1 較好 (+{v11_score - v1_score:.1f} 分)')
    else:
        print(f'結論: v1.0 較好 (+{v1_score - v11_score:.1f} 分)')
    
    return {
        'v1': v1_metrics,
        'v11': v11_metrics,
        'v1_trades': v1_trades,
        'v11_trades': v11_trades
    }

# ==================== 參數優化 ====================

def grid_search(symbol, param_grid, start_date='2025-01-01'):
    """網格搜索最優參數"""
    print()
    print('='*60)
    print(f' 網格搜索: {symbol}')
    print('='*60)
    
    # 生成所有參數組合
    keys = list(param_grid.keys())
    values = list(param_grid.values())
    combinations = list(itertools.product(*values))
    
    print(f'總共 {len(combinations)} 種組合')
    print()
    
    best_score = 0
    best_params = None
    best_metrics = None
    results = []
    
    for i, combo in enumerate(combinations):
        params = dict(zip(keys, combo))
        
        trades = run_backtest(symbol, params, start_date=start_date)
        metrics = calculate_metrics(trades) if trades else {}
        
        # 評分: WR * 0.4 + PF * 30 + return * 0.1
        score = (metrics.get('win_rate', 0) * 0.4 + 
                min(metrics.get('profit_factor', 0), 5) * 30 + 
                min(metrics.get('total_return', 0), 50) * 0.1)
        
        results.append({
            'params': params,
            'metrics': metrics,
            'score': score
        })
        
        if score > best_score:
            best_score = score
            best_params = params
            best_metrics = metrics
            print(f'  [{i+1}/{len(combinations)}] 新最佳! Score={score:.1f}')
        else:
            if (i + 1) % 50 == 0:
                print(f'  [{i+1}/{len(combinations)}]')
    
    print()
    print('='*60)
    print(' 最佳參數')
    print('='*60)
    print()
    for k, v in best_params.items():
        print(f'  {k}: {v}')
    print()
    print(f' Win Rate: {best_metrics.get("win_rate", 0):.1f}%')
    print(f' Profit Factor: {best_metrics.get("profit_factor", 0):.2f}')
    print(f' Total Return: {best_metrics.get("total_return", 0):.1f}%')
    print(f' Score: {best_score:.1f}')
    
    return {
        'best_params': best_params,
        'best_metrics': best_metrics,
        'best_score': best_score,
        'all_results': results
    }

# ==================== 主程式 ====================

def main():
    print()
    print('╔' + '═'*58 + '╗')
    print('║' + ' '*12 + 'Nana 回測系統 v1.0' + ' '*23 + '║')
    print('╚' + '═'*58 + '╝')
    print()
    
    # 測試股票
    test_stocks = ['2330', '2317', '2454']
    
    # v1.0 參數
    v1_params = {
        'rsi_min': 40,
        'rsi_max': 70,
        'atr_min': 0.003,
        'inst_min_score': 0,
        'total_min': 40,
        'entry_min': 60,
        'hold_days': 5
    }
    
    # v1.1 參數
    v11_params = {
        'rsi_min': 40,
        'rsi_max': 75,
        'atr_min': 0.003,
        'inst_min_score': 10,
        'total_min': 50,
        'entry_min': 65,
        'hold_days': 7
    }
    
    # 1. 策略比較
    print()
    print('='*60)
    print(' 第一階段: v1.0 vs v1.1 策略比較')
    print('='*60)
    
    all_results = {}
    for symbol in test_stocks:
        result = compare_strategies(symbol, v1_params, v11_params)
        all_results[symbol] = result
    
    # 2. 單一股票網格搜索
    print()
    print('='*60)
    print(' 第二階段: 網格搜索最優參數')
    print('='*60)
    
    grid_results = {}
    for symbol in test_stocks[:1]:  # 只做一檔示範
        result = grid_search(symbol, PARAM_GRID)
        grid_results[symbol] = result
    
    # 3. 總結
    print()
    print('='*60)
    print(' 回測總結')
    print('='*60)
    print()
    
    total_v1_wr = np.mean([all_results[s]['v1'].get('win_rate', 0) for s in test_stocks])
    total_v11_wr = np.mean([all_results[s]['v11'].get('win_rate', 0) for s in test_stocks])
    
    print(f'平均勝率:')
    print(f'  v1.0: {total_v1_wr:.1f}%')
    print(f'  v1.1: {total_v11_wr:.1f}%')
    
    if total_v11_wr > total_v1_wr:
        print(f'  → v1.1 勝出 +{total_v11_wr - total_v1_wr:.1f}%')
    else:
        print(f'  → v1.0 勝出 +{total_v1_wr - total_v11_wr:.1f}%')
    
    # 儲存結果
    output = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'test_stocks': test_stocks,
        'comparison': all_results,
        'grid_search': grid_results
    }
    
    with open('Tina_Quant_System/teams/nana/backtest_results.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print()
    print('已儲存: backtest_results.json')
    print('='*60)

if __name__ == '__main__':
    main()