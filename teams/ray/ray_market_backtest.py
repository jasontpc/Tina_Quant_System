"""
Ray 歷史大盤回測模組 - TWII DCA 策略回測
=========================================
功能：
  - 抓取台股大盤 (^TWII) 歷史數據
  - 模擬不同 DCA 策略表現
  - 比較固定日期 DCA vs 價格觸發 DCA vs Buy&Hold
  - 生成視覺化報告

Author: Ray Team
Date: 2026-04-24
"""

import json
import math
import os
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

# ======================
# 絕對路徑設定
# ======================
BASE_DIR = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\ray")
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# ======================
# 回測時間區間
# ======================
PERIODS = {
    "2019-2020": ("2019-01-01", "2020-12-31"),
    "2020-2021": ("2020-01-01", "2021-12-31"),
    "2022-2023": ("2022-01-01", "2023-12-31"),
    "2023-2024": ("2023-01-01", "2024-12-31"),
    "2024-2026": ("2024-01-01", "2026-03-31"),
    "2019-2026": ("2019-01-01", "2026-03-31"),
}

# ======================
# 策略定義
# ======================
STRATEGIES = [
    "fixed_date_dca",      # 每月固定日期（1號）買
    "price_triggered_dca", # 價格低於均線10%時買
    "monthly_dca",         # 每月一次（15號）
    "weekly_dca",          # 每週一次
    "buy_and_hold",        # 買入持有
]

# ======================
# 工具函數
# ======================

def get_twii_data(start: str, end: str):
    """抓取 TWII 歷史數據"""
    ticker = yf.Ticker("^TWII")
    df = ticker.history(start=start, end=end, interval="1d")
    if df.empty:
        print(f"[警告] ^TWII 無資料 ({start} ~ {end})")
        return None
    df = df.reset_index()
    df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
    return df

def calc_max_drawdown(cumulative_returns: np.ndarray) -> float:
    """計算最大回撤"""
    peak = np.maximum.accumulate(cumulative_returns)
    drawdown = (cumulative_returns - peak) / peak
    return float(np.min(drawdown))

def calc_sharpe_ratio(returns: np.ndarray, risk_free_rate: float = 0.01) -> float:
    """計算 Sharpe Ratio（年化）"""
    if len(returns) == 0 or np.std(returns) == 0:
        return 0.0
    mean_ret = np.mean(returns)
    std_ret = np.std(returns)
    return float((mean_ret - risk_free_rate / 252) / std_ret * math.sqrt(252))

def calc_volatility(returns: np.ndarray) -> float:
    """計算波動度（年化標準差）"""
    if len(returns) == 0:
        return 0.0
    return float(np.std(returns) * math.sqrt(252))

def get_trading_days(df) -> list:
    """取得所有交易日"""
    return df['Date'].tolist()

def get_monthly_dates(start: str, end: str, day: int = 1) -> list:
    """取得每月的指定日期"""
    dates = []
    current = datetime.strptime(start, "%Y-%m-%d")
    end_dt = datetime.strptime(end, "%Y-%m-%d")
    while current <= end_dt:
        try:
            date_str = current.strftime("%Y-%m-%d")
            dates.append(date_str)
        except:
            pass
        # 下個月的同日
        month = current.month + 1
        year = current.year
        if month > 12:
            month = 1
            year += 1
        # 處理該月沒有31號的情況
        try:
            current = datetime(year, month, day)
        except:
            # 該月沒有此日期，往後找
            day_to_use = min(day, 28)
            current = datetime(year, month, day_to_use)
    return dates

def get_weekly_dates(start: str, end: str, weekday: int = 0) -> list:
    """取得每週的指定星期幾 (0=Monday)"""
    dates = []
    current = datetime.strptime(start, "%Y-%m-%d")
    end_dt = datetime.strptime(end, "%Y-%m-%d")
    # 找到第一個目標星期
    days_ahead = weekday - current.weekday()
    if days_ahead < 0:
        days_ahead += 7
    current += timedelta(days=days_ahead)
    while current <= end_dt:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(weeks=1)
    return dates

# ======================
# 策略模擬器
# ======================

def simulate_fixed_date_dca(df, dates: list) -> dict:
    """固定日期 DCA 策略"""
    date_set = set(dates)
    records = []
    total_cost = 0
    total_units = 0

    for _, row in df.iterrows():
        date = row['Date']
        price = row['Close']
        if date in date_set and price > 0:
            amount = 10000  # 每次投入 1 萬
            units = amount / price
            total_cost += amount
            total_units += units
            records.append({
                'date': date,
                'price': price,
                'units': units,
                'cost': amount,
                'value': total_units * price,
            })

    if total_units == 0:
        return {'return_pct': 0, 'sharpe': 0, 'max_dd': 0, 'volatility': 0, 'avg_cost': 0}

    final_price = df.iloc[-1]['Close']
    final_value = total_units * final_price
    total_return = (final_value - total_cost) / total_cost

    # 計算過程指標
    values = [r['value'] for r in records]
    returns_list = []
    for i in range(1, len(values)):
        if values[i-1] > 0:
            returns_list.append((values[i] - values[i-1]) / values[i-1])

    return {
        'return_pct': float(total_return * 100),
        'sharpe': calc_sharpe_ratio(np.array(returns_list)),
        'max_dd': calc_max_drawdown(np.array(values)),
        'volatility': calc_volatility(np.array(returns_list)),
        'avg_cost': float(total_cost / total_units) if total_units > 0 else 0,
        'records': records,
        'total_cost': total_cost,
        'total_units': total_units,
        'final_value': final_value,
    }

def simulate_price_triggered_dca(df, threshold_pct: float = 0.10) -> dict:
    """價格觸發 DCA - 低於均線時買入"""
    df = df.copy()
    df['MA20'] = df['Close'].rolling(window=20).mean()

    records = []
    total_cost = 0
    total_units = 0

    for _, row in df.iterrows():
        if pd.isna(row['MA20']):
            continue
        price = row['Close']
        ma = row['MA20']
        if price < ma * (1 - threshold_pct) and price > 0:
            amount = 10000
            units = amount / price
            total_cost += amount
            total_units += units
            records.append({
                'date': row['Date'],
                'price': price,
                'units': units,
                'cost': amount,
                'trigger': 'below_MA',
                'value': total_units * price,
            })

    if total_units == 0:
        return {'return_pct': 0, 'sharpe': 0, 'max_dd': 0, 'volatility': 0, 'avg_cost': 0}

    final_price = df.iloc[-1]['Close']
    final_value = total_units * final_price
    total_return = (final_value - total_cost) / total_cost

    values = [r['value'] for r in records]
    returns_list = [(values[i] - values[i-1]) / values[i-1] for i in range(1, len(values)) if values[i-1] > 0]

    return {
        'return_pct': float(total_return * 100),
        'sharpe': calc_sharpe_ratio(np.array(returns_list)),
        'max_dd': calc_max_drawdown(np.array(values)),
        'volatility': calc_volatility(np.array(returns_list)),
        'avg_cost': float(total_cost / total_units),
        'records': records,
        'total_cost': total_cost,
        'total_units': total_units,
        'final_value': final_value,
    }

def simulate_monthly_dca(df, day: int = 15) -> dict:
    """每月一次 DCA"""
    dates = []
    for _, row in df.iterrows():
        d = datetime.strptime(row['Date'], "%Y-%m-%d")
        if d.day == day:
            dates.append(row['Date'])
    return simulate_fixed_date_dca(df, dates)

def simulate_weekly_dca(df, weekday: int = 0) -> dict:
    """每週一次 DCA (0=Monday)"""
    dates = []
    seen = set()
    for _, row in df.iterrows():
        d = datetime.strptime(row['Date'], "%Y-%m-%d")
        # 取得週一
        monday = d - timedelta(days=d.weekday())
        monday_str = monday.strftime("%Y-%m-%d")
        if monday_str not in seen:
            seen.add(monday_str)
            dates.append(monday_str)
    return simulate_fixed_date_dca(df, dates)

def simulate_buy_and_hold(df) -> dict:
    """Buy & Hold 策略"""
    first_price = df.iloc[0]['Close']
    last_price = df.iloc[-1]['Close']
    # 假設一開始投入 100000
    initial = 100000
    units = initial / first_price
    final_value = units * last_price
    total_return = (final_value - initial) / initial

    # 計算每日收益率
    prices = df['Close'].values
    daily_returns = np.diff(prices) / prices[:-1]

    return {
        'return_pct': float(total_return * 100),
        'sharpe': calc_sharpe_ratio(daily_returns),
        'max_dd': calc_max_drawdown(np.cumsum(daily_returns + 1)),
        'volatility': calc_volatility(daily_returns),
        'avg_cost': float(first_price),
        'total_cost': initial,
        'total_units': units,
        'final_value': final_value,
    }

# ======================
# 主回測引擎
# ======================

def run_backtest(period_name: str, start: str, end: str) -> dict:
    """執行單一時間區間的回測"""
    print(f"\n{'='*60}")
    print(f"回測區間: {period_name} ({start} ~ {end})")
    print(f"{'='*60}")

    df = get_twii_data(start, end)
    if df is None or len(df) < 60:
        print(f"[錯誤] 資料不足，跳過 {period_name}")
        return {}

    twii_start = round(float(df.iloc[0]['Close']), 2)
    twii_end = round(float(df.iloc[-1]['Close']), 2)

    results = {
        'period': period_name,
        'start': start,
        'end': end,
        'twii_start': twii_start,
        'twii_end': twii_end,
        'twii_return': round((twii_end - twii_start) / twii_start * 100, 2),
        'strategies': {},
    }

    print(f"TWII: {twii_start} → {twii_end} ({results['twii_return']:+.2f}%)")

    # 1. 固定日期 DCA (每月1號)
    fixed_dates = get_monthly_dates(start, end, day=1)
    res = simulate_fixed_date_dca(df, fixed_dates)
    results['strategies']['fixed_date_dca'] = {
        'return': f"{res['return_pct']:+.2f}%",
        'sharpe': round(res['sharpe'], 2),
        'max_drawdown': f"{res['max_dd']*100:.2f}%",
        'volatility': f"{res['volatility']*100:.2f}%",
        'avg_cost': round(res['avg_cost'], 2),
        'trades': len(res.get('records', [])),
        'final_value': round(res.get('final_value', 0), 0),
    }
    print(f"  固定日期DCA: {res['return_pct']:+.2f}% | Sharpe: {res['sharpe']:.2f}")

    # 2. 價格觸發 DCA
    res = simulate_price_triggered_dca(df)
    results['strategies']['price_triggered_dca'] = {
        'return': f"{res['return_pct']:+.2f}%",
        'sharpe': round(res['sharpe'], 2),
        'max_drawdown': f"{res['max_dd']*100:.2f}%",
        'volatility': f"{res['volatility']*100:.2f}%",
        'avg_cost': round(res['avg_cost'], 2),
        'trades': len(res.get('records', [])),
        'final_value': round(res.get('final_value', 0), 0),
    }
    print(f"  價格觸發DCA: {res['return_pct']:+.2f}% | Sharpe: {res['sharpe']:.2f}")

    # 3. 每月 DCA (15號)
    res = simulate_monthly_dca(df, day=15)
    results['strategies']['monthly_dca'] = {
        'return': f"{res['return_pct']:+.2f}%",
        'sharpe': round(res['sharpe'], 2),
        'max_drawdown': f"{res['max_dd']*100:.2f}%",
        'volatility': f"{res['volatility']*100:.2f}%",
        'avg_cost': round(res['avg_cost'], 2),
        'trades': len(res.get('records', [])),
        'final_value': round(res.get('final_value', 0), 0),
    }
    print(f"  每月DCA:     {res['return_pct']:+.2f}% | Sharpe: {res['sharpe']:.2f}")

    # 4. 每週 DCA
    res = simulate_weekly_dca(df)
    results['strategies']['weekly_dca'] = {
        'return': f"{res['return_pct']:+.2f}%",
        'sharpe': round(res['sharpe'], 2),
        'max_drawdown': f"{res['max_dd']*100:.2f}%",
        'volatility': f"{res['volatility']*100:.2f}%",
        'avg_cost': round(res['avg_cost'], 2),
        'trades': len(res.get('records', [])),
        'final_value': round(res.get('final_value', 0), 0),
    }
    print(f"  每週DCA:     {res['return_pct']:+.2f}% | Sharpe: {res['sharpe']:.2f}")

    # 5. Buy & Hold
    res = simulate_buy_and_hold(df)
    results['strategies']['buy_and_hold'] = {
        'return': f"{res['return_pct']:+.2f}%",
        'sharpe': round(res['sharpe'], 2),
        'max_drawdown': f"{res['max_dd']*100:.2f}%",
        'volatility': f"{res['volatility']*100:.2f}%",
        'avg_cost': round(res['avg_cost'], 2),
        'trades': 1,
        'final_value': round(res.get('final_value', 0), 0),
    }
    print(f"  Buy&Hold:    {res['return_pct']:+.2f}% | Sharpe: {res['sharpe']:.2f}")

    return results

def run_all_backtests() -> dict:
    """執行所有時間區間的回測"""
    all_results = {
        'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'title': 'TWII 歷史大盤 DCA 回測報告',
        'periods': {},
        'summary': {
            'best_per_period': {},
            'overall_best': None,
            'dca_beats_bh_count': 0,
        }
    }

    best_overall = {'name': '', 'return': -999}

    for period_name, (start, end) in PERIODS.items():
        result = run_backtest(period_name, start, end)
        if result:
            all_results['periods'][period_name] = result

            # 記錄每期最佳策略
            strat_returns = {}
            for strat, data in result['strategies'].items():
                ret_str = data['return'].replace('%', '').replace('+', '')
                strat_returns[strat] = float(ret_str)

            best_strat = max(strat_returns, key=strat_returns.get)
            all_results['summary']['best_per_period'][period_name] = {
                'strategy': best_strat,
                'return': f"{strat_returns[best_strat]:+.2f}%",
            }

            # 檢查 DCA 是否打敗 B&H
            dca_returns = [v for k, v in strat_returns.items() if 'dca' in k]
            if dca_returns and max(dca_returns) > strat_returns.get('buy_and_hold', -999):
                all_results['summary']['dca_beats_bh_count'] += 1

            # 檢查整體最佳
            for strat, ret in strat_returns.items():
                if ret > best_overall['return']:
                    best_overall = {'name': strat, 'return': ret, 'period': period_name}

    all_results['summary']['overall_best'] = {
        'strategy': best_overall['name'],
        'return': f"{best_overall['return']:+.2f}%",
        'period': best_overall['period'],
    }

    return all_results

def print_summary(report: dict):
    """Print summary report"""
    print(f"\n{'='*60}")
    print("TWII Market Backtest Summary")
    print(f"{'='*60}")

    print("\n[Best Strategy Per Period]")
    for period, info in report['summary']['best_per_period'].items():
        print(f"  {period}: {info['strategy']:20s} {info['return']}")

    print(f"\n[Overall Best] {report['summary']['overall_best']['strategy']} ({report['summary']['overall_best']['period']})")
    print(f"            Return: {report['summary']['overall_best']['return']}")

    dca_count = report['summary']['dca_beats_bh_count']
    total_periods = len(report['periods'])
    print(f"\n[DCA vs Buy&Hold] DCA wins: {dca_count}/{total_periods} periods")

    print(f"\n{'='*60}")
    print("Strategy Legend:")
    print("  fixed_date_dca      = Monthly on 1st")
    print("  price_triggered_dca = Buy when price < MA20 by 10%")
    print("  monthly_dca         = Monthly on 15th")
    print("  weekly_dca          = Weekly on Monday")
    print("  buy_and_hold        = Buy and Hold")
    print(f"{'='*60}")

def save_report(report: dict, filename: str = None):
    """儲存報告為 JSON"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"twii_backtest_{timestamp}.json"

    filepath = REPORTS_DIR / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nReport saved: {filepath}")

    # 同時儲存一份最新報告
    latest_path = REPORTS_DIR / "twii_backtest_latest.json"
    with open(latest_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return str(filepath)

# ======================
# 入口點
# ======================

if __name__ == "__main__":
    print("Ray Market Backtest System Started")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Run all backtests
    report = run_all_backtests()

    # Print summary
    print_summary(report)

    # Save report
    filepath = save_report(report)

    print("\nBacktest Complete!")
    print(f"Report: {filepath}")