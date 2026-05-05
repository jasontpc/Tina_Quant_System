# -*- coding: utf-8 -*-
"""
Leo 個股參數交易系統 v2.0
結合失敗數據庫優化參數
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
TRADE_LOG = os.path.join(BASE_DIR, "leo_per_stock_v2_trades.json")
PARAMS_FILE = os.path.join(BASE_DIR, "leo_per_stock_params_v2.json")

# === 載入 v2.0 參數 ===
with open(PARAMS_FILE, 'r', encoding='utf-8') as f:
    PARAMS_DATA = json.load(f)

STOCK_PARAMS = {ticker: data['adjusted_params'] for ticker, data in PARAMS_DATA['stocks'].items()}
STOCK_NAMES = {ticker: data['name'] for ticker, data in PARAMS_DATA['stocks'].items()}

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

def analyze_stock(ticker, params):
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

        # === v2.0 進場邏輯：結合失敗數據庫優化 ===
        rsi_ok = params['rsi_threshold'] <= current_rsi <= params.get('rsi_threshold_max', 55)
        hold_days_min = params.get('hold_days_min', 14)
        momentum_ok = current_momentum > -3.0  # 稍微嚴格

        signal = "HOLD"
        entry_signal = False
        reason = ""

        if (rsi_ok and
            not pd.isna(current_ma60) and
            current_price > current_ma60 and
            ma_bull and
            momentum_ok):
            signal = "BUY"
            entry_signal = True
            reason = f"RSI={current_rsi:.1f}, Momentum={current_momentum:+.2f}%, MA Bull"
        else:
            if current_rsi < params['rsi_threshold']:
                reason = f"RSI太低({current_rsi:.1f}<{params['rsi_threshold']})"
            elif current_rsi > params.get('rsi_threshold_max', 55):
                reason = f"RSI太高({current_rsi:.1f}>{params.get('rsi_threshold_max',55)})"
            elif current_price <= current_ma60:
                reason = "價格低於MA60"
            elif not ma_bull:
                reason = "MA空頭排列"
            elif not momentum_ok:
                reason = f"動量不足({current_momentum:+.2f}%)"

        return {
            'ticker': ticker,
            'name': STOCK_NAMES[ticker],
            'price': float(current_price),
            'rsi': float(current_rsi),
            'momentum': float(current_momentum),
            'ma_bull': ma_bull,
            'signal': signal,
            'entry_signal': entry_signal,
            'reason': reason,
            'params': params,
            'weight': params.get('weight', 1.0)
        }
    except Exception as e:
        return None

def run_cycle():
    print("=" * 60)
    print("Leo 個股參數交易系統 v2.0")
    print("結合失敗數據庫優化")
    print("=" * 60)

    results = []
    for ticker, params in STOCK_PARAMS.items():
        print(f"分析 {ticker}...", end=" ")
        r = analyze_stock(ticker, params)
        if r:
            results.append(r)
            if r['entry_signal']:
                print(f"✅ BUY (權重{r['weight']:.1f}x) | {r['reason']}")
            else:
                print(f"⚪ {r['signal']} | {r['reason']}")
        else:
            print(f"❌ 無法分析")

    print()
    print("【進場候選】")
    candidates = [r for r in results if r['entry_signal']]
    if candidates:
        candidates.sort(key=lambda x: x['weight'], reverse=True)
        for r in candidates:
            print(f"  ✅ {r['ticker']} {r['name']} | RSI={r['rsi']:.1f} | 權重={r['weight']:.1f}x | {r['reason']}")
    else:
        print("  無進場訊號")

    with open(os.path.join(BASE_DIR, "leo_per_stock_v2_analysis.json"), 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    return results

if __name__ == '__main__':
    run_cycle()
