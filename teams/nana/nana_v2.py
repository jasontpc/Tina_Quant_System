# -*- coding: utf-8 -*-
"""
Nana v2.0 - 自動化回測與優化系統
配備 Optuna 貝氏優化 + Walk-Forward 分析
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
import yfinance as yf
import numpy as np
import optuna
from datetime import datetime, timedelta
import json

optuna.logging.set_verbosity(optuna.logging.WARNING)

DB_PATH = 'skills/stock-analyzer/scripts/tina_master.db'

# 股票池
STOCKS = [
    '2330','2454','2317','2382','3034','2379','2451','2308','2345','2353',
    '2395','2401','2492','2610','2880','2881','2882','2883','2884','2885',
    '2886','2887','2891','2892','3008','3033','3044','3189','3231','3443',
    '3481','3665','3717','4938','4958','6415','6505','6669','6770','8016',
    '8046','8105','8261','8341','8464','8926','8996','9945','2385','2603'
]

def get_rsi(closes, period=14):
    delta = np.diff(closes)
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    ag = np.mean(gain[-period:])
    al = np.mean(loss[-period:])
    return 100 - (100 / (1 + ag / al)) if al != 0 else 50

def get_atr(h, period=14):
    if len(h) < 2:
        return 0
    trs = []
    for i in range(-period, 0):
        hi = float(h['High'].iloc[i])
        lo = float(h['Low'].iloc[i])
        cl = float(h['Close'].iloc[i-1]) if i-1 >= -len(h) else float(h['Close'].iloc[i])
        trs.append(max(hi-lo, abs(hi-cl), abs(lo-cl)))
    return np.mean(trs) if trs else 0

def get_inst(symbol, date_str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        SELECT SUM(foreign_net), SUM(trust_net) FROM MarketData
        WHERE symbol = ? AND date <= ? AND date >= date(?, '-5 days')
    ''', (symbol, date_str, date_str))
    f, t = cur.fetchone()
    conn.close()
    return (f or 0), (t or 0)

def nana_score(rsi, bias, atr_pct, ma20, ma60, f_net, t_net, params):
    """Nana 評分函數 (可調參數)"""
    # 法人評分 (最高80分)
    inst_max = params.get('inst_max', 80)
    if f_net > 5000:
        f_score = inst_max * 0.5
    elif f_net > 1000:
        f_score = inst_max * 0.375
    elif f_net > 0:
        f_score = inst_max * 0.1875
    else:
        f_score = 0
    
    if t_net > 1000:
        t_score = inst_max * 0.5
    elif t_net > 0:
        t_score = inst_max * 0.25
    else:
        t_score = 0
    
    base = f_score + t_score
    if f_net > 0 and t_net > 0:
        base += inst_max * 0.125  # 同步加成12.5%
    
    inst_score = min(inst_max, base)
    
    # 技術評分 (最高20分)
    tech_max = params.get('tech_max', 20)
    rsi_low = params.get('rsi_low', 40)
    rsi_high = params.get('rsi_high', 70)
    
    if rsi_low <= rsi <= rsi_high:
        rsi_score = tech_max * 0.5
    elif 30 <= rsi < rsi_low or rsi_high < rsi <= 80:
        rsi_score = tech_max * 0.25
    else:
        rsi_score = 0
    
    ma_score = tech_max * 0.25 if ma20 > ma60 else 0
    
    atr_score = tech_max * 0.25 if atr_pct >= 1.0 else (tech_max * 0.15 if atr_pct >= 0.3 else 0)
    
    tech_score = rsi_score + ma_score + atr_score
    
    return inst_score + tech_score

def check_entry(rsi, atr_pct, ma20, ma60, f_net, t_net, params):
    """檢查是否進場"""
    rsi_low = params.get('rsi_low', 40)
    rsi_high = params.get('rsi_high', 70)
    
    if not (rsi_low <= rsi <= rsi_high):
        return False, f'RSI {rsi:.1f} 超出範圍'
    if atr_pct < params.get('atr_min', 0.3):
        return False, f'ATR {atr_pct:.2f}% 不足'
    if not (ma20 > ma60):
        return False, 'MA 空頭'
    if not (f_net > 0 or t_net > 0):
        return False, '法人無買超'
    
    return True, 'OK'

def backtest_period(symbol, start_date, end_date, params, holding_days=7):
    """單一股票單一期間回測"""
    try:
        ticker = yf.Ticker(symbol + '.TW')
        h = ticker.history(start=start_date, end=end_date, period='365d')
        
        if len(h) < 60:
            return None
        
        closes = list(h['Close'].values)
        dates = list(h.index)
        
        trades = []
        
        for i in range(30, len(closes) - holding_days - 5):
            date_str = dates[i].strftime('%Y-%m-%d')
            close = closes[i]
            
            ma20 = np.mean(closes[i-19:i+1])
            ma60 = np.mean(closes[i-59:i+1]) if i >= 60 else ma20
            rsi = get_rsi(closes[:i+1])
            atr = get_atr(h, i)
            atr_pct = atr / close * 100
            bias = (close / ma20 - 1) * 100
            
            f_net, t_net = get_inst(symbol, date_str)
            
            entry_ok, msg = check_entry(rsi, atr_pct, ma20, ma60, f_net, t_net, params)
            
            if not entry_ok:
                continue
            
            score = nana_score(rsi, bias, atr_pct, ma20, ma60, f_net, t_net, params)
            entry_threshold = params.get('entry_threshold', 60)
            
            if score < entry_threshold:
                continue
            
            # 持有 N 天後出场
            exit_price = closes[i + holding_days]
            ret = (exit_price / close - 1) * 100
            
            trades.append({
                'date': date_str,
                'entry': close,
                'exit': exit_price,
                'return': ret,
                'score': score,
                'rsi': rsi,
                'atr': atr_pct
            })
        
        return trades
    except:
        return None

def calculate_metrics(returns):
    """計算績效指標"""
    if not returns:
        return {'win_rate': 0, 'avg': 0, 'sharpe': 0, 'mdd': 0, 'pf': 0, 'total': 0}
    
    total = len(returns)
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]
    
    win_rate = len(wins) / total * 100 if total > 0 else 0
    avg = np.mean(returns) if total > 0 else 0
    
    total_win = sum(wins) if wins else 0
    total_loss = abs(sum(losses)) if losses else 0
    pf = total_win / total_loss if total_loss > 0 else 0
    
    # Sharpe Ratio (假設無風險利率 4%)
    rf = 4 / 252 * 100  # 日利率
    excess = [r - rf for r in returns]
    sharpe = np.mean(excess) / np.std(excess) * np.sqrt(252) if np.std(excess) > 0 else 0
    
    # MDD
    sorted_ret = sorted(returns)
    cum, max_dd, peak = 0, 0, 0
    for r in sorted_ret:
        cum += r
        peak = max(peak, cum)
        max_dd = max(max_dd, peak - cum)
    
    return {
        'total': total,
        'win_rate': win_rate,
        'avg': avg,
        'sharpe': sharpe,
        'mdd': max_dd,
        'pf': pf
    }

def run_backtest(params, train_start, train_end, test_start=None, test_end=None):
    """執行完整回測"""
    all_trades = []
    
    for symbol in STOCKS:
        trades = backtest_period(symbol, train_start, train_end, params)
        if trades:
            all_trades.extend(trades)
    
    if not all_trades:
        return {'train': {'win_rate': 0, 'sharpe': 0, 'avg': 0, 'total': 0}, 'test': None, 'trades': 0}
    
    returns = [t['return'] for t in all_trades]
    metrics = calculate_metrics(returns)
    
    # 測試期間
    test_metrics = None
    if test_start and test_end:
        test_trades = []
        for symbol in STOCKS:
            trades = backtest_period(symbol, test_start, test_end, params)
            if trades:
                test_trades.extend(trades)
        
        if test_trades:
            test_returns = [t['return'] for t in test_trades]
            test_metrics = calculate_metrics(test_returns)
    
    return {
        'train': metrics,
        'test': test_metrics,
        'trades': len(all_trades)
    }

def objective(trial):
    """Optuna 目標函數"""
    params = {
        'rsi_low': trial.suggest_int('rsi_low', 35, 55),
        'rsi_high': trial.suggest_int('rsi_high', 60, 80),
        'atr_min': trial.suggest_float('atr_min', 0.2, 0.8),
        'inst_max': trial.suggest_int('inst_max', 60, 85),
        'tech_max': trial.suggest_int('tech_max', 15, 30),
        'entry_threshold': trial.suggest_int('entry_threshold', 50, 90),
    }
    
    # 訓練期 2024
    result = run_backtest(
        params,
        '2024-01-01', '2024-12-31',
        '2025-01-01', '2025-12-31'
    )
    
    train_sharpe = result['train']['sharpe']
    train_wr = result['train']['win_rate']
    train_total = result['train']['total']
    
    if train_total < 100:
        return 0  # 信號不足
    
    # 目標: Sharpe > 0.5, WR > 50%
    score = train_sharpe * 0.7 + (train_wr / 100) * 0.3
    
    return score

def run_optimization(n_trials=50):
    """執行 Optuna 優化"""
    print('='*60)
    print(' Nana v2.0 自動化參數優化')
    print('='*60)
    print()
    print(f' 優化目標: Sharpe Ratio + Win Rate')
    print(f' 試驗次數: {n_trials}')
    print()
    
    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    
    print(' 優化完成!')
    print()
    print(f' 最佳 Sharpe Score: {study.best_value:.3f}')
    print()
    print(' 最佳參數:')
    for k, v in study.best_params.items():
        print(f'   {k}: {v}')
    
    return study.best_params, study.best_value

def walk_forward_analysis(best_params, window_days=90):
    """滾動式分析 (Walk-Forward)"""
    print()
    print('='*60)
    print(' Walk-Forward 滾動驗證')
    print('='*60)
    print()
    
    periods = [
        ('2023-07-01', '2023-12-31', '2024-Q1'),
        ('2024-01-01', '2024-03-31', '2024-Q1'),
        ('2024-04-01', '2024-06-30', '2024-Q2'),
        ('2024-07-01', '2024-09-30', '2024-Q3'),
        ('2024-10-01', '2024-12-31', '2024-Q4'),
        ('2025-01-01', '2025-03-31', '2025-Q1'),
    ]
    
    results = []
    
    for train_s, train_e, train_name in periods:
        result = run_backtest(best_params, train_s, train_e)
        m = result['train']
        print(f' {train_name}: WR={m["win_rate"]:.1f}% Sharpe={m["sharpe"]:.2f} 交易={m["total"]}')
        results.append((train_name, m))
    
    # 穩定性分析
    sharpes = [r[1]['sharpe'] for r in results]
    wins = [r[1]['win_rate'] for r in results]
    
    print()
    print(f' Sharpe 平均: {np.mean(sharpes):.2f} (標準差: {np.std(sharpes):.2f})')
    print(f' 勝率 平均: {np.mean(wins):.1f}% (標準差: {np.std(wins):.1f}%)')
    
    # 是否穩定
    stable = np.std(sharpes) < 0.5 and np.mean(wins) > 45
    
    return results, stable

def main():
    print('='*60)
    print(' Nana v2.0 自動化回測與優化系統')
    print('='*60)
    print()
    
    # 1. 執行優化
    print('【第一步】Optuna 貝氏優化')
    best_params, best_score = run_optimization(n_trials=30)
    
    # 2. 滾動驗證
    print()
    print('【第二步】Walk-Forward 滾動驗證')
    wf_results, stable = walk_forward_analysis(best_params)
    
    # 3. 儲存結果
    result_data = {
        'best_params': best_params,
        'best_score': best_score,
        'wf_results': [(name, m) for name, m in wf_results],
        'stable': stable,
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M')
    }
    
    with open('Tina_Quant_System/teams/nana/optimization_result.json', 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    
    print()
    print('='*60)
    print(' 最終結論')
    print('='*60)
    print()
    
    if stable:
        print(' ✅ 系統穩定，建議採用優化後參數')
        print(f'    最佳 Sharpe: {best_score:.3f}')
        for k, v in best_params.items():
            print(f'    {k}: {v}')
    else:
        print(' ⚠️ 系統不夠穩定，維持原本參數')
    
    print()
    print('='*60)

if __name__ == '__main__':
    main()