# -*- coding: utf-8 -*-
"""
ray_backtest_manager.py — 暴力回測引擎（VectorBT + 標籤化 + 三位一體）

功能：
1. 三層次語意標籤（MA/MACD/KDJ 三位一體）
2. 向量化計算標籤信號（RSI/MACD/KDJ/BB）
3. VectorBT 暴力參數掃描
4. Walk-Forward 驗證 + 蒙地卡羅模擬
5. 產出 Sharpe/PnL/勝率報告
6. 批量多標的 + RSI 樓梯掃描

使用方法：
  python scripts/ray_backtest_manager.py --ticker NVDA --period 5y --rsi-entry 40
  python scripts/ray_backtest_manager.py --tickers NVDA,META,AMD --period 5y --rsi-entry 40
  python scripts/ray_backtest_manager.py --tickers NVDA,META,AMD --period 5y  (樓梯掃描 35/40/45)
"""

import sys, os, json, time, warnings
from pathlib import Path
import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

# ── 路徑設定 ──────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR / "scripts" / "utils"))

try:
    from ray_guard import ray_singleton
except ImportError:
    def ray_singleton(fn): return fn

try:
    import vectorbt as vbt
except ImportError:
    print("[ERROR] VectorBT not installed. Run: pip install vectorbt")
    sys.exit(1)

# ── 語意標籤矩陣工廠（三位一體）─────────────────────────────────────────
def compute_labels(close: pd.Series, period: int = 14, rsi_entry: int = 35) -> dict:
    """將價格數據轉化為標籤化布林矩陣
    
    三位一體進場哲學：
      均線（MA）是路徑 → 確認趨勢方向
      MACD 是引擎推力 → 確認動能真實性
      KDJ 是油門 → 捕捉精確進場時機
    
    Args:
        close: 價格序列
        period: RSI 計算週期（預設 14）
        rsi_entry: RSI 進場閾值（預設 35，可調整為 40/45）
    """
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi_series = 100 - (100 / (1 + rs))

    # ── RSI 標籤（動態閾值）────────────────────────────────
    rsi_above_70 = rsi_series > 70       # [OVERHEATED]
    rsi_below_entry = rsi_series < rsi_entry  # [OVERSOLD]（可調整：35/40/45）
    rsi_above_80 = rsi_series > 80        # [RSI_EXTREME]
    rsi_ideal = (rsi_series >= 40) & (rsi_series <= 55)  # [RSI_IDEAL_ZONE]

    # ── MACD（引擎推力）────────────────────────────────────
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    macd_hist = macd - macd_signal
    macd_above_0 = macd_hist > 0         # [TREND_INTACT] 零軸上方
    macd_below_0 = macd_hist < 0          # [MOMENTUM_DRY] 零軸下方
    macd_cross_up = (macd_hist > 0) & (macd_hist.shift() <= 0)  # [MACD_TURN_POSITIVE]

    # ── KDJ（油門）────────────────────────────────────────
    high_roll = close.rolling(9).max()
    low_roll = close.rolling(9).min()
    rsv = (close - low_roll) / (high_roll - low_roll + 1e-9) * 100
    k = rsv.ewm(alpha=1/3).mean()
    d = k.ewm(alpha=1/3).mean()
    j = 3 * k - 2 * d
    kdj_cross_up = (k > d) & (k.shift() <= d.shift())  # 黃金交叉
    kdj_cross_down = (k < d) & (k.shift() >= d.shift())  # 死亡交叉
    kdj_overbought = j > 90              # [OVERHEATED]
    kdj_oversold = j < 20                # [KDJ_OVERSOLD]
    kdj_low_cross = kdj_cross_up & (k < 40)  # [KDJ_LOW_GOLDEN]（低位黃金交叉）

    # ── BB─────────────────────────────────────────────────
    bb_ma = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_upper = bb_ma + 2 * bb_std
    bb_lower = bb_ma - 2 * bb_std
    bb_pos = (close - bb_lower) / (bb_upper - bb_lower + 1e-9) * 100
    bb_above_90 = bb_pos > 90            # [BB_BREAK]
    bb_below_15 = bb_pos < 15            # [OVERSOLD]
    bb_normal = (bb_pos >= 20) & (bb_pos <= 45)  # [BB_NORMAL_ZONE]

    # ── MA 趨勢（路徑方向）───────────────────────────────────
    ma5 = close.ewm(span=5).mean()
    ma20 = close.ewm(span=20).mean()
    ma60 = close.ewm(span=60).mean()
    ma_bull_3tier = (ma5 > ma20) & (ma20 > ma60)   # 三層多頭
    ma_bull_2tier = (ma20 > ma60) & ~ma_bull_3tier  # 兩層多頭
    ma_bear_3tier = (ma5 < ma20) & (ma20 < ma60)   # 三層空頭
    ma_bull = ma_bull_3tier | ma_bull_2tier
    ma_bear = ma_bear_3tier

    # ── 三位一體組合進場邏輯 ────────────────────────────────
    # 路徑正確（MA多頭）+ 引擎有推力（MACD零軸上）+ 油門踩下（KDJ低位金叉）
    entries = (
        rsi_below_entry              # RSI 超賣
        & macd_above_0              # 動能確認（引擎有推力）
        & (bb_pos < 30)             # BB 超賣
        & ma_bull                   # 趨勢確認（路徑正確）
    )
    exits = rsi_above_70 | rsi_above_80 | kdj_overbought   # [OVERHEATED]

    # ── Vol 標籤（需 volumn data）───────────────────────────
    try:
        vol = pd.Series(range(len(close)), index=close.index).astype(float) * 0.5  # placeholder
        vol_ma = vol.rolling(20).mean()
        vol_ratio = vol / vol_ma.replace(0, np.nan)
        vol_div = vol_ratio < 0.5   # [VOL_PRICE_DIVERGENCE]
    except:
        vol_div = pd.Series(False, index=close.index)

    return {
        'close': close,
        'entries': entries,
        'exits': exits,
        'rsi': rsi_series,
        'bb_pos': bb_pos,
        'macd_hist': macd_hist,
        'k': k, 'd': d, 'j': j,
        'ma_bull': ma_bull,
        'ma_bear': ma_bear,
        'ma_bull_3tier': ma_bull_3tier,
        'ma_bull_2tier': ma_bull_2tier,
        'rsi_entry': rsi_entry,
        'labels': {
            'OVERHEATED': rsi_above_70 | kdj_overbought | bb_above_90,
            'OVERSOLD': rsi_below_entry | bb_below_15,
            'RSI_IDEAL_ZONE': rsi_ideal,
            'TREND_INTACT': macd_above_0,
            'MOMENTUM_DRY': macd_below_0,
            'MACD_TURN_POSITIVE': macd_cross_up,
            'KDJ_CROSS_UP': kdj_cross_up,
            'KDJ_LOW_GOLDEN': kdj_low_cross,
            'KDJ_CROSS_DOWN': kdj_cross_down,
            'BB_BREAK': bb_above_90,
            'BB_NORMAL_ZONE': bb_normal,
            'RSI_EXTREME': rsi_above_80,
            'KDJ_OVERSOLD': kdj_oversold,
            'VOL_PRICE_DIVERGENCE': vol_div,
            'MA_BULL_3TIER': ma_bull_3tier,
            'MA_BULL_2TIER': ma_bull_2tier,
            'MA_BEAR_3TIER': ma_bear_3tier,
        }
    }

# ── Walk-Forward 驗證 ─────────────────────────────────────
def walk_forward_validate(close: pd.Series, train_ratio: float = 0.7, rsi_entry: int = 35) -> dict:
    """三層次 Walk-Forward 驗證（訓練集/測試集/一致性）
    
    修復：測試集 entries/exits 位置已修正（原本放反了）
    """
    n = int(len(close) * train_ratio)
    train = close[:n]
    test = close[n:]

    labels_train = compute_labels(train, rsi_entry=rsi_entry)
    labels_test = compute_labels(test, rsi_entry=rsi_entry)

    # 訓練集回測（正常：entries 進場，exits 出場）
    pf_train = vbt.Portfolio.from_signals(
        labels_train['close'],
        labels_train['entries'],
        labels_train['exits'],
        freq='D'
    )

    # 測試集回測（✅ 修正：entries=entries, exits=exits，不再反轉）
    pf_test = vbt.Portfolio.from_signals(
        labels_test['close'],
        labels_test['entries'],   # ✅ 進場信號
        labels_test['exits'],     # ✅ 出場信號
        freq='D'
    )

    train_return = pf_train.total_return()
    test_return = pf_test.total_return()

    return {
        'train_return': float(train_return),
        'test_return': float(test_return),
        'train_sharpe': float(pf_train.sharpe()),
        'test_sharpe': float(pf_test.sharpe()),
        'train_trades': int(pf_train.trades.count()),
        'test_trades': int(pf_test.trades.count()),
        'consistency': abs(test_return / train_return) if train_return != 0 else 0,
        'train_win_rate': float(pf_train.trades.win_rate()) if pf_train.trades.count() > 0 else 0,
        'test_win_rate': float(pf_test.trades.win_rate()) if pf_test.trades.count() > 0 else 0,
    }

# ── 蒙地卡羅模擬 ──────────────────────────────────────────
def monte_carlo_sim(returns: pd.Series, n_sims: int = 1000) -> dict:
    results = []
    for _ in range(n_sims):
        shuffled = returns.sample(frac=1, replace=True).values
        cumulative = (1 + shuffled).prod()
        results.append(cumulative - 1)
    results = np.array(results)
    return {
        'mean': np.mean(results),
        'median': np.median(results),
        'p5': np.percentile(results, 5),
        'p95': np.percentile(results, 95),
        'worst': np.min(results),
        'best': np.max(results),
        'win_rate': np.mean(results > 0)
    }

# ── 單一標的回測 ─────────────────────────────────────────
@ray_singleton
def run_single_backtest(ticker: str, period: str, rsi_entry: int) -> dict:
    """對單一標的執行完整回測"""
    print(f"\n{'='*50}")
    print(f"  {ticker} | RSI < {rsi_entry} | {period}")
    print(f"{'='*50}")
    log = {
        "started": time.strftime("%Y-%m-%d %H:%M:%S"),
        "ticker": ticker,
        "period": period,
        "rsi_entry": rsi_entry,
    }

    # Step 1: 載入數據
    print(f"[1/5] 載入歷史數據...")
    try:
        import yfinance as yf
        df = yf.Ticker(ticker).history(period=period, auto_adjust=True)
        close = df['Close'].astype(float)
        print(f"  資料：{len(close)} 筆，{close.index[0].date()} ~ {close.index[-1].date()}")
        log['data_points'] = len(close)
    except Exception as e:
        print(f"[ERROR] 資料載入失敗：{e}")
        return {"error": str(e), "ticker": ticker}

    # Step 2: 計算標籤（使用動態 RSI 閾值）
    print(f"[2/5] 計算語意標籤矩陣（RSI < {rsi_entry}）...")
    labels = compute_labels(close, rsi_entry=rsi_entry)
    entries = labels['entries']
    exits = labels['exits']
    print(f"  進場信号：{entries.sum()} 筆 | 出場信号：{exits.sum()} 筆")

    # Step 3: 基礎回測（VectorBT）
    print(f"[3/5] VectorBT 向量化回測...")
    pf = vbt.Portfolio.from_signals(close, entries, exits, freq='D')
    total_return = pf.total_return()
    sharpe = pf.sharpe()
    trades_count = pf.trades.count()
    win_rate = pf.trades.win_rate()

    print(f"  總報酬：{total_return:+.2%}")
    print(f"  Sharpe：{sharpe:.2f}")
    print(f"  交易次數：{trades_count} | 勝率：{win_rate:.0%}")
    if trades_count > 0:
        wins = pf.trades.win()
        losses = pf.trades.loss()
        if len(wins) > 0:
            print(f"  平均獲利：+{wins.mean():.2%} | 平均虧損：{losses.mean():.2%}")

    log['results'] = {
        'total_return': float(total_return),
        'sharpe': float(sharpe),
        'trades': int(trades_count),
        'win_rate': float(win_rate)
    }

    # Step 4: Walk-Forward 驗證
    print(f"[4/5] Walk-Forward 驗證（70/30 split）...")
    wf = walk_forward_validate(close, train_ratio=0.7, rsi_entry=rsi_entry)
    print(f"  訓練集報酬：{wf['train_return']:+.2%} | Sharpe：{wf['train_sharpe']:.2f} | 交易：{wf['train_trades']}次")
    print(f"  測試集報酬：{wf['test_return']:+.2%} | Sharpe：{wf['test_sharpe']:.2f} | 交易：{wf['test_trades']}次")
    print(f"  一致性比率：{wf['consistency']:.2f}（越接近1越穩健）")
    log['walk_forward'] = wf

    # Step 5: 蒙地卡羅
    print(f"[5/5] 蒙地卡羅模擬（1000次）...")
    returns_series = close.pct_change().dropna()
    mc = monte_carlo_sim(returns_series, n_sims=1000)
    print(f"  平均報酬：{mc['mean']:+.2%}")
    print(f"  5% 分位：{mc['p5']:+.2%} | 95% 分位：{mc['p95']:+.2%}")
    print(f"  最差模擬：{mc['worst']:+.2%} | 最佳模擬：{mc['best']:+.2%}")
    print(f"  勝率：{mc['win_rate']:.0%}")
    log['monte_carlo'] = mc

    # 產出報告
    log['completed'] = time.strftime("%Y-%m-%d %H:%M:%S")
    report_path = BASE_DIR / "stores" / f"backtest_{ticker}_{period.replace('y','')}_rsi{rsi_entry}_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

    print(f"\n=== {ticker} 回測完成 ===")
    print(f"報酬：{total_return:+.2%} | Sharpe：{sharpe:.2f} | 交易：{trades_count}次 | 勝率：{win_rate:.0%}")
    print(f"報告：{report_path.name}")
    print(f"Walk-Forward 一致性：{wf['consistency']:.2f}")

    return log


# ── 批量多標的掃描 ─────────────────────────────────────────
def run_batch_backtest(tickers: list, period: str, rsi_entry: int) -> dict:
    """批量回測多支股票，輸出整合報告"""
    print(f"\n{'#'*60}")
    print(f"  批量回測模式 | RSI < {rsi_entry} | 標的：{len(tickers)}支")
    print(f"{'#'*60}")
    
    results = {}
    summary = []
    
    for ticker in tickers:
        try:
            log = run_single_backtest(ticker, period, rsi_entry)
            results[ticker] = log
            
            if 'error' not in log:
                r = log['results']
                wf = log.get('walk_forward', {})
                summary.append({
                    'ticker': ticker,
                    'return': r['total_return'],
                    'sharpe': r['sharpe'],
                    'trades': r['trades'],
                    'win_rate': r['win_rate'],
                    'wf_consistency': wf.get('consistency', 0),
                    'wf_test_return': wf.get('test_return', 0),
                })
        except Exception as e:
            print(f"[ERROR] {ticker} 回測失敗：{e}")
            results[ticker] = {"error": str(e)}
    
    # 產出批量報告
    batch_report = {
        'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
        'rsi_entry': rsi_entry,
        'period': period,
        'tickers': tickers,
        'summary': sorted(summary, key=lambda x: x['sharpe'], reverse=True),
        'results': results,
    }
    
    batch_path = BASE_DIR / "stores" / f"batch_backtest_rsi{rsi_entry}_{period.replace('y','')}_report.json"
    with open(batch_path, "w", encoding="utf-8") as f:
        json.dump(batch_report, f, ensure_ascii=False, indent=2)
    
    # 排名表格
    print(f"\n{'='*70}")
    print(f"  批量回測結果排名（RSI < {rsi_entry}）")
    print(f"{'='*70}")
    print(f"{'標的':<8} {'總報酬':>10} {'Sharpe':>8} {'交易':>6} {'勝率':>6} {'WF一致性':>10} {'WF測試報酬':>12}")
    print(f"{'-'*70}")
    for s in summary:
        print(f"{s['ticker']:<8} {s['return']:>+9.1%} {s['sharpe']:>7.2f} {s['trades']:>5d} {s['win_rate']:>5.0%} {s['wf_consistency']:>9.2f} {s['wf_test_return']:>+11.2%}")
    print(f"{'-'*70}")
    print(f"批量報告：{batch_path.name}")
    
    return batch_report


# ── CLI ────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Ray Backtest Manager — VectorBT 暴力回測引擎 + 三位一體')
    parser.add_argument('--ticker', default=None, help='單一標的（如 NVDA）')
    parser.add_argument('--tickers', default=None, help='批量標的，逗號分隔（如 NVDA,META,AMD）')
    parser.add_argument('--period', default='5y', help='回測週期（預設 5y）')
    parser.add_argument('--rsi-entry', type=int, default=35, choices=[35, 40, 45],
                        help='RSI 進場閾值（預設 35，越高進場越多）')
    parser.add_argument('--mode', default='fast', help='模式（fast/batch）')
    args = parser.parse_args()

    # 批量模式
    if args.tickers:
        tickers = [t.strip() for t in args.tickers.split(',')]
        print(f"🚀 批量模式：{tickers}")
        batch_report = run_batch_backtest(tickers, args.period, args.rsi_entry)
    # 單一模式
    elif args.ticker:
        result = run_single_backtest(args.ticker, args.period, args.rsi_entry)
        print(f"\n回測結果：{result}")
    # RSI 樓梯掃描（35/40/45 三組）
    else:
        print("📊 RSI 樓梯掃描模式（35 → 40 → 45）")
        default_tickers = ['NVDA', 'META', 'AMD', 'AMAT', 'QQQ']
        for rsi_val in [35, 40, 45]:
            print(f"\n{'#'*60}")
            print(f"  RSI 閾值掃描：< {rsi_val}")
            print(f"{'#'*60}")
            run_batch_backtest(default_tickers, args.period, rsi_val)