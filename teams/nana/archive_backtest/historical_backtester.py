# -*- coding: utf-8 -*-
"""
Nana 歷史大盤回測模組
 Historical Market Backtester
抓取 TWII 歷史數據，分析市場狀態，輸出最佳參數建議
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import os
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional

import yfinance as yf
import pandas as pd
import numpy as np

# === 路徑設定 ===
BASE_DIR = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\nana"
REGIME_FILE = os.path.join(BASE_DIR, "market_regime.json")
PARAM_REC_FILE = os.path.join(BASE_DIR, "param_recommendations.json")


def fetch_twii_history(years: int = 5) -> Optional[pd.DataFrame]:
    """抓取 TWII（台灣加權指數）歷史數據"""
    try:
        ticker = yf.Ticker("^TWII")
        end_date = date.today()
        start_date = end_date - timedelta(days=years * 365)
        hist = ticker.history(start=start_date, end=end_date, interval="1wk")
        if hist.empty or len(hist) < 100:
            print(f"[WARN] TWII data too short: {len(hist)} rows")
            return None
        return hist
    except Exception as e:
        print(f"[ERROR] fetch_twii_history: {e}")
        return None


def calculate_regime_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """計算市場狀態指標"""
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    vol = df["Volume"]

    # SMA
    sma20 = close.rolling(20).mean()
    sma60 = close.rolling(60).mean()

    # RSI (14)
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    # BIAS (20)
    bias = ((close - sma20) / sma20) * 100

    # ATR (14)
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()

    # Volatility (20日標準差)
    vol_std = close.rolling(20).std()

    df_ind = pd.DataFrame({
        "close": close,
        "sma20": sma20,
        "sma60": sma60,
        "rsi": rsi,
        "bias": bias,
        "atr": atr,
        "vol_std": vol_std,
        "volume": vol,
    }, index=df.index)
    return df_ind


def classify_market_regime(rsi: float, bias: float, close: float, sma20: float, sma60: float) -> str:
    """分類市場狀態"""
    if pd.isna(rsi) or pd.isna(bias) or pd.isna(sma20):
        return "UNKNOWN"

    if rsi > 80:
        return "OVERBOUGHT"
    elif rsi < 40:
        return "OVERSOLD"
    elif rsi >= 60:
        return "BULL"
    elif rsi >= 50 and bias > 0:
        return "BULL"
    elif rsi >= 50 and bias < -5:
        return "RECOVERY"
    elif rsi < 50 and bias > 5:
        return "DISTRESS"
    elif rsi < 50:
        return "BEAR"
    else:
        return "CONSOLIDATE"


def run_historical_backtester():
    """主執行函式：歷史大盤回測"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] === Nana 歷史大盤回測 ===")

    # 1. 抓取 TWII 5年歷史數據
    df = fetch_twii_history(years=5)
    if df is None:
        print("[ERROR] Failed to fetch TWII data")
        return None

    print(f"[INFO] TWII data loaded: {len(df)} rows from {df.index[0].date()} to {df.index[-1].date()}")

    # 2. 計算指標
    df_ind = calculate_regime_indicators(df)
    df_ind["regime"] = df_ind.apply(
        lambda row: classify_market_regime(
            row["rsi"], row["bias"], row["close"], row["sma20"], row["sma60"]
        ), axis=1
    )

    # 3. 分析每個市場狀態
    regimes = ["OVERBOUGHT", "BULL", "CONSOLIDATE", "RECOVERY", "BEAR", "OVERSOLD", "DISTRESS"]
    regime_stats = {}

    for regime in regimes:
        regime_df = df_ind[df_ind["regime"] == regime]
        if len(regime_df) < 5:
            continue

        avg_rsi = regime_df["rsi"].mean()
        avg_bias = regime_df["bias"].mean()
        avg_atr_pct = (regime_df["atr"] / regime_df["close"] * 100).mean()
        avg_vol = regime_df["volume"].mean()
        duration = len(regime_df)

        # 計算市場報酬（之後收盤價 vs 之前收盤價）
        returns = regime_df["close"].pct_change().dropna()
        win_rate = (returns > 0).sum() / len(returns) * 100 if len(returns) > 0 else 0
        avg_return = returns.mean() * 100 if len(returns) > 0 else 0

        regime_stats[regime] = {
            "episodes": duration,
            "avg_rsi": round(avg_rsi, 2),
            "avg_bias": round(avg_bias, 2),
            "avg_atr_pct": round(avg_atr_pct, 4),
            "avg_vol": int(avg_vol),
            "win_rate": round(win_rate, 2),
            "avg_return_pct": round(avg_return, 4),
        }

        print(f"  [{regime}] episodes={duration}, RSI={avg_rsi:.1f}, BIAS={avg_bias:.1f}%, ATR%={avg_atr_pct:.2f}%, win_rate={win_rate:.1f}%")

    # 4. 根據歷史數據推薦 ATR 停損/停利參數
    param_recommendations = {}

    for regime, stats in regime_stats.items():
        atr_pct = stats["avg_atr_pct"]

        # ATR 停損：1.5x ATR（保守）/ 2x ATR（積極）
        # ATR 停利：3x ATR / 4x ATR
        param_recommendations[regime] = {
            "atr_stop_loss": round(atr_pct * 1.5, 4),
            "atr_target_profit": round(atr_pct * 3.0, 4),
            "hold_days_max": 10 if regime in ["BULL", "OVERBOUGHT"] else 7,
            "entry_rsi_max": 65 if regime in ["BULL", "CONSOLIDATE"] else 60,
        }

    # 5. 市場狀態 → 參數對應表
    current_rsi = df_ind["rsi"].iloc[-1]
    current_bias = df_ind["bias"].iloc[-1]
    current_close = df_ind["close"].iloc[-1]
    current_sma20 = df_ind["sma20"].iloc[-1]
    current_sma60 = df_ind["sma60"].iloc[-1]
    current_regime = classify_market_regime(current_rsi, current_bias, current_close, current_sma20, current_sma60)

    print(f"\n=== 當前市場狀態 ===")
    print(f"日期: {df.index[-1].date()}")
    print(f"指數: {current_close:,.0f}")
    print(f"RSI: {current_rsi:.2f}")
    print(f"BIAS: {current_bias:.2f}%")
    print(f"SMA20: {current_sma20:,.0f}")
    print(f"SMA60: {current_sma60:,.0f}")
    print(f"市場狀態: {current_regime}")

    if current_regime in param_recommendations:
        rec = param_recommendations[current_regime]
        print(f"\n=== {current_regime} 參數建議 ===")
        print(f"ATR 停損: {rec['atr_stop_loss']:.2f}%")
        print(f"ATR 停利: {rec['atr_target_profit']:.2f}%")
        print(f"最大持有天數: {rec['hold_days_max']} 天")
        print(f"進場 RSI 上限: {rec['entry_rsi_max']}")

    # 6. 儲存結果
    result = {
        "backtest_date": datetime.now().isoformat(),
        "data_range": {
            "start": df.index[0].isoformat(),
            "end": df.index[-1].isoformat(),
            "rows": len(df)
        },
        "current_state": {
            "regime": current_regime,
            "close": round(current_close, 2),
            "rsi": round(current_rsi, 2),
            "bias": round(current_bias, 2),
            "atr_pct": round((df_ind["atr"].iloc[-1] / current_close) * 100, 4),
        },
        "regime_stats": regime_stats,
        "param_recommendations": param_recommendations,
    }

    with open(REGIME_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    with open(PARAM_REC_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "current_regime": current_regime,
            "recommendations": param_recommendations.get(current_regime, {}),
            "all_regimes": param_recommendations,
            "updated_at": datetime.now().isoformat()
        }, f, ensure_ascii=False, indent=2)

    print(f"\n結果已儲存至:")
    print(f"  {REGIME_FILE}")
    print(f"  {PARAM_REC_FILE}")

    return result


if __name__ == "__main__":
    run_historical_backtester()
