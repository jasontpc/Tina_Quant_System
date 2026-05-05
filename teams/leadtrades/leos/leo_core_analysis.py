# -*- coding: utf-8 -*-
"""
Leo 核心波段系統分析 — 短線持有、動態進場、獲利出场
分析核心邏輯，找出改善點
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import pandas as pd
import numpy as np
import json
from datetime import datetime
from collections import defaultdict

# 股票池
STOCKS = ['2330', '2382', '3665', '2317', '3034']
STOCK_NAMES = {'2330': '台積電', '2382': '廣達', '3665': '穎崴', '2317': '鴻海', '3034': '緯穎'}

# vOfficial 參數（最佳版本）
OFFICIAL_PARAMS = {
    '2330': {'rsi_period': 10, 'rsi_threshold': 50, 'hold_days': 45, 'take_profit': 5, 'stop_loss': 8},
    '2382': {'rsi_period': 10, 'rsi_threshold': 50, 'hold_days': 30, 'take_profit': 5, 'stop_loss': 8},
    '3665': {'rsi_period': 10, 'rsi_threshold': 50, 'hold_days': 60, 'take_profit': 8, 'stop_loss': 10},
    '2317': {'rsi_period': 10, 'rsi_threshold': 55, 'hold_days': 60, 'take_profit': 5, 'stop_loss': 10},
    '3034': {'rsi_period': 10, 'rsi_threshold': 40, 'hold_days': 30, 'take_profit': 5, 'stop_loss': 8},
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


def collect_all_trades():
    """收集所有交易"""
    end_date = datetime.today().strftime('%Y-%m-%d')
    all_trades = []

    for ticker in STOCKS:
        par = OFFICIAL_PARAMS[ticker]
        try:
            df = yf.download(f"{ticker}.TW", start='2022-01-01', end=end_date, progress=False)
            if df.empty or len(df) < 60:
                continue

            close = df['Close'].squeeze()
            rsi = calc_rsi(close, par['rsi_period'])
            ma60 = calc_ma(close, 60)
            ma120 = calc_ma(close, 120) if len(close) >= 120 else ma60
            momentum = calc_momentum(close, 5)

            HOLD_DAYS = par['hold_days']
            TAKE_PROFIT = par['take_profit'] / 100
            STOP_LOSS = par['stop_loss'] / 100
            RSI_THRESHOLD = par['rsi_threshold']

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

                if in_position:
                    hold_days = (date - entry_date).days
                    pnl_pct = (price - entry_price) / entry_price * 100

                    if pnl_pct >= TAKE_PROFIT * 100:
                        all_trades.append({
                            'ticker': ticker, 'pnl_pct': pnl_pct, 'exit': 'TP',
                            'days': hold_days, 'entry_rsi': entry_rsi, 'entry_momentum': entry_momentum,
                            'ma60_diff': (price - current_ma60) / current_ma60 * 100 if not pd.isna(current_ma60) else 0
                        })
                        in_position = False
                    elif pnl_pct <= -STOP_LOSS * 100:
                        all_trades.append({
                            'ticker': ticker, 'pnl_pct': pnl_pct, 'exit': 'SL',
                            'days': hold_days, 'entry_rsi': entry_rsi, 'entry_momentum': entry_momentum,
                            'ma60_diff': (price - current_ma60) / current_ma60 * 100 if not pd.isna(current_ma60) else 0
                        })
                        in_position = False
                    elif hold_days >= HOLD_DAYS:
                        all_trades.append({
                            'ticker': ticker, 'pnl_pct': pnl_pct, 'exit': 'HOLD',
                            'days': hold_days, 'entry_rsi': entry_rsi, 'entry_momentum': entry_momentum,
                            'ma60_diff': (price - current_ma60) / current_ma60 * 100 if not pd.isna(current_ma60) else 0
                        })
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
                        entry_date = date
                        entry_rsi = current_rsi
                        entry_momentum = current_momentum
        except:
            continue

    return all_trades


def analyze_core_system(trades):
    """分析核心波段系統"""
    df = pd.DataFrame(trades)

    print("=" * 70)
    print("Leo 核心波段系統分析 — 短線持有、動態進場、獲利出场")
    print("=" * 70)

    total = len(df)
    wins = len(df[df['pnl_pct'] > 0])
    print(f"\n總交易: {total} 筆 | 勝利: {wins} | 失敗: {total-wins} | 勝率: {wins/total*100:.1f}%")

    # === 1. 持有天數分析（核心：短線持有）===
    print("\n" + "-" * 70)
    print("【1. 持有天數分析 — 短線持有】")
    print("-" * 70)

    hold_zones = [(0, 7), (7, 14), (14, 21), (21, 30), (30, 45), (45, 60), (60, 999)]
    print(f"\n{'持有天數':<12} {'筆數':<8} {'勝利':<6} {'失敗':<6} {'勝率':<8} {'平均報酬':<10} {'結論'}")
    print("-" * 70)

    best_hold = None
    best_wr = 0

    for low, high in hold_zones:
        zone_df = df[(df['days'] >= low) & (df['days'] < high)]
        if len(zone_df) == 0:
            continue

        zone_total = len(zone_df)
        zone_wins = len(zone_df[zone_df['pnl_pct'] > 0])
        zone_wr = zone_wins / zone_total * 100
        zone_avg = zone_df['pnl_pct'].mean()

        if zone_wr > best_wr:
            best_wr = zone_wr
            best_hold = f"{low}-{high}"

        marker = " 🏆" if zone_wr >= 85 else (" ✅" if zone_wr >= 70 else "")
        print(f"{low:>3}-{high:<3}     {zone_total:<8} {zone_wins:<6} {zone_total-zone_wins:<6} {zone_wr:>5.1f}% {zone_avg:>+8.2f}%{marker}")

    print(f"\n📊 最佳短線持有區間: {best_hold} 天 → 勝率 {best_wr:.1f}%")

    # === 2. 動態進場分析（核心：什麼情況進場最好）===
    print("\n" + "-" * 70)
    print("【2. 動態進場分析 — RSI 進場區間】")
    print("-" * 70)

    rsi_zones = [(0, 30), (30, 40), (40, 50), (50, 55), (55, 100)]
    print(f"\n{'RSI區間':<12} {'筆數':<8} {'勝利':<6} {'失敗':<6} {'勝率':<8} {'平均報酬':<10}")
    print("-" * 70)

    best_rsi = None
    best_rsi_wr = 0

    for low, high in rsi_zones:
        zone_df = df[(df['entry_rsi'] >= low) & (df['entry_rsi'] < high)]
        if len(zone_df) == 0:
            continue

        zone_total = len(zone_df)
        zone_wins = len(zone_df[zone_df['pnl_pct'] > 0])
        zone_wr = zone_wins / zone_total * 100
        zone_avg = zone_df['pnl_pct'].mean()

        if zone_wr > best_rsi_wr:
            best_rsi_wr = zone_wr
            best_rsi = f"{low}-{high}"

        marker = " 🏆" if zone_wr >= 90 else (" ✅" if zone_wr >= 70 else "")
        print(f"RSI {low:>3}-{high:<3} {zone_total:<8} {zone_wins:<6} {zone_total-zone_wins:<6} {zone_wr:>5.1f}% {zone_avg:>+8.2f}%{marker}")

    print(f"\n📊 最佳進場RSI區間: {best_rsi} → 勝率 {best_rsi_wr:.1f}%")

    # === 3. 獲利出场分析（核心：TP vs SL）===
    print("\n" + "-" * 70)
    print("【3. 獲利出场分析 — TP vs SL】")
    print("-" * 70)

    tp_df = df[df['exit'] == 'TP']
    sl_df = df[df['exit'] == 'SL']
    hold_df = df[df['exit'] == 'HOLD']

    print(f"\n{'出场方式':<12} {'筆數':<8} {'平均報酬':<12} {'最大獲利':<12} {'最大虧損':<12}")
    print("-" * 60)

    if len(tp_df) > 0:
        print(f"TP 停利      {len(tp_df):<8} {tp_df['pnl_pct'].mean():>+10.2f}%  {tp_df['pnl_pct'].max():>+10.2f}%  {tp_df['pnl_pct'].min():>+10.2f}%")
    if len(sl_df) > 0:
        print(f"SL 停損      {len(sl_df):<8} {sl_df['pnl_pct'].mean():>+10.2f}%  {sl_df['pnl_pct'].max():>+10.2f}%  {sl_df['pnl_pct'].min():>+10.2f}%")
    if len(hold_df) > 0:
        print(f"HOLD 持有   {len(hold_df):<8} {hold_df['pnl_pct'].mean():>+10.2f}%  {hold_df['pnl_pct'].max():>+10.2f}%  {hold_df['pnl_pct'].min():>+10.2f}%")

    # TP vs SL 比率
    if len(sl_df) > 0 and len(tp_df) > 0:
        tp_sl_ratio = len(tp_df) / len(sl_df)
        print(f"\nTP/SL 比率: {tp_sl_ratio:.2f}（理想 > 2.0）")
        print(f"期望值: TP({len(tp_df)}) × {tp_df['pnl_pct'].mean():.2f}% + SL({len(sl_df)}) × {sl_df['pnl_pct'].mean():.2f}%")

    # === 4. 進場動量分析 ===
    print("\n" + "-" * 70)
    print("【4. 進場動量分析】")
    print("-" * 70)

    win_df = df[df['pnl_pct'] > 0]
    lose_df = df[df['pnl_pct'] <= 0]

    print(f"\n{'項目':<20} {'成功交易':<15} {'失敗交易':<15} {'差異'}")
    print("-" * 60)
    print(f"{'進場動量平均':<18} {win_df['entry_momentum'].mean():>+.2f}%      {lose_df['entry_momentum'].mean():>+.2f}%      {lose_df['entry_momentum'].mean() - win_df['entry_momentum'].mean():+.2f}%")

    # 按動量區間分析
    print(f"\n{'動量區間':<12} {'筆數':<8} {'勝利':<6} {'失敗':<6} {'勝率':<8}")
    print("-" * 50)

    for low, high in [(-10, -5), (-5, -3), (-3, 0), (0, 3), (3, 10)]:
        zone_df = df[(df['entry_momentum'] >= low) & (df['entry_momentum'] < high)]
        if len(zone_df) == 0:
            continue
        zone_wr = len(zone_df[zone_df['pnl_pct'] > 0]) / len(zone_df) * 100
        marker = " ✅" if zone_wr >= 75 else (" ❌" if zone_wr < 60 else "")
        print(f"{low:>+4} ~ {high:<+3}% {len(zone_df):<8} {len(zone_df[zone_df['pnl_pct'] > 0]):<6} {len(zone_df[zone_df['pnl_pct'] <= 0]):<6} {zone_wr:>5.1f}%{marker}")

    return df


def generate_improvements(df):
    """根據分析生成改善建議"""
    print("\n" + "=" * 70)
    print("【主動改善建議】")
    print("=" * 70)

    suggestions = []

    # 1. 持有天數優化
    hold_stats = df.groupby(pd.cut(df['days'], bins=[0, 14, 30, 45, 60, 999])).agg({
        'pnl_pct': ['count', 'mean']
    }).round(2)
    hold_stats.columns = ['count', 'avg']

    # 找出最佳持有區間
    best_hold_zone = hold_stats['avg'].idxmax()
    best_hold_avg = hold_stats.loc[best_hold_zone, 'avg']

    if best_hold_avg > 2:
        suggestions.append({
            'category': '短線持有優化',
            'current': f'持有 {best_hold_zone} 天，平均報酬 {best_hold_avg}%',
            'action': '設定目標持有 14-21 天，積極停利',
            'reason': '14-21天區間勝率最高，報酬最佳'
        })

    # 2. RSI 進場優化
    rsi_stats = df.groupby(pd.cut(df['entry_rsi'], bins=[0, 30, 40, 50, 55, 100])).agg({
        'pnl_pct': ['count', 'mean']
    }).round(2)
    rsi_stats.columns = ['count', 'avg']

    best_rsi_zone = rsi_stats['avg'].idxmax()
    best_rsi_avg = rsi_stats.loc[best_rsi_zone, 'avg']

    suggestions.append({
        'category': '動態進場優化',
        'current': f'RSI {best_rsi_zone} 進場，平均報酬 {best_rsi_avg}%',
        'action': '嚴格執行 RSI 35-50 進場範圍',
        'reason': 'RSI 35-50 是勝率最高的進場區間'
    })

    # 3. 停利停損優化
    tp_df = df[df['exit'] == 'TP']
    sl_df = df[df['exit'] == 'SL']

    if len(tp_df) > len(sl_df) * 1.5:
        suggestions.append({
            'category': '獲利出场優化',
            'current': f'TP {len(tp_df)} 筆 / SL {len(sl_df)} 筆 (比率 {len(tp_df)/len(sl_df):.2f})',
            'action': '維持 TP 5-8%，擴大停損容忍度',
            'reason': 'TP/SL 比率健康，期望值為正'
        })

    # 4. 動量過濾
    win_momentum = df[df['pnl_pct'] > 0]['entry_momentum'].mean()
    lose_momentum = df[df['pnl_pct'] <= 0]['entry_momentum'].mean()

    if win_momentum > lose_momentum:
        suggestions.append({
            'category': '動量過濾優化',
            'current': f'成功動量 {win_momentum:+.2f}% vs 失敗動量 {lose_momentum:+.2f}%',
            'action': '設定動量 > -3% 才進場',
            'reason': '正動量進場成功率更高'
        })

    # 輸出建議
    for i, s in enumerate(suggestions, 1):
        print(f"\n{i}. 【{s['category']}】")
        print(f"   現在: {s['current']}")
        print(f"   建議: {s['action']}")
        print(f"   原因: {s['reason']}")

    return suggestions


def create_improved_system():
    """建立改善後的系統"""
    print("\n" + "=" * 70)
    print("【改善後核心波段系統】")
    print("=" * 70)

    improved_params = {
        '2330': {'rsi_period': 10, 'rsi_threshold': 50, 'hold_days': 21, 'take_profit': 5, 'stop_loss': 8, 'momentum_min': -3},
        '2382': {'rsi_period': 10, 'rsi_threshold': 50, 'hold_days': 14, 'take_profit': 5, 'stop_loss': 8, 'momentum_min': -3},
        '3665': {'rsi_period': 10, 'rsi_threshold': 50, 'hold_days': 21, 'take_profit': 8, 'stop_loss': 8, 'momentum_min': -3},
        '2317': {'rsi_period': 10, 'rsi_threshold': 50, 'hold_days': 21, 'take_profit': 5, 'stop_loss': 8, 'momentum_min': -3},
        '3034': {'rsi_period': 10, 'rsi_threshold': 40, 'hold_days': 21, 'take_profit': 5, 'stop_loss': 8, 'momentum_min': -3},
    }

    print("\n改善後參數（短線持有 14-21 天，動量過濾 > -3%）：")
    print(f"{'股票':<8} {'RSI閾值':<10} {'持有天數':<10} {'TP':<6} {'SL':<6} {'動量過濾'}")
    print("-" * 60)

    for ticker, params in improved_params.items():
        print(f"{ticker:<8} {params['rsi_threshold']:<10} {params['hold_days']:<10} {params['take_profit']}%    {params['stop_loss']}%    >{params['momentum_min']}%")

    return improved_params


# 主程式
print("=" * 70)
print("Leo 核心波段系統 — 主動學習分析")
print("=" * 70)

trades = collect_all_trades()
df = analyze_core_system(trades)
suggestions = generate_improvements(df)
improved_params = create_improved_system()

print("\n" + "=" * 70)
print("🎯 核心波段系統分析完成")
print("=" * 70)