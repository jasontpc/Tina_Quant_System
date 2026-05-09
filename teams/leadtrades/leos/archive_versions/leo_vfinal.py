# -*- coding: utf-8 -*-
"""
Leo 最終版參數 vFinal — 根據 RSI 區間深度分析優化
發現：RSI 30-40 是 100% 勝率區間，真正要避開的是 RSI >50
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime

BASE_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leadtrades\leos'

STOCKS = {
    '2330': '台積電',
    '2382': '廣達',
    '3665': '穎崴',
    '2317': '鴻海',
    '3034': '緯穎',
}

# === vFinal 參數：根據 RSI 分析結果 ===
# RSI 30-40 = 100%勝率 → 設為主要進場區間
# RSI 50-55 = 75%勝率，報酬最低 → 設為上限
VFINAL_PARAMS = {
    '2330': {
        'rsi_period': 10,
        'rsi_threshold': 30,      # 允許 RSI 30-50 進場
        'rsi_threshold_max': 50,
        'hold_days': 30,         # 7-14天勝率最高(88.9%, 83.3%)
        'hold_days_max': 45,
        'take_profit': 8,        # TP 8% 符合數據
        'stop_loss': 6,          # 減少大虧
    },
    '2382': {
        'rsi_period': 10,
        'rsi_threshold': 30,      # 允許低 RSI 進場
        'rsi_threshold_max': 50,
        'hold_days': 21,         # 21-30天勝率 88.9%
        'hold_days_max': 45,
        'take_profit': 8,
        'stop_loss': 6,
    },
    '3665': {
        'rsi_period': 10,
        'rsi_threshold': 35,      # 稍微嚴格（曾經平均虧損 -10.71%）
        'rsi_threshold_max': 55,   # 但上限放寬一點
        'hold_days': 45,
        'hold_days_max': 60,
        'take_profit': 8,
        'stop_loss': 6,
    },
    '2317': {
        'rsi_period': 10,
        'rsi_threshold': 35,
        'rsi_threshold_max': 55,
        'hold_days': 30,
        'hold_days_max': 60,
        'take_profit': 6,
        'stop_loss': 8,
    },
    '3034': {
        'rsi_period': 10,
        'rsi_threshold': 30,      # 100%勝率區間
        'rsi_threshold_max': 50,
        'hold_days': 21,
        'hold_days_max': 45,
        'take_profit': 6,
        'stop_loss': 8,
    },
}


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


def backtest_vfinal():
    """回測 vFinal 參數"""
    end_date = datetime.today().strftime('%Y-%m-%d')
    all_trades = []

    print("=" * 60)
    print("Leo vFinal 回測驗證")
    print("=" * 60)

    for ticker, params in VFINAL_PARAMS.items():
        print(f"回測 {ticker}...", end=' ')
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
            RSI_THRESHOLD_MAX = params['rsi_threshold_max']

            in_position = False
            entry_price = 0
            entry_date = None
            entry_rsi = 0

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
                        all_trades.append({'ticker': ticker, 'name': STOCKS[ticker], 'pnl_pct': pnl_pct, 'exit': 'TP', 'days': hold_days, 'entry_rsi': entry_rsi})
                        in_position = False
                    elif pnl_pct <= -STOP_LOSS * 100:
                        all_trades.append({'ticker': ticker, 'name': STOCKS[ticker], 'pnl_pct': pnl_pct, 'exit': 'SL', 'days': hold_days, 'entry_rsi': entry_rsi})
                        in_position = False
                    elif hold_days >= HOLD_DAYS:
                        all_trades.append({'ticker': ticker, 'name': STOCKS[ticker], 'pnl_pct': pnl_pct, 'exit': 'HOLD', 'days': hold_days, 'entry_rsi': entry_rsi})
                        in_position = False
                else:
                    ma_bull = current_ma60 > current_ma120 if not pd.isna(current_ma120) else True
                    momentum_ok = current_momentum > -5.0
                    rsi_ok = RSI_THRESHOLD <= current_rsi <= RSI_THRESHOLD_MAX

                    if (rsi_ok and
                        not pd.isna(current_ma60) and
                        price > current_ma60 and
                        ma_bull and
                        momentum_ok):
                        in_position = True
                        entry_price = price
                        entry_date = date
                        entry_rsi = current_rsi

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
    sl_count = len(df[df['exit'] == 'SL'])
    tp_count = len(df[df['exit'] == 'TP'])
    return {
        'total': total,
        'wins': wins,
        'losses': total - wins,
        'win_rate': win_rate,
        'avg_return': avg_return,
        'sl_count': sl_count,
        'tp_count': tp_count,
    }


def analyze_by_rsi(trades):
    """按 RSI 區間分析"""
    df = pd.DataFrame(trades)
    zones = [(0, 35), (35, 40), (40, 45), (45, 50), (50, 55), (55, 100)]

    print("\n【vFinal RSI 區間分析】")
    print(f"{'區間':<10} {'筆數':<6} {'勝率':<8} {'平均報酬':<10}")
    print("-" * 40)

    for low, high in zones:
        zone_df = df[(df['entry_rsi'] >= low) & (df['entry_rsi'] < high)]
        if len(zone_df) == 0:
            continue
        wr = len(zone_df[zone_df['pnl_pct'] > 0]) / len(zone_df) * 100
        avg = zone_df['pnl_pct'].mean()
        marker = " ✅" if wr >= 85 else ""
        print(f"RSI {low:>3}-{high:<3} {len(zone_df):<6} {wr:>5.1f}% {avg:>+8.2f}%{marker}")


def analyze_by_stock(trades):
    """按股票分析"""
    df = pd.DataFrame(trades)
    print("\n【vFinal 個股表現】")
    print(f"{'股票':<8} {'名稱':<6} {'筆數':<6} {'勝率':<8} {'平均報酬':<10} {'SL':<4} {'TP':<4}")
    print("-" * 55)

    for ticker, name in STOCKS.items():
        stock_df = df[df['ticker'] == ticker]
        if len(stock_df) == 0:
            continue
        wr = len(stock_df[stock_df['pnl_pct'] > 0]) / len(stock_df) * 100
        avg = stock_df['pnl_pct'].mean()
        sl = len(stock_df[stock_df['exit'] == 'SL'])
        tp = len(stock_df[stock_df['exit'] == 'TP'])
        print(f"{ticker:<8} {name:<6} {len(stock_df):<6} {wr:>5.1f}% {avg:>+8.2f}% {sl:<4} {tp:<4}")


def save_final_params():
    """儲存 vFinal 參數"""
    output = {
        'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'version': 'vFinal',
        'description': '根據 RSI 區間深度分析優化（RSI 30-40 = 100%勝率）',
        'params': VFINAL_PARAMS,
        'stocks': STOCKS,
    }

    output_file = os.path.join(BASE_DIR, 'leo_per_stock_params_vFinal.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ vFinal 參數已存: {output_file}")
    return output_file


trades = backtest_vfinal()
metrics = evaluate(trades)

print()
print("=" * 60)
print("【vFinal 整體績效】")
print("=" * 60)
print(f"總交易: {metrics['total']} 筆")
print(f"勝利: {metrics['wins']} / 失敗: {metrics['losses']}")
print(f"勝率: {metrics['win_rate']:.1f}%")
print(f"平均報酬: {metrics['avg_return']:+.2f}%")
print(f"SL: {metrics['sl_count']} 筆 / TP: {metrics['tp_count']} 筆")

analyze_by_rsi(trades)
analyze_by_stock(trades)
save_final_params()

print()
print("=" * 60)
print("🎯 vFinal 分析完成")
print("=" * 60)