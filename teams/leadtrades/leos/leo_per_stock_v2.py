# -*- coding: utf-8 -*-
"""
Leo 個股參數 v2.0 — 結合失敗數據庫優化
根據失敗分析修正每檔股票的專屬參數
"""

import json
import os

BASE_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leadtrades\leos'
PARAMS_FILE = os.path.join(BASE_DIR, 'leo_per_stock_params.json')
OUTPUT_FILE = os.path.join(BASE_DIR, 'leo_per_stock_params_v2.json')

# === 失敗數據分析帶來的修正 ===
# 發現問題：
# 1. RSI <35 進場平均虧損 -11.1%
# 2. 持有 <14d 平均虧損 -11.9%
# 3. RSI > 45 進場佔60%失敗
# 4. 3665/2317 平均虧損 > -10%

FAILURE_ADJUSTMENTS = {
    '2330': {
        'reason': '失敗分析：進場RSI均36.43（偏低），持有<14d最危險',
        'entry_rsi_min': 35,   # 原40→35，避免錯過但仍謹慎
        'entry_rsi_max': 50,   # 維持50
        'stop_loss': 6,        # 原8→6，減少大虧
        'hold_days_min': 14,   # 持有至少14天
    },
    '2382': {
        'reason': '失敗分析：進場RSI均43.40，動量平均0.08（最强），可放寬',
        'entry_rsi_min': 40,   # 原40→40
        'entry_rsi_max': 55,   # 原50→55，放寬上限捕捉回檔
        'stop_loss': 6,        # 原8→6，減少大虧
        'hold_days_min': 14,
    },
    '3665': {
        'reason': '失敗分析：平均虧損-10.71%最嚴重，進場RSI均47.05偏高，需嚴格限制',
        'entry_rsi_min': 45,   # 原40→45，大幅提高（失敗主因）',
        'entry_rsi_max': 55,   # 維持55
        'stop_loss': 6,        # 原10→6，止血
        'hold_days_min': 21,   # 原30→21，避免短期持有虧損
        'weight_reduce': 0.5,   # 降低50%倉位
    },
    '2317': {
        'reason': '失敗分析：進場RSI均47.13偏高，最大虧損-14.29%，需嚴格進場',
        'entry_rsi_min': 45,   # 原55→45，降低進場RSI下限（避免低RSI進場）',
        'entry_rsi_max': 55,   # 維持55
        'stop_loss': 8,       # 維持8
        'hold_days_min': 21,   # 原60→21，避免長期持有風險
    },
    '3034': {
        'reason': '失敗分析：100%勝率但交易量少(9筆)，需擴大進場範圍',
        'entry_rsi_min': 35,   # 原40→35，增加進場次數
        'entry_rsi_max': 55,   # 原40→55，放寬
        'stop_loss': 8,        # 維持8
        'hold_days_min': 14,
        'weight_boost': 1.5,   # 增加50%倉位
    },
}


def apply_adjustments():
    """根據失敗數據庫調整個股參數"""
    with open(PARAMS_FILE, 'r', encoding='utf-8') as f:
        original = json.load(f)

    print("=" * 60)
    print("Leo 個股參數 v2.0 — 結合失敗數據庫優化")
    print("=" * 60)

    adjusted = {
        'date': '2026-04-27 06:03',
        'version': 'v2.0',
        'stocks': {}
    }

    for ticker, data in original['stocks'].items():
        orig_params = data['params']
        orig_metrics = data['metrics']

        adj = FAILURE_ADJUSTMENTS.get(ticker, {})

        new_params = {
            'rsi_period': orig_params['rsi_period'],
            'rsi_threshold': adj.get('entry_rsi_min', orig_params['rsi_threshold']),
            'rsi_threshold_max': adj.get('entry_rsi_max', 55),
            'hold_days': orig_params['hold_days'],
            'take_profit': orig_params['take_profit'],
            'stop_loss': adj.get('stop_loss', orig_params['stop_loss']),
            'hold_days_min': adj.get('hold_days_min', 14),
            'weight': adj.get('weight_reduce', adj.get('weight_boost', 1.0)),
        }

        adjusted['stocks'][ticker] = {
            'name': data['name'],
            'original_params': orig_params,
            'adjusted_params': new_params,
            'original_metrics': orig_metrics,
            'adjustment_reason': adj.get('reason', ''),
        }

        print(f"\n{ticker} {data['name']}")
        print(f"  調整原因: {adj.get('reason', '無')}")
        print(f"  停損: {orig_params['stop_loss']}% → {new_params['stop_loss']}%")
        print(f"  進場RSI: {orig_params['rsi_threshold']} → {new_params['rsi_threshold']} (max {new_params['rsi_threshold_max']})")
        print(f"  最小持有: {new_params['hold_days_min']} 天")
        print(f"  倉位權重: {new_params['weight']:.1f}x")

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(adjusted, f, ensure_ascii=False, indent=2)

    print(f"\n✅ v2.0 參數已存: {OUTPUT_FILE}")
    return adjusted


def create_v2_trading_script():
    """建立 v2 交易腳本"""
    with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
        params = json.load(f)

    script = '''# -*- coding: utf-8 -*-
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

BASE_DIR = r"C:\\Users\\USER\\.openclaw\\workspace\\Tina_Quant_System\\teams\\leadtrades\\leos"
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
'''

    script_path = os.path.join(BASE_DIR, 'leo_per_stock_v2_trade.py')
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script)

    print(f"✅ v2.0 交易腳本已生成: {script_path}")


if __name__ == '__main__':
    result = apply_adjustments()
    create_v2_trading_script()
    print()
    print("=" * 60)
    print("🎯 個股參數 v2.0 完成！")
    print("=" * 60)