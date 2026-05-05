# -*- coding: utf-8 -*-
"""
Nana 交易狀況預測模組
 Trade Predictor
根據市場狀態預測未來交易機會，提前識別風險
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
PREDICTION_FILE = os.path.join(BASE_DIR, "trade_predictions.json")
REGIME_FILE = os.path.join(BASE_DIR, "market_regime.json")
MONITOR_FILE = os.path.join(BASE_DIR, "monitor_stocks.json")


def load_market_regime() -> Dict:
    """載入市場狀態"""
    if os.path.exists(REGIME_FILE):
        with open(REGIME_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_monitor_stocks() -> List[Dict]:
    """讀取監控股票清單"""
    if os.path.exists(MONITOR_FILE):
        with open(MONITOR_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("stocks", [])
    return []


def fetch_stock_data(ticker_str: str, days: int = 30) -> Optional[pd.DataFrame]:
    """抓取股票歷史數據"""
    try:
        ticker = yf.Ticker(ticker_str)
        hist = ticker.history(period=f"{days}d")
        return hist
    except Exception as e:
        return None


def calculate_indicators(hist: pd.DataFrame) -> Dict:
    """計算技術指標"""
    close = hist["Close"]
    high = hist["High"]
    low = hist["Low"]
    vol = hist["Volume"]

    # Get valid (non-NaN) data - last row may be today's empty candle when market is closed
    close_valid = close.dropna()
    high_valid = high.dropna()
    low_valid = low.dropna()
    vol_valid = vol.dropna()
    
    if len(close_valid) == 0:
        return {
            "close": None, "rsi": 50, "bias": 0, "vol_ratio": 1, "atr": 0,
            "sma20": None, "volume": 0
        }

    last_close = close_valid.iloc[-1]
    last_high = high_valid.iloc[-1]
    last_low = low_valid.iloc[-1]
    last_vol = vol_valid.iloc[-1]

    sma20 = close_valid.rolling(20).mean()
    sma60 = close_valid.rolling(60).mean()

    delta = close_valid.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    bias = ((close_valid - sma20) / sma20) * 100

    vol_ma20 = vol_valid.rolling(20).mean()
    vol_ratio = vol_valid / vol_ma20

    tr1 = high_valid - low_valid
    tr2 = abs(high_valid - close_valid.shift())
    tr3 = abs(low_valid - close_valid.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()

    current = {
        "close": float(last_close),
        "rsi": float(rsi.iloc[-1]),
        "bias": float(bias.iloc[-1]),
        "vol_ratio": float(vol_ratio.iloc[-1]),
        "atr": float(atr.iloc[-1]),
        "sma20": float(sma20.iloc[-1]),
        "volume": int(last_vol),
    }
    return current


def predict_stock_direction(ind: Dict, regime: str) -> Dict:
    """預測個股方向"""
    rsi = ind["rsi"]
    bias = ind["bias"]
    vol_ratio = ind["vol_ratio"]

    score = 0
    signal = "NEUTRAL"
    risk = "LOW"
    prediction = ""

    # RSI 評分
    if rsi < 30:
        score += 20
        signal = "OVERSOLD_BULL"
        prediction = "可能反彈"
    elif rsi < 45:
        score += 15
        signal = "RECOVERY"
        prediction = "有機會上漲"
    elif rsi < 55:
        score += 10
        signal = "NEUTRAL"
    elif rsi < 65:
        score += 5
        signal = "CAUTIOUS"
    elif rsi < 75:
        score -= 10
        risk = "MEDIUM"
        signal = "OVERBOUGHT"
        prediction = "小心回調"
    else:
        score -= 20
        risk = "HIGH"
        signal = "VERY_OVERBOUGHT"
        prediction = "風險很高"

    # BIAS 評分
    if bias < -8:
        score += 15
        prediction = "偏離過大，反彈機會"
    elif bias < -4:
        score += 10
    elif bias > 8:
        score -= 15
        risk = "HIGH"
        prediction = "偏離過大，回調風險"
    elif bias > 4:
        score -= 10
        risk = "MEDIUM"

    # Vol 評分
    if vol_ratio >= 1.5:
        score += 10

    # 市場狀態調整
    if regime == "BEAR":
        if signal.startswith("OVERSOLD"):
            score += 10  # 超賣有機會
        else:
            score -= 15
    elif regime == "BULL":
        if signal in ["RECOVERY", "NEUTRAL"]:
            score += 10
        else:
            score -= 5
    elif regime == "OVERBOUGHT":
        score -= 20
        risk = "HIGH"
        prediction = "市場過熱，個股風險大"

    # 風險評估
    if ind["rsi"] > 75:
        risk = "HIGH"
    elif ind["rsi"] > 65:
        risk = "MEDIUM"

    return {
        "signal": signal,
        "score": score,
        "risk": risk,
        "prediction": prediction,
    }


def run_trade_predictor():
    """主執行函式：交易狀況預測"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] === Nana 交易預測 ===")

    # 1. 取得市場狀態
    regime_data = load_market_regime()
    current_regime = "UNKNOWN"
    current_rsi = 50
    if regime_data:
        current_regime = regime_data.get("current_state", {}).get("regime", "UNKNOWN")
        current_rsi = regime_data.get("current_state", {}).get("rsi", 50)

    print(f"[INFO] Current market regime: {current_regime}, RSI: {current_rsi}")

    # 2. 抓取監控股票
    monitor_stocks = load_monitor_stocks()
    if not monitor_stocks:
        monitor_stocks = [
            {"stock_id": "2449", "name": "京元電子"},
            {"stock_id": "2891", "name": "中信金"},
            {"stock_id": "3231", "name": "緯創"},
            {"stock_id": "2886", "name": "兆豐金"},
            {"stock_id": "2317", "name": "鴻海"},
            {"stock_id": "3665", "name": "穎崴"},
            {"stock_id": "3035", "name": "智原"},
            {"stock_id": "2379", "name": "瑞昱"},
            {"stock_id": "2382", "name": "廣達"},
            {"stock_id": "1101", "name": "台泥"},
        ]

    # 3. 分析每檔股票
    predictions = []
    opportunities = []
    risks = []

    for stock in monitor_stocks:
        sid = stock["stock_id"]
        ticker_str = f"{sid}.TW"
        hist = fetch_stock_data(ticker_str, days=60)
        if hist is None or len(hist) < 30:
            continue

        ind = calculate_indicators(hist)
        pred = predict_stock_direction(ind, current_regime)
        pred["stock_id"] = sid
        pred["name"] = stock.get("name", sid)
        pred["close"] = round(ind["close"], 2)
        pred["rsi"] = round(ind["rsi"], 2)
        pred["bias"] = round(ind["bias"], 2)
        pred["vol_ratio"] = round(ind["vol_ratio"], 2)
        pred["atr"] = round(ind["atr"], 2)
        predictions.append(pred)

        if pred["risk"] == "LOW" and pred["score"] >= 15:
            opportunities.append(pred)
        elif pred["risk"] == "HIGH":
            risks.append(pred)

    # 排序
    opportunities.sort(key=lambda x: x["score"], reverse=True)
    risks.sort(key=lambda x: x["rsi"], reverse=True)

    # 4. 生成明日預測信號
    tomorrow_signals = {
        "date": date.today().isoformat(),
        "market_regime": current_regime,
        "market_rsi": current_rsi,
        "summary": {
            "total_stocks_analyzed": len(predictions),
            "opportunities": len(opportunities),
            "risks": len(risks),
        },
        "opportunities": opportunities[:5],
        "risks": risks[:5],
        "all_predictions": sorted(predictions, key=lambda x: x["score"], reverse=True)[:10],
    }

    # 5. 輸出
    print(f"\n=== {date.today().isoformat()} 交易預測 ===")
    print(f"市場狀態: {current_regime} | RSI: {current_rsi}")
    print(f"\n分析股票數: {len(predictions)}")
    print(f"有機會: {len(opportunities)} 檔 | 風險: {len(risks)} 檔")

    if opportunities:
        print(f"\n--- 明日有機會 ({len(opportunities)} 檔) ---")
        for op in opportunities[:5]:
            print(f"  {op['stock_id']} {op['name']} Score={op['score']} Signal={op['signal']} RSI={op['rsi']} BIAS={op['bias']:.1f}% -> {op['prediction']}")

    if risks:
        print(f"\n--- 風險警示 ({len(risks)} 檔) ---")
        for r in risks[:5]:
            print(f"  {r['stock_id']} {r['name']} RSI={r['rsi']} Risk={r['risk']} -> {r['prediction']}")

    # 6. 儲存
    with open(PREDICTION_FILE, "w", encoding="utf-8") as f:
        json.dump(tomorrow_signals, f, ensure_ascii=False, indent=2)

    print(f"\n預測結果已儲存至: {PREDICTION_FILE}")
    return tomorrow_signals


if __name__ == "__main__":
    run_trade_predictor()
