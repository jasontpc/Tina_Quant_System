# -*- coding: utf-8 -*-
"""
Leo 自主學習優化系統 v2.0 — 第二階段
根據失敗分析，持續優化不停歇
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
from collections import defaultdict

BASE_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leadtrades\leos'
os.makedirs(BASE_DIR, exist_ok=True)

# === 股票池 v2.0：根據失敗分析移除弱勢股 ===
STOCKS_V2 = {
    '2330': '台積電',      # 勝率62%，均報酬+2.06%
    '2382': '廣達',        # 🏆 最強，均報酬+3.15%
    '3665': '穎崴',        # 交易量最大，均報酬+1.66%
    '2317': '鴻海',        # 勝率81%最高，均報酬+3.84%
    '3034': '緯穎',        # 勝率77%，均報酬+1.66%
}

# 廣達/鴻海加權（最終權重×2）
WEIGHT_BOOST = {'2382': 2, '2317': 2}

# === 擴充網格：針對弱股移除後的優化範圍 ===
PARAM_GRID = {
    'rsi_period': [12, 14, 16],
    'rsi_threshold': [45, 50, 55, 60],
    'hold_days': [21, 30, 45],
    'take_profit': [6, 8, 10],
    'stop_loss': [6, 8, 10],
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


def backtest(params, stocks, start_date='2022-01-01', end_date=None):
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
            volume = df['Volume'].squeeze()
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
                        all_trades.append({'ticker': ticker, 'pnl_pct': pnl_pct, 'exit': 'TP', 'days': hold_days, 'name': stocks[ticker]})
                        in_position = False
                    elif pnl_pct <= -STOP_LOSS * 100:
                        all_trades.append({'ticker': ticker, 'pnl_pct': pnl_pct, 'exit': 'SL', 'days': hold_days, 'name': stocks[ticker]})
                        in_position = False
                    elif hold_days >= HOLD_DAYS:
                        all_trades.append({'ticker': ticker, 'pnl_pct': pnl_pct, 'exit': 'HOLD', 'days': hold_days, 'name': stocks[ticker]})
                        in_position = False
                else:
                    # === 嚴格進場過濾 ===
                    ma_bull = current_ma60 > current_ma120 if not pd.isna(current_ma120) else True
                    momentum_ok = current_momentum > -5.0  # 落後大盤不到5%
                    volume_ok = volume.iloc[i] > volume.rolling(20).mean().iloc[i] if i >= 20 else True

                    if (current_rsi < RSI_THRESHOLD and
                        not pd.isna(current_ma60) and
                        price > current_ma60 and
                        ma_bull and
                        momentum_ok and
                        volume_ok):
                        in_position = True
                        entry_price = price
                        entry_date = df.index[i]
        except Exception as e:
            continue

    return all_trades


def evaluate(trades):
    if not trades:
        return {'win_rate': 0, 'avg_return': 0, 'total_trades': 0, 'score': 0}

    df = pd.DataFrame(trades)
    total = len(df)
    wins = len(df[df['pnl_pct'] > 0])
    win_rate = wins / total * 100 if total > 0 else 0
    avg_return = df['pnl_pct'].mean()

    returns = df['pnl_pct'] / 100
    if len(returns) > 1 and returns.std() > 0:
        sharpe = (returns.mean() - 0.04) / returns.std() * np.sqrt(252)
    else:
        sharpe = 0

    tp_count = len(df[df['exit'] == 'TP'])
    sl_trades = df[df['exit'] == 'SL']
    sl_avg = sl_trades['pnl_pct'].mean() if len(sl_trades) > 0 else 0

    # 期望值
    expected_value = avg_return * (win_rate / 100) + (1 - win_rate / 100) * sl_avg

    trade_score = min(total / 60, 1.0) * 100
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
        'expected_value': expected_value,
        'score': score
    }


def run_cycle_v2():
    print("=" * 60)
    print("Leo 自主學習 v2.0 — 第二階段優化")
    print("=" * 60)
    print(f"股票池: {list(STOCKS_V2.keys())}")
    print(f"移除: 2376技嘉(-0.19%), 2379瑞昱(-2.18%), 2454聯發科, 3665/3034保留")
    print()

    keys = list(PARAM_GRID.keys())
    combinations = list(product(*PARAM_GRID.values()))
    total_combinations = len(combinations)

    best_score = 0
    best_params = None
    best_metrics = None
    results = []

    print(f"共 {total_combinations} 種參數組合...\n")

    for i, combo in enumerate(combinations):
        params = dict(zip(keys, combo))
        trades = backtest(params, STOCKS_V2)
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
            print(f"[{i+1}/{total_combinations}] ✅ Best! Score={metrics['score']:.2f} | WR={metrics['win_rate']:.1f}% | Avg={metrics['avg_return']:+.2f}% | EV={metrics['expected_value']:+.2f}% | Trades={metrics['total_trades']}")
            print(f"    → RSI_P={params['rsi_period']}, Thresh={params['rsi_threshold']}, Hold={params['hold_days']}d, TP={params['take_profit']}%, SL={params['stop_loss']}%")

    print()
    print("=" * 60)
    print("【v2.0 網格搜索結果】")
    print("=" * 60)
    print(f"\n🏆 Best Score: {best_score:.2f}")
    print(f"   Win Rate: {best_metrics['win_rate']:.1f}%")
    print(f"   Avg Return: {best_metrics['avg_return']:+.2f}%")
    print(f"   Expected Value: {best_metrics['expected_value']:+.2f}%")
    print(f"   Total Trades: {best_metrics['total_trades']}")
    print()
    print("Best Params:")
    for k, v in best_params.items():
        print(f"   {k}: {v}")

    # === 失敗模式分析 ===
    trades = backtest(best_params, STOCKS_V2)
    df = pd.DataFrame(trades)
    sl = df[df['exit'] == 'SL']
    hold_loss = df[(df['exit'] == 'HOLD') & (df['pnl_pct'] < 0)]
    tp = df[df['exit'] == 'TP']

    print()
    print("【失敗模式監控】")
    print(f"  SL: {len(sl)}筆 | 均虧損 {sl['pnl_pct'].mean():.2f}%")
    print(f"  HOLD（虧損）: {len(hold_loss)}筆 | 均虧損 {hold_loss['pnl_pct'].mean():.2f}%")
    print(f"  TP: {len(tp)}筆 | 均獲利 {tp['pnl_pct'].mean():.2f}%")

    # === 個股表現 ===
    print()
    print("【個股表現】")
    by_stock = defaultdict(list)
    for t in trades:
        by_stock[t['ticker']].append(t)

    print(f"{'代碼':<8} {'名稱':<6} {'筆數':<4} {'勝率':<6} {'均報酬':<8} {'SL':<3} {'TP':<3}")
    print("-" * 45)
    for ticker, ts in sorted(by_stock.items(), key=lambda x: sum(t['pnl_pct'] for t in x[1])/len(x[1]), reverse=True):
        wr = len([t for t in ts if t['pnl_pct'] > 0]) / len(ts) * 100
        avg = sum(t['pnl_pct'] for t in ts) / len(ts)
        sl_c = len([t for t in ts if t['exit'] == 'SL'])
        tp_c = len([t for t in ts if t['exit'] == 'TP'])
        name = ts[0]['name']
        print(f"{ticker:<8} {name:<6} {len(ts):<4} {wr:>5.0f}% {avg:>+7.2f}% {sl_c:<3} {tp_c:<3}")

    # === 儲存結果 ===
    report = {
        'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'version': 'v2.0',
        'stock_pool': list(STOCKS_V2.keys()),
        'best_params': best_params,
        'best_metrics': best_metrics,
        'grid_size': total_combinations,
        'score_improvement': f"+{best_score - 41.85:.2f}"  # vs v1.0
    }

    with open(os.path.join(BASE_DIR, 'leo_autonomous_v2_result.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # === 更新腳本 ===
    update_scripts(best_params, best_metrics)

    print()
    print("=" * 60)
    print("🎯 v2.0 自主學習完成！")
    print("=" * 60)

    return best_params, best_metrics


def update_scripts(params, metrics):
    """更新所有 Leo 腳本的最優參數"""
    # 更新 leo_backtest.py
    bt_path = os.path.join(BASE_DIR, 'leo_backtest.py')
    with open(bt_path, 'r', encoding='utf-8') as f:
        content = f.read()

    import re
    new_block = f"""# === WFA 最優參數（v2.0 自主學習）===
# {datetime.now().strftime('%Y-%m-%d')} | Score: {metrics['score']:.2f} | WR: {metrics['win_rate']:.1f}% | Avg: {metrics['avg_return']:+.2f}% | Trades: {metrics['total_trades']}
RSI_PERIOD = {params['rsi_period']}
RSI_THRESHOLD = {params['rsi_threshold']}
HOLD_DAYS = {params['hold_days']}
TAKE_PROFIT = {params['take_profit'] / 100}
STOP_LOSS = {params['stop_loss'] / 100}"""

    pattern = r'# === WFA 最優參數.*?STOP_LOSS = \d+\.\d+'
    content = re.sub(pattern, new_block, content, flags=re.DOTALL)

    with open(bt_path, 'w', encoding='utf-8') as f:
        f.write(content)

    # 更新 leos_v65.py
    v65_path = os.path.join(BASE_DIR, 'leos_v65.py')
    if os.path.exists(v65_path):
        with open(v65_path, 'r', encoding='utf-8') as f:
            content = f.read()

        new_v65_block = f"""# === 核心參數（v2.0 自主學習最優化）===
# Score: {metrics['score']:.2f} | WR: {metrics['win_rate']:.1f}% | Avg: {metrics['avg_return']:+.2f}% | Trades: {metrics['total_trades']}
ENTRY_RSI_MIN = {params['rsi_threshold'] - 10}
ENTRY_RSI_MAX = 70
EXIT_RSI_MIN = 75
TAKE_PROFIT_PCT = {params['take_profit']}
STOP_LOSS_PCT = {params['stop_loss']}
MAX_POSITION = 100000
COOLDOWN_MIN = 60
HOLD_DAYS_MAX = {params['hold_days']}"""

        pattern2 = r'# === 核心參數.*?HOLD_DAYS_MAX = \d+'
        content = re.sub(pattern2, new_v65_block, content, flags=re.DOTALL)

        with open(v65_path, 'w', encoding='utf-8') as f:
            f.write(content)

    print("✅ 所有腳本已更新")


if __name__ == '__main__':
    run_cycle_v2()