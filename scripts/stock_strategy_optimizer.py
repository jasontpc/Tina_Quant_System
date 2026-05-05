# -*- coding: utf-8 -*-
"""
Tina 大腦 - 個股特性策略調優系統
================================
根據股票特性（均值回歸/趨勢跟隨/強勢突破）自動調整策略參數
"""
import sqlite3, json, sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
WORKSPACE = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
DATA = WORKSPACE / 'data'
DB = DATA / 'yfinance.db'
CHAR_DB = DATA / 'stock_characteristics.db'

# 策略模板
STRATEGY_TEMPLATES = {
    'STRONG_UPTREND': {
        'rsi_min': 40, 'rsi_max': 70,
        'macd_positive': True, 'ma_bull': True,
        'vol_min': 1.2, 'sl_mult': 2.0, 'tp_mult': 4.0,
        'strategy_name': '順勢追蹤',
        'notes': '強趨勢股，MA 多頭時進場，容忍回檔'
    },
    'MEAN_REVERSION': {
        'rsi_min': 25, 'rsi_max': 50,
        'macd_positive': False, 'ma_bull': False,
        'vol_min': 1.0, 'sl_mult': 1.5, 'tp_mult': 3.0,
        'strategy_name': '均值回歸',
        'notes': '逆勢操作，RSI 超賣時進場'
    },
    'OVERSOLD_REGULAR': {
        'rsi_min': 20, 'rsi_max': 40,
        'macd_positive': False, 'ma_bull': False,
        'vol_min': 1.3, 'sl_mult': 1.0, 'tp_mult': 4.0,
        'strategy_name': '超跌反彈',
        'notes': 'RSI 極低時進場，嚴格停損'
    },
    'TREND_FOLLOWING': {
        'rsi_min': 45, 'rsi_max': 70,
        'macd_positive': True, 'ma_bull': True,
        'vol_min': 1.5, 'sl_mult': 1.5, 'tp_mult': 3.0,
        'strategy_name': '趨勢跟隨',
        'notes': 'MACD 金叉確認後進場'
    },
    'RANGE_BOUND': {
        'rsi_min': 30, 'rsi_max': 60,
        'macd_positive': False, 'ma_bull': False,
        'vol_min': 1.0, 'sl_mult': 1.0, 'tp_mult': 2.5,
        'strategy_name': '區間操作',
        'notes': '區間上緣賣，下緣買'
    },
    'MIXED': {
        'rsi_min': 35, 'rsi_max': 55,
        'macd_positive': True, 'ma_bull': True,
        'vol_min': 1.0, 'sl_mult': 1.5, 'tp_mult': 3.0,
        'strategy_name': '綜合策略',
        'notes': '多條件確認後進場'
    }
}

def load_stock_characteristics():
    """讀取股票特性資料庫"""
    conn = sqlite3.connect(str(CHAR_DB))
    c = conn.cursor()
    c.execute("SELECT symbol, classification FROM stock_characteristics")
    rows = c.fetchall()
    conn.close()
    return {r[0]: r[1] for r in rows}

def backtest_stock_with_strategy(sym, params, days=730):
    """針對單一股票回測特定策略"""
    conn = sqlite3.connect(str(DB))
    cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    c = conn.cursor()
    c.execute("""
        SELECT date, close, high, low, volume, rsi_14, macd_hist, sma_20, sma_60
        FROM daily_ohlcv WHERE symbol=? AND date>=? ORDER BY date
    """, (sym, cutoff))
    rows = c.fetchall()
    conn.close()

    if len(rows) < 60:
        return None

    prices = [r[1] for r in rows]
    highs = [r[2] for r in rows]
    lows = [r[3] for r in rows]
    rsis = [r[5] if r[5] else 50 for r in rows]
    macds = [r[6] if r[6] else 0 for r in rows]
    sma20 = [r[7] if r[7] else prices[i] for i, r in enumerate(rows)]
    sma60 = [r[8] if r[8] else prices[i] for i, r in enumerate(rows)]

    trades = []
    for i in range(60, len(prices) - 15):
        rsi_i = rsis[i]
        macd_i = macds[i]
        ma20 = sma20[i]
        ma60 = sma60[i]

        # Apply filters
        if not (params['rsi_min'] <= rsi_i <= params['rsi_max']):
            continue
        if params.get('macd_positive') and macd_i <= 0:
            continue
        if params.get('ma_bull') and not (ma20 > ma60):
            continue

        atr = sum(max(highs[j]-lows[j], abs(highs[j]-prices[j-1]) if j > 0 else 0)
                 for j in range(max(0,i-13), i+1)) / 14
        sl = prices[i] - atr * params['sl_mult']
        tp = prices[i] + atr * params['tp_mult']

        for j in range(i+1, min(i+16, len(prices))):
            if prices[j] <= sl:
                trades.append('loss'); break
            elif prices[j] >= tp:
                trades.append('win'); break

    return trades

def analyze_and_optimize():
    print('='*70)
    print('  Tina 個股特性策略調優系統')
    print('  ' + datetime.now().strftime('%Y-%m-%d %H:%M'))
    print('='*70)

    # 讀取股票特性
    print('\n[1] 讀取股票特性資料庫...')
    chars = load_stock_characteristics()
    print('  已載入 %d 檔股票特性' % len(chars))

    # 讀取觀察名單
    with open('data/team_watch_list.json', 'r', encoding='utf-8') as f:
        watchlist = json.load(f)

    all_symbols = watchlist['all_symbols']
    print('  觀察名單: %d 檔' % len(all_symbols))

    # 為每檔股票找最佳策略
    print('\n[2] 為每檔股票評估 6 種策略模板...')
    results = {}

    for sym in all_symbols:
        if sym not in chars:
            classification = 'MIXED'  # default
        else:
            classification = chars[sym]

        best_strategy = None
        best_wr = 0
        best_trades = 0

        for strat_name, params in STRATEGY_TEMPLATES.items():
            trades = backtest_stock_with_strategy(sym, params)
            if not trades:
                continue
            wins = sum(1 for t in trades if t == 'win')
            wr = wins / len(trades) * 100
            if wr > best_wr:
                best_wr = wr
                best_trades = len(trades)
                best_strategy = strat_name

        results[sym] = {
            'classification': classification,
            'best_strategy': best_strategy,
            'wr': best_wr,
            'trades': best_trades
        }

    # 顯示結果
    print('\n' + '='*70)
    print('  個股策略調優結果')
    print('='*70)
    print('%-12s %-20s %-18s %6s %5s' % ('代號', '特性分類', '最佳策略', '交易', '勝率'))
    print('-'*75)

    strategy_counts = {}
    for sym, r in sorted(results.items(), key=lambda x: -x[1]['wr']):
        strat = r['best_strategy'] or 'NONE'
        cls = r['classification'] or 'MIXED'
        wr_icon = '🟢' if r['wr'] >= 60 else ('🟡' if r['wr'] >= 40 else '🔴')
        print('%s %-20s %-18s %6d %s%.1f%%' % (sym, cls[:20], strat[:18], r['trades'], wr_icon, r['wr']))
        if strat not in strategy_counts:
            strategy_counts[strat] = 0
        strategy_counts[strat] += 1

    print('\n【策略分佈】')
    for strat, count in sorted(strategy_counts.items(), key=lambda x: -x[1]):
        print('  %s: %d 檔' % (strat, count))

    # 生成優化後的 team_watch_list
    print('\n' + '='*70)
    print('  生成優化後的團隊設定')
    print('='*70)

    optimized_teams = {}
    for team_name, team_info in watchlist['teams'].items():
        optimized_symbols = []
        team_strategies = {}

        for sym in team_info['watch_list']:
            if sym in results:
                strat = results[sym]['best_strategy']
                if strat:
                    optimized_symbols.append(sym)
                    team_strategies[sym] = strat

        optimized_teams[team_name] = {
            'watch_list': team_info['watch_list'],
            'optimized_for': team_strategies,
            'params': STRATEGY_TEMPLATES.copy()
        }

        print('\n%s 團隊:' % team_name)
        for sym, strat in team_strategies.items():
            r = results[sym]
            print('  %s -> %s (WR=%.1f%%, %d trades)' % (sym, strat, r['wr'], r['trades']))

    # 保存優化結果
    print('\n[3] 保存優化結果...')
    with open('data/optimized_stock_strategies.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print('  已保存: data/optimized_stock_strategies.json')

    return results

if __name__ == '__main__':
    analyze_and_optimize()