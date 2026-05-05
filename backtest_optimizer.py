# -*- coding: utf-8 -*-
"""
多維度回測分析器 + 自動參數優化器 v1.0
功能：
  1. 讀取 Nana/Leo/Ray 三大團隊的回測數據
  2. 分析虧損原因、给出優化建議
  3. 執行 Grid Search 參數網格搜索
  4. 自動比較勝率 vs 頻率的平衡點
  5. 將最優參數寫入 best_params.json
用法:
  python backtest_optimizer.py [team] [mode]
  mode: report / grid_search / apply_best
"""

import sys, os, json, itertools, time
import yfinance as yf
import numpy as np
from datetime import datetime
from typing import List, Dict, Tuple

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams'
CONFIG_DIR = os.path.join(BASE_DIR, '..', 'skills', 'stock-analyzer', 'scripts')

# ========== 指標計算 ==========
def get_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50.0
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0:
        return 100
    return float(100 - (100 / (1 + avg_gain / avg_loss)))

def get_atr(highs, lows, closes, period=14):
    if len(closes) < period + 1:
        return 5.0
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        trs.append(tr)
    return float(np.mean(trs[-period:])) if trs else 5.0

def get_ma(closes, period):
    if len(closes) < period:
        return 0.0
    return float(np.mean(closes[-period:]))

def get_ma_slope(closes, period=20, bars=5):
    if len(closes) < period + bars:
        return 0.0
    ma_now = np.mean(closes[-period:])
    ma_prev = np.mean(closes[-(period+bars):-bars])
    return float((ma_now - ma_prev) / ma_prev * 100) if ma_prev != 0 else 0.0

def get_adx(highs, lows, closes, period=14):
    """計算 ADX（趨勢強度指標）"""
    if len(closes) < period * 2:
        return 20.0
    # 簡化 ADX：使用價格相對於均線的位置
    ma = get_ma(closes, period)
    slope = get_ma_slope(closes, period, 5)
    return max(10.0, min(80.0, 20.0 + abs(slope) * 3))

def get_momentum(closes, period=20):
    if len(closes) < period + 1:
        return 0.0
    return float((closes[-1] / closes[-period] - 1) * 100)

# ========== 資料取得 ==========
def fetch_history(symbol, days=400):
    try:
        t = yf.Ticker(f'{symbol}.TW')
        h = t.history(period=f'{days}d')
        if h.empty or len(h) < 60:
            return None
        return {
            'close': h['Close'].values,
            'high': h['High'].values,
            'low': h['Low'].values,
            'volume': h['Volume'].values,
            'symbol': symbol
        }
    except:
        return None

# ========== 單筆交易模擬 ==========
def simulate_trade(entry_idx, data, params):
    """
    根據 params 模擬一筆交易
    params: {rsi_entry, atr_tp, atr_sl, hold_days, trend_filter, ma_period, adx_threshold}
    """
    closes = data['close']
    highs = data['high']
    lows = data['low']

    entry_price = float(closes[entry_idx])
    atr = get_atr(highs[entry_idx:], lows[entry_idx:], closes[entry_idx:])

    tp_mult = params.get('atr_tp_mult', 3.0)
    sl_mult = params.get('atr_sl_mult', 2.0)
    hold_days = params.get('hold_days', 7)
    trailing_atr = params.get('trailing_atr', 2.0)

    target = entry_price + (atr * tp_mult)
    stop = entry_price - (atr * sl_mult)
    highest = entry_price

    exit_reason = 'hold_expired'
    exit_price = float(closes[entry_idx + hold_days]) if entry_idx + hold_days < len(closes) else float(closes[-1])
    exit_day = hold_days

    for day in range(hold_days):
        if entry_idx + day >= len(closes):
            break
        cur = float(closes[entry_idx + day])
        highest = max(highest, cur)

        trailing = highest - (atr * trailing_atr)
        if cur < trailing:
            exit_reason = 'trailing_stop'
            exit_price = cur
            exit_day = day
            break
        if cur >= target:
            exit_reason = 'take_profit'
            exit_price = cur
            exit_day = day
            break
        if cur <= stop:
            exit_reason = 'stop_loss'
            exit_price = cur
            exit_day = day
            break

    ret = (exit_price - entry_price) / entry_price * 100
    return {
        'entry_idx': entry_idx,
        'entry_price': entry_price,
        'exit_price': exit_price,
        'exit_reason': exit_reason,
        'hold_days': exit_day + 1,
        'return_pct': ret,
        'atr': atr
    }

# ========== 參數網格搜索 ==========
def grid_search(team='nana', stocks=None, start_date='2025-01-01', end_date='2026-04-25'):
    """
    Grid Search：找出最佳參數組合
    目標：Score = WinRate * (TradeCount ** 0.5) * (AvgReturn / abs(AvgLoss))
    """
    if stocks is None:
        if team == 'nana':
            stocks = ['2330','2317','2454','2303','2382','2881','2884','2891','3008','3037','3231','3443','4532','4770','4938','4952','5203','5215','5388','5471','5538','5876','5880','6116','6139','6176','6183','6230','6257','6285','6409','6415','6446','6550','6579','6581','6770','6789','8016','8028','8046','8081','8131','8150','8261','8454','8464']
        elif team == 'leo':
            stocks = ['2330','2454','2317','2379','2376','2382','3034']
        else:
            stocks = ['0050','0056','00878','00919','00713','00646']

    # 參數網格
    param_grid = {
        'rsi_entry_min': [30, 35, 40],
        'rsi_entry_max': [50, 55, 60],
        'atr_tp_mult': [2.5, 3.0, 3.5],
        'atr_sl_mult': [1.5, 2.0, 2.5],
        'hold_days': [5, 7, 10],
        'trailing_atr': [1.5, 2.0, 2.5],
        'score_min': [30, 35, 38, 40],
        'adx_threshold': [15, 20, 25],  # 趨勢過濾：ADX > 此值才進場
    }

    # 簡化：先跑固定參數組合，找出邊際改善方向
    results = []

    # 組合生成（笛卡爾積，但限制總組合數）
    keys = list(param_grid.keys())
    values = [param_grid[k] for k in keys]

    print("=" * 60)
    print(f"  Grid Search — {team.upper()} 波段系統")
    print(f"  股票池: {len(stocks)} 檔")
    print(f"  目標: 最大化 Score = WR * sqrt(交易次數) * (AvgRet/|AvgLoss|)")
    print("=" * 60)

    # 測試不同 RSI + ATR 組合（固定其餘參數）
    test_configs = [
        # RSI 寬鬆版本（增加頻率）
        {'rsi_entry_min': 30, 'rsi_entry_max': 60, 'atr_tp_mult': 3.0, 'atr_sl_mult': 1.5, 'hold_days': 5, 'trailing_atr': 1.5, 'score_min': 30, 'adx_threshold': 15},
        # RSI 嚴格版本（提高勝率）
        {'rsi_entry_min': 40, 'rsi_entry_max': 50, 'atr_tp_mult': 3.5, 'atr_sl_mult': 2.0, 'hold_days': 7, 'trailing_atr': 2.0, 'score_min': 40, 'adx_threshold': 25},
        # 中間版本（平衡）
        {'rsi_entry_min': 35, 'rsi_entry_max': 55, 'atr_tp_mult': 3.0, 'atr_sl_mult': 2.0, 'hold_days': 7, 'trailing_atr': 2.0, 'score_min': 35, 'adx_threshold': 20},
        # 高停利版本
        {'rsi_entry_min': 35, 'rsi_entry_max': 55, 'atr_tp_mult': 4.0, 'atr_sl_mult': 1.5, 'hold_days': 10, 'trailing_atr': 2.0, 'score_min': 35, 'adx_threshold': 20},
        # 短持版本（提高頻率）
        {'rsi_entry_min': 30, 'rsi_entry_max': 60, 'atr_tp_mult': 2.0, 'atr_sl_mult': 2.0, 'hold_days': 3, 'trailing_atr': 1.5, 'score_min': 30, 'adx_threshold': 15},
    ]

    for cfg in test_configs:
        print(f"\n測試配置: RSI={cfg['rsi_entry_min']}-{cfg['rsi_entry_max']}, "
              f"TP={cfg['atr_tp_mult']}x, SL={cfg['atr_sl_mult']}x, HOLD={cfg['hold_days']}d, "
              f"TRAIL={cfg['trailing_atr']}x, SCORE>={cfg['score_min']}, ADX>{cfg['adx_threshold']}")

        all_trades = []
        stock_stats = {}

        for sym in stocks:
            data = fetch_history(sym, days=400)
            if data is None:
                continue

            closes = data['close']
            highs = data['high']
            lows = data['low']

            if len(closes) < 60:
                continue

            # ADX 趨勢過濾
            adx = get_adx(highs, lows, closes)

            sym_trades = []
            for i in range(20, len(closes) - 10, 5):
                rsi = get_rsi(closes[:i+1])
                ma20 = get_ma(closes[:i+1], 20)
                ma20_diff = ((closes[i] - ma20) / ma20 * 100) if ma20 != 0 else 0
                slope = get_ma_slope(closes[:i+1])
                momentum = get_momentum(closes[:i+1])

                # 進場條件
                if not (cfg['rsi_entry_min'] <= rsi <= cfg['rsi_entry_max']):
                    continue
                if abs(ma20_diff) > 3.0:
                    continue
                if adx < cfg['adx_threshold']:
                    continue

                # 分數計算（Nana制）
                score = 0
                if 40 <= rsi <= 50: score += 20
                elif 50 < rsi <= 55: score += 10
                if abs(ma20_diff) < 2: score += 15
                elif abs(ma20_diff) < 3: score += 10
                if momentum > 3: score += 10
                elif momentum > 0: score += 5
                if slope > 1.0: score += 8
                elif slope > 0.5: score += 5

                if score < cfg['score_min']:
                    continue

                trade = simulate_trade(i, data, cfg)
                trade['symbol'] = sym
                trade['rsi'] = round(rsi, 1)
                trade['score'] = score
                trade['adx'] = adx
                sym_trades.append(trade)

            if sym_trades:
                stock_stats[sym] = {
                    'trades': len(sym_trades),
                    'wr': len([t for t in sym_trades if t['return_pct'] > 0]) / len(sym_trades) * 100,
                    'avg': sum(t['return_pct'] for t in sym_trades) / len(sym_trades)
                }
                all_trades.extend(sym_trades)

        if not all_trades:
            print("  無交易")
            continue

        wins = [t for t in all_trades if t['return_pct'] > 0]
        losses = [t for t in all_trades if t['return_pct'] <= 0]
        wr = len(wins) / len(all_trades) * 100
        avg_ret = sum(t['return_pct'] for t in all_trades) / len(all_trades)
        avg_win = sum(t['return_pct'] for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t['return_pct'] for t in losses) / len(losses) if losses else 0

        # Score = WinRate * sqrt(TradeCount) * (AvgReturn / |AvgLoss|)
        score = wr * (len(all_trades) ** 0.5) * (abs(avg_ret) / abs(avg_loss) if avg_loss != 0 else 1)

        results.append({
            'config': cfg,
            'total_trades': len(all_trades),
            'win_rate': wr,
            'avg_return': avg_ret,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'max_gain': max(t['return_pct'] for t in all_trades),
            'max_loss': min(t['return_pct'] for t in all_trades),
            'score': score,
            'stock_stats': stock_stats
        })

        print(f"  交易: {len(all_trades)}筆, WR: {wr:.1f}%, Avg: {avg_ret:+.2f}%, "
              f"AvgWin: {avg_win:+.2f}%, AvgLoss: {avg_loss:+.2f}%")
        print(f"  Score: {score:.1f}")

    # 排序
    results.sort(key=lambda x: x['score'], reverse=True)

    print("\n" + "=" * 60)
    print("  Grid Search 結果排名")
    print("=" * 60)
    for i, r in enumerate(results[:5]):
        cfg = r['config']
        print(f"\n#{i+1} Score={r['score']:.1f}")
        print(f"   交易: {r['total_trades']}筆, WR={r['win_rate']:.1f}%, Avg={r['avg_return']:+.2f}%")
        print(f"   RSI={cfg['rsi_entry_min']}-{cfg['rsi_entry_max']}, TP={cfg['atr_tp_mult']}x, "
              f"SL={cfg['atr_sl_mult']}x, HOLD={cfg['hold_days']}d, "
              f"TRAIL={cfg['trailing_atr']}x, SCORE>={cfg['score_min']}, ADX>{cfg['adx_threshold']}")

    return results

# ========== 輸出多維度回測報告 ==========
def generate_backtest_report(team='nana'):
    """產生詳細回測報告"""
    import os
    report_file = os.path.join(BASE_DIR, team, 'reports', 'sim_trades.json')
    if not os.path.exists(report_file):
        print(f'找不到 {report_file}，請先執行 unified_backtest.py')
        return None

    with open(report_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    trades = data.get('trades', [])
    stats = data.get('stats', {})

    print("=" * 60)
    print(f"  多維度回測報告 — {team.upper()}")
    print(f"  回測區間: {data.get('backtest_period', 'N/A')}")
    print("=" * 60)
    print()

    print(f"  總交易: {stats.get('total_trades', 0)}筆")
    print(f"  勝率: {stats.get('win_rate', 0):.1f}%")
    print(f"  平均報酬: {stats.get('avg_return', 0):+.2f}%")
    print(f"  平均獲利: {stats.get('avg_win', 0):+.2f}%")
    print(f"  平均虧損: {stats.get('avg_loss', 0):+.2f}%")
    print(f"  最大獲利: {stats.get('max_gain', 0):+.2f}%")
    print(f"  最大虧損: {stats.get('max_loss', 0):+.2f}%")
    print()

    # 虧損交易分析
    losses = [t for t in trades if t.get('return_pct', 0) <= 0]
    wins = [t for t in trades if t.get('return_pct', 0) > 0]

    print(f"  虧損交易分析（{len(losses)}筆）")
    print(f"  ─ 平均虧損: {stats.get('avg_loss', 0):+.2f}%")

    # 按原因分類
    by_reason = {}
    for t in losses:
        reason = t.get('exit_reason', 'unknown')
        if reason not in by_reason:
            by_reason[reason] = []
        by_reason[reason].append(t)

    print(f"  虧損原因分布:")
    for reason, ts in sorted(by_reason.items(), key=lambda x: -len(x[1])):
        avg = sum(t['return_pct'] for t in ts) / len(ts)
        print(f"    {reason}: {len(ts)}筆, Avg={avg:+.2f}%")

    # 勝出交易分析
    print()
    print(f"  勝出交易分析（{len(wins)}筆）")
    avg_win_only = sum(t['return_pct'] for t in wins) / len(wins) if wins else 0
    print(f"  平均獲利: {avg_win_only:+.2f}%")

    by_reason_win = {}
    for t in wins:
        reason = t.get('exit_reason', 'unknown')
        if reason not in by_reason_win:
            by_reason_win[reason] = []
        by_reason_win[reason].append(t)

    print(f"  獲利原因分布:")
    for reason, ts in sorted(by_reason_win.items(), key=lambda x: -len(x[1])):
        avg = sum(t['return_pct'] for t in ts) / len(ts)
        print(f"    {reason}: {len(ts)}筆, Avg={avg:+.2f}%")

    print()
    print("  優化建議:")
    print("  1. 若 stop_loss 虧損過多 → 提高 ATR停損 倍數（1.5x → 2.0x）")
    print("  2. 若 hold_expired 過多 → 縮短持有天數（7 → 5天）")
    print("  3. 若 trailing_stop 頻繁觸發 → 放寬 trailing ATR（2.0x → 2.5x）")
    print("  4. 若進場不足 → 降低 score_min（35 → 30）")
    print("  5. 若勝率低於40% → 加入 ADX>20 趨勢過濾")

    return data


# ========== 自動寫入最佳參數 ==========
def save_best_params(team='nana', results=None):
    """將最佳參數寫入 best_params.json"""
    if results is None or len(results) == 0:
        print('沒有結果可寫入')
        return

    best = results[0]  # 已按 score 排序
    best_config = best['config']

    save_dir = os.path.join(BASE_DIR, team)
    os.makedirs(save_dir, exist_ok=True)

    params_file = os.path.join(save_dir, 'best_params.json')
    output = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'team': team,
        'best_config': best_config,
        'backtest_result': {
            'total_trades': best['total_trades'],
            'win_rate': best['win_rate'],
            'avg_return': best['avg_return'],
            'avg_win': best['avg_win'],
            'avg_loss': best['avg_loss'],
            'score': best['score'],
        }
    }

    with open(params_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"最佳參數已寫入: {params_file}")
    print(json.dumps(best_config, indent=2))
    return best_config


if __name__ == '__main__':
    import sys
    team = sys.argv[1] if len(sys.argv) > 1 else 'nana'
    mode = sys.argv[2] if len(sys.argv) > 2 else 'grid_search'

    if mode == 'report':
        generate_backtest_report(team)
    elif mode == 'grid_search':
        results = grid_search(team)
        if results:
            save_best_params(team, results)
    else:
        print('用法: python backtest_optimizer.py [nana|leo|ray] [report|grid_search]')
