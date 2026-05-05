# -*- coding: utf-8 -*-
"""
Leo 改善版核心波段系統 v2 — 短線持有、動態進場、獲利出场
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# 改善後參數
IMPROVED_PARAMS = {
    '2330': {'rsi_period': 10, 'rsi_threshold': 50, 'hold_days': 21, 'take_profit': 5, 'stop_loss': 8, 'momentum_min': -3},
    '2382': {'rsi_period': 10, 'rsi_threshold': 50, 'hold_days': 14, 'take_profit': 5, 'stop_loss': 8, 'momentum_min': -3},
    '3665': {'rsi_period': 10, 'rsi_threshold': 50, 'hold_days': 21, 'take_profit': 8, 'stop_loss': 8, 'momentum_min': -3},
    '2317': {'rsi_period': 10, 'rsi_threshold': 50, 'hold_days': 21, 'take_profit': 5, 'stop_loss': 8, 'momentum_min': -3},
    '3034': {'rsi_period': 10, 'rsi_threshold': 40, 'hold_days': 21, 'take_profit': 5, 'stop_loss': 8, 'momentum_min': -3},
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

def backtest_improved():
    end_date = datetime.today().strftime('%Y-%m-%d')
    all_trades = []

    print("=" * 60)
    print("Leo 改善版核心波段系統 v2 回測")
    print("=" * 60)

    for ticker, params in IMPROVED_PARAMS.items():
        print(f"回測 {ticker} {STOCK_NAMES[ticker]}...", end=' ')
        try:
            df = yf.download(f"{ticker}.TW", start='2022-01-01', end=end_date, progress=False)
            if df.empty or len(df) < 60:
                print("無數據")
                continue

            close = df['Close'].squeeze()
            rsi = calc_rsi(close, params['rsi_period'])
            ma60 = calc_ma(close, 60)
            ma120 = calc_ma(close, 120) if len(close) >= 120 else ma60
            momentum = calc_momentum(close, 5)

            HOLD_DAYS = params['hold_days']
            TAKE_PROFIT = params['take_profit'] / 100
            STOP_LOSS = params['stop_loss'] / 100
            RSI_THRESHOLD = params['rsi_threshold']
            MOMENTUM_MIN = params['momentum_min']

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
                        all_trades.append({'ticker': ticker, 'pnl_pct': pnl_pct, 'exit': 'TP', 'days': hold_days})
                        in_position = False
                    elif pnl_pct <= -STOP_LOSS * 100:
                        all_trades.append({'ticker': ticker, 'pnl_pct': pnl_pct, 'exit': 'SL', 'days': hold_days})
                        in_position = False
                    elif hold_days >= HOLD_DAYS:
                        all_trades.append({'ticker': ticker, 'pnl_pct': pnl_pct, 'exit': 'HOLD', 'days': hold_days})
                        in_position = False
                else:
                    ma_bull = current_ma60 > current_ma120 if not pd.isna(current_ma120) else True
                    momentum_ok = current_momentum > MOMENTUM_MIN

                    if (current_rsi < RSI_THRESHOLD and
                        not pd.isna(current_ma60) and
                        price > current_ma60 and
                        ma_bull and
                        momentum_ok):
                        in_position = True
                        entry_price = price
                        entry_date = date

            stock_trades = [t for t in all_trades if t['ticker'] == ticker]
            print(f"{len(stock_trades)} 筆")

        except Exception as e:
            print(f"錯誤: {e}")

    return all_trades

def evaluate(trades):
    df = pd.DataFrame(trades)
    total = len(df)
    wins = len(df[df['pnl_pct'] > 0])
    win_rate = wins / total * 100 if total > 0 else 0
    avg_return = df['pnl_pct'].mean()
    tp_count = len(df[df['exit'] == 'TP'])
    sl_count = len(df[df['exit'] == 'SL'])
    return {
        'total': total, 'wins': wins, 'losses': total-wins,
        'win_rate': win_rate, 'avg_return': avg_return,
        'tp_count': tp_count, 'sl_count': sl_count,
    }

def show_stock_performance(trades):
    df = pd.DataFrame(trades)
    print("\n【改善版個股表現】")
    print(f"{'股票':<8} {'名稱':<6} {'筆數':<6} {'勝率':<8} {'平均報酬':<10} {'TP':<4} {'SL':<4}")
    print("-" * 55)

    for ticker in IMPROVED_PARAMS.keys():
        stock_df = df[df['ticker'] == ticker]
        if len(stock_df) == 0:
            continue
        name = STOCK_NAMES[ticker]
        wr = len(stock_df[stock_df['pnl_pct'] > 0]) / len(stock_df) * 100
        avg = stock_df['pnl_pct'].mean()
        tp = len(stock_df[stock_df['exit'] == 'TP'])
        sl = len(stock_df[stock_df['exit'] == 'SL'])
        print(f"{ticker:<8} {name:<6} {len(stock_df):<6} {wr:>5.1f}% {avg:>+8.2f}% {tp:<4} {sl:<4}")

trades = backtest_improved()
metrics = evaluate(trades)

print()
print("=" * 60)
print("【改善版 v2 整體績效】")
print("=" * 60)
print(f"總交易: {metrics['total']} 筆")
print(f"勝利: {metrics['wins']} / 失敗: {metrics['losses']}")
print(f"勝率: {metrics['win_rate']:.1f}%")
print(f"平均報酬: {metrics['avg_return']:+.2f}%")
print(f"TP: {metrics['tp_count']} 筆 / SL: {metrics['sl_count']} 筆")

show_stock_performance(trades)

print()
print("=" * 60)
print("🎯 改善版 v2 完成")
print("=" * 60)