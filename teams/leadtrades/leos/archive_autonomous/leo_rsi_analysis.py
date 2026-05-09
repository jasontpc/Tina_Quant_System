# -*- coding: utf-8 -*-
"""
Leo RSI 區間深度分析 — 找出最高勝率進場區間
分析所有交易（含成功+失敗），找出最佳 RSI 進場範圍
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

STOCKS = {
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
    """收集所有進場紀錄（含成功和失敗）"""
    end_date = datetime.today().strftime('%Y-%m-%d')
    all_entries = []

    for ticker, par in STOCKS.items():
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
                        all_entries.append({'ticker': ticker, 'pnl_pct': pnl_pct, 'exit': 'TP', 'days': hold_days, 'entry_rsi': entry_rsi})
                        in_position = False
                    elif pnl_pct <= -STOP_LOSS * 100:
                        all_entries.append({'ticker': ticker, 'pnl_pct': pnl_pct, 'exit': 'SL', 'days': hold_days, 'entry_rsi': entry_rsi})
                        in_position = False
                    elif hold_days >= HOLD_DAYS:
                        all_entries.append({'ticker': ticker, 'pnl_pct': pnl_pct, 'exit': 'HOLD', 'days': hold_days, 'entry_rsi': entry_rsi})
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
        except:
            continue

    return all_entries

def analyze_by_rsiZone(trades):
    """按 RSI 區間分析勝率和平均報酬"""
    df = pd.DataFrame(trades)
    
    print("=" * 70)
    print("Leo RSI 區間深度分析 — 找出最高勝率進場區間")
    print("=" * 70)
    
    # 定義 RSI 區間
    zones = [(0, 30), (30, 35), (35, 40), (40, 45), (45, 50), (50, 55), (55, 100)]
    
    print(f"\n{'RSI區間':<12} {'筆數':<8} {'勝利':<6} {'失敗':<6} {'勝率':<8} {'平均報酬':<10} {'SL%':<8} {'TP%':<8}")
    print("-" * 70)
    
    results = []
    for low, high in zones:
        zone_df = df[(df['entry_rsi'] >= low) & (df['entry_rsi'] < high)]
        if len(zone_df) == 0:
            continue
        
        total = len(zone_df)
        wins = len(zone_df[zone_df['pnl_pct'] > 0])
        losses = total - wins
        win_rate = wins / total * 100
        avg_return = zone_df['pnl_pct'].mean()
        sl_pct = len(zone_df[zone_df['exit'] == 'SL']) / total * 100
        tp_pct = len(zone_df[zone_df['exit'] == 'TP']) / total * 100
        
        print(f"{low:>3}-{high:<3}     {total:<8} {wins:<6} {losses:<6} {win_rate:>5.1f}% {avg_return:>+8.2f}% {sl_pct:>5.1f}%   {tp_pct:>5.1f}%")
        
        results.append({
            'zone': f"{low}-{high}",
            'total': total,
            'win_rate': win_rate,
            'avg_return': avg_return,
            'sl_pct': sl_pct,
        })
    
    # 找出最佳區間
    if results:
        best_wr = max(results, key=lambda x: x['win_rate'])
        best_avg = max(results, key=lambda x: x['avg_return'])
        
        print()
        print(f"📊 最佳勝率區間: RSI {best_wr['zone']} → 勝率 {best_wr['win_rate']:.1f}%")
        print(f"📊 最佳平均報酬區間: RSI {best_avg['zone']} → 報酬 {best_avg['avg_return']:+.2f}%")
    
    return results

def analyze_by_holdDays(trades):
    """按持有天數分析"""
    df = pd.DataFrame(trades)
    
    print()
    print("=" * 70)
    print("持有天數分析")
    print("=" * 70)
    
    zones = [(0, 7), (7, 14), (14, 21), (21, 30), (30, 45), (45, 60), (60, 999)]
    
    print(f"\n{'持有天數':<12} {'筆數':<8} {'勝利':<6} {'失敗':<6} {'勝率':<8} {'平均報酬':<10}")
    print("-" * 60)
    
    for low, high in zones:
        zone_df = df[(df['days'] >= low) & (df['days'] < high)]
        if len(zone_df) == 0:
            continue
        
        total = len(zone_df)
        wins = len(zone_df[zone_df['pnl_pct'] > 0])
        losses = total - wins
        win_rate = wins / total * 100
        avg_return = zone_df['pnl_pct'].mean()
        
        print(f"{low:>3}-{high:<3}     {total:<8} {wins:<6} {losses:<6} {win_rate:>5.1f}% {avg_return:>+8.2f}%")

trades = collect_all_trades()
print(f"\n總交易筆數: {len(trades)}")
analyze_by_rsiZone(trades)
analyze_by_holdDays(trades)
print()
print("=" * 70)