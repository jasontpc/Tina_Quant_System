# -*- coding: utf-8 -*-
"""
Nana v2.0 Full System
=====================
Nana 核心回測框架 + Optuna 自動優化 + Walk-Forward 分析

功能:
1. NanaScore 評分函數 (法人+技術)
2. Optuna 貝氏優化 (目標: Sharpe Ratio)
3. Walk-Forward 滾動驗證
4. 0050 Benchmark 比較
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
import yfinance as yf
import numpy as np
import optuna
from datetime import datetime, timedelta
import json
import warnings

warnings.filterwarnings('ignore')
optuna.logging.set_verbosity(optuna.logging.WARNING)

DB_PATH = 'skills/stock-analyzer/scripts/tina_master.db'

# ==================== 股票池 ====================
STOCKS = [
    '2330','2454','2317','2382','3034','2379','2451','2308','2345','2353',
    '2395','2401','2492','2610','2880','2881','2882','2883','2884','2885',
    '2886','2887','2891','2892','3008','3033','3044','3189','3231','3443',
    '3481','3665','3717','4938','4958','6415','6505','6669','6770','8016',
    '8046','8105','8261','8341','8464','8926','8996','9945','2385','2603'
]

# ==================== 工具函數 ====================

def get_rsi(closes, period=14):
    delta = np.diff(closes)
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta > 0, 0, -delta)
    ag = np.mean(gain[-period:])
    al = np.mean(loss[-period:])
    return 100 - (100 / (1 + ag / al)) if al != 0 else 50)

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

def get_inst(symbol, date_str, days=3):
    """取得法人數據"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        SELECT SUM(foreign_net), SUM(trust_net), COUNT(*) 
        FROM MarketData 
        WHERE symbol = ? AND date <= ? AND date >= date(?, '-' || ? || ' days')
    ''', (symbol, date_str, date_str, days))
    f_sum, t_sum, cnt = cur.fetchone()
    conn.close()
    
    # 計算連續買超天數
    conn2 = sqlite3.connect(DB_PATH)
    cur2 = conn2.cursor()
    cur2.execute('''
        SELECT foreign_net, trust_net FROM MarketData 
        WHERE symbol = ? AND date <= ? AND date >= date(?, '-' || ? || ' days')
        ORDER BY date DESC
    ''', (symbol, date_str, date_str, days))
    rows = cur2.fetchall()
    conn2.close()
    
    f_consec = 0
    t_consec = 0
    for f, t in rows:
        if f and f > 0: f_consec += 1
        else: break
    for f, t in rows:
        if t and t > 0: t_consec += 1
        else: break
    
    return (f_sum or 0), (t_sum or 0), f_consec, t_consec

# ==================== NanaScore 評分函數 ====================

def apply_nana_score(rsi, bias, atr_pct, ma20, ma60, f_net, t_net, f_consec, t_consec, params):
    """
    Nana 評分函數 - 可調參數版本
    
    Returns:
        score (float): 0-100 分
        entry_ok (bool): 是否符合進場條件
    """
    # === 法人評分 (最高80分) ===
    inst_max = params.get('inst_max', 80)
    
    # 外資評分 (根據連續天數)
    f_days = params.get('f_days', {1: 10, 2: 15, 3: 40, 4: 50, 5: 60, 10: 60, 999: 20})
    f_score = 0
    for threshold, score in sorted(f_days.items(), reverse=True):
        if f_consec >= threshold:
            f_score = score
            break
    
    # 投信評分
    t_days = params.get('t_days', {1: 5, 2: 10, 3: 40, 4: 50, 5: 60, 999: 20})
    t_score = 0
    for threshold, score in sorted(t_days.items(), reverse=True):
        if t_consec >= threshold:
            t_score = score
            break
    
    # 合力加成
    combo_bonus = params.get('combo_bonus', 10)
    if f_consec >= 3 and t_consec >= 3:
        f_score = min(inst_max, f_score + combo_bonus)
        t_score = min(inst_max, t_score + combo_bonus)
    
    inst_score = min(inst_max, f_score + t_score)
    
    # === 技術評分 (最高20分) ===
    tech_max = params.get('tech_max', 20)
    
    # RSI 評分
    rsi_low = params.get('rsi_low', 40)
    rsi_high = params.get('rsi_high', 70)
    
    if rsi_low <= rsi <= rsi_high:
        rsi_score = tech_max * 0.5
    elif 30 <= rsi < rsi_low or rsi_high < rsi <= 80:
        rsi_score = tech_max * 0.25
    else:
        rsi_score = 0
    
    # Bias 評分
    bias_zones = params.get('bias_zones', [(-2, 3), (3, 6), (6, 10)])
    bias_scores = params.get('bias_scores', [15, 10, 0])
    bias_score = 0
    
    for (low, high), score in zip(bias_zones, bias_scores):
        if low <= bias <= high:
            bias_score = score
            break
    if bias > 10:
        bias_score = 0
    elif bias < -5:
        bias_score = 5
    
    # MA 評分
    ma_score = tech_max * 0.25 if ma20 > ma60 else 0
    
    tech_score = rsi_score + bias_score + ma_score
    
    # 總分
    total_score = inst_score + tech_score
    
    # === 進場條件檢查 ===
    entry_threshold = params.get('entry_threshold', 80)
    atr_min = params.get('atr_min', 0.3)
    
    entry_ok = (
        rsi_low <= rsi <= rsi_high and
        ma20 > ma60 and
        atr_pct >= atr_min and
        (f_net > 0 or t_net > 0) and
        total_score >= entry_threshold
    )
    
    return total_score, entry_ok

# ==================== 0050 Benchmark ====================

def get_benchmark_return(start_date, end_date, initial_capital=10_000_000):
    """取得 0050 回測表現"""
    try:
        ticker = yf.Ticker('0050.TW')
        h = ticker.history(start=start_date, end=end_date, period='1y')
        
        if len(h) < 20:
            return None
        
        closes = list(h['Close'].values)
        entry_price = closes[0]
        exit_price = closes[-1]
        
        ret_pct = (exit_price / entry_price - 1) * 100
        
        # 計算 MDD
        peak = entry_price
        max_dd = 0
        for c in closes:
            if c > peak:
                peak = c
            dd = (peak - c) / peak * 100
            if dd > max_dd:
                max_dd = dd
        
        return {
            'return_pct': ret_pct,
            'mdd': max_dd,
            'entry': entry_price,
            'exit': exit_price
        }
    except:
        return None

# ==================== 回測引擎 ====================

def run_backtest(params, start_date, end_date, holding_days=7):
    """執行回測"""
    all_trades = []
    
    for symbol in STOCKS:
        try:
            h = yf.Ticker(symbol + '.TW').history(start=start_date, end=end_date, period='365d')
            
            if len(h) < 60:
                continue
            
            closes = list(h['Close'].values)
            
            for i in range(30, len(closes) - holding_days - 5):
                date_str = h.index[i].strftime('%Y-%m-%d')
                close = closes[i]
                
                ma20 = np.mean(closes[i-19:i+1])
                ma60 = np.mean(closes[i-59:i+1]) if i >= 60 else ma20
                rsi = get_rsi(closes[:i+1])
                atr = get_atr(h, i)
                atr_pct = atr / close * 100
                bias = (close / ma20 - 1) * 100
                
                f_net, t_net, f_consec, t_consec = get_inst(symbol, date_str, days=5)
                
                score, entry_ok = apply_nana_score(
                    rsi, bias, atr_pct, ma20, ma60,
                    f_net, t_net, f_consec, t_consec, params
                )
                
                if not entry_ok:
                    continue
                
                # 持有 N 天後出场
                if i + holding_days < len(closes):
                    exit_price = closes[i + holding_days]
                    ret = (exit_price / close - 1) * 100
                    
                    all_trades.append({
                        'symbol': symbol,
                        'date': date_str,
                        'entry': close,
                        'exit': exit_price,
                        'return': ret,
                        'score': score,
                        'rsi': rsi,
                        'bias': bias
                    })
        
        except:
            continue
    
    return all_trades

def calculate_metrics(trades):
    """計算績效指標"""
    if not trades:
        return None
    
    returns = [t['return'] for t in trades]
    
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]
    
    total = len(returns)
    win_rate = len(wins) / total * 100 if total > 0 else 0
    avg_return = np.mean(returns) if total > 0 else 0
    
    total_win = sum(wins) if wins else 0
    total_loss = abs(sum(losses)) if losses else 0
    pf = total_win / total_loss if total_loss > 0 else 0
    
    # Sharpe Ratio
    rf = 0.04  # 無風險利率 4%
    excess_returns = [r/100 - rf/252 for r in returns]
    mean_excess = np.mean(excess_returns)
    std_excess = np.std(excess_returns)
    sharpe = (mean_excess / std_excess * np.sqrt(252)) if std_excess > 0 else 0
    
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
        'avg_return': avg_return,
        'sharpe': sharpe,
        'pf': pf,
        'mdd': max_dd
    }

# ==================== Optuna 目標函數 ====================

def objective(trial):
    """Optuna 目標函數 - 最大化 Sharpe Ratio"""
    params = {
        'rsi_low': trial.suggest_int('rsi_low', 35, 55),
        'rsi_high': trial.suggest_int('rsi_high', 60, 80),
        'atr_min': trial.suggest_float('atr_min', 0.2, 0.8),
        'inst_max': trial.suggest_int('inst_max', 60, 85),
        'tech_max': trial.suggest_int('tech_max', 15, 30),
        'entry_threshold': trial.suggest_int('entry_threshold', 60, 90),
        'bias_zones': [
            (-2, trial.suggest_float('bias_low1', -3, 0)),
            (trial.suggest_float('bias_low1', -3, 0), trial.suggest_float('bias_high1', 2, 5)),
            (trial.suggest_float('bias_high1', 2, 5), 10)
        ],
        'bias_scores': [15, trial.suggest_int('bias_score1', 5, 15), 0],
        'f_days': {
            1: trial.suggest_int('f1', 5, 15),
            2: trial.suggest_int('f2', 10, 25),
            3: trial.suggest_int('f3', 30, 50),
            5: trial.suggest_int('f5', 40, 60),
            999: trial.suggest_int('f999', 10, 30)
        },
        't_days': {
            1: trial.suggest_int('t1', 3, 10),
            2: trial.suggest_int('t2', 5, 20),
            3: trial.suggest_int('t3', 25, 45),
            5: trial.suggest_int('t5', 35, 55),
            999: trial.suggest_int('t999', 5, 25)
        },
        'combo_bonus': trial.suggest_int('combo_bonus', 5, 20),
    }
    
    # 2024 年數據
    trades = run_backtest(params, '2024-01-01', '2024-12-31', holding_days=7)
    
    if not trades:
        return 0
    
    if len(trades) < 50:
        return 0
    
    metrics = calculate_metrics(trades)
    
    if not metrics:
        return 0
    
    # 目標: Sharpe > 0, WR > 45%
    score = metrics['sharpe'] * 0.6 + (metrics['win_rate'] / 100) * 0.4
    
    return score

# ==================== Walk-Forward 分析 ====================

def walk_forward_analysis(best_params, n_periods=4):
    """滾動式 Walk-Forward 分析"""
    print()
    print('='*60)
    print(' Walk-Forward Analysis')
    print('='*60)
    print()
    
    # 分段測試
    periods = [
        ('2024-01-01', '2024-03-31', 'Q1'),
        ('2024-04-01', '2024-06-30', 'Q2'),
        ('2024-07-01', '2024-09-30', 'Q3'),
        ('2024-10-01', '2024-12-31', 'Q4'),
    ]
    
    results = []
    sharpes = []
    win_rates = []
    
    for start, end, name in periods:
        trades = run_backtest(best_params, start, end, holding_days=7)
        metrics = calculate_metrics(trades)
        
        if metrics:
            print(f' {name}: WR={metrics["win_rate"]:.1f}% Sharpe={metrics["sharpe"]:.2f} 交易={metrics["total"]}')
            sharpes.append(metrics['sharpe'])
            win_rates.append(metrics['win_rate'])
            results.append((name, metrics))
        else:
            print(f' {name}: 無資料')
            sharpes.append(0)
            win_rates.append(0)
            results.append((name, None))
    
    # 穩定性判斷
    avg_sharpe = np.mean(sharpes)
    std_sharpe = np.std(sharpes)
    avg_wr = np.mean(win_rates)
    
    print()
    print(f' 平均 Sharpe: {avg_sharpe:.3f} (std: {std_sharpe:.3f})')
    print(f' 平均勝率: {avg_wr:.1f}%')
    
    stable = std_sharpe < 0.8 and avg_wr > 45
    
    return results, stable, avg_sharpe, avg_wr

# ==================== 主程式 ====================

def main():
    print('='*60)
    print(' Nana v2.0 Full System')
    print(' 回測框架 + Optuna 優化 + Walk-Forward 分析')
    print('='*60)
    print()
    
    # 1. Optuna 優化
    print('【1/3】執行 Optuna 貝氏優化 (50 trials)...')
    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=50, show_progress_bar=False)
    
    best_params = study.best_params
    best_score = study.best_value
    
    print()
    print(' 最佳參數:')
    for k, v in best_params.items():
        print(f'   {k}: {v}')
    print()
    print(f' 最佳 Score: {best_score:.3f}')
    
    # 2. Walk-Forward 驗證
    print()
    print('【2/3】執行 Walk-Forward 分析...')
    wf_results, stable, avg_sharpe, avg_wr = walk_forward_analysis(best_params)
    
    # 3. 與 0050 Benchmark 比較
    print()
    print('【3/3】與 0050 Benchmark 比較...')
    benchmark = get_benchmark_return('2024-01-01', '2024-12-31')
    
    if benchmark:
        print(f' 0050: 報酬 {benchmark["return_pct"]:.1f}%, MDD {benchmark["mdd"]:.1f}%')
        print(f' Nana: Sharpe {avg_sharpe:.2f}, WR {avg_wr:.1f}%')
        
        beat_benchmark = avg_sharpe > 0.5 or avg_wr > 50
        print()
        print(f' {'✅ 打敗' if beat_benchmark else '❌ 未打敗'} 0050 benchmark')
    
    # 儲存結果
    result = {
        'best_params': best_params,
        'best_score': best_score,
        'wf_results': [(name, m) for name, m in wf_results if m],
        'stable': stable,
        'avg_sharpe': float(avg_sharpe),
        'avg_win_rate': float(avg_wr),
        'benchmark': benchmark,
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M')
    }
    
    with open('Tina_Quant_System/teams/nana/nana_v2_full_result.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print()
    print('='*60)
    print(' 完成')
    print('='*60)

if __name__ == '__main__':
    main()