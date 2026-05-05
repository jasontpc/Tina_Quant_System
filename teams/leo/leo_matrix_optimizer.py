# -*- coding: utf-8 -*-
"""
Leo 科技股波段 — 多維回測矩陣優化器 v1.0
功能：
  1. 參數熱力圖（RSI Period x Threshold x Hold Days）
  2. Walk-Forward Analysis（訓練/驗證集）
  3. 夏普比率、恢復因子、盈虧比、穩定性係數
  4. CSV + 參數高原標註
  5. 專注 Leo 8檔科技股
"""

import sys, os, json, itertools, time
import yfinance as yf
import numpy as np
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

# ===== Leo 科技股池 =====
LEO_STOCKS = ['2330', '2454', '2317', '2379', '2376', '2382', '3665', '3034']

# ===== 參數矩陣 =====
RSI_PERIODS = [10, 12, 14, 16, 18]
RSI_THRESHOLDS = [40, 45, 50, 55, 60]   # 低於此值進場
HOLD_DAYS = [3, 5, 7, 10]
TP_PCTS = [10, 15, 20]                   # 停利 %
SL_PCTS = [6, 8, 10]                     # 停損 %

# ===== 市場環境定義 =====
# 用 MA200 斜率區分多頭/空頭/盤整
BULL_THRESHOLD = 0.5    # MA200 斜率 > 0.5% = 多頭
BEAR_THRESHOLD = -0.5   # MA200 斜率 < -0.5% = 空頭

# ===== 費用 =====
SLIPPAGE = 0.001        # 0.1% 滑點
COMMISSION = 0.001      # 0.1% 單邊手續費

OUTPUT_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leo\matrix_results'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ===== 指標計算 =====
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

def get_ma_slope(closes, period=200, bars=20):
    if len(closes) < period + bars:
        return 0.0
    ma_now = np.mean(closes[-period:])
    ma_prev = np.mean(closes[-(period+bars):-bars])
    return float((ma_now - ma_prev) / ma_prev * 100) if ma_prev != 0 else 0.0

def get_momentum(closes, bars=5):
    if len(closes) < bars + 1:
        return 0.0
    return float((closes[-1] / closes[-bars-1] - 1) * 100)

# ===== 資料取得 =====
def fetch_history(symbol, days=800):
    try:
        t = yf.Ticker(f'{symbol}.TW')
        h = t.history(period=f'{days}d')
        if h.empty or len(h) < 200:
            return None
        return {
            'close': h['Close'].values,
            'high': h['High'].values,
            'low': h['Low'].values,
            'dates': [d.strftime('%Y-%m-%d') for d in h.index],
        }
    except:
        return None

# ===== 市場環境分類 =====
def classify_regime(closes):
    slope = get_ma_slope(closes, 200, 20)
    if slope > BULL_THRESHOLD:
        return 'BULL'
    elif slope < BEAR_THRESHOLD:
        return 'BEAR'
    else:
        return 'RANGE'

# ===== 交易模擬 =====
def simulate_trade(entry_idx, data, params):
    closes = data['close']
    entry_price = float(closes[entry_idx]) * (1 + SLIPPAGE)  # 買貴
    hold_days = params['hold_days']
    tp_pct = params['tp_pct'] / 100
    sl_pct = params['sl_pct'] / 100

    target = entry_price * (1 + tp_pct)
    stop = entry_price * (1 - sl_pct)
    highest = entry_price

    if entry_idx + hold_days >= len(closes):
        return None

    exit_reason = 'hold_expired'
    exit_price = float(closes[entry_idx + hold_days]) * (1 - SLIPPAGE)

    for day in range(hold_days):
        if entry_idx + day >= len(closes):
            break
        cur = float(closes[entry_idx + day])
        highest = max(highest, cur)

        if cur >= target:
            exit_reason = 'take_profit'
            exit_price = cur * (1 - SLIPPAGE)
            break
        if cur <= stop:
            exit_reason = 'stop_loss'
            exit_price = cur * (1 + SLIPPAGE)
            break

    net = (exit_price - entry_price) / entry_price * 100 - COMMISSION * 2
    return {
        'return_pct': net,
        'exit_reason': exit_reason,
        'hold_days': hold_days,
    }

# ===== 單參數回測 =====
def backtest_params(symbol, rsi_period, rsi_threshold, hold_days, tp_pct, sl_pct, train_end='2024-06-01', val_end='2025-01-01'):
    data = fetch_history(symbol)
    if data is None:
        return None

    closes = data['close']
    dates = data['dates']
    regime_all = [classify_regime(closes[:i+1]) for i in range(len(closes))]

    train_trades, val_trades = [], []
    train_bull, train_bear, train_range = [], [], []
    val_bull, val_bear, val_range = [], [], []

    for i in range(rsi_period + 5, len(closes) - hold_days - 5, 3):
        rsi = get_rsi(closes[:i+1], rsi_period)
        mom5 = get_momentum(closes[:i+1], 5)
        ma20 = get_ma(closes[:i+1], 20)
        price = float(closes[i])
        pos_ma20 = ((price - ma20) / ma20 * 100) if ma20 != 0 else 0
        regime = regime_all[i] if i < len(regime_all) else 'RANGE'

        # 進場條件
        if rsi >= rsi_threshold:
            continue
        if pos_ma20 > 25:  # 過熱不追
            continue

        params = {'hold_days': hold_days, 'tp_pct': tp_pct, 'sl_pct': sl_pct}
        trade = simulate_trade(i, data, params)
        if trade is None:
            continue

        trade['date'] = dates[i] if i < len(dates) else ''
        trade['rsi'] = round(rsi, 1)
        trade['momentum'] = round(mom5, 2)
        trade['regime'] = regime

        # 分配到訓練/驗證 + 市場環境
        if trade['date'] < train_end:
            train_trades.append(trade)
            if regime == 'BULL':
                train_bull.append(trade)
            elif regime == 'BEAR':
                train_bear.append(trade)
            else:
                train_range.append(trade)
        elif trade['date'] < val_end:
            val_trades.append(trade)
            if regime == 'BULL':
                val_bull.append(trade)
            elif regime == 'BEAR':
                val_bear.append(trade)
            else:
                val_range.append(trade)

    return {
        'train': train_trades,
        'val': val_trades,
        'train_bull': train_bull, 'train_bear': train_bear, 'train_range': train_range,
        'val_bull': val_bull, 'val_bear': val_bear, 'val_range': val_range,
    }

# ===== 指標計算 =====
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
    pl_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0

    # 夏普
    if len(rets) > 1:
        rf = 0.01 / 252
        excess = [r/100 - rf for r in rets]
        sharpe = np.mean(excess) / np.std(excess) * np.sqrt(252) if np.std(excess) > 0 else 0
    else:
        sharpe = 0

    # 最大回撤
    cum = np.cumsum(rets)
    peak = np.maximum.accumulate(cum)
    dd = peak - cum
    max_dd = np.max(dd) if len(dd) > 0 else 0
    recovery = abs(total / max_dd) if max_dd != 0 else 0

    # 穩定性（回測報酬標準差）
    stability = np.std(rets) if len(rets) > 1 else 0

    return {
        'n': len(trades),
        'wr': wr,
        'avg': total / len(rets),
        'total': total,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'pl_ratio': pl_ratio,
        'sharpe': sharpe,
        'max_dd': max_dd,
        'recovery': recovery,
        'stability': stability,
        'max_gain': max(rets) if rets else 0,
        'max_loss': min(rets) if rets else 0,
    }

# ===== 主矩陣掃描 =====
def run_leo_matrix():
    print("=" * 70)
    print("  Leo 科技股波段 — 多維回測矩陣優化器")
    print("  股票: " + str(LEO_STOCKS))
    print("  訓練期: ~2024-06-01 | 驗證期: 2025-01-01~")
    print("=" * 70)

    all_results = []
    configs = list(itertools.product(RSI_PERIODS, RSI_THRESHOLDS, HOLD_DAYS, TP_PCTS, SL_PCTS))
    total = len(configs) * len(LEO_STOCKS)
    print(f"\n總組合: {len(configs)} configs x {len(LEO_STOCKS)} stocks = {total}")
    print("-" * 70)

    count = 0
    for rsi_p, rsi_t, hold, tp, sl in configs:
        for sym in LEO_STOCKS:
            result = backtest_params(sym, rsi_p, rsi_t, hold, tp, sl)
            if result is None:
                continue

            train_m = calc_metrics(result['train'])
            val_m = calc_metrics(result['val'])

            if train_m is None or val_m is None:
                continue
            if train_m['n'] < 10 or val_m['n'] < 3:
                continue

            # 市場環境表現
            def env_stats(trades_list):
                m = calc_metrics(trades_list)
                return m['wr'] if m else 0, m['avg'] if m else 0

            tb_wr, tb_avg = env_stats(result['train_bull'])
            vb_wr, vb_avg = env_stats(result['val_bull'])
            trb_wr, _ = env_stats(result['train_range'])
            vrb_wr, _ = env_stats(result['val_range'])

            # 過擬合指標
            wr_diff = abs(train_m['wr'] - val_m['wr'])
            ret_diff = abs(train_m['avg'] - val_m['avg'])

            # 綜合分數（避免過擬合）
            score = (
                min(train_m['sharpe'], val_m['sharpe']) * 10 +
                min(train_m['pl_ratio'], val_m['pl_ratio']) * 5 +
                min(train_m['wr'], val_m['wr']) * 0.5 -
                wr_diff * 3 - ret_diff * 10
            )

            all_results.append({
                'symbol': sym,
                'rsi_period': rsi_p,
                'rsi_threshold': rsi_t,
                'hold_days': hold,
                'tp_pct': tp,
                'sl_pct': sl,
                'train_n': train_m['n'],
                'train_wr': train_m['wr'],
                'train_avg': train_m['avg'],
                'train_sharpe': train_m['sharpe'],
                'train_pl': train_m['pl_ratio'],
                'train_recovery': train_m['recovery'],
                'train_stability': train_m['stability'],
                'val_n': val_m['n'],
                'val_wr': val_m['wr'],
                'val_avg': val_m['avg'],
                'val_sharpe': val_m['sharpe'],
                'val_pl': val_m['pl_ratio'],
                'val_recovery': val_m['recovery'],
                'val_bull_wr': vb_wr,
                'val_bull_avg': vb_avg,
                'val_range_wr': vrb_wr,
                'wr_diff': wr_diff,
                'ret_diff': ret_diff,
                'score': score,
            })

            count += 1
            if count % 50 == 0:
                print(f"  {count}/{total}...")

    # 排序
    all_results.sort(key=lambda x: x['score'], reverse=True)

    # CSV 輸出
    csv_file = os.path.join(OUTPUT_DIR, 'leo_matrix_results.csv')
    cols = ['symbol', 'rsi_period', 'rsi_threshold', 'hold_days', 'tp_pct', 'sl_pct',
            'train_n', 'train_wr', 'train_avg', 'train_sharpe', 'train_pl', 'train_stability',
            'val_n', 'val_wr', 'val_avg', 'val_sharpe', 'val_pl', 'val_recovery',
            'val_bull_wr', 'val_bull_avg', 'val_range_wr', 'wr_diff', 'ret_diff', 'score']
    with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
        f.write(','.join(cols) + '\n')
        for r in all_results:
            f.write(','.join(str(r[c]) for c in cols) + '\n')

    # Top 10
    print("\n" + "=" * 70)
    print("  Top 10 最優參數（按 Score）")
    print("=" * 70)
    print(f"{'Sym':<6} {'RSI_P':<6} {'Thresh':<6} {'Hold':<5} {'TP%':<5} {'SL%':<5} "
          f"{'Trn_WR':<8} {'Val_WR':<8} {'Trn_Shp':<9} {'Val_Shp':<9} {'Score':<8}")
    print("-" * 90)

    for r in all_results[:10]:
        print(f"{r['symbol']:<6} {r['rsi_period']:<6} {r['rsi_threshold']:<6} {r['hold_days']:<5} "
              f"{r['tp_pct']:<5} {r['sl_pct']:<5} "
              f"{r['train_wr']:<8.1f} {r['val_wr']:<8.1f} "
              f"{r['train_sharpe']:<9.2f} {r['val_sharpe']:<9.2f} {r['score']:<8.2f}")

    # 參數高原分析
    print("\n" + "=" * 70)
    print("  參數高原區（至少2檔股票重疊）")
    print("=" * 70)

    plateau = {}
    for r in all_results[:50]:
        key = (r['rsi_period'], r['rsi_threshold'], r['hold_days'], r['tp_pct'], r['sl_pct'])
        if key not in plateau:
            plateau[key] = []
        plateau[key].append(r)

    for key, items in sorted(plateau.items(), key=lambda x: -len(x[1])):
        if len(items) >= 2:
            avg_score = sum(i['score'] for i in items) / len(items)
            avg_wr = np.mean([i['val_wr'] for i in items])
            avg_sharpe = np.mean([i['val_sharpe'] for i in items])
            symbols = ', '.join(set(i['symbol'] for i in items))
            print(f"\n  RSI_P={key[0]} Thresh={key[1]} Hold={key[2]}d TP={key[3]}% SL={key[4]}%")
            print(f"    股票: {symbols}")
            print(f"    出現: {len(items)}次 | Avg Score={avg_score:.1f} | Val WR={avg_wr:.1f}% | Val Sharpe={avg_sharpe:.2f}")

    # 寫入最佳參數
    if all_results:
        best = all_results[0]
        best_params = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'source': 'leo_matrix_optimizer',
            'best_config': {
                'rsi_period': best['rsi_period'],
                'rsi_threshold': best['rsi_threshold'],
                'hold_days': best['hold_days'],
                'tp_pct': best['tp_pct'],
                'sl_pct': best['sl_pct'],
            },
            'train_wr': best['train_wr'],
            'val_wr': best['val_wr'],
            'train_sharpe': best['train_sharpe'],
            'val_sharpe': best['val_sharpe'],
            'val_pl_ratio': best['val_pl'],
            'val_recovery': best['val_recovery'],
            'score': best['score'],
            'symbols': list(set(r['symbol'] for r in all_results[:10])),
        }
        best_file = os.path.join(OUTPUT_DIR, 'best_leo_params.json')
        with open(best_file, 'w', encoding='utf-8') as f:
            json.dump(best_params, f, ensure_ascii=False, indent=2)
        print(f"\n  Best params: RSI_P={best['rsi_period']} Thresh={best['rsi_threshold']} Hold={best['hold_days']}d TP={best['tp_pct']}% SL={best['sl_pct']}%")
        print(f"  Val WR={best['val_wr']:.1f}% | Val Sharpe={best['val_sharpe']:.2f} | Score={best['score']:.2f}")
        print(f"\n  Written: {best_file}")

    print(f"\n  CSV: {csv_file}")
    print(f"  Total results: {len(all_results)}")

    return all_results

if __name__ == '__main__':
    run_leo_matrix()