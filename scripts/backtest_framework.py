# -*- coding: utf-8 -*-
"""
Tina Backtest Framework v1.0
==============================
通用歷史數據回測框架 — 支援波段/Growth-Long/DCA 三種策略比較

資料來源：data/yfinance.db（本地 K 線資料庫）
策略池：swing / growth_long / dca / etf

用法：
  python backtest_framework.py                          # 全策略回測（2023-2026）
  python backtest_framework.py --strategy swing         # 只測波段
  python backtest_framework.py --start 2024-01-01      # 自訂起始日
  python backtest_framework.py --symbols AMD,NVDA,META # 指定標的
  python backtest_framework.py --report                 # 輸出 HTML 報告
"""

import sqlite3, json, os, sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from collections import defaultdict

# ── 路徑設定 ────────────────────────────────────────────────────────────────
WORKSPACE   = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
DB_PATH     = WORKSPACE / 'data' / 'yfinance.db'
OUTPUT_DIR  = WORKSPACE / 'data' / 'backtest_results'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── 策略參數 ────────────────────────────────────────────────────────────────
STRATEGIES = {

    # ===== 策略 A：波段交易（Swing）=====
    'swing': {
        'description': 'RSI均值回歸波段策略，持有5-10天',
        'entry_rsi_max': 55,
        'entry_rsi_min': 30,
        'ma_required': True,           # MA20 > MA60 多頭排列
        'stop_loss_pct': 0.08,         # -8%
        'stop_loss_atr_x': 1.5,
        'take_profit_pct': 0.10,
        'take_profit_atr_x': 3.5,
        'trailing_atr_x': 2.0,
        'max_hold_days': 7,
        'position_pct': 0.10,          # 單筆投入10%資金
        'min_atr_pct': 0.005,
        'adx_threshold': 20,
        'institutional_filter': True,
    },

    # ===== 策略 B：長期持有成長股（Growth-Long）=====
    'growth_long': {
        'description': '長期持有成長股，目標+50-100%，持有6-24個月',
        'entry_rsi_max': 50,
        'entry_rsi_min': 20,
        'ma_required': True,
        'stop_loss_pct': 0.20,         # -20%
        'take_profit_pct': 0.50,      # +50%（不常見）
        'trailing_pct': 0.20,         # 追蹤止損：高點回撤20%
        'max_hold_days': 540,         # 18個月
        'position_pct': 0.15,         # 單筆投入15%資金
        'revenue_growth_min': 0.15,   # 營收YoY >15%（代理）
        'hold_period_exit': True,
        'rsi_overbought_exit': 75,
    },

    # ===== 策略 C：DCA（定期定額）=====
    'dca': {
        'description': '定期定額指數投資，不在乎進場時機',
        'entry_rsi_max': 100,          # 始終進場
        'dca_frequency_days': 30,     # 每月一次
        'position_pct': 0.05,          # 每次投入5%資金
        'stop_loss_pct': 0.30,        # 寬鬆停損
        'max_hold_days': 1825,        # 5年
        'evaluate_exit_rsi': True,    # RSI>70考慮賣出
        'evaluate_exit_rsi_threshold': 70,
    },

    # ===== 策略 D：ETF 趨勢追蹤 ======
    'etf_trend': {
        'description': 'ETF 趨勢追蹤，MA黃金交叉進場',
        'entry_ma_cross': True,        # MA5 > MA20 黃金交叉
        'entry_rsi_max': 65,
        'stop_loss_pct': 0.10,
        'take_profit_pct': 0.15,
        'trailing_pct': 0.08,
        'max_hold_days': 60,
        'position_pct': 0.20,
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# 資料庫存取
# ═══════════════════════════════════════════════════════════════════════════

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def get_symbols(universe: str = 'all', limit: Optional[int] = None) -> List[str]:
    """取得資料庫中的股票標的"""
    conn = get_db()
    c = conn.cursor()

    query = '''
        SELECT DISTINCT d.symbol
        FROM daily_ohlcv d
        WHERE d.date >= '2020-01-01'
        AND d.close IS NOT NULL AND d.close > 0
        AND d.volume > 0
    '''
    if universe == 'tw':
        query += " AND d.symbol LIKE '%.TW'"
    elif universe == 'us':
        query += " AND (d.symbol NOT LIKE '%.TW' AND d.symbol NOT LIKE '%.TWO')"

    query += " ORDER BY d.symbol"

    if limit:
        query += f" LIMIT {limit}"

    c.execute(query)
    result = [r[0] for r in c.fetchall()]
    conn.close()
    return result


def load_ohlcv(symbol: str, start: str = '2020-01-01', end: str = '2026-12-31') -> pd.DataFrame:
    """從本地 DB 載入 K 線資料"""
    conn = get_db()
    df = pd.read_sql('''
        SELECT date, open, high, low, close, volume,
               change_pct, sma_20, sma_60, sma_120,
               rsi_14, atr_14, macd, macd_sig, macd_hist,
               bb_upper, bb_middle, bb_lower, vol_ratio
        FROM daily_ohlcv
        WHERE symbol=? AND date >= ? AND date <= ?
        ORDER BY date
    ''', conn, params=(symbol, start, end), parse_dates=['date'])
    conn.close()

    if df.empty:
        return df

    # 清理不良數據
    df = df[df['close'] > 0]
    df = df[df['date'] >= '2020-01-01']  # 移除遠期異常數據

    # 填補少數指標
    df['rsi_14'] = df['rsi_14'].fillna(50)
    df['atr_14'] = df['atr_14'].fillna(df['close'] * 0.02)
    df['sma_20'] = df['sma_20'].fillna(df['close'])
    df['sma_60'] = df['sma_60'].fillna(df['close'])
    df['macd_hist'] = df['macd_hist'].fillna(0)

    return df


# ═══════════════════════════════════════════════════════════════════════════
# 指標計算
# ═══════════════════════════════════════════════════════════════════════════

def calc_rsi(closes: np.ndarray, period: int = 14) -> np.ndarray:
    if len(closes) < period + 1:
        return np.full_like(closes, 50.0)
    deltas = np.diff(closes, prepend=closes[0])
    gains  = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_g  = pd.Series(gains).rolling(period).mean().values
    avg_l  = pd.Series(losses).rolling(period).mean().values
    rs     = avg_g / np.where(avg_l == 0, 1e-10, avg_l)
    return 100 - (100 / (1 + rs))


def calc_atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> np.ndarray:
    trs = np.zeros(len(highs))
    trs[1:] = np.maximum(
        highs[1:] - lows[1:],
        np.maximum(
            np.abs(highs[1:] - closes[:-1]),
            np.abs(lows[1:] - closes[:-1])
        )
    )
    return pd.Series(trs).rolling(period).mean().fillna(0).values


def calc_ma(closes: np.ndarray, n: int) -> np.ndarray:
    return pd.Series(closes).rolling(n).mean().bfill().values


# ═══════════════════════════════════════════════════════════════════════════
# 進場/出场信號
# ═══════════════════════════════════════════════════════════════════════════

def generate_signals(df: pd.DataFrame, strategy: str) -> pd.DataFrame:
    """根據策略產生進場/出场信號"""
    params = STRATEGIES[strategy]
    df = df.copy()

    closes = df['close'].values
    highs  = df['high'].values
    lows   = df['low'].values
    rsi    = df['rsi_14'].fillna(50).values
    atr    = df['atr_14'].fillna(df['close'] * 0.02).values
    sma20  = df['sma_20'].values
    sma60  = df['sma_60'].values
    macd_h = df['macd_hist'].fillna(0).values
    volume = df['volume'].values

    # 基礎指標
    ma20   = calc_ma(closes, 20)
    ma60   = calc_ma(closes, 60)
    ma5    = calc_ma(closes, 5)
    ma200  = calc_ma(closes, 200)

    # 動量指標
    mom5   = (closes / np.roll(closes, 5) - 1) * 100
    mom20  = (closes / np.roll(closes, 20) - 1) * 100

    # ATR
    atr14  = calc_atr(highs, lows, closes, 14)

    entry_signals = [0] * len(df)
    exit_signals  = [0] * len(df)
    signal_reasons = [''] * len(df)

    # 停損/停利追蹤（持倉期間）
    in_pos    = False
    entry_p   = 0.0
    entry_atr = 0.0
    entry_idx = 0
    high_water = 0.0

    for i in range(50, len(df)):  # 從第50根開始（需要足夠歷史數據）
        price = closes[i]
        date  = df['date'].iloc[i]

        if not in_pos:
            # ── 進場條件檢查 ──
            can_entry = True

            if strategy == 'swing':
                # 波段進場邏輯
                if rsi[i] >= params['entry_rsi_max'] or rsi[i] < params['entry_rsi_min']:
                    can_entry = False
                if params['ma_required'] and not (sma20[i] > sma60[i]):
                    can_entry = False
                if atr14[i] / price < params['min_atr_pct']:
                    can_entry = False

            elif strategy == 'growth_long':
                # Growth-Long 進場邏輯
                if rsi[i] >= params['entry_rsi_max']:
                    can_entry = False
                if params['ma_required'] and not (ma20[i] > ma60[i]):
                    can_entry = False

            elif strategy == 'dca':
                # DCA：固定頻率進場，無視價格
                pass  # 始終可進場

            elif strategy == 'etf_trend':
                # ETF 趨勢：MA5 > MA20 黃金交叉
                if not (ma5[i] > ma20[i]):
                    can_entry = False
                if rsi[i] >= params['entry_rsi_max']:
                    can_entry = False

            if can_entry and i % (params.get('dca_frequency_days', 1) or 1) == 0:
                entry_signals[i] = 1
                signal_reasons[i] = f'ENTRY:RSI={rsi[i]:.1f}'
                in_pos    = True
                entry_p   = price
                entry_atr = atr14[i]
                entry_idx = i
                high_water = price

        else:
            # ── 持倉期間：檢查出场條件 ──
            high_water = max(high_water, price)
            ret_from_entry = (price / entry_p - 1) * 100
            days_held = i - entry_idx

            should_exit = False
            exit_reason = ''

            # 停損檢查
            if price <= entry_p * (1 - params['stop_loss_pct']):
                should_exit = True; exit_reason = f'SL:{ret_from_entry:.1f}%'
            elif params.get('stop_loss_atr_x') and price <= entry_p - entry_atr * params['stop_loss_atr_x']:
                should_exit = True; exit_reason = f'SL_ATR:{ret_from_entry:.1f}%'

            # 停利檢查（Growth/Swing）
            if not should_exit and params.get('take_profit_pct'):
                if ret_from_entry >= params['take_profit_pct'] * 100:
                    should_exit = True; exit_reason = f'TP:{ret_from_entry:.1f}%'

            # 追蹤止損
            if not should_exit and params.get('trailing_pct'):
                trail_loss = (price / high_water - 1) * 100
                if trail_loss <= -params['trailing_pct'] * 100:
                    should_exit = True; exit_reason = f'TRAIL:{trail_loss:.1f}%'
                elif params.get('trailing_atr_x'):
                    if price <= entry_p - entry_atr * params['trailing_atr_x']:
                        should_exit = True; exit_reason = f'TRAIL_ATR:{ret_from_entry:.1f}%'

            # RSI 過高出场（Growth）
            if not should_exit and params.get('evaluate_exit_rsi') and rsi[i] > params['evaluate_exit_rsi_threshold']:
                should_exit = True; exit_reason = f'RSI_HIGH:{rsi[i]:.1f}'

            # 持有期到期
            if not should_exit and days_held >= params['max_hold_days']:
                should_exit = True; exit_reason = f'HOLD_MAX:{days_held}d'

            # RSI 超買出场（Growth-Long）
            if not should_exit and params.get('rsi_overbought_exit') and rsi[i] > params['rsi_overbought_exit']:
                should_exit = True; exit_reason = f'RSI_OB:{rsi[i]:.1f}'

            if should_exit:
                exit_signals[i] = 1
                signal_reasons[i] = signal_reasons[i] + f' | {exit_reason}' if signal_reasons[i] else f'EXIT: {exit_reason}'
                in_pos = False

    df['entry_signal'] = entry_signals
    df['exit_signal']  = exit_signals
    df['signal_reason'] = signal_reasons

    return df


# ═══════════════════════════════════════════════════════════════════════════
# 回測引擎
# ═══════════════════════════════════════════════════════════════════════════

def run_backtest(symbol: str, strategy: str, start: str = '2023-01-01', end: str = '2026-05-08') -> Dict:
    """對單一標的執行單一策略回測"""
    params = STRATEGIES[strategy]
    df = load_ohlcv(symbol, start, end)

    if df.empty or len(df) < 100:
        return None

    df = generate_signals(df, strategy)

    # 模擬交易
    capital      = 1_000_000    # 初始資金 100萬
    position     = 0
    shares        = 0
    entry_price   = 0
    entry_date     = None
    trades        = []
    equity_curve  = [capital]

    for i, row in df.iterrows():
        price = row['close']
        date  = row['date']

        if row['entry_signal'] == 1 and position == 0:
            # 進場
            alloc     = capital * params['position_pct']
            shares    = int(alloc / price)
            cost      = shares * price
            position  = 1
            entry_price = price
            entry_date  = date

        elif row['exit_signal'] == 1 and position == 1:
            # 出场
            proceeds  = shares * price
            pnl_pct   = (proceeds / (shares * entry_price) - 1) * 100
            pnl_abs   = proceeds - (shares * entry_price)

            capital   += pnl_abs
            trades.append({
                'symbol':     symbol,
                'entry_date': str(entry_date)[:10],
                'exit_date':   str(date)[:10],
                'entry_price': entry_price,
                'exit_price':  price,
                'shares':      shares,
                'pnl_pct':     pnl_pct,
                'pnl_abs':     pnl_abs,
                'reason':      row['signal_reason'],
                'days_held':   (date - entry_date).days if entry_date else 0,
            })
            position = 0
            shares   = 0

        equity_curve.append(capital)

    # 關閉最後持倉（如果還在場）
    if position == 1:
        last_price = df['close'].iloc[-1]
        pnl_pct    = (last_price / entry_price - 1) * 100
        pnl_abs    = shares * (last_price - entry_price)
        capital   += pnl_abs
        trades.append({
            'symbol':     symbol,
            'entry_date': str(entry_date)[:10],
            'exit_date':   str(df['date'].iloc[-1])[:10],
            'entry_price': entry_price,
            'exit_price':  last_price,
            'shares':      shares,
            'pnl_pct':     pnl_pct,
            'pnl_abs':     pnl_abs,
            'reason':      'END_OF_PERIOD',
            'days_held':   (df['date'].iloc[-1] - entry_date).days if entry_date else 0,
        })

    if not trades:
        return None

    # 計算績效指標
    df_trades = pd.DataFrame(trades)
    total_return  = (capital / 1_000_000 - 1) * 100
    win_trades    = df_trades[df_trades['pnl_pct'] > 0]
    loss_trades   = df_trades[df_trades['pnl_pct'] <= 0]
    win_rate      = len(win_trades) / len(df_trades) * 100 if trades else 0
    avg_win       = win_trades['pnl_pct'].mean() if not win_trades.empty else 0
    avg_loss      = loss_trades['pnl_pct'].mean() if not loss_trades.empty else 0
    profit_factor = abs(win_trades['pnl_abs'].sum() / loss_trades['pnl_abs'].sum()) if not loss_trades.empty and loss_trades['pnl_abs'].sum() != 0 else 999

    # 最大回落
    eq = np.array(equity_curve)
    peak = np.maximum.accumulate(eq)
    drawdown = (eq - peak) / peak * 100
    max_dd = drawdown.min()

    # Sharpe（简化版，使用日報酬）
    daily_returns = np.diff(equity_curve) / np.array(equity_curve)[:-1]
    daily_returns = daily_returns[np.isfinite(daily_returns)]
    sharpe = daily_returns.mean() / daily_returns.std() * np.sqrt(252) if len(daily_returns) > 5 and daily_returns.std() > 0 else 0

    return {
        'symbol':         symbol,
        'strategy':      strategy,
        'total_return':  total_return,
        'num_trades':    len(trades),
        'win_rate':      win_rate,
        'avg_win_pct':   avg_win,
        'avg_loss_pct':  avg_loss,
        'profit_factor': profit_factor,
        'max_drawdown': max_dd,
        'sharpe_ratio':  sharpe,
        'trades':        trades,
        'final_capital': capital,
    }


def run_multi_strategy(symbol: str, start: str = '2023-01-01', end: str = '2026-05-08') -> Dict:
    """對單一標的執行所有策略比較"""
    results = {}
    for strat in STRATEGIES:
        r = run_backtest(symbol, strat, start, end)
        if r:
            results[strat] = r
    return results


def run_universe_backtest(symbols: List[str], strategy: str,
                           start: str = '2023-01-01', end: str = '2026-05-08',
                           progress: bool = True) -> List[Dict]:
    """對整個宇宙執行單一策略回測"""
    all_results = []
    total = len(symbols)

    for idx, sym in enumerate(symbols):
        if progress and idx % 10 == 0:
            print(f'  [{idx}/{total}] {sym}...')
        try:
            r = run_backtest(sym, strategy, start, end)
            if r:
                all_results.append(r)
        except Exception as e:
            pass

    return all_results


def aggregate_results(results: List[Dict]) -> Dict:
    """彙總多檔股票的回測結果"""
    if not results:
        return {}

    total_return = [r['total_return'] for r in results]
    win_rates     = [r['win_rate'] for r in results]
    num_trades    = [r['num_trades'] for r in results]

    return {
        'num_symbols':   len(results),
        'avg_return':    np.mean(total_return),
        'median_return': np.median(total_return),
        'max_return':    np.max(total_return),
        'min_return':    np.min(total_return),
        'avg_win_rate':  np.mean(win_rates),
        'avg_trades':    np.mean(num_trades),
        'best_symbol':   max(results, key=lambda x: x['total_return'])['symbol'],
        'worst_symbol':  min(results, key=lambda x: x['total_return'])['symbol'],
        'all_results':    results,
    }


# ═══════════════════════════════════════════════════════════════════════════
# 報告輸出
# ═══════════════════════════════════════════════════════════════════════════

def print_summary(results: List[Dict], title: str = 'Backtest Results'):
    if not results:
        print('[EMPTY] No results to display')
        return

    print('=' * 70)
    print(f'  {title}')
    print('=' * 70)
    print(f'  {"Symbol":<12} {"Return":>8} {"WinRate":>8} {"Trades":>7} {"Sharpe":>8} {"MaxDD":>8}')
    print('-' * 70)

    for r in sorted(results, key=lambda x: x['total_return'], reverse=True):
        print(f"  {r['symbol']:<12} {r['total_return']:>+7.2f}% {r['win_rate']:>7.1f}% {r['num_trades']:>7} {r['sharpe_ratio']:>8.2f} {r['max_drawdown']:>8.2f}%")

    agg = aggregate_results(results)
    print()
    print(f'  Summary: {agg["num_symbols"]} symbols | Avg Return: {agg["avg_return"]:+.2f}% | Median: {agg["median_return"]:+.2f}%')
    print(f'  Win Rate: {agg["avg_win_rate"]:.1f}% | Best: {agg["best_symbol"]} ({max(r["total_return"] for r in results):+.2f}%)')
    print(f'  Worst: {agg["worst_symbol"]} ({min(r["total_return"] for r in results):+.2f}%) | Max DD: {min(r["max_drawdown"] for r in results):.2f}%')
    print()


def compare_strategies(multi_results: Dict[str, List[Dict]]) -> pd.DataFrame:
    """比較所有策略的績效"""
    rows = []
    for strat, results in multi_results.items():
        if not results:
            continue
        agg = aggregate_results(results)
        rows.append({
            'Strategy':     strat,
            'Symbols':      agg['num_symbols'],
            'Avg Return':   f"{agg['avg_return']:+.2f}%",
            'Median Return': f"{agg['median_return']:+.2f}%",
            'Avg WinRate':   f"{agg['avg_win_rate']:.1f}%",
            'Best Symbol':   agg['best_symbol'],
            'Best Return':   f"{max(r['total_return'] for r in results):+.2f}%",
            'Worst Symbol':  agg['worst_symbol'],
            'Worst Return':  f"{min(r['total_return'] for r in results):+.2f}%",
        })

    df = pd.DataFrame(rows)
    return df


# ═══════════════════════════════════════════════════════════════════════════
# 主程式
# ═══════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Tina Backtest Framework')
    parser.add_argument('--strategy',  default=None, help='只測單一策略（swing/growth_long/dca/etf_trend）')
    parser.add_argument('--symbol',     default=None, help='單一標的（如 AMD）')
    parser.add_argument('--symbols',    default=None, help='多標的逗號分隔（如 AMD,NVDA,META）')
    parser.add_argument('--universe',   default='us', help='股票宇宙（us/tw/all）')
    parser.add_argument('--limit',      type=int, default=None, help='限制股票數量（用於快速測試）')
    parser.add_argument('--start',      default='2023-01-01', help='回測起始日')
    parser.add_argument('--end',        default='2026-05-08', help='回測結束日')
    parser.add_argument('--compare',    action='store_true', help='策略比較模式')
    parser.add_argument('--report',     action='store_true', help='輸出詳細報告')
    parser.add_argument('--save',       action='store_true', help='儲存結果到 JSON')
    args = parser.parse_args()

    # 決定標的
    if args.symbol:
        symbols = [args.symbol]
    elif args.symbols:
        symbols = args.symbols.split(',')
    else:
        symbols = get_symbols(universe=args.universe, limit=args.limit)
        print(f'[INFO] Loaded {len(symbols)} symbols from {args.universe} universe')

    # 決定策略
    strategies_to_run = [args.strategy] if args.strategy else list(STRATEGIES.keys())

    all_multi = {}

    for strat in strategies_to_run:
        print()
        print(f'[INFO] Running backtest for strategy: {strat}')
        print(f'       Period: {args.start} → {args.end} | Symbols: {len(symbols)}')

        results = run_universe_backtest(symbols, strat, args.start, args.end, progress=True)
        print_summary(results, f'{strat.upper()} Backtest Results ({args.start} to {args.end})')

        all_multi[strat] = results

        if args.save and results:
            out_file = OUTPUT_DIR / f'backtest_{strat}_{datetime.now().strftime("%Y%m%d")}.json'
            # 只保存摘要，不保存完整 trades（太大了）
            summary = [{k: v for k, v in r.items() if k != 'trades'} for r in results]
            with open(out_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            print(f'[SAVED] {out_file}')

    # 策略比較
    if args.compare and len(all_multi) > 1:
        print()
        print('=' * 70)
        print('  Strategy Comparison')
        print('=' * 70)
        df = compare_strategies(all_multi)
        print(df.to_string(index=False))

    print()
    print('[DONE] Backtest framework complete')


if __name__ == '__main__':
    main()