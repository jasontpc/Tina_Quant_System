# -*- coding: utf-8 -*-
"""
Ray Backtester — 歷史回測模組
功能：抓取5年歷史數據，測試不同 DCA 策略表現，比較 Buy & Hold vs DCA
"""
import yfinance as yf
import pandas as pd
import json
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\ray')
REPORT_FILE = BASE_DIR / 'reports' / 'backtest_report.json'

ETF_NAMES = {
    '0050': '元大台灣50', '0056': '元大高股息', '00878': '國泰永續高息',
    '00919': '群益台灣精選', '00713': '元大高息低波'
}

BACKTEST_ETFS = ['0050', '0056', '00878', '00919', '00713']


def get_historical_data(etf_id, years=5):
    """抓取多年歷史數據"""
    sym = etf_id + '.TW'
    end = datetime.now()
    start = end - timedelta(days=years * 365)
    h = yf.Ticker(sym).history(start=start, end=end, auto_adjust=True)
    close = h['Close'].squeeze() if isinstance(h['Close'], pd.DataFrame) else h['Close']
    return close


def get_1y_position(close, at_date):
    """計算某日期的近1年位置"""
    date_idx = close.index.get_loc(at_date)
    start_idx = max(0, date_idx - 252)
    year_data = close.iloc[start_idx:date_idx + 1]
    if len(year_data) < 20:
        return 50.0
    low = year_data.min()
    high = year_data.max()
    price = year_data.iloc[-1]
    if high <= low:
        return 50.0
    return (price - low) / (high - low) * 100


def calc_sharpe(returns, risk_free=0.02):
    """計算 Sharpe Ratio"""
    if not returns or len(returns) < 2:
        return 0.0
    excess = [r - risk_free / 252 for r in returns]
    mean_ex = sum(excess) / len(excess)
    if mean_ex == 0:
        return 0.0
    std = (sum((x - mean_ex) ** 2 for x in excess) / len(excess)) ** 0.5
    return mean_ex / std * (252 ** 0.5) if std > 0 else 0.0


def calc_max_drawdown(prices):
    """計算最大回撤"""
    if len(prices) < 2:
        return 0.0
    peak = prices[0]
    max_dd = 0.0
    for p in prices:
        if p > peak:
            peak = p
        dd = (peak - p) / peak * 100
        if dd > max_dd:
            max_dd = dd
    return max_dd


def backtest_fixed_dca(close, monthly_amount=10000):
    """策略A：固定 DCA（每月 $10,000）"""
    trades = []
    shares = 0
    total_cost = 0.0
    prices = []
    monthly_dates = pd.date_range(start=close.index[0], end=close.index[-1], freq='MS')
    values = []
    
    for d in monthly_dates:
        if d not in close.index:
            continue
        price = close.loc[d]
        shares_bought = int(monthly_amount / price)
        shares += shares_bought
        total_cost += shares_bought * price
        trades.append({'date': d.isoformat(), 'price': float(price), 'shares': shares_bought, 'total_shares': shares, 'total_cost': float(total_cost)})
        if shares > 0:
            cur_val = shares * price
            values.append(cur_val)
            prices.append(float(price))
    
    final_price = close.iloc[-1]
    final_value = shares * final_price
    total_return = (final_value - total_cost) / total_cost * 100 if total_cost > 0 else 0
    
    # 日報酬
    daily_returns = []
    for i in range(1, len(values)):
        if values[i-1] > 0:
            daily_returns.append((values[i] - values[i-1]) / values[i-1])
    
    return {
        'strategy': 'A: 固定 DCA',
        'total_trades': len(trades),
        'total_cost': round(total_cost, 2),
        'total_shares': round(shares, 2),
        'avg_cost': round(total_cost / shares, 4) if shares > 0 else 0,
        'final_value': round(final_value, 2),
        'total_return_pct': round(total_return, 2),
        'max_drawdown_pct': round(calc_max_drawdown(values), 2),
        'sharpe_ratio': round(calc_sharpe(daily_returns), 3)
    }


def backtest_position_dca(close, monthly_amount=10000, threshold=60):
    """策略B：位置觸發 DCA（位置 < threshold% 才買）"""
    trades = []
    shares = 0
    total_cost = 0.0
    values = []
    monthly_dates = pd.date_range(start=close.index[0], end=close.index[-1], freq='MS')
    
    for d in monthly_dates:
        if d not in close.index:
            continue
        price = close.loc[d]
        position = get_1y_position(close, d)
        
        if position < threshold:
            shares_bought = int(monthly_amount / price)
        else:
            shares_bought = 0
        
        shares += shares_bought
        total_cost += shares_bought * price
        trades.append({'date': d.isoformat(), 'price': float(price), 'position_pct': round(position, 1), 'shares': shares_bought, 'total_shares': shares, 'total_cost': float(total_cost)})
        if shares > 0:
            values.append(shares * price)
    
    final_price = close.iloc[-1]
    final_value = shares * final_price
    total_return = (final_value - total_cost) / total_cost * 100 if total_cost > 0 else 0
    
    daily_returns = []
    for i in range(1, len(values)):
        if values[i-1] > 0:
            daily_returns.append((values[i] - values[i-1]) / values[i-1])
    
    return {
        'strategy': 'B: 位置觸發 DCA',
        'total_trades': len([t for t in trades if t['shares'] > 0]),
        'total_cost': round(total_cost, 2),
        'total_shares': round(shares, 2),
        'avg_cost': round(total_cost / shares, 4) if shares > 0 else 0,
        'final_value': round(final_value, 2),
        'total_return_pct': round(total_return, 2),
        'max_drawdown_pct': round(calc_max_drawdown(values), 2),
        'sharpe_ratio': round(calc_sharpe(daily_returns), 3)
    }


def backtest_buy_hold(close, initial_amount=100000):
    """策略C：Buy & Hold（一次買入）"""
    buy_price = close.iloc[0]
    shares = initial_amount / buy_price
    total_cost = initial_amount
    values = [float(close.loc[d]) * shares for d in pd.date_range(start=close.index[0], end=close.index[-1], freq='D') if d in close.index]
    
    final_price = close.iloc[-1]
    final_value = shares * final_price
    total_return = (final_value - total_cost) / total_cost * 100 if total_cost > 0 else 0
    
    daily_returns = []
    for i in range(1, len(values)):
        if values[i-1] > 0:
            daily_returns.append((values[i] - values[i-1]) / values[i-1])
    
    return {
        'strategy': 'C: Buy & Hold',
        'total_trades': 1,
        'total_cost': round(total_cost, 2),
        'total_shares': round(shares, 2),
        'avg_cost': round(buy_price, 4),
        'final_value': round(final_value, 2),
        'total_return_pct': round(total_return, 2),
        'max_drawdown_pct': round(calc_max_drawdown(values), 2),
        'sharpe_ratio': round(calc_sharpe(daily_returns), 3)
    }


def run_backtest(etf_id='0050', years=5, monthly_amount=10000, threshold=60):
    """對單一 ETF 執行回測"""
    print(f'=== Ray 歷史回測 — {ETF_NAMES.get(etf_id, etf_id)} ({etf_id}) ===')
    print(f'期間: 近 {years} 年 | 初始金額: ${monthly_amount * 12:,}/年 | DCA 閾值: {threshold}%')
    print()
    
    close = get_historical_data(etf_id, years)
    close = close.dropna()  # 清除尾部 NaN
    if len(close) < 100:
        print(f'[錯誤] {etf_id} 數據不足 ({len(close)} 筆)')
        return None
    
    print(f'數據: {close.index[0].strftime("%Y-%m-%d")} ~ {close.index[-1].strftime("%Y-%m-%d")} ({len(close)} 筆)')
    print()
    
    # 三種策略
    result_a = backtest_fixed_dca(close, monthly_amount)
    result_b = backtest_position_dca(close, monthly_amount, threshold)
    result_c = backtest_buy_hold(close, monthly_amount * 12)
    
    results = [result_a, result_b, result_c]
    
    # 比較表格
    print(f'{"策略":<20s} {"總成本":>12s} {"平均成本":>10s} {"最終價值":>12s} {"報酬%":>8s} {"最大回撒":>8s} {"Sharpe":>8s}')
    print('  ' + '-' * 85)
    for r in results:
        print(f'  {r["strategy"]:<18s} ${r["total_cost"]:>11,.0f} ${r["avg_cost"]:>9.2f} ${r["final_value"]:>11,.0f} {r["total_return_pct"]:>7.1f}% {r["max_drawdown_pct"]:>7.1f}% {r["sharpe_ratio"]:>7.3f}')
    print()
    
    # 找出最佳策略
    best = max(results, key=lambda x: x['total_return_pct'])
    print(f'  → 最佳策略: {best["strategy"]} (報酬 {best["total_return_pct"]}%)')
    print()
    
    return {
        'etf_id': etf_id,
        'name': ETF_NAMES.get(etf_id, etf_id),
        'period_start': close.index[0].isoformat(),
        'period_end': close.index[-1].isoformat(),
        'results': results,
        'best_strategy': best['strategy']
    }


def run_all_backtests():
    """對所有 ETF 執行回測"""
    print('=' * 60)
    print('Ray 全體 ETF 歷史回測')
    print('=' * 60)
    print()
    
    all_results = {}
    for etf_id in BACKTEST_ETFS:
        r = run_backtest(etf_id, years=5)
        if r:
            all_results[etf_id] = r
        print()
    
    # 總結報告
    print('=' * 60)
    print('【回測總結 — 哪種策略最適合哪種 ETF】')
    print('=' * 60)
    print()
    print(f'{"ETF":<8s} {"最佳策略":<20s} {"報酬%":>8s} {"平均成本":>10s} {"最大回撒":>8s}')
    print('  ' + '-' * 60)
    for etf_id, r in all_results.items():
        best = r['best_strategy']
        results_list = r['results']
        best_result = next((x for x in results_list if x['strategy'] == best), results_list[0])
        print(f'  {etf_id:<8s} {best:<20s} {best_result["total_return_pct"]:>7.1f}% ${best_result["avg_cost"]:>9.2f} {best_result["max_drawdown_pct"]:>7.1f}%')
    print()
    
    # 儲存報告
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f'報告已儲存到 {REPORT_FILE}')
    
    return all_results


if __name__ == '__main__':
    etf_id = sys.argv[1] if len(sys.argv) > 1 else '0050'
    if etf_id == 'all':
        run_all_backtests()
    else:
        run_backtest(etf_id)
