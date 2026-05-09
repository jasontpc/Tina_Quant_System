# -*- coding: utf-8 -*-
"""
Ray DCA Optimizer — DCA 參數優化引擎
功能：
  - 根據歷史數據回測不同 DCA 參數組合
  - 找出每檔 ETF 的最佳 DCA 策略

分析維度：
  - 買入頻率：每月/每週/每季
  - 買入金額：固定金額/動態金額
  - 持有期間：1年/3年/5年

用法:
  python scripts/ray_dca_optimizer.py 0050
  python scripts/ray_dca_optimizer.py 0050 --frequency monthly --years 5
  python scripts/ray_dca_optimizer.py --all
"""
import yfinance as yf
import pandas as pd
import numpy as np
import sys
import os
import json
from datetime import datetime, timedelta
from itertools import product

# Dynamic path setup
_ScriptDir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ScriptDir not in sys.path:
    sys.path.insert(0, _ScriptDir)

sys.stdout.reconfigure(encoding='utf-8')

ETF_NAMES = {
    '0050': '元大台灣50', '0056': '元大高股息', '00878': '國泰永續高息',
    '00919': '群益台灣精選', '00713': '元大高息低波', '00646': '富邦S&P500',
    '00662': '富邦NASDAQ', '00757': '統一大FANG+'
}

REPORTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'reports')


def get_historical_prices(etf_id, years=5):
    """抓取多年歷史價格"""
    sym = etf_id + '.TW'
    h = yf.Ticker(sym).history(period=f'{years}y')
    close = h['Close'].squeeze() if isinstance(h['Close'], pd.DataFrame) else h['Close']
    return close


def dca_backtest(close, frequency='monthly', amount=5000, start_idx=None, end_idx=None):
    """
    DCA 回測

    參數:
      close: pandas Series 價格資料
      frequency: 'monthly' | 'weekly' | 'quarterly'
      amount: 每次買入金額
      start_idx, end_idx: 回測區間

    返回: dict 含各項指標
    """
    prices = close.copy()
    if end_idx is None:
        end_idx = len(prices) - 1
    if start_idx is None:
        # 預設從資料的 1/3 處開始（留足夠歷史算指標）
        start_idx = max(252, len(prices) // 3)

    # 切片為回測區間
    prices = prices.iloc[start_idx:end_idx + 1].reset_index(drop=True)
    if len(prices) < 60:
        return None

    # 頻率設定
    if frequency == 'monthly':
        day_interval = 21
    elif frequency == 'weekly':
        day_interval = 5
    elif frequency == 'quarterly':
        day_interval = 63
    else:
        day_interval = 21

    # 模擬 DCA
    total_cost = 0.0
    total_units = 0.0
    trades = []
    cumulative_units = 0.0
    portfolio_values = []

    for i in range(0, len(prices) - 1, day_interval):
        price = float(prices.iloc[i])
        if price <= 0:
            continue
        units = amount / price
        total_units += units
        total_cost += amount
        cumulative_units = total_units
        trades.append({
            'date': f'trade_{i}',
            'price': price,
            'amount': amount,
            'units': units
        })
        idx_in_slice = min(i, len(prices) - 1)
        pv = cumulative_units * float(prices.iloc[idx_in_slice])
        portfolio_values.append(pv)

    if total_units == 0:
        return None

    # 最終價值
    final_price = float(prices.iloc[-1])
    final_value = total_units * final_price
    total_return = final_value - total_cost
    total_return_pct = (total_return / total_cost) * 100 if total_cost > 0 else 0

    # 年化報酬
    years_held = len(trades) * day_interval / 252
    annualized_return = ((final_value / total_cost) ** (1 / max(years_held, 0.1)) - 1) * 100

    # 平均成本
    avg_cost = total_cost / total_units if total_units > 0 else 0

    # 最大回撤
    max_drawdown = 0.0
    peak = 0.0
    for pv in portfolio_values:
        if pv > peak:
            peak = pv
        dd = (peak - pv) / peak * 100 if peak > 0 else 0
        if dd > max_drawdown:
            max_drawdown = dd

    # Sharpe Ratio
    returns_series = pd.Series(portfolio_values).pct_change().dropna()
    if len(returns_series) > 5 and returns_series.std() > 0:
        sharpe = (annualized_return / 100) / (returns_series.std() * np.sqrt(252)) if returns_series.std() > 0 else 0
    else:
        sharpe = 0

    return {
        'total_cost': round(total_cost, 0),
        'total_units': round(total_units, 2),
        'final_value': round(final_value, 0),
        'total_return': round(total_return, 0),
        'total_return_pct': round(total_return_pct, 2),
        'annualized_return': round(annualized_return, 2),
        'avg_cost': round(avg_cost, 2),
        'max_drawdown_pct': round(max_drawdown, 2),
        'sharpe_ratio': round(sharpe, 2),
        'trade_count': len(trades),
        'frequency': frequency,
        'amount': amount
    }


def optimize_frequency(close, amount=5000):
    """比較不同頻率"""
    frequencies = ['monthly', 'weekly', 'quarterly']
    results = {}

    for freq in frequencies:
        r = dca_backtest(close, frequency=freq, amount=amount)
        if r:
            results[freq] = r

    return results


def optimize_amount(close, frequency='monthly'):
    """比較不同買入金額"""
    amounts = [3000, 5000, 10000, 15000]
    results = {}

    for amt in amounts:
        r = dca_backtest(close, frequency=frequency, amount=amt)
        if r:
            results[amt] = r

    return results


def find_best_params(etf_id, years=5, amount=5000, verbose=True):
    """找出最佳參數組合"""
    name = ETF_NAMES.get(etf_id, etf_id)

    if verbose:
        print()
        print(f'{"="*60}')
        print(f'  DCA 參數優化 — {name} ({etf_id})')
        print(f'  回測期間: 近 {years} 年')
        print(f'{"="*60}')

    # 取得價格資料
    close = get_historical_prices(etf_id, years=years)
    if len(close) < 252:
        print(f'  [錯誤] 資料不足，無法回測')
        return None

    # 1. 頻率優化
    if verbose:
        print()
        print('  【頻率比較】')
    freq_results = optimize_frequency(close, amount=amount)

    best_freq = None
    best_freq_return = -999
    for freq, r in freq_results.items():
        if verbose:
            print(f'    {freq:<8s} 總報酬: {r["total_return_pct"]:>6.2f}% | 年化: {r["annualized_return"]:>5.2f}% | 最大回撤: {r["max_drawdown_pct"]:>5.2f}% | Sharpe: {r["sharpe_ratio"]:>5.2f}')
        if r['total_return_pct'] > best_freq_return:
            best_freq_return = r['total_return_pct']
            best_freq = freq

    # 2. 金額優化
    if verbose:
        print()
        print('  【金額比較】')
    amt_results = optimize_amount(close, frequency='monthly')

    best_amt = None
    best_amt_return = -999
    for amt, r in amt_results.items():
        if verbose:
            print(f'    ${amt:<5,} 總報酬: {r["total_return_pct"]:>6.2f}% | 年化: {r["annualized_return"]:>5.2f}% | 最大回撤: {r["max_drawdown_pct"]:>5.2f}% | Sharpe: {r["sharpe_ratio"]:>5.2f}')
        if r['total_return_pct'] > best_amt_return:
            best_amt_return = r['total_return_pct']
            best_amt = amt

    # 3. 持有期間分析
    if verbose:
        print()
        print('  【持有期間分析】')

    period_results = {}
    for yrs in [1, 3, 5]:
        r = dca_backtest(close, frequency='monthly', amount=amount)
        if r:
            period_results[yrs] = r
            if verbose:
                print(f'    {yrs}年  總報酬: {r["total_return_pct"]:>6.2f}% | 年化: {r["annualized_return"]:>5.2f}% | Sharpe: {r["sharpe_ratio"]:>5.2f}')

    # 整理最佳參數
    best = {
        'etf_id': etf_id,
        'name': name,
        'best_frequency': best_freq,
        'best_amount': best_amt,
        'frequency_results': freq_results,
        'amount_results': amt_results,
        'period_results': period_results,
        'optimization_date': datetime.now().strftime('%Y-%m-%d')
    }

    if verbose:
        print()
        print(f'  【最佳參數】')
        print(f'    頻率: {best_freq}')
        print(f'    金額: ${best_amt:,}/次')

        # 最終 Best 配置回測
        best_result = dca_backtest(close, frequency=best_freq, amount=best_amt)
        if best_result:
            print()
            print(f'  【最佳配置回測結果】')
            print(f'    總成本: ${best_result["total_cost"]:,.0f}')
            print(f'    最終價值: ${best_result["final_value"]:,.0f}')
            print(f'    總報酬: {best_result["total_return_pct"]:+.2f}% ({best_result["total_return"]:,.0f})')
            print(f'    年化報酬: {best_result["annualized_return"]:+.2f}%')
            print(f'    平均成本: ${best_result["avg_cost"]:.2f}')
            print(f'    最大回撤: {best_result["max_drawdown_pct"]:.2f}%')
            print(f'    Sharpe: {best_result["sharpe_ratio"]:.2f}')

        print()
        print(f'{"="*60}')

    return best


def run_all_optimization(core_etfs=None):
    """對所有核心 ETF 執行優化"""
    if core_etfs is None:
        core_etfs = ['0050', '0056', '00878', '00919', '00713', '00646']

    print()
    print('=' * 60)
    print('  Ray DCA 全市場參數優化')
    print(f'  時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print('=' * 60)

    all_results = []
    for etf_id in core_etfs:
        try:
            result = find_best_params(etf_id, years=5, verbose=True)
            if result:
                all_results.append(result)
        except Exception as e:
            print(f'  {etf_id}: 優化失敗 ({e})')

    # 儲存
    os.makedirs(REPORTS_DIR, exist_ok=True)
    report_file = os.path.join(REPORTS_DIR, 'dca_optimizer_results.json')
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            'date': datetime.now().strftime('%Y-%m-%d'),
            'results': all_results
        }, f, ensure_ascii=False, indent=2)

    print()
    print(f'  ✅ 全部優化完成，報告已儲存: {report_file}')

    # 摘要排名
    print()
    print('【總報酬排名（5年月 DCA）】')
    print(f'  {"ETF":<8s} {"頻率":<8s} {"金額":>6s} {"總報酬":>8s} {"年化":>8s} {"Sharpe":>6s}')
    print(f'  {"-"*8} {"-"*8} {"-"*6} {"-"*8} {"-"*8} {"-"*6}')

    ranking = []
    for r in all_results:
        fr = r.get('frequency_results', {}).get('monthly', {})
        ranking.append({
            'etf_id': r['etf_id'],
            'name': r['name'],
            'total_return_pct': fr.get('total_return_pct', 0),
            'annualized': fr.get('annualized_return', 0),
            'sharpe': fr.get('sharpe_ratio', 0)
        })

    ranking.sort(key=lambda x: x['total_return_pct'], reverse=True)
    for item in ranking:
        print(f"  {item['etf_id']:<8s} monthly   ${5000:<5,} {item['total_return_pct']:>7.2f}% {item['annualized']:>7.2f}% {item['sharpe']:>6.2f}")

    print('=' * 60)
    return all_results


if __name__ == '__main__':
    if '--all' in sys.argv:
        run_all_optimization()
    elif len(sys.argv) > 1:
        etf_id = sys.argv[1]
        find_best_params(etf_id)
    else:
        run_all_optimization(['0050', '00646', '00878', '00919'])