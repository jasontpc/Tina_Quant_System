# -*- coding: utf-8 -*-
"""
Leo 個股參數優化系統 v1.0 — 2026-04-27
每檔股票獨立優化，專屬參數最大化勝率
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

BASE_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leadtrades\leos'
os.makedirs(BASE_DIR, exist_ok=True)

# 股票池
STOCKS = {
    '2330': '台積電',
    '2382': '廣達',
    '3665': '穎崴',
    '2317': '鴻海',
    '3034': '緯穎',
}

PARAM_GRID = {
    'rsi_period': [10, 12, 14],
    'rsi_threshold': [40, 45, 50, 55],
    'hold_days': [21, 30, 45, 60],
    'take_profit': [5, 6, 8, 10],
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


def backtest_stock(ticker, params, start_date='2022-01-01', end_date=None):
    RSI_PERIOD = params['rsi_period']
    RSI_THRESHOLD = params['rsi_threshold']
    HOLD_DAYS = params['hold_days']
    TAKE_PROFIT = params['take_profit'] / 100
    STOP_LOSS = params['stop_loss'] / 100

    if end_date is None:
        end_date = datetime.today().strftime('%Y-%m-%d')

    try:
        df = yf.download(f"{ticker}.TW", start=start_date, end=end_date, progress=False)
        if df.empty or len(df) < 60:
            return []

        close = df['Close'].squeeze()
        rsi = calc_rsi(close, RSI_PERIOD)
        ma60 = calc_ma(close, 60)
        ma120 = calc_ma(close, 120) if len(close) >= 120 else ma60
        momentum = calc_momentum(close, 5)

        trades = []
        in_position = False
        entry_price = 0
        entry_date = None

        for i in range(60, len(df) - HOLD_DAYS):
            price = close.iloc[i]
            current_rsi = rsi.iloc[i]
            current_ma60 = ma60.iloc[i]
            current_ma120 = ma120.iloc[i]
            current_momentum = momentum.iloc[i]
            date = df.index[i]

            if in_position:
                hold_days = (df.index[i] - entry_date).days
                pnl_pct = (price - entry_price) / entry_price * 100

                if pnl_pct >= TAKE_PROFIT * 100:
                    trades.append({'pnl_pct': pnl_pct, 'exit': 'TP', 'days': hold_days})
                    in_position = False
                elif pnl_pct <= -STOP_LOSS * 100:
                    trades.append({'pnl_pct': pnl_pct, 'exit': 'SL', 'days': hold_days})
                    in_position = False
                elif hold_days >= HOLD_DAYS:
                    trades.append({'pnl_pct': pnl_pct, 'exit': 'HOLD', 'days': hold_days})
                    in_position = False
            else:
                ma_bull = current_ma60 > current_ma120 if not pd.isna(current_ma120) else True
                momentum_ok = current_momentum > -5.0

                if (current_rsi < RSI_THRESHOLD and
                    not pd.isna(current_ma60) and
                    price > current_ma60 and
                    ma_bull and
                    momentum_ok):
                    in_position = True
                    entry_price = price
                    entry_date = df.index[i]

        return trades
    except:
        return []


def evaluate(trades):
    if not trades:
        return {'win_rate': 0, 'avg_return': 0, 'total_trades': 0, 'score': 0, 'tp_rate': 0}

    df = pd.DataFrame(trades)
    total = len(df)
    wins = len(df[df['pnl_pct'] > 0])
    win_rate = wins / total * 100 if total > 0 else 0
    avg_return = df['pnl_pct'].mean()
    tp_count = len(df[df['exit'] == 'TP'])
    tp_rate = tp_count / total * 100 if total > 0 else 0

    returns = df['pnl_pct'] / 100
    if len(returns) > 1 and returns.std() > 0:
        sharpe = (returns.mean() - 0.04) / returns.std() * np.sqrt(252)
    else:
        sharpe = 0

    trade_score = min(total / 20, 1.0) * 100  # 每檔至少20筆
    score = (win_rate * 0.40 +
             max(avg_return + 5, 0) * 0.30 +
             max(sharpe + 2, 0) * 0.15 +
             trade_score * 0.15)

    return {
        'total_trades': total,
        'wins': wins,
        'win_rate': win_rate,
        'avg_return': avg_return,
        'sharpe': sharpe,
        'tp_count': tp_count,
        'tp_rate': tp_rate,
        'score': score
    }


def optimize_stock(ticker, name):
    """針對單一股票進行網格搜索"""
    print(f"\n{'='*50}")
    print(f"開始優化 {ticker} {name}")
    print('='*50)

    keys = list(PARAM_GRID.keys())
    combinations = list(product(*PARAM_GRID.values()))

    best_score = 0
    best_params = None
    best_metrics = None

    for combo in combinations:
        params = dict(zip(keys, combo))
        trades = backtest_stock(ticker, params)
        metrics = evaluate(trades)

        if metrics['score'] > best_score:
            best_score = metrics['score']
            best_params = params.copy()
            best_metrics = metrics.copy()

    print(f"🏆 {ticker} 最優: Score={best_score:.2f} | WR={best_metrics['win_rate']:.1f}% | Avg={best_metrics['avg_return']:+.2f}% | Trades={best_metrics['total_trades']}")
    print(f"   Params: RSI_P={best_params['rsi_period']}, Thresh={best_params['rsi_threshold']}, Hold={best_params['hold_days']}d, TP={best_params['take_profit']}%, SL={best_params['stop_loss']}%")

    return {
        'ticker': ticker,
        'name': name,
        'params': best_params,
        'metrics': best_metrics
    }


def main():
    print("=" * 60)
    print("Leo 個股參數優化系統 v1.0")
    print("每檔股票獨立優化，專屬參數最大化勝率")
    print("=" * 60)

    results = {}
    all_results = []

    for ticker, name in STOCKS.items():
        result = optimize_stock(ticker, name)
        results[ticker] = result
        all_results.append(result)

    # === 總結 ===
    print()
    print("=" * 60)
    print("【個股參數優化總結】")
    print("=" * 60)

    print(f"\n{'股票':<8} {'筆數':<6} {'勝率':<8} {'均報酬':<10} {'Score':<8} {'專屬參數'}")
    print("-" * 80)

    for ticker, name in STOCKS.items():
        r = results[ticker]
        m = r['metrics']
        p = r['params']
        print(f"{ticker:<8} {m['total_trades']:<6} {m['win_rate']:>5.1f}% {m['avg_return']:>+8.2f}% {m['score']:>6.2f}  RSI_P={p['rsi_period']}, Th={p['rsi_threshold']}, Hold={p['hold_days']}d, TP={p['take_profit']}%, SL={p['stop_loss']}%")

    # === 整合參數表 ===
    combined_report = {
        'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'stocks': {}
    }

    for ticker, r in results.items():
        combined_report['stocks'][ticker] = {
            'name': r['name'],
            'params': r['params'],
            'metrics': r['metrics']
        }

    with open(os.path.join(BASE_DIR, 'leo_per_stock_params.json'), 'w', encoding='utf-8') as f:
        json.dump(combined_report, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 個股參數已存: leo_per_stock_params.json")

    # === 建立新的個股優化腳本 ===
    create_per_stock_trading_script(results)

    print()
    print("=" * 60)
    print("🎯 個股參數優化完成！")
    print("=" * 60)

    return results


def create_per_stock_trading_script(results):
    """根據個股參數生成交易腳本"""
    script_content = '''# -*- coding: utf-8 -*-
"""
Leo 個股參數交易系統 v1.0
每檔股票使用專屬優化參數
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import yfinance as yf
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime

BASE_DIR = r"C:\\Users\\USER\\.openclaw\\workspace\\Tina_Quant_System\\teams\\leadtrades\\leos"
TRADE_LOG = os.path.join(BASE_DIR, "leo_per_stock_trades.json")
PARAMS_FILE = os.path.join(BASE_DIR, "leo_per_stock_params.json")

# === 個股參數 ===
STOCK_PARAMS = {
''' + ',\n'.join([f"    '{ticker}': {json.dumps(r['params'], ensure_ascii=False)}" for ticker, r in results.items()]) + '''
}

# === 股票名稱 ===
STOCK_NAMES = {
''' + ',\n'.join([f"    '{ticker}': '{r['name']}'" for ticker, r in results.items()]) + '''
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


def load_trades():
    if os.path.exists(TRADE_LOG):
        with open(TRADE_LOG, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_trades(trades):
    with open(TRADE_LOG, 'w', encoding='utf-8') as f:
        json.dump(trades, f, ensure_ascii=False, indent=2)


def analyze_stock(ticker, params):
    """使用專屬參數分析個股"""
    try:
        df = yf.download(f"{ticker}.TW", period="3mo", progress=False)
        if df.empty or len(df) < 30:
            return None

        close = df['Close'].squeeze()
        rsi = calc_rsi(close, params['rsi_period'])
        ma60 = calc_ma(close, 60)
        ma120 = calc_ma(close, 120) if len(close) >= 120 else ma60
        momentum = calc_momentum(close, 5)

        current_rsi = rsi.iloc[-1]
        current_ma60 = ma60.iloc[-1]
        current_ma120 = ma120.iloc[-1] if len(close) >= 120 else ma60.iloc[-1]
        current_momentum = momentum.iloc[-1]
        current_price = close.iloc[-1]

        ma_bull = current_ma60 > current_ma120 if not pd.isna(current_ma120) else True
        momentum_ok = current_momentum > -5.0

        signal = "HOLD"
        entry_signal = False

        if (current_rsi < params['rsi_threshold'] and
            not pd.isna(current_ma60) and
            current_price > current_ma60 and
            ma_bull and
            momentum_ok):
            signal = "BUY"
            entry_signal = True

        return {
            'ticker': ticker,
            'name': STOCK_NAMES[ticker],
            'price': float(current_price),
            'rsi': float(current_rsi),
            'ma60': float(current_ma60) if not pd.isna(current_ma60) else None,
            'ma120': float(current_ma120) if not pd.isna(current_ma120) else None,
            'momentum': float(current_momentum),
            'ma_bull': ma_bull,
            'signal': signal,
            'entry_signal': entry_signal,
            'params': params
        }
    except Exception as e:
        print(f"  [錯誤] {ticker}: {e}")
        return None


def run_cycle():
    print("=" * 60)
    print("Leo 個股參數交易系統 v1.0")
    print("=" * 60)

    results = []
    for ticker, params in STOCK_PARAMS.items():
        print(f"分析 {ticker}...", end=" ")
        r = analyze_stock(ticker, params)
        if r:
            results.append(r)
            if r['entry_signal']:
                print(f"✅ BUY | RSI={r['rsi']:.1f} | Momentum={r['momentum']:+.2f}%")
            else:
                print(f"⚪ {r['signal']} | RSI={r['rsi']:.1f}")
        else:
            print(f"❌ 無法分析")

    print()
    print("【進場候選】")
    candidates = [r for r in results if r['entry_signal']]
    if candidates:
        for r in candidates:
            print(f"  ✅ {r['ticker']} {r['name']}: RSI={r['rsi']:.1f}, Momentum={r['momentum']:+.2f}%")
    else:
        print("  無進場訊號")

    # 儲存
    with open(os.path.join(BASE_DIR, "leo_per_stock_analysis.json"), 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    return results


if __name__ == '__main__':
    run_cycle()
'''

    with open(os.path.join(BASE_DIR, 'leo_per_stock_trade.py'), 'w', encoding='utf-8') as f:
        f.write(script_content)

    print("✅ 個股參數交易腳本已生成: leo_per_stock_trade.py")


if __name__ == '__main__':
    main()