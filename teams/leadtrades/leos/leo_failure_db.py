# -*- coding: utf-8 -*-
"""
Leo 交易失敗數據庫 v1.0 — 2026-04-27
專門收集、分析、追蹤失敗交易，主動給出改善建議
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import yfinance as yf
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict

BASE_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leadtrades\leos'
DB_FILE = os.path.join(BASE_DIR, 'leo_failure_db.json')
ANALYSIS_FILE = os.path.join(BASE_DIR, 'leo_failure_analysis_report.json')

# === 股票池（使用個股參數優化結果）===
STOCK_PARAMS = {
    '2330': {'rsi_period': 10, 'rsi_threshold': 50, 'hold_days': 45, 'take_profit': 5, 'stop_loss': 8},
    '2382': {'rsi_period': 10, 'rsi_threshold': 50, 'hold_days': 30, 'take_profit': 5, 'stop_loss': 8},
    '3665': {'rsi_period': 10, 'rsi_threshold': 50, 'hold_days': 60, 'take_profit': 8, 'stop_loss': 10},
    '2317': {'rsi_period': 10, 'rsi_threshold': 55, 'hold_days': 60, 'take_profit': 5, 'stop_loss': 10},
    '3034': {'rsi_period': 10, 'rsi_threshold': 40, 'hold_days': 30, 'take_profit': 5, 'stop_loss': 8},
}


def load_db():
    """載入失敗數據庫"""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'trades': [], 'stats': {}, 'last_updated': None}


def save_db(db):
    """儲存失敗數據庫"""
    import numpy as np
    class NumpyEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, (np.bool_,)): return bool(obj)
            if isinstance(obj, (np.integer,)): return int(obj)
            if isinstance(obj, (np.floating,)): return float(obj)
            if isinstance(obj, np.ndarray): return obj.tolist()
            return super().default(obj)
    db['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2, cls=NumpyEncoder)


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


def backtest_with_failure_tracking(ticker, params, start_date='2022-01-01', end_date=None):
    """回測並記錄所有失敗交易"""
    RSI_PERIOD = params['rsi_period']
    RSI_THRESHOLD = params['rsi_threshold']
    HOLD_DAYS = params['hold_days']
    TAKE_PROFIT = params['take_profit'] / 100
    STOP_LOSS = params['stop_loss'] / 100

    if end_date is None:
        end_date = datetime.today().strftime('%Y-%m-%d')

    failures = []

    try:
        df = yf.download(f"{ticker}.TW", start=start_date, end=end_date, progress=False)
        if df.empty or len(df) < 60:
            return []

        close = df['Close'].squeeze()
        volume = df['Volume'].squeeze()
        rsi = calc_rsi(close, RSI_PERIOD)
        ma60 = calc_ma(close, 60)
        ma120 = calc_ma(close, 120) if len(close) >= 120 else ma60
        momentum = calc_momentum(close, 5)

        in_position = False
        entry_price = 0
        entry_date = None
        entry_rsi = 0
        entry_momentum = 0

        for i in range(60, len(df) - HOLD_DAYS):
            date = df.index[i]
            price = close.iloc[i]
            current_rsi = rsi.iloc[i]
            current_ma60 = ma60.iloc[i]
            current_ma120 = ma120.iloc[i]
            current_momentum = momentum.iloc[i]
            current_volume = volume.iloc[i]

            if in_position:
                hold_days = (df.index[i] - entry_date).days
                pnl_pct = (price - entry_price) / entry_price * 100
                duration = hold_days

                exit_reason = None
                is_failure = pnl_pct < 0

                if pnl_pct >= TAKE_PROFIT * 100:
                    exit_reason = 'TP'
                    is_failure = False
                elif pnl_pct <= -STOP_LOSS * 100:
                    exit_reason = 'SL'
                    is_failure = True
                elif hold_days >= HOLD_DAYS:
                    exit_reason = 'HOLD'
                    is_failure = pnl_pct < 0

                if exit_reason:
                    trade = {
                        'ticker': ticker,
                        'entry_date': entry_date.strftime('%Y-%m-%d'),
                        'exit_date': date.strftime('%Y-%m-%d'),
                        'entry_price': float(entry_price),
                        'exit_price': float(price),
                        'pnl_pct': float(pnl_pct),
                        'exit_reason': exit_reason,
                        'hold_days': duration,
                        'is_failure': is_failure,
                        'entry_rsi': float(entry_rsi),
                        'entry_momentum': float(entry_momentum),
                        'market_rsi_at_entry': float(current_rsi) if not in_position else 0,
                        'price_change_pct': float((price - entry_price) / entry_price * 100),
                    }
                    in_position = False

                    if is_failure:
                        failures.append(trade)

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
                    entry_rsi = current_rsi
                    entry_momentum = current_momentum

        return failures
    except Exception as e:
        print(f"  [錯誤] {ticker}: {e}")
        return []


def build_failure_db():
    """建立失敗交易資料庫"""
    print("=" * 60)
    print("Leo 交易失敗數據庫 v1.0")
    print("=" * 60)

    db = load_db()
    all_failures = []

    print("\n收集失敗交易...")
    for ticker, params in STOCK_PARAMS.items():
        print(f"  分析 {ticker}...", end=' ')
        failures = backtest_with_failure_tracking(ticker, params)
        all_failures.extend(failures)
        print(f"{len(failures)} 筆失敗")

    db['trades'] = all_failures
    save_db(db)

    print(f"\n總失敗交易: {len(all_failures)} 筆")
    return db


def analyze_failures(db):
    """深度分析失敗交易"""
    failures = db['trades']
    if not failures:
        print("無失敗交易數據")
        return

    df = pd.DataFrame(failures)

    print()
    print("=" * 60)
    print("【失敗模式分析】")
    print("=" * 60)

    # === 1. 按退出方式分類 ===
    by_exit = df.groupby('exit_reason').agg({
        'pnl_pct': ['count', 'mean', 'min'],
        'hold_days': 'mean'
    }).round(2)
    by_exit.columns = ['筆數', '平均虧損', '最大虧損', '平均持有天數']

    print("\n📊 按退出方式:")
    print(by_exit.to_string())

    # === 2. 按股票分類 ===
    print("\n📊 按股票:")
    by_ticker = df.groupby('ticker').agg({
        'pnl_pct': ['count', 'mean', 'min'],
        'entry_rsi': 'mean',
        'entry_momentum': 'mean'
    }).round(2)
    by_ticker.columns = ['筆數', '平均虧損', '最大虧損', '進場RSI均', '進場動量均']

    # 排名（最差到最差）
    by_ticker = by_ticker.sort_values('平均虧損')
    print(by_ticker.to_string())

    # === 3. 按進場RSI區間分析 ===
    print("\n📊 按進場RSI區間:")
    df['rsi_zone'] = pd.cut(df['entry_rsi'], bins=[0, 35, 40, 45, 50, 100], labels=['<35', '35-40', '40-45', '45-50', '>50'])
    by_rsi = df.groupby('rsi_zone', observed=True).agg({
        'pnl_pct': ['count', 'mean'],
        'hold_days': 'mean'
    }).round(2)
    by_rsi.columns = ['筆數', '平均虧損', '平均天數']
    print(by_rsi.to_string())

    # === 4. 按持有天數分析 ===
    print("\n📊 按持有天數:")
    df['hold_zone'] = pd.cut(df['hold_days'], bins=[0, 14, 30, 45, 60, 999], labels=['<14d', '14-30d', '30-45d', '45-60d', '>60d'])
    by_hold = df.groupby('hold_zone', observed=True).agg({
        'pnl_pct': ['count', 'mean'],
        'entry_rsi': 'mean'
    }).round(2)
    by_hold.columns = ['筆數', '平均虧損', '進場RSI均']
    print(by_hold.to_string())

    # === 5. 最差交易 Top 10 ===
    print("\n📊 最差交易 Top 10:")
    worst = df.nsmallest(10, 'pnl_pct')[['ticker', 'entry_date', 'exit_reason', 'pnl_pct', 'hold_days', 'entry_rsi']]
    print(worst.to_string())

    # === 6. 生成改善建議 ===
    suggestions = generate_suggestions(df, by_ticker, by_rsi, by_hold)

    return {
        'total_failures': len(df),
        'by_exit': by_exit.to_dict(),
        'by_ticker': by_ticker.to_dict(),
        'suggestions': suggestions
    }


def generate_suggestions(df, by_ticker, by_rsi, by_hold):
    """根據分析生成改善建議"""
    suggestions = []

    # === 建議1：股票權重調整 ===
    ticker_avg = df.groupby('ticker')['pnl_pct'].mean()
    worst_stock = ticker_avg.idxmin()
    worst_avg = ticker_avg.min()
    if worst_avg < -8:
        suggestions.append({
            'priority': 'HIGH',
            'category': '股票權重',
            'issue': f"{worst_stock} 平均虧損 {worst_avg:.1f}%",
            'action': f"調降 {worst_stock} 持倉權重，或提高進場RSI門檻",
            'reason': "該股票失敗交易虧損幅度過大"
        })

    # === 建議2：停損優化 ===
    sl_df = df[df['exit_reason'] == 'SL']
    if len(sl_df) > 0:
        sl_avg = sl_df['pnl_pct'].mean()
        sl_count = len(sl_df)
        if sl_avg < -12:
            suggestions.append({
                'priority': 'HIGH',
                'category': '停損優化',
                'issue': f"SL 平均虧損 {sl_avg:.1f}%，停損觸發 {sl_count} 次",
                'action': "考慮縮窄停損至 6-8% 或提高進場門檻",
                'reason': "停損觸發過度，虧損幅度過大"
            })

    # === 建議3：進場RSI優化 ===
    if len(by_rsi) > 0:
        try:
            worst_rsi_zone = df.groupby('rsi_zone', observed=True)['pnl_pct'].mean().idxmin()
            worst_rsi_avg = df.groupby('rsi_zone', observed=True)['pnl_pct'].mean().min()
            if worst_rsi_avg < -5:
                suggestions.append({
                    'priority': 'MEDIUM',
                    'category': '進場條件',
                    'issue': f"RSI {worst_rsi_zone} 區間進場平均虧損 {worst_rsi_avg:.1f}%",
                    'action': f"提高進場門檻，避免 RSI {worst_rsi_zone} 區間進場",
                    'reason': "特定RSI區間進場失敗率過高"
                })
        except:
            pass

    # === 建議4：持有天數優化 ===
    if len(by_hold) > 0:
        try:
            worst_hold_zone = df.groupby('hold_zone', observed=True)['pnl_pct'].mean().idxmin()
            worst_hold_avg = df.groupby('hold_zone', observed=True)['pnl_pct'].mean().min()
            if worst_hold_avg < -5:
                suggestions.append({
                    'priority': 'MEDIUM',
                    'category': '持有策略',
                    'issue': f"持有 {worst_hold_zone} 平均虧損 {worst_hold_avg:.1f}%",
                    'action': f"設定最大持有天數 {worst_hold_zone.replace('d','')} 天，強制退出",
                    'reason': "特定持有天數區間失敗率過高"
                })
        except:
            pass

    # === 建議5：動量過濾 ===
    momentum_avg = df['entry_momentum'].mean()
    if momentum_avg < -2:
        suggestions.append({
            'priority': 'MEDIUM',
            'category': '動量過濾',
            'issue': f"進場時平均動量 {momentum_avg:.1f}%",
            'action': "提高動量過濾門檻：近5日漲幅落後大盤 < 2% 才進場",
            'reason': "進場時動量偏弱，容易觸發失敗"
        })

    # === 建議6：TP/ SL 比例優化 ===
    tp_count = len(df[df['exit_reason'] == 'TP'])
    sl_count = len(df[df['exit_reason'] == 'SL'])
    if sl_count > 0 and tp_count > 0 and sl_count > tp_count * 0.5:
        suggestions.append({
            'priority': 'HIGH',
            'category': '停利停損比',
            'issue': f"SL({sl_count}) > TP({tp_count})，比率 {sl_count/tp_count:.1f}",
            'action': "停利目標維持或調低，停損可收緊至6-8%",
            'reason': "停損次數過多，期望值被破壞"
        })

    # === 建議7：市場狀態過濾 ===
    high_rsi_entries = df[df['entry_rsi'] > 45]
    if len(high_rsi_entries) > len(df) * 0.3:
        suggestions.append({
            'priority': 'MEDIUM',
            'category': '市場過濾',
            'issue': f"{len(high_rsi_entries)} 筆進場時RSI>45 ({len(high_rsi_entries)/len(df)*100:.0f}%)",
            'action': "RSI > 45 時不進場（除非強烈多頭排列）",
            'reason': "高RSI進場失敗率偏高"
        })

    return suggestions


def print_suggestions(suggestions):
    """輸出改善建議"""
    print()
    print("=" * 60)
    print("【主動改善建議】")
    print("=" * 60)

    priority_colors = {'HIGH': '🔴', 'MEDIUM': '🟡', 'LOW': '🟢'}

    for i, s in enumerate(sorted(suggestions, key=lambda x: {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}[x['priority']]), 1):
        icon = priority_colors.get(s['priority'], '⚪')
        print(f"\n{icon} [{s['priority']}] {s['category']}")
        print(f"   問題：{s['issue']}")
        print(f"   建議：{s['action']}")
        print(f"   原因：{s['reason']}")


def run_cycle():
    """執行完整分析流程"""
    print("=" * 60)
    print("Leo 交易失敗數據庫分析系統 v1.0")
    print("=" * 60)
    print(f"時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 1. 建立失敗數據庫
    db = build_failure_db()

    # 2. 分析失敗模式
    analysis = analyze_failures(db)

    # 3. 輸出改善建議
    if analysis and analysis['suggestions']:
        print_suggestions(analysis['suggestions'])

        # 4. 儲存分析報告
        report = {
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_failures': len(db['trades']),
            'suggestions': analysis['suggestions'],
            'by_ticker': {k: v for k, v in analysis['by_ticker'].items()},
            'last_updated': db.get('last_updated')
        }
        with open(ANALYSIS_FILE, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 分析報告已存: {ANALYSIS_FILE}")
    else:
        print("\n✅ 無失敗交易或無需改善")

    print()
    print("=" * 60)
    print("🎯 失敗數據庫分析完成")
    print("=" * 60)

    return db, analysis


if __name__ == '__main__':
    run_cycle()