# -*- coding: utf-8 -*-
"""
Tina 大腦回測歷史分析 - 沙盤推演系統
======================================
目標：尋找增加勝率 AND 交易數量的策略
"""
import sqlite3, json, sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
WORKSPACE = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
DATA = WORKSPACE / 'data'
DB = DATA / 'yfinance.db'

def get_all_trades(days=730):
    """取得所有股票的历史数据用于回测"""
    conn = sqlite3.connect(str(DB))
    c = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    c.execute("""
        SELECT symbol, date, close, high, low, volume, rsi_14, macd_hist, sma_20, sma_60
        FROM daily_ohlcv WHERE date >= ? ORDER BY symbol, date
    """, (cutoff,))
    rows = c.fetchall()
    conn.close()
    return rows

def analyze_existing_params(trades_data):
    """分析現有參數的表現"""
    results = {}
    for sym, df in trades_data.groupby('symbol'):
        prices = df['close'].tolist()
        highs = df['high'].tolist()
        lows = df['low'].tolist()
        rsis = df['rsi_14'].fillna(50).tolist()
        macds = df['macd_hist'].fillna(0).tolist()
        sma20 = df['sma_20'].fillna(0).tolist()
        sma60 = df['sma_60'].fillna(0).tolist()

        trades = []
        for i in range(60, len(prices) - 15):
            entry_price = prices[i]
            rsi_i = rsis[i]
            macd_i = macds[i]
            ma20 = sma20[i] if sma20[i] > 0 else entry_price
            ma60 = sma60[i] if sma60[i] > 0 else entry_price

            # 现有策略：RSI 35-50 + MA多頭
            if 35 <= rsi_i <= 50 and ma20 > ma60 and macd_i > 0:
                atr = sum(max(highs[j]-lows[j], abs(highs[j]-prices[j-1]) if j > 0 else 0)
                         for j in range(max(0,i-13), i+1)) / 14
                sl = entry_price - atr * 1.5
                tp = entry_price + atr * 3.0
                for j in range(i+1, min(i+16, len(prices))):
                    if prices[j] <= sl:
                        trades.append({'result': 'loss', 'entry': entry_price, 'exit': sl, 'date': df.iloc[i]['date']})
                        break
                    elif prices[j] >= tp:
                        trades.append({'result': 'win', 'entry': entry_price, 'exit': tp, 'date': df.iloc[i]['date']})
                        break

        if trades:
            wins = sum(1 for t in trades if t['result'] == 'win')
            total = len(trades)
            results[sym] = {'wins': wins, 'total': total, 'wr': wins/total*100, 'trades': trades}

    return results

def test_new_strategies(trades_data, param_sets):
    """測試新策略參數組合"""
    print('\n' + '='*70)
    print('  沙盤推演 - 新策略參數測試')
    print('='*70)

    all_results = {}

    for param_name, params in param_sets.items():
        print('\n【測試】%s' % param_name)
        print('  RSI: %d-%d | MACD: %s | MA: %s | Vol: %s' % (
            params['rsi_min'], params['rsi_max'],
            '>0' if params['macd_positive'] else 'any',
            'bull' if params['ma_bull'] else 'any',
            '%.1fx' % params['vol_min'] if params['vol_min'] > 1 else 'off'))

        all_sym_trades = []
        all_wins = 0
        all_total = 0

        for sym, df in trades_data.groupby('symbol'):
            prices = df['close'].tolist()
            highs = df['high'].tolist()
            lows = df['low'].tolist()
            rsis = df['rsi_14'].fillna(50).tolist()
            macds = df['macd_hist'].fillna(0).tolist()
            sma20 = df['sma_20'].fillna(0).tolist()
            sma60 = df['sma_60'].fillna(0).tolist()
            vols = df['volume'].fillna(0).tolist()

            avg_vol = sum(vols) / len(vols) if vols else 1

            sym_trades = []
            for i in range(60, len(prices) - 15):
                rsi_i = rsis[i]
                macd_i = macds[i]
                ma20 = sma20[i] if sma20[i] > 0 else prices[i]
                ma60 = sma60[i] if sma60[i] > 0 else prices[i]
                vol_r = vols[i] / avg_vol if avg_vol > 0 else 1

                # RSI filter
                if not (params['rsi_min'] <= rsi_i <= params['rsi_max']):
                    continue

                # MACD filter
                if params['macd_positive'] and macd_i <= 0:
                    continue

                # MA filter
                if params['ma_bull'] and not (ma20 > ma60):
                    continue

                # Volume filter
                if params['vol_min'] > 1 and vol_r < params['vol_min']:
                    continue

                # Entry
                atr = sum(max(highs[j]-lows[j], abs(highs[j]-prices[j-1]) if j > 0 else 0)
                         for j in range(max(0,i-13), i+1)) / 14
                sl = prices[i] - atr * params['sl_mult']
                tp = prices[i] + atr * params['tp_mult']

                for j in range(i+1, min(i+16, len(prices))):
                    if prices[j] <= sl:
                        sym_trades.append('loss')
                        break
                    elif prices[j] >= tp:
                        sym_trades.append('win')
                        break

            all_sym_trades.append({'sym': sym, 'trades': sym_trades})
            all_wins += sum(1 for t in sym_trades if t == 'win')
            all_total += len(sym_trades)

        wr = all_wins / all_total * 100 if all_total > 0 else 0
        all_results[param_name] = {'wins': all_wins, 'total': all_total, 'wr': wr}

        print('  結果: %d/%d trades, WR=%.1f%%' % (all_wins, all_total, wr))

    return all_results

def main():
    print('='*70)
    print('  Tina 大腦回測歷史分析 - 沙盤推演系統')
    print('  ' + datetime.now().strftime('%Y-%m-%d %H:%M'))
    print('='*70)

    # 讀取歷史數據
    print('\n[1] 讀取回測數據（730天）...')
    rows = get_all_trades(730)
    print('  總記錄: %d rows' % len(rows))

    df = pd.DataFrame(rows, columns=['symbol','date','close','high','low','volume','rsi_14','macd_hist','sma_20','sma_60'])
    print('  股票數: %d' % df['symbol'].nunique())

    # 分析現有策略
    print('\n[2] 分析現有策略表現...')
    existing = analyze_existing_params(df)
    total_wins = sum(v['wins'] for v in existing.values())
    total_trades = sum(v['total'] for v in existing.values())
    existing_wr = total_wins / total_trades * 100 if total_trades > 0 else 0
    print('  現有策略: %d trades, WR=%.1f%%' % (total_trades, existing_wr))

    # 沙盤推演參數組
    param_sets = {
        '現有策略 (RSI 35-50)': {
            'rsi_min': 35, 'rsi_max': 50, 'macd_positive': True,
            'ma_bull': True, 'vol_min': 1.0, 'sl_mult': 1.5, 'tp_mult': 3.0
        },
        '放寬RSI (30-55)': {
            'rsi_min': 30, 'rsi_max': 55, 'macd_positive': True,
            'ma_bull': True, 'vol_min': 1.0, 'sl_mult': 1.5, 'tp_mult': 3.0
        },
        '放寬RSI (25-60)': {
            'rsi_min': 25, 'rsi_max': 60, 'macd_positive': True,
            'ma_bull': True, 'vol_min': 1.0, 'sl_mult': 1.5, 'tp_mult': 2.5
        },
        '取消MA多頭限制': {
            'rsi_min': 35, 'rsi_max': 55, 'macd_positive': True,
            'ma_bull': False, 'vol_min': 1.0, 'sl_mult': 1.5, 'tp_mult': 3.0
        },
        '加入量能過濾 (1.3x)': {
            'rsi_min': 35, 'rsi_max': 55, 'macd_positive': True,
            'ma_bull': True, 'vol_min': 1.3, 'sl_mult': 1.5, 'tp_mult': 3.0
        },
        '擴大TP (4x ATR)': {
            'rsi_min': 35, 'rsi_max': 55, 'macd_positive': True,
            'ma_bull': True, 'vol_min': 1.0, 'sl_mult': 1.5, 'tp_mult': 4.0
        },
        '縮短停損 (1x ATR)': {
            'rsi_min': 35, 'rsi_max': 55, 'macd_positive': True,
            'ma_bull': True, 'vol_min': 1.0, 'sl_mult': 1.0, 'tp_mult': 3.0
        },
        '完全放寬 (RSI 25-60, no MA, vol 1.0)': {
            'rsi_min': 25, 'rsi_max': 60, 'macd_positive': False,
            'ma_bull': False, 'vol_min': 1.0, 'sl_mult': 1.5, 'tp_mult': 3.0
        },
        '最佳化 (RSI 30-50, no MA, TP 4x)': {
            'rsi_min': 30, 'rsi_max': 50, 'macd_positive': False,
            'ma_bull': False, 'vol_min': 1.0, 'sl_mult': 1.5, 'tp_mult': 4.0
        },
    }

    # 執行沙盤推演
    results = test_new_strategies(df, param_sets)

    # 排序結果
    print('\n' + '='*70)
    print('  沙盤推演結果排名')
    print('='*70)
    sorted_results = sorted(results.items(), key=lambda x: (-x[1]['wr'], -x[1]['total']))
    for i, (name, r) in enumerate(sorted_results, 1):
        icon = '🥇' if i == 1 else ('🥈' if i == 2 else ('🥉' if i == 3 else '  '))
        print('%s %d. %s: %d trades, WR=%.1f%%' % (icon, i, name, r['total'], r['wr']))

    # 找出最佳策略
    best_name, best = sorted_results[0]
    improvement_wr = best['wr'] - existing_wr
    improvement_trades = best['total'] - total_trades

    print('\n' + '='*70)
    print('  裁判裁決')
    print('='*70)
    print('\n現有策略: %d trades, WR=%.1f%%' % (total_trades, existing_wr))
    print('最佳策略: %s' % best_name)
    print('  -> %d trades, WR=%.1f%%' % (best['total'], best['wr']))
    print()
    print('勝率改善: %+.1f%%' % improvement_wr)
    print('交易數改善: %+d' % improvement_trades)

    if improvement_wr > 5 and improvement_trades > 10:
        print('\n>>> 建議：採納 %s' % best_name)
    elif improvement_wr > 0:
        print('\n>>> 建議：逐步測試，先在 WATCH 名單上試用')
    else:
        print('\n>>> 建議：維持現有策略')

if __name__ == '__main__':
    main()