# -*- coding: utf-8 -*-
"""
Leo v2.0 參數回測驗證 — 對比 v1.0 vs v2.0
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import pandas as pd
import numpy as np
import json
from datetime import datetime

# === v1.0 原始參數 ===
V1_PARAMS = {
    '2330': {'rsi_period': 10, 'rsi_threshold': 50, 'hold_days': 45, 'take_profit': 5, 'stop_loss': 8},
    '2382': {'rsi_period': 10, 'rsi_threshold': 50, 'hold_days': 30, 'take_profit': 5, 'stop_loss': 8},
    '3665': {'rsi_period': 10, 'rsi_threshold': 50, 'hold_days': 60, 'take_profit': 8, 'stop_loss': 10},
    '2317': {'rsi_period': 10, 'rsi_threshold': 55, 'hold_days': 60, 'take_profit': 5, 'stop_loss': 10},
    '3034': {'rsi_period': 10, 'rsi_threshold': 40, 'hold_days': 30, 'take_profit': 5, 'stop_loss': 8},
}

# === v2.0 修正參數 ===
V2_PARAMS = {
    '2330': {'rsi_period': 10, 'rsi_threshold': 35, 'rsi_threshold_max': 50, 'hold_days': 45, 'hold_days_min': 14, 'take_profit': 5, 'stop_loss': 6, 'weight': 1.0},
    '2382': {'rsi_period': 10, 'rsi_threshold': 40, 'rsi_threshold_max': 55, 'hold_days': 30, 'hold_days_min': 14, 'take_profit': 5, 'stop_loss': 6, 'weight': 1.0},
    '3665': {'rsi_period': 10, 'rsi_threshold': 45, 'rsi_threshold_max': 55, 'hold_days': 60, 'hold_days_min': 21, 'take_profit': 8, 'stop_loss': 6, 'weight': 0.5},
    '2317': {'rsi_period': 10, 'rsi_threshold': 45, 'rsi_threshold_max': 55, 'hold_days': 60, 'hold_days_min': 21, 'take_profit': 5, 'stop_loss': 8, 'weight': 1.0},
    '3034': {'rsi_period': 10, 'rsi_threshold': 35, 'rsi_threshold_max': 55, 'hold_days': 30, 'hold_days_min': 14, 'take_profit': 5, 'stop_loss': 8, 'weight': 1.5},
}

STOCK_NAMES = {'2330': '台積電', '2382': '廣達', '3665': '穎崴', '2317': '鴻海', '3034': '緯穎'}


def calc_rsi(prices, period=12):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calc_ma(prices, period):
    return prices.rolling(window=period).mean()

def calc_momentum(prices, days=5):
    return prices.pct_change(days) * 100

def backtest_version(params, version_name, start_date='2022-01-01', end_date=None):
    """使用指定參數版本回測"""
    if end_date is None:
        end_date = datetime.today().strftime('%Y-%m-%d')

    all_trades = []

    for ticker, par in params.items():
        try:
            df = yf.download(f"{ticker}.TW", start=start_date, end=end_date, progress=False)
            if df.empty or len(df) < 60:
                continue

            close = df['Close'].squeeze()
            rsi = calc_rsi(close, par['rsi_period'])
            ma60 = calc_ma(close, 60)
            ma120 = calc_ma(close, 120) if len(close) >= 120 else ma60
            momentum = calc_momentum(close, 5)

            HOLD_DAYS = par['hold_days']
            TAKE_PROFIT = par['take_profit'] / 100
            STOP_LOSS = par['stop_loss'] / 100
            RSI_THRESHOLD = par['rsi_threshold']
            RSI_THRESHOLD_MAX = par.get('rsi_threshold_max', 55)
            HOLD_DAYS_MIN = par.get('hold_days_min', 1)

            in_position = False
            entry_price = 0
            entry_date = None

            for i in range(60, len(df) - HOLD_DAYS):
                date = df.index[i]
                price = close.iloc[i]
                current_rsi = rsi.iloc[i]
                current_ma60 = ma60.iloc[i]
                current_ma120 = ma120.iloc[i]
                current_momentum = momentum.iloc[i]

                if in_position:
                    hold_days = (date - entry_date).days
                    pnl_pct = (price - entry_price) / entry_price * 100

                    if pnl_pct >= TAKE_PROFIT * 100:
                        all_trades.append({'ticker': ticker, 'pnl_pct': pnl_pct, 'exit': 'TP', 'days': hold_days, 'weight': par.get('weight', 1.0)})
                        in_position = False
                    elif pnl_pct <= -STOP_LOSS * 100:
                        all_trades.append({'ticker': ticker, 'pnl_pct': pnl_pct, 'exit': 'SL', 'days': hold_days, 'weight': par.get('weight', 1.0)})
                        in_position = False
                    elif hold_days >= HOLD_DAYS:
                        all_trades.append({'ticker': ticker, 'pnl_pct': pnl_pct, 'exit': 'HOLD', 'days': hold_days, 'weight': par.get('weight', 1.0)})
                        in_position = False
                else:
                    ma_bull = current_ma60 > current_ma120 if not pd.isna(current_ma120) else True
                    momentum_ok = current_momentum > -3.0

                    # v2.0 進場條件
                    rsi_ok = RSI_THRESHOLD <= current_rsi <= RSI_THRESHOLD_MAX
                    hold_ok = True  # 進場時不限制持有天數

                    if (rsi_ok and
                        not pd.isna(current_ma60) and
                        price > current_ma60 and
                        ma_bull and
                        momentum_ok):
                        in_position = True
                        entry_price = price
                        entry_date = date

        except Exception as e:
            continue

    return all_trades

def evaluate(trades):
    if not trades:
        return {}
    df = pd.DataFrame(trades)
    total = len(df)
    wins = len(df[df['pnl_pct'] > 0])
    win_rate = wins / total * 100 if total > 0 else 0
    avg_return = df['pnl_pct'].mean()
    return {
        'total': total,
        'wins': wins,
        'losses': total - wins,
        'win_rate': win_rate,
        'avg_return': avg_return,
    }

print("=" * 60)
print("Leo v1.0 vs v2.0 參數回測對比")
print("=" * 60)

v1_trades = backtest_version(V1_PARAMS, "v1.0")
v2_trades = backtest_version(V2_PARAMS, "v2.0")

v1_metrics = evaluate(v1_trades)
v2_metrics = evaluate(v2_trades)

print(f"\n{'版本':<8} {'總交易':<8} {'勝利':<6} {'失敗':<6} {'勝率':<10} {'平均報酬':<12}")
print("-" * 60)
print(f"v1.0   {v1_metrics['total']:<8} {v1_metrics['wins']:<6} {v1_metrics['losses']:<6} {v1_metrics['win_rate']:>7.1f}% {v1_metrics['avg_return']:>+10.2f}%")
print(f"v2.0   {v2_metrics['total']:<8} {v2_metrics['wins']:<6} {v2_metrics['losses']:<6} {v2_metrics['win_rate']:>7.1f}% {v2_metrics['avg_return']:>+10.2f}%")

if v2_metrics['win_rate'] > v1_metrics['win_rate']:
    print(f"\n✅ v2.0 勝率提升: {v2_metrics['win_rate'] - v1_metrics['win_rate']:+.1f}%")
if v2_metrics['avg_return'] > v1_metrics['avg_return']:
    print(f"✅ v2.0 平均報酬提升: {v2_metrics['avg_return'] - v1_metrics['avg_return']:+.2f}%")

print()
print("=" * 60)
print("🎯 回測對比完成")
print("=" * 60)