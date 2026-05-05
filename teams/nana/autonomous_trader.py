# -*- coding: utf-8 -*-
"""
Nana 自主交易模擬系統
 Autonomous Trading Simulator
根據 Nana v5.28 參數模擬進場/持有/出場決策
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import os
from datetime import datetime, date
from typing import Optional, Dict, List

import yfinance as yf
import pandas as pd
import numpy as np

# === 路徑設定 ===
BASE_DIR = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\nana"
AUTONOMOUS_TRADES_FILE = os.path.join(BASE_DIR, "autonomous_trades.json")
MONITOR_FILE = os.path.join(BASE_DIR, "monitor_stocks.json")

# Nana v5.28 進場參數 (動態，見 get_effective_entry_params)
# 預設值會被 market_regime.json 覆蓋
ENTRY_RSI_MAX_DEFAULT = 65
ENTRY_BIAS_MAX = 10.0  # %
ENTRY_SCORE_MIN = 40  # v5.41: 提高門檻 25→40，避免過度寬鬆進場
ENTRY_VOL_MIN = 0.8
MAX_POSITIONS = 5
VIRTUAL_CAPITAL = 100000  # NT$ per trade

# ATR 停損/停利參數
ATR_MULTIPLIER_STOP = 1.5
ATR_MULTIPLIER_TARGET = 3.0
HOLD_DAYS_MAX = 5  # 5日持有勝率最高（57.4% @ RSI<25）

# OVERBOUGHT 專用參數（v5.41修正）
OVERBOUGHT_HOLD_DAYS_MAX = 4  # 過熱市場持有期縮短至4天
OVERBOUGHT_ENTRY_RSI_MAX = 25  # v5.42: 根據歷史回測，RSI<25 勝率 57.4% 最高

# BIAS EXIT - v5.39發現：BIAS>5.0時出场勝率97.4%，Avg=6.54%
BIAS_EXIT_THRESHOLD = 5.0

# 動態進場參數（由 get_effective_entry_params 設定）
_effective_entry_rsi_max = ENTRY_RSI_MAX_DEFAULT  # 模組級變量
effective_hold_days_max = HOLD_DAYS_MAX  # v5.41: 動態持有期

# === 市場體制檢查 ===
def get_market_regime():
    """檢查大盤體制，return (regime, rsi, entry_rsi_max)"""
    global _effective_entry_rsi_max, effective_hold_days_max
    REGIME_FILE = os.path.join(BASE_DIR, "market_regime.json")
    if os.path.exists(REGIME_FILE):
        with open(REGIME_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            cs = data.get("current_state", {})
            regime = cs.get("regime", "NEUTRAL")
            rsi = cs.get("rsi", 50)
            # 動態讀取進場 RSI 門檻
            params = data.get("param_recommendations", {})
            regime_params = params.get(regime, {})
            entry_rsi_max = regime_params.get("entry_rsi_max", ENTRY_RSI_MAX_DEFAULT)
            # v5.41: OVERBOUGHT 使用更嚴格的 RSI<55
            if regime == "OVERBOUGHT":
                entry_rsi_max = min(entry_rsi_max, OVERBOUGHT_ENTRY_RSI_MAX)
            _effective_entry_rsi_max = entry_rsi_max
            # v5.41: OVERBOUGHT 持有期縮短
            effective_hold_days_max = OVERBOUGHT_HOLD_DAYS_MAX if regime == "OVERBOUGHT" else HOLD_DAYS_MAX
            return regime, rsi, entry_rsi_max
    return "NEUTRAL", 50, ENTRY_RSI_MAX_DEFAULT


def load_monitor_stocks() -> List[Dict]:
    """讀取監控股票清單"""
    if os.path.exists(MONITOR_FILE):
        with open(MONITOR_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("stocks", [])
    return []


def load_autonomous_trades() -> Dict:
    """載入虛擬交易記錄"""
    if os.path.exists(AUTONOMOUS_TRADES_FILE):
        with open(AUTONOMOUS_TRADES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "trades": [],
        "open_positions": [],
        "stats": {
            "total_trades": 0,
            "win_rate": 0.0,
            "avg_return": 0.0,
            "max_loss": 0.0,
            "max_gain": 0.0,
            "total_profit": 0.0
        },
        "last_updated": datetime.now().isoformat()
    }


def save_autonomous_trades(data: Dict):
    """儲存虛擬交易記錄"""
    data["last_updated"] = datetime.now().isoformat()
    with open(AUTONOMOUS_TRADES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def calculate_indicators(ticker_str: str) -> Optional[Dict]:
    """計算技術指標：RSI, BIAS, Vol, ATR"""
    try:
        ticker = yf.Ticker(ticker_str)
        hist = ticker.history(period="3mo")
        if hist.empty or len(hist) < 30:
            return None

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
            return None
        
        last_close = close_valid.iloc[-1]
        last_high = high_valid.iloc[-1]
        last_low = low_valid.iloc[-1]
        last_vol = vol_valid.iloc[-1]

        # SMA
        sma20 = close_valid.rolling(20).mean()
        sma60 = close_valid.rolling(60).mean()

        # RSI (14) - use only valid data
        delta = close_valid.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        # BIAS (20)
        bias = ((close_valid - sma20) / sma20) * 100

        # Vol Ratio (vs 20日均量)
        vol_ma20 = vol_valid.rolling(20).mean()
        vol_ratio = vol_valid / vol_ma20

        # ATR (14) - need to recalculate with valid data
        tr1 = high_valid - low_valid
        tr2 = abs(high_valid - close_valid.shift())
        tr3 = abs(low_valid - close_valid.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()

        current = {
            "close": round(float(last_close), 2),
            "rsi": round(float(rsi.iloc[-1]), 2),
            "bias": round(float(bias.iloc[-1]), 2),
            "vol_ratio": round(float(vol_ratio.iloc[-1]), 2),
            "atr": round(float(atr.iloc[-1]), 2),
            "sma20": round(float(sma20.iloc[-1]), 2),
            "sma60": round(float(sma60.iloc[-1]), 2) if not pd.isna(sma60.iloc[-1]) else None,
            "volume": int(last_vol),
        }
        return current
    except Exception as e:
        print(f"[ERROR] calculate_indicators {ticker_str}: {e}")
        return None


def check_entry_signals(indicators: Dict) -> bool:
    """檢查進場信號（使用 market_regime 動態門檻）"""
    global _effective_entry_rsi_max
    rsi = indicators.get("rsi", 100)
    bias = indicators.get("bias", 100)
    vol_ratio = indicators.get("vol_ratio", 0)
    return (
        rsi < _effective_entry_rsi_max  # 動態門檻（OVERBOUGHT=60, BULL=65）
        and abs(bias) < ENTRY_BIAS_MAX
        and vol_ratio >= ENTRY_VOL_MIN
    )


def check_exit_signals(indicators: Dict, entry_price: float, entry_atr: float, entry_date_str: str = None) -> Dict:
    """檢查出場信號：停損/停利/BIAS_EXIT/持有期（使用日曆天計算）"""
    current_price = indicators.get("close", entry_price)
    atr = indicators.get("atr", entry_atr)
    bias = indicators.get("bias", 0)

    stop_loss = entry_price - (atr * ATR_MULTIPLIER_STOP)
    target_profit = entry_price + (atr * ATR_MULTIPLIER_TARGET)

    # FIX v5.40: use calendar days instead of execution cycles
    hold_days = 0
    if entry_date_str:
        try:
            entry_d = datetime.strptime(entry_date_str, "%Y-%m-%d").date()
            hold_days = (date.today() - entry_d).days
        except:
            hold_days = 0

    signals = {
        "stop_loss_triggered": current_price <= stop_loss,
        "target_triggered": current_price >= target_profit,
        "bias_exit_triggered": bias > BIAS_EXIT_THRESHOLD,  # v5.39: BIAS>5.0 → 97.4% WR
        "stop_loss_price": round(stop_loss, 2),
        "target_price": round(target_profit, 2),
        "current_price": current_price,
        "atr": atr,
        "bias": bias,
        "return_pct": round(((current_price - entry_price) / entry_price) * 100, 2),
        "hold_days": hold_days,  # calendar-correct
    }
    return signals


def calculate_score(indicators: Dict) -> float:
    """計算 Nana score（簡化版）"""
    score = 0.0
    rsi = indicators.get("rsi", 50)
    bias = indicators.get("bias", 0)
    vol_ratio = indicators.get("vol_ratio", 1)

    # RSI 40-65進場最佳
    if 40 <= rsi < 50:
        score += 30
    elif 50 <= rsi < 60:
        score += 25
    elif 60 <= rsi < 65:
        score += 15

    # BIAS 負值為佳
    if bias < -5:
        score += 20
    elif bias < 0:
        score += 15
    elif bias < 5:
        score += 10

    # Vol 量能
    if vol_ratio >= 1.5:
        score += 25
    elif vol_ratio >= 1.2:
        score += 20
    elif vol_ratio >= 0.8:
        score += 10

    return score


def run_autonomous_trader():
    """主執行函式：每日自主交易模擬"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] === Nana 自主交易模擬 ===")

    # 1. 載入資料
    monitor_stocks = load_monitor_stocks()
    if not monitor_stocks:
        # 如果沒有監控清單，用內建股票
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
        print("[WARN] No monitor list found, using default stocks")

    data = load_autonomous_trades()
    open_positions = data.get("open_positions", [])

    print(f"[INFO] Open positions: {len(open_positions)}")
    print(f"[INFO] Monitor stocks: {len(monitor_stocks)}")

    # 2. 處理已有持倉：檢查停損/停利
    exited_trades = []
    updated_positions = []

    for pos in open_positions:
        sid = pos["stock_id"]
        ticker_str = f"{sid}.TW"
        ind = calculate_indicators(ticker_str)
        if ind is None:
            updated_positions.append(pos)
            continue

        signals = check_exit_signals(ind, pos["entry_price"], pos.get("atr", ind.get("atr", 5)), pos.get("entry_date"))
        pos["hold_days"] = signals.get("hold_days", 0)  # FIX v5.40: calendar days
        pos["current_price"] = signals["current_price"]
        pos["return_pct"] = signals["return_pct"]

        if signals["stop_loss_triggered"]:
            # 停損出局
            trade = {
                "trade_id": f"{sid}_{date.today().isoformat().replace('-', '')}_{datetime.now().strftime('%H%M%S')}",
                "stock_id": sid,
                "name": pos.get("name", sid),
                "entry_price": pos["entry_price"],
                "exit_price": signals["current_price"],
                "entry_date": pos["entry_date"],
                "exit_date": date.today().isoformat(),
                "hold_days": pos["hold_days"],
                "return_pct": signals["return_pct"],
                "profit_loss": round((signals["current_price"] - pos["entry_price"]) * VIRTUAL_CAPITAL / pos["entry_price"], 2),
                "exit_reason": "stop_loss",
                "trade_type": "virtual",
                "recorded_at": datetime.now().isoformat(),
            }
            exited_trades.append(trade)
            print(f"[EXIT] {sid} STOP LOSS @ {signals['current_price']} ({signals['return_pct']:+.2f}%)")
        elif signals["target_triggered"]:
            # 停利出局
            trade = {
                "trade_id": f"{sid}_{date.today().isoformat().replace('-', '')}_{datetime.now().strftime('%H%M%S')}",
                "stock_id": sid,
                "name": pos.get("name", sid),
                "entry_price": pos["entry_price"],
                "exit_price": signals["current_price"],
                "entry_date": pos["entry_date"],
                "exit_date": date.today().isoformat(),
                "hold_days": pos["hold_days"],
                "return_pct": signals["return_pct"],
                "profit_loss": round((signals["current_price"] - pos["entry_price"]) * VIRTUAL_CAPITAL / pos["entry_price"], 2),
                "exit_reason": "target_profit",
                "trade_type": "virtual",
                "recorded_at": datetime.now().isoformat(),
            }
            exited_trades.append(trade)
            print(f"[EXIT] {sid} TARGET PROFIT @ {signals['current_price']} ({signals['return_pct']:+.2f}%)")
        elif signals["bias_exit_triggered"]:
            # BIAS_EXIT - v5.39發現：BIAS>5.0時出场，97.4% WR
            trade = {
                "trade_id": f"{sid}_{date.today().isoformat().replace('-', '')}_{datetime.now().strftime('%H%M%S')}",
                "stock_id": sid,
                "name": pos.get("name", sid),
                "entry_price": pos["entry_price"],
                "exit_price": signals["current_price"],
                "entry_date": pos["entry_date"],
                "exit_date": date.today().isoformat(),
                "hold_days": pos["hold_days"],
                "return_pct": signals["return_pct"],
                "profit_loss": round((signals["current_price"] - pos["entry_price"]) * VIRTUAL_CAPITAL / pos["entry_price"], 2),
                "exit_reason": "bias_exit",
                "trade_type": "virtual",
                "recorded_at": datetime.now().isoformat(),
            }
            exited_trades.append(trade)
            print(f"[EXIT] {sid} BIAS_EXIT (BIAS={signals['bias']:.1f}%) @ {signals['current_price']} ({signals['return_pct']:+.2f}%)")
        elif pos["hold_days"] >= effective_hold_days_max:  # v5.41: 使用動態持有期
            # 持有期滿，強制出场
            trade = {
                "trade_id": f"{sid}_{date.today().isoformat().replace('-', '')}_{datetime.now().strftime('%H%M%S')}",
                "stock_id": sid,
                "name": pos.get("name", sid),
                "entry_price": pos["entry_price"],
                "exit_price": signals["current_price"],
                "entry_date": pos["entry_date"],
                "exit_date": date.today().isoformat(),
                "hold_days": pos["hold_days"],
                "return_pct": signals["return_pct"],
                "profit_loss": round((signals["current_price"] - pos["entry_price"]) * VIRTUAL_CAPITAL / pos["entry_price"], 2),
                "exit_reason": "hold_days_max",
                "trade_type": "virtual",
                "recorded_at": datetime.now().isoformat(),
            }
            exited_trades.append(trade)
            print(f"[EXIT] {sid} HOLD DAYS MAX @ {signals['current_price']} ({signals['return_pct']:+.2f}%)")
        else:
            updated_positions.append(pos)

    # 3. 新增出场交易
    data["trades"].extend(exited_trades)
    data["open_positions"] = updated_positions
    open_positions = updated_positions

    # 4. 執行進場篩選
    regime, mrsi, entry_rsi_max = get_market_regime()
    print(f"[INFO] Market regime: {regime} | TWII RSI={mrsi:.1f} | entry_RSI_max={entry_rsi_max}")
    
    if len(open_positions) < MAX_POSITIONS:
        candidates = []
        for stock in monitor_stocks:
            sid = stock["stock_id"]
            ticker_str = f"{sid}.TW"
            ind = calculate_indicators(ticker_str)
            if ind is None:
                continue

            if check_entry_signals(ind):
                score = calculate_score(ind)
                ind["stock_id"] = sid
                ind["name"] = stock.get("name", sid)
                ind["score"] = score
                ind["ticker"] = ticker_str
                candidates.append(ind)

        # 按 score 排序，取最高的
        candidates.sort(key=lambda x: x.get("score", 0), reverse=True)

        available_slots = MAX_POSITIONS - len(open_positions)
        # Skip candidates already in open positions (prevent duplicates)
        held_ids = {pos["stock_id"] for pos in open_positions}
        # 市場OVERBOUGHT時禁止新進場（v5.39發現：OVERBOUGHT進場勝率低）
        if regime == "OVERBOUGHT":
            print(f"[WARN] Market OVERBOUGHT (RSI={mrsi:.1f}) - blocking all new entries, holding existing positions")
        else:
            for cand in candidates[:available_slots]:
                if cand.get("score", 0) >= ENTRY_SCORE_MIN and cand["stock_id"] not in held_ids:
                    # v5.41: ATR 波動率標準化作為 position size 維度
                    atr_pct = (cand["atr"] / cand["close"]) * 100 if cand["close"] > 0 else 2.0
                    vol_factor = round(max(0.5, min(1.0, 1.5 / atr_pct)) if atr_pct > 0 else 1.0, 2)
                    
                    new_pos = {
                        "stock_id": cand["stock_id"],
                        "name": cand["name"],
                        "entry_price": cand["close"],
                        "entry_date": date.today().isoformat(),
                        "atr": cand["atr"],
                        "atr_pct": round(atr_pct, 2),
                        "vol_factor": vol_factor,
                        "hold_days": 0,
                        "current_price": cand["close"],
                        "return_pct": 0.0,
                        "score": cand["score"],
                        "rsi": cand["rsi"],
                        "bias": cand["bias"],
                        "vol_ratio": cand["vol_ratio"],
                    }
                    open_positions.append(new_pos)
                    print(f"[ENTRY] {cand['stock_id']} {cand['name']} @ {cand['close']} RSI={cand['rsi']} BIAS={cand['bias']:.1f}% Vol={cand['vol_ratio']:.2f} Score={cand['score']}")

        data["open_positions"] = open_positions

    # 5. 更新統計
    all_trades = data["trades"]
    if all_trades:
        returns = [t["return_pct"] for t in all_trades]
        wins = [r for r in returns if r > 0]
        data["stats"] = {
            "total_trades": len(all_trades),
            "win_rate": round(len(wins) / len(all_trades) * 100, 2),
            "avg_return": round(sum(returns) / len(returns), 4),
            "max_gain": round(max(returns), 4) if returns else 0,
            "max_loss": round(min(returns), 4) if returns else 0,
            "total_profit": round(sum(t.get("profit_loss", 0) for t in all_trades), 2),
        }
    else:
        data["stats"] = {
            "total_trades": 0,
            "win_rate": 0.0,
            "avg_return": 0.0,
            "max_loss": 0.0,
            "max_gain": 0.0,
            "total_profit": 0.0
        }

    save_autonomous_trades(data)

    # 6. 終端機輸出摘要
    print(f"\n=== Nana 自主交易模擬摘要 ===")
    print(f"總交易次數: {data['stats']['total_trades']}")
    print(f"勝率: {data['stats']['win_rate']:.1f}%")
    print(f"平均報酬: {data['stats']['avg_return']:+.2f}%")
    print(f"最大獲利: {data['stats']['max_gain']:+.2f}%")
    print(f"最大虧損: {data['stats']['max_loss']:+.2f}%")
    print(f"目前持倉: {len(data['open_positions'])} 檔")
    for pos in data["open_positions"]:
        print(f"  {pos['stock_id']} {pos['name']}: {pos['current_price']} ({pos['return_pct']:+.2f}%)")

    print(f"\n記錄已儲存至: {AUTONOMOUS_TRADES_FILE}")
    return data


if __name__ == "__main__":
    run_autonomous_trader()
