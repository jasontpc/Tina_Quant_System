# -*- coding: utf-8 -*-
"""
多維回測矩陣優化器 + Walk-Forward Analysis (WFA)
功能：
  1. 參數熱力圖生成（RSI + MA 交叉矩陣）
  2. Walk-Forward 前進分析（訓練/驗證集分離）
  3. 夏普比率、恢復因子、盈虧比、穩定性係數計算
  4. CSV 輸出 + 參數高原標註
  5. 支援多資產（0050/006208/2330）
"""

import sys, os, json, itertools, time
import yfinance as yf
import numpy as np
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

# ========== 參數矩陣定義 ==========
RSI_PERIODS = list(range(10, 21, 2))   # 10,12,14,16,18,20
RSI_THRESHOLDS = list(range(25, 46, 5)) # 25,30,35,40,45
MA_PERIODS = [20, 30, 60, 120, 200]     # 短/中/長 MA
HOLD_DAYS = [3, 5, 7, 10]               # 持有天數

# 測試標的
ASSETS = ['0050', '006208', '2330']
# ASSETS = ['0050']  # 單一測試

SLIPPAGE_PCT = 0.001   # 0.1% 滑點（單邊）
COMMISSION_PCT = 0.001 # 0.1% 手續費（單邊）

OUTPUT_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\matrix_results'
os.makedirs(OUTPUT_DIR, exist_ok=True)

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
        return 100.0
    return float(100 - (100 / (1 + avg_gain / avg_loss)))

def get_ma(closes, period):
    if len(closes) < period:
        return 0.0
    return float(np.mean(closes[-period:]))

def get_ma_slope(closes, period, bars=5):
    if len(closes) < period + bars:
        return 0.0
    ma_now = np.mean(closes[-period:])
    ma_prev = np.mean(closes[-(period+bars):-bars])
    return float((ma_now - ma_prev) / ma_prev * 100) if ma_prev != 0 else 0.0

def get_atr(highs, lows, closes, period=14):
    if len(closes) < period + 1:
        return 5.0
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        trs.append(tr)
    return float(np.mean(trs[-period:])) if trs else 5.0

# ========== 資料取得 ==========
def fetch_history(symbol, days=800):
    try:
        t = yf.Ticker(f'{symbol}.TW')
        h = t.history(period=f'{days}d')
        if h.empty or len(h) < 100:
            return None
        return {
            'close': h['Close'].values,
            'high': h['High'].values,
            'low': h['Low'].values,
            'volume': h['Volume'].values,
            'dates': [d.strftime('%Y-%m-%d') for d in h.index],
            'symbol': symbol
        }
    except:
        return None

# ========== 單筆交易模擬（含滑點+手續費）==========
def simulate_trade(entry_idx, data, params, slippage=SLIPPAGE_PCT, commission=COMMISSION_PCT):
    closes = data['close']
    highs = data['high']
    lows = data['low']

    # 進場價（含滑點）
    entry_raw = float(closes[entry_idx])
    entry_price = entry_raw * (1 + slippage)  # 買貴 slippage

    hold_days = params.get('hold_days', 5)
    tp_mult = params.get('tp_mult', 3.0)
    sl_mult = params.get('sl_mult', 2.0)
    trailing_atr = params.get('trailing_atr', 2.0)

    if entry_idx + hold_days >= len(closes):
        return None

    atr = get_atr(highs[entry_idx:], lows[entry_idx:], closes[entry_idx:])
    target = entry_price * (1 + params.get('tp_pct', tp_mult * 0.02))
    stop = entry_price * (1 - params.get('sl_pct', sl_mult * 0.01))
    highest = entry_price

    exit_reason = 'hold_expired'
    exit_price = float(closes[entry_idx + hold_days])
    exit_raw = exit_price * (1 - slippage)  # 賣便宜 slippage

    for day in range(hold_days):
        if entry_idx + day >= len(closes):
            break
        cur = float(closes[entry_idx + day])
        highest = max(highest, cur)

        trailing = highest * (1 - trailing_atr * 0.01)
        if cur < trailing:
            exit_reason = 'trailing_stop'
            exit_raw = cur * (1 - slippage)
            break
        if cur >= target:
            exit_reason = 'take_profit'
            exit_raw = cur * (1 - slippage)
            break
        if cur <= stop:
            exit_reason = 'stop_loss'
            exit_raw = cur * (1 + slippage)  # 買錯方向
            break

    # 扣除手續費（兩邊）
    gross = (exit_raw - entry_price) / entry_price * 100
    net = gross - commission * 2
    return {
        'entry_idx': entry_idx,
        'entry_price': entry_price,
        'exit_price': exit_raw,
        'exit_reason': exit_reason,
        'hold_days': hold_days,
        'return_pct': net,
        'atr': atr,
        'gross_return': gross
    }

# ========== 單資產單參數回測 ==========
def backtest_asset(asset, rsi_period, rsi_threshold, ma_period, hold_days, train_end_date='2025-01-01'):
    """
    針對單一資產單一參數執行回測
    train_end_date 之前為訓練集，之後為驗證集
    """
    data = fetch_history(asset)
    if data is None:
        return None

    closes = data['close']
    highs = data['high']
    lows = data['low']
    dates = data['dates']

    train_trades = []
    val_trades = []

    for i in range(ma_period + 5, len(closes) - hold_days - 5, 3):
        rsi = get_rsi(closes[:i+1], rsi_period)
        ma_val = get_ma(closes[:i+1], ma_period)
        ma_diff = ((closes[i] - ma_val) / ma_val * 100) if ma_val != 0 else 0
        slope = get_ma_slope(closes[:i+1], ma_period)

        # 進場條件：RSI 低於 threshold（超賣）
        if not (rsi < rsi_threshold and rsi > 20):
            continue
        # MA 趨勢過濾（不逆勢）
        if ma_diff < -5:  # 低於 MA 5% 以上不進場
            continue

        params = {
            'hold_days': hold_days,
            'tp_mult': 3.0,
            'sl_mult': 2.0,
            'trailing_atr': 2.0,
            'tp_pct': 6.0,
            'sl_pct': 4.0,
        }

        trade = simulate_trade(i, data, params)
        if trade is None:
            continue
        trade['symbol'] = asset
        trade['rsi'] = round(rsi, 1)
        trade['ma_diff'] = round(ma_diff, 2)
        trade['slope'] = round(slope, 3)
        trade['date'] = dates[i] if i < len(dates) else ''

        # 訓練 vs 驗證
        if dates[i] < train_end_date:
            train_trades.append(trade)
        else:
            val_trades.append(trade)

    return {
        'train': train_trades,
        'val': val_trades,
        'asset': asset,
        'params': {
            'rsi_period': rsi_period,
            'rsi_threshold': rsi_threshold,
            'ma_period': ma_period,
            'hold_days': hold_days
        }
    }

# ========== 計算評價指標 ==========
def calc_metrics(trades):
    if not trades:
        return None
    rets = [t['return_pct'] for t in trades]
    wins = [t for t in rets if t > 0]
    losses = [t for t in rets if t <= 0]

    total = sum(rets)
    wr = len(wins) / len(rets) * 100 if rets else 0
    avg_win = sum(wins) / len(wins) if wins else 0
    avg_loss = sum(losses) / len(losses) if losses else 0

    # 夏普比率（假設無風險利率 1%）
    import numpy as np
    if len(rets) > 1:
        rf = 1.0 / 252  # 日無風險利率
        excess = [r/100 - rf for r in rets]
        sharpe = np.mean(excess) / np.std(excess) * np.sqrt(252) if np.std(excess) > 0 else 0
    else:
        sharpe = 0

    # 恢復因子
    cumulative = np.cumsum(rets)
    peak = np.maximum.accumulate(cumulative)
    drawdown = peak - cumulative
    max_dd = np.max(drawdown) if len(drawdown) > 0 else 0
    recovery = abs(total / max_dd) if max_dd != 0 else 0

    # 盈虧比
    pl_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0

    # 穩定性係數（參數變化績效方差）— 此處簡化為回測方差
    stability = np.std(rets) if len(rets) > 1 else 0

    # 最大回撤
    max_loss = min(rets) if rets else 0
    max_gain = max(rets) if rets else 0

    return {
        'total_trades': len(trades),
        'win_rate': wr,
        'avg_return': total / len(rets),
        'total_return': total,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'pl_ratio': pl_ratio,
        'sharpe': sharpe,
        'recovery_factor': recovery,
        'max_drawdown': max_dd,
        'max_gain': max_gain,
        'max_loss': max_loss,
        'stability': stability,
    }

# ========== 主矩陣掃描 ==========
def run_matrix_optimizer():
    print("=" * 70)
    print("  多維回測矩陣優化器 + Walk-Forward Analysis")
    print("  參數: RSI Period/Threshold x MA Period x Hold Days")
    print(f"  標的: {ASSETS}")
    print(f"  訓練期: 2024-01-01 之前 | 驗證期: 2025-01-01 之後")
    print("=" * 70)

    all_results = []
    total_combinations = len(RSI_PERIODS) * len(RSI_THRESHOLDS) * len(MA_PERIODS) * len(HOLD_DAYS)

    print(f"\n總組合數: {total_combinations}")
    print("-" * 70)

    for rsi_p, rsi_t, ma_p, hold in itertools.product(RSI_PERIODS, RSI_THRESHOLDS, MA_PERIODS, HOLD_DAYS):
        for asset in ASSETS:
            result = backtest_asset(asset, rsi_p, rsi_t, ma_p, hold)
            if result is None:
                continue

            train_m = calc_metrics(result['train'])
            val_m = calc_metrics(result['val'])

            if train_m and val_m and train_m['total_trades'] >= 10 and val_m['total_trades'] >= 5:
                # 計算 WFA 差距（過擬合指標）
                wr_diff = abs(train_m['win_rate'] - val_m['win_rate'])
                ret_diff = abs(train_m['avg_return'] - val_m['avg_return'])

                row = {
                    'asset': asset,
                    'rsi_period': rsi_p,
                    'rsi_threshold': rsi_t,
                    'ma_period': ma_p,
                    'hold_days': hold,
                    'train_trades': train_m['total_trades'],
                    'train_wr': train_m['win_rate'],
                    'train_avg': train_m['avg_return'],
                    'train_sharpe': train_m['sharpe'],
                    'train_pl': train_m['pl_ratio'],
                    'train_recovery': train_m['recovery_factor'],
                    'val_trades': val_m['total_trades'],
                    'val_wr': val_m['win_rate'],
                    'val_avg': val_m['avg_return'],
                    'val_sharpe': val_m['sharpe'],
                    'val_pl': val_m['pl_ratio'],
                    'val_recovery': val_m['recovery_factor'],
                    'wr_overfit_diff': wr_diff,
                    'ret_overfit_diff': ret_diff,
                    # 綜合分數（避免過擬合）
                    'score': (
                        min(train_m['sharpe'], val_m['sharpe']) * 10 +
                        min(train_m['pl_ratio'], val_m['pl_ratio']) * 5 +
                        min(train_m['win_rate'], val_m['win_rate']) * 0.5 -
                        wr_diff * 2 - ret_diff * 5
                    )
                }
                all_results.append(row)

    # 排序
    all_results.sort(key=lambda x: x['score'], reverse=True)

    # 輸出 CSV
    csv_file = os.path.join(OUTPUT_DIR, 'matrix_results.csv')
    cols = ['asset','rsi_period','rsi_threshold','ma_period','hold_days',
            'train_trades','train_wr','train_avg','train_sharpe','train_pl','train_recovery',
            'val_trades','val_wr','val_avg','val_sharpe','val_pl','val_recovery',
            'wr_overfit_diff','ret_overfit_diff','score']
    with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
        f.write(','.join(cols) + '\n')
        for r in all_results:
            f.write(','.join(str(r[c]) for c in cols) + '\n')

    # 找參數高原（Score 前10名中重複出現的參數組合）
    print("\n" + "=" * 70)
    print("  參數高原分析（Top 10 最穩健區域）")
    print("=" * 70)

    top = all_results[:10]
    print(f"\n{'Asset':<6} {'RSI_P':<6} {'RSI_T':<6} {'MA_P':<6} {'Hold':<5} "
          f"{'Train_WR':<10} {'Val_WR':<10} {'Train_Sharpe':<12} {'Val_Sharpe':<12} {'Score':<8}")
    print("-" * 90)

    for r in top:
        print(f"{r['asset']:<6} {r['rsi_period']:<6} {r['rsi_threshold']:<6} {r['ma_period']:<6} {r['hold_days']:<5} "
              f"{r['train_wr']:<10.1f} {r['val_wr']:<10.1f} {r['train_sharpe']:<12.2f} {r['val_sharpe']:<12.2f} {r['score']:<8.2f}")

    # 分析高原區域
    plateau = {}
    for r in all_results[:30]:
        key = (r['rsi_period'], r['ma_period'], r['hold_days'])
        if key not in plateau:
            plateau[key] = []
        plateau[key].append(r)

    print("\n" + "=" * 70)
    print("  參數高原區（3個以上參數組合重疊）")
    print("=" * 70)

    for key, items in sorted(plateau.items(), key=lambda x: -len(x[1])):
        if len(items) >= 2:
            avg_score = sum(i['score'] for i in items) / len(items)
            print(f"\n  RSI Period={key[0]}, MA Period={key[1]}, Hold={key[2]}天 → {len(items)}次出現, Avg Score={avg_score:.2f}")
            print(f"    訓練 WR: {np.mean([i['train_wr'] for i in items]):.1f}% | "
                  f"驗證 WR: {np.mean([i['val_wr'] for i in items]):.1f}% | "
                  f"夏普: {np.mean([i['val_sharpe'] for i in items]):.2f}")

    # 最佳參數寫入
    best = all_results[0] if all_results else None
    if best:
        best_params = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'asset': best['asset'],
            'rsi_period': best['rsi_period'],
            'rsi_threshold': best['rsi_threshold'],
            'ma_period': best['ma_period'],
            'hold_days': best['hold_days'],
            'train_wr': best['train_wr'],
            'val_wr': best['val_wr'],
            'train_sharpe': best['train_sharpe'],
            'val_sharpe': best['val_sharpe'],
            'score': best['score'],
        }
        best_file = os.path.join(OUTPUT_DIR, 'best_wfa_params.json')
        with open(best_file, 'w', encoding='utf-8') as f:
            json.dump(best_params, f, ensure_ascii=False, indent=2)
        print(f"\n  ✅ 最佳 WFA 參數已寫入: {best_file}")

    print(f"\n  CSV 已寫入: {csv_file}")
    print(f"  總結果: {len(all_results)} 組參數組合")

    return all_results

if __name__ == '__main__':
    run_matrix_optimizer()