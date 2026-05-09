# -*- coding: utf-8 -*-
"""
Leo 個股參數交易系統 v1.0
每檔股票使用專屬優化參數
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import yfinance as yf
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime

BASE_DIR = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leadtrades\leos"
TRADE_LOG = os.path.join(BASE_DIR, "leo_per_stock_trades.json")
PARAMS_FILE = os.path.join(BASE_DIR, "leo_per_stock_params.json")

# === 個股參數 ===
STOCK_PARAMS = {
    '2330': {"rsi_period": 10, "rsi_threshold": 50, "hold_days": 45, "take_profit": 5, "stop_loss": 8},
    '2382': {"rsi_period": 10, "rsi_threshold": 50, "hold_days": 30, "take_profit": 5, "stop_loss": 8},
    '3665': {"rsi_period": 10, "rsi_threshold": 50, "hold_days": 60, "take_profit": 8, "stop_loss": 10},
    '2317': {"rsi_period": 10, "rsi_threshold": 55, "hold_days": 60, "take_profit": 5, "stop_loss": 10},
    '3034': {"rsi_period": 10, "rsi_threshold": 40, "hold_days": 30, "take_profit": 5, "stop_loss": 8}
}

# === 股票名稱 ===
STOCK_NAMES = {
    '2330': '台積電',
    '2382': '廣達',
    '3665': '穎崴',
    '2317': '鴻海',
    '3034': '緯穎'
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


def load_trades():
    if os.path.exists(TRADE_LOG):
        with open(TRADE_LOG, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_trades(trades):
    with open(TRADE_LOG, 'w', encoding='utf-8') as f:
        json.dump(trades, f, ensure_ascii=False, indent=2)


def analyze_stock(ticker, params):
    """使用專屬參數分析個股"""
    try:
        df = yf.download(f"{ticker}.TW", period="3mo", progress=False)
        if df.empty or len(df) < 30:
            return None

        close = df['Close'].squeeze()
        rsi = calc_rsi(close, params['rsi_period'])
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
        entry_signal = False

        if (current_rsi < params['rsi_threshold'] and
            not pd.isna(current_ma60) and
            current_price > current_ma60 and
            ma_bull and
            momentum_ok):
            signal = "BUY"
            entry_signal = True

        return {
            'ticker': ticker,
            'name': STOCK_NAMES[ticker],
            'price': float(current_price),
            'rsi': float(current_rsi),
            'ma60': float(current_ma60) if not pd.isna(current_ma60) else None,
            'ma120': float(current_ma120) if not pd.isna(current_ma120) else None,
            'momentum': float(current_momentum),
            'ma_bull': ma_bull,
            'signal': signal,
            'entry_signal': entry_signal,
            'params': params
        }
    except Exception as e:
        print(f"  [錯誤] {ticker}: {e}")
        return None


def run_cycle():
    print("=" * 60)
    print("Leo 個股參數交易系統 v1.0")
    print("=" * 60)

    results = []
    for ticker, params in STOCK_PARAMS.items():
        print(f"分析 {ticker}...", end=" ")
        r = analyze_stock(ticker, params)
        if r:
            results.append(r)
            if r['entry_signal']:
                print(f"✅ BUY | RSI={r['rsi']:.1f} | Momentum={r['momentum']:+.2f}%")
            else:
                print(f"⚪ {r['signal']} | RSI={r['rsi']:.1f}")
        else:
            print(f"❌ 無法分析")

    print()
    print("【進場候選】")
    candidates = [r for r in results if r['entry_signal']]
    if candidates:
        for r in candidates:
            print(f"  ✅ {r['ticker']} {r['name']}: RSI={r['rsi']:.1f}, Momentum={r['momentum']:+.2f}%")
    else:
        print("  無進場訊號")

    # 儲存
    with open(os.path.join(BASE_DIR, "leo_per_stock_analysis.json"), 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    return results


if __name__ == '__main__':
    run_cycle()
