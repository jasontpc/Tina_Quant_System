# -*- coding: utf-8 -*-
"""
Leo 自主學習優化系統 v1.0
功能：
  - 自動執行多輪參數網格搜索
  - 每輪分析失敗模式
  - 自動更新最優參數
  - 持續優化直到收斂或達到最大迭代次數
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import yfinance as yf
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime
from itertools import product

# === 股票池（根據失敗分析：移除2454/2379，提高廣達權重）===
STOCKS = {
    '2330': '台積電',
    '2382': '廣達',      # 最強，權重提升
    '3665': '穎崴',      # 交易量最大
    '2317': '鴻海',      # 穩健
    '3034': '緯穎',      # 勝率高
    '2376': '技嘉',      # SL偏高，需嚴格停損
}

# 廣達特別加權（最終權重×2）
WEIGHT_BOOST = {'2382': 2}

# === 結果輸出目錄 ===
BASE_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leadtrades\leos'
os.makedirs(BASE_DIR, exist_ok=True)


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


def backtest(params, stocks, start_date='2022-01-01', end_date=None):
    """使用指定參數進行回測"""
    RSI_PERIOD = params['rsi_period']
    RSI_THRESHOLD = params['rsi_threshold']
    HOLD_DAYS = params['hold_days']
    TAKE_PROFIT = params['take_profit'] / 100
    STOP_LOSS = params['stop_loss'] / 100

    if end_date is None:
        end_date = datetime.today().strftime('%Y-%m-%d')

    all_trades = []

    for ticker in stocks.keys():
        try:
            df = yf.download(f"{ticker}.TW", start=start_date, end=end_date, progress=False)
            if df.empty or len(df) < 60:
                continue

            close = df['Close'].squeeze()
            rsi = calc_rsi(close, RSI_PERIOD)
            ma60 = calc_ma(close, 60)
            ma120 = calc_ma(close, 120) if len(close) >= 120 else ma60
            momentum = calc_momentum(close, 5)

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
                    hold_days = (df.index[i] - entry_date).days
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
                    # === 改良進場條件：MA60 > MA120 多頭排列 + 動量過濾 ===
                    ma_bull = current_ma60 > current_ma120 if not pd.isna(current_ma120) else True
                    momentum_ok = current_momentum > -3.0  # 落後大盤不到3%

                    if (current_rsi < params['rsi_threshold'] and
                        not pd.isna(current_ma60) and
                        price > current_ma60 and
                        ma_bull and
                        momentum_ok):
                        in_position = True
                        entry_price = price
                        entry_date = df.index[i]
        except Exception as e:
            continue

    return all_trades


def evaluate(trades):
    """計算績效指標"""
    if not trades:
        return {'win_rate': 0, 'avg_return': 0, 'total_trades': 0, 'sharpe': 0, 'score': 0}

    df = pd.DataFrame(trades)
    total = len(df)
    wins = len(df[df['pnl_pct'] > 0])
    win_rate = wins / total * 100 if total > 0 else 0
    avg_return = df['pnl_pct'].mean()

    # Sharpe Ratio
    returns = df['pnl_pct'] / 100
    if len(returns) > 1 and returns.std() > 0:
        sharpe = (returns.mean() - 0.04) / returns.std() * np.sqrt(252)
    else:
        sharpe = 0

    # 停利次數（高效交易）
    tp_count = len(df[df['exit'] == 'TP'])

    # 失敗模式分數：SL虧損幅度
    sl_trades = df[df['exit'] == 'SL']
    sl_avg = sl_trades['pnl_pct'].mean() if len(sl_trades) > 0 else 0

    # 綜合分數：勝率×0.4 + 期望值×0.3 + Sharpe×0.2 + 交易次數權重×0.1
    trade_score = min(total / 50, 1.0) * 100  # 目標50筆以上
    score = (win_rate * 0.35 +
             max(avg_return + 5, 0) * 0.30 +
             max(sharpe + 2, 0) * 0.15 +
             trade_score * 0.15 +
             tp_count / total * 100 * 0.05)

    return {
        'total_trades': total,
        'wins': wins,
        'win_rate': win_rate,
        'avg_return': avg_return,
        'sharpe': sharpe,
        'tp_count': tp_count,
        'sl_avg': sl_avg,
        'score': score
    }


def grid_search():
    """網格搜索最優參數"""
    print("=" * 60)
    print("Leo 自主學習優化系統 v1.0")
    print("=" * 60)

    # 參數網格
    param_grid = {
        'rsi_period': [10, 12, 14],
        'rsi_threshold': [45, 50, 55],
        'hold_days': [14, 21, 30],
        'take_profit': [8, 10, 12],
        'stop_loss': [6, 8, 10],
    }

    keys = list(param_grid.keys())
    combinations = list(product(*param_grid.values()))
    total_combinations = len(combinations)

    best_score = 0
    best_params = None
    best_metrics = None
    results = []

    print(f"\n共 {total_combinations} 種參數組合...\n")

    for i, combo in enumerate(combinations):
        params = dict(zip(keys, combo))
        trades = backtest(params, STOCKS)
        metrics = evaluate(trades)

        results.append({
            'params': params,
            'metrics': metrics,
            'score': metrics['score']
        })

        if metrics['score'] > best_score:
            best_score = metrics['score']
            best_params = params.copy()
            best_metrics = metrics.copy()
            print(f"[{i+1}/{total_combinations}] ✅ New Best! Score={metrics['score']:.2f} | WR={metrics['win_rate']:.1f}% | Avg={metrics['avg_return']:+.2f}% | Trades={metrics['total_trades']}")
            print(f"    → Params: RSI_P={params['rsi_period']}, Thresh={params['rsi_threshold']}, Hold={params['hold_days']}d, TP={params['take_profit']}%, SL={params['stop_loss']}%")
        else:
            print(f"[{i+1}/{total_combinations}] Score={metrics['score']:.2f} | WR={metrics['win_rate']:.1f}% | Trades={metrics['total_trades']}")

    print()
    print("=" * 60)
    print("【網格搜索結果】")
    print("=" * 60)
    print(f"\n🏆 Best Score: {best_score:.2f}")
    print(f"   Win Rate: {best_metrics['win_rate']:.1f}%")
    print(f"   Avg Return: {best_metrics['avg_return']:+.2f}%")
    print(f"   Total Trades: {best_metrics['total_trades']}")
    print(f"   Sharpe: {best_metrics['sharpe']:.2f}")
    print()
    print("Best Params:")
    for k, v in best_params.items():
        print(f"   {k}: {v}")

    # === 失敗模式分析 ===
    print()
    print("【失敗模式分析】")
    trades = backtest(best_params, STOCKS)
    df = pd.DataFrame(trades)
    sl = df[df['exit'] == 'SL']
    hold_loss = df[(df['exit'] == 'HOLD') & (df['pnl_pct'] < 0)]
    tp = df[df['exit'] == 'TP']

    print(f"  SL: {len(sl)}筆 | 均虧損 {sl['pnl_pct'].mean():.2f}%")
    print(f"  HOLD: {len(hold_loss)}筆 | 均虧損 {hold_loss['pnl_pct'].mean():.2f}%")
    print(f"  TP: {len(tp)}筆 | 均獲利 {tp['pnl_pct'].mean():.2f}%")

    # 輸出結果
    report = {
        'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'best_params': best_params,
        'best_metrics': best_metrics,
        'grid_size': total_combinations,
        'all_results': [
            {'params': r['params'], 'score': r['score'], 'wr': r['metrics']['win_rate'], 'avg': r['metrics']['avg_return']}
            for r in results
        ]
    }

    with open(os.path.join(BASE_DIR, 'leo_autonomous_result.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 結果已存: leo_autonomous_result.json")

    # === 更新回測腳本 ===
    update_backtest_script(best_params, best_metrics)

    print()
    print("=" * 60)
    print("🎯 自主學習完成！已自動更新 leo_backtest.py")
    print("=" * 60)

    return best_params, best_metrics


def update_backtest_script(params, metrics):
    """自動更新 leo_backtest.py 的最優參數"""
    script_path = os.path.join(BASE_DIR, 'leo_backtest.py')

    with open(script_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 替換 WFA 參數區塊
    new_params_block = f"""# === WFA 最優參數 ===
# 2026-04-27 自主學習優化系統 v1.0 自動更新
# Score: {metrics['score']:.2f} | WR: {metrics['win_rate']:.1f}% | Avg: {metrics['avg_return']:+.2f}% | Trades: {metrics['total_trades']}
RSI_PERIOD = {params['rsi_period']}
RSI_THRESHOLD = {params['rsi_threshold']}
HOLD_DAYS = {params['hold_days']}
TAKE_PROFIT = {params['take_profit'] / 100}
STOP_LOSS = {params['stop_loss'] / 100}"""

    # 找到並替換參數區塊
    import re
    pattern = r'# === WFA 最優參數 ===.*?STOP_LOSS = \d+\.\d+'
    content = re.sub(pattern, new_params_block, content, flags=re.DOTALL)

    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ leo_backtest.py 已更新最優參數")


if __name__ == '__main__':
    best_params, best_metrics = grid_search()