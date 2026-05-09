# -*- coding: utf-8 -*-
"""
Leo 整合優化主腳本 — 2026-04-27
整合核心功能：一鍵執行分析、改善、排程
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime

BASE_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leadtrades\leos'

# === 正式版參數（vOfficial）===
OFFICIAL_PARAMS = {
    '2330': {'rsi_period': 10, 'rsi_threshold': 50, 'hold_days': 45, 'take_profit': 5, 'stop_loss': 8},
    '2382': {'rsi_period': 10, 'rsi_threshold': 50, 'hold_days': 30, 'take_profit': 5, 'stop_loss': 8},
    '3665': {'rsi_period': 10, 'rsi_threshold': 50, 'hold_days': 60, 'take_profit': 8, 'stop_loss': 10},
    '2317': {'rsi_period': 10, 'rsi_threshold': 55, 'hold_days': 60, 'take_profit': 5, 'stop_loss': 10},
    '3034': {'rsi_period': 10, 'rsi_threshold': 40, 'hold_days': 30, 'take_profit': 5, 'stop_loss': 8},
}

STOCK_NAMES = {'2330': '台積電', '2382': '廣達', '3665': '穎崴', '2317': '鴻海', '3034': '緯穎'}

STOCKS = ['2330', '2382', '3665', '2317', '3034']

# 改善規則（根據版本歷史資料庫）
IMPROVEMENT_RULES = [
    {'id': 'RULE_001', 'rule': 'RSI 進場閾值維持 40-55', 'confidence': 'HIGH'},
    {'id': 'RULE_002', 'rule': '避免擴大 RSI 進場範圍（不要 < 30）', 'confidence': 'HIGH'},
    {'id': 'RULE_003', 'rule': '持有天數維持 30-45 天', 'confidence': 'MEDIUM'},
    {'id': 'RULE_004', 'rule': 'TP 5-8%，SL 8-10%，TP/SL > 2.0', 'confidence': 'HIGH'},
    {'id': 'RULE_005', 'rule': '失敗數據庫需 > 50 筆才具統計顯著性', 'confidence': 'HIGH'},
    {'id': 'RULE_006', 'rule': '全量數據分析優先於失敗數據分析', 'confidence': 'HIGH'},
]


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


def daily_scan():
    """每日市場掃描"""
    print("=" * 60)
    print("Leo 每日市場掃描")
    print("=" * 60)

    results = []
    for ticker in STOCKS:
        par = OFFICIAL_PARAMS[ticker]
        try:
            df = yf.download(f"{ticker}.TW", period="3mo", progress=False)
            if df.empty or len(df) < 30:
                continue

            close = df['Close'].squeeze()
            rsi = calc_rsi(close, par['rsi_period'])
            ma60 = calc_ma(close, 60)
            ma120 = calc_ma(close, 120) if len(close) >= 120 else ma60
            momentum = calc_momentum(close, 5)

            current_rsi = rsi.iloc[-1]
            current_ma60 = ma60.iloc[-1]
            current_ma120 = ma120.iloc[-1] if len(close) >= 120 else ma60.iloc[-1]
            current_momentum = momentum.iloc[-1]
            current_price = close.iloc[-1]

            ma_bull = current_ma60 > current_ma120 if not pd.isna(current_ma120) else True
            momentum_ok = current_momentum > -5.0

            signal = "HOLD"
            if (current_rsi < par['rsi_threshold'] and
                not pd.isna(current_ma60) and
                current_price > current_ma60 and
                ma_bull and
                momentum_ok):
                signal = "BUY"

            results.append({
                'ticker': ticker,
                'name': STOCK_NAMES[ticker],
                'price': float(current_price),
                'rsi': float(current_rsi),
                'momentum': float(current_momentum),
                'ma60': float(current_ma60) if not pd.isna(current_ma60) else None,
                'ma_bull': ma_bull,
                'signal': signal,
                'params': par,
            })

            icon = "✅" if signal == "BUY" else "⚪"
            print(f"{icon} {ticker} {STOCK_NAMES[ticker]}: RSI={current_rsi:.1f}, Momentum={current_momentum:+.2f}%, Signal={signal}")

        except Exception as e:
            print(f"❌ {ticker}: {e}")

    # 儲存
    with open(os.path.join(BASE_DIR, 'leo_daily_scan.json'), 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 每日掃描已存: leo_daily_scan.json")
    return results


def backtest_with_rules():
    """根據改善規則回測"""
    print("\n" + "=" * 60)
    print("Leo 規則驗證回測")
    print("=" * 60)

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
                        all_trades.append({'ticker': ticker, 'pnl_pct': pnl_pct, 'exit': 'TP', 'days': hold_days})
                        in_position = False
                    elif pnl_pct <= -STOP_LOSS * 100:
                        all_trades.append({'ticker': ticker, 'pnl_pct': pnl_pct, 'exit': 'SL', 'days': hold_days})
                        in_position = False
                    elif hold_days >= HOLD_DAYS:
                        all_trades.append({'ticker': ticker, 'pnl_pct': pnl_pct, 'exit': 'HOLD', 'days': hold_days})
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
        except:
            continue

    # 評估
    df = pd.DataFrame(all_trades)
    total = len(df)
    wins = len(df[df['pnl_pct'] > 0])
    win_rate = wins / total * 100 if total > 0 else 0
    avg_return = df['pnl_pct'].mean()
    tp_count = len(df[df['exit'] == 'TP'])
    sl_count = len(df[df['exit'] == 'SL'])

    print(f"\n總交易: {total} 筆 | 勝利: {wins} | 失敗: {total-wins}")
    print(f"勝率: {win_rate:.1f}%")
    print(f"平均報酬: {avg_return:+.2f}%")
    print(f"TP/SL 比率: {tp_count/max(sl_count,1):.2f}")

    return {
        'total': total, 'wins': wins, 'losses': total-wins,
        'win_rate': win_rate, 'avg_return': avg_return,
        'tp_count': tp_count, 'sl_count': sl_count,
    }


def analyze_and_improve():
    """分析並給出改善建議"""
    print("\n" + "=" * 60)
    print("Leo 改善建議")
    print("=" * 60)

    print("\n【改善規則遵守情況】")
    for rule in IMPROVEMENT_RULES:
        icon = "🔴" if rule['confidence'] == 'HIGH' else "🟡"
        print(f"{icon} {rule['id']}: {rule['rule']}")

    print("\n【市場狀態檢查】")
    try:
        twii = yf.Ticker('^TWII').history(period='1mo')
        if len(twii) >= 20:
            close = twii['Close'].dropna()
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rsi = (100 - (100 / (1 + gain / loss))).iloc[-1]
            print(f"  TWII RSI: {rsi:.1f}")
            if rsi > 85:
                print("  ⚠️ 市場過熱，所有系統觀望")
            elif rsi > 70:
                print("  🟡 市場偏高，谨慎进場")
            else:
                print("  ✅ 市場正常，可考慮進場")
    except Exception as e:
        print(f"  無法獲取 TWII 數據: {e}")


def save_daily_report(metrics):
    """儲存每日報告"""
    report = {
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'version': 'vOfficial',
        'metrics': metrics,
        'rules': IMPROVEMENT_RULES,
    }

    report_file = os.path.join(BASE_DIR, 'leo_daily_report.json')
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 每日報告已存: {report_file}")


def main():
    print("=" * 60)
    print("Leo 整合優化主腳本")
    print("=" * 60)
    print(f"時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 1. 每日市場掃描
    scan_results = daily_scan()

    # 2. 規則驗證回測
    metrics = backtest_with_rules()

    # 3. 改善建議
    analyze_and_improve()

    # 4. 儲存報告
    save_daily_report(metrics)

    print()
    print("=" * 60)
    print("🎯 整合分析完成")
    print("=" * 60)


if __name__ == '__main__':
    main()