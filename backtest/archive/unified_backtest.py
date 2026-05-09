# -*- coding: utf-8 -*-
"""
Tina 統一回測引擎 v1.0 — Nana / Leo / Ray 三大團隊共享
功能：
  - 使用真實歷史報價（yfinance）
  - 統一回測框架：進場篩選 → 持倉模擬 → 結算統計
  - 支援 Nana 波段、Leo 波段、Ray DCA 三種策略
  - 自動寫入各團隊 sim_trades.json
用法:
  python unified_backtest.py [team] [start_date] [end_date]
  例如: python unified_backtest.py nana 2025-01-01 2025-12-31
"""

import sys, os, json
import yfinance as yf
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional

sys.stdout.reconfigure(encoding='utf-8')

# ========== 全域設定 ==========
VALID_STOCKS = [
    "2330","2317","2454","2303","2382","2408","2376","2379","3034","3045",
    "3665","3711","2308","2345","2388","2441","2451","2474","2498","2542",
    "2615","2633","2881","2882","2883","2884","2885","2886","2887","2891",
    "2892","2912","2939","3008","3037","3231","3443","3481","3530","3673",
    "3702","4155","4164","4306","4532","4746","4770","4938","4952","4961",
    "5203","5215","5234","5388","5471","5538","5871","5876","5880","6116",
    "6139","6176","6183","6230","6257","6285","6409","6415","6446","6533",
    "6550","6552","6579","6581","6770","6789","8016","8028","8046","8081",
    "8131","8150","8261","8454","8464","8478","8481"
]

BASE_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams'

# ========== 技術指標工具 ==========
def get_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50.0
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0:
        return 100
    return 100 - (100 / (1 + avg_gain / avg_loss))

def get_atr(highs, lows, closes, period=14):
    if len(closes) < period + 1:
        return 5.0
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        trs.append(tr)
    return float(np.mean(trs[-period:])) if trs else 5.0

def get_ma20(closes):
    if len(closes) < 20:
        return float(closes[-1]) if len(closes) > 0 else 100.0
    return float(np.mean(closes[-20:]))

def get_ma120(closes):
    if len(closes) < 120:
        return None
    return float(np.mean(closes[-120:]))

def get_momentum(closes, period=20):
    if len(closes) < period + 1:
        return 0.0
    return float((closes[-1] / closes[-period] - 1) * 100)

def get_volume_ratio(volumes, period=5):
    if len(volumes) < period + 1:
        return 1.0
    return float(volumes[-1] / np.mean(volumes[-period:]))

def get_ma_slope(closes, period=20, bars=5):
    if len(closes) < period + bars:
        return 0.0
    ma_now = np.mean(closes[-period:])
    ma_prev = np.mean(closes[-(period+bars):-bars])
    return float((ma_now - ma_prev) / ma_prev * 100) if ma_prev != 0 else 0.0

# ========== 資料取得 ==========
def fetch_stock_history(symbol, days=400):
    """取得股票歷史數據（涵蓋足夠回測區間）"""
    try:
        ticker = yf.Ticker(f"{symbol}.TW")
        hist = ticker.history(period=f"{days}d")
        if hist.empty or len(hist) < 60:
            return None
        return {
            "close": hist['Close'].values,
            "open": hist['Open'].values,
            "high": hist['High'].values,
            "low": hist['Low'].values,
            "volume": hist['Volume'].values,
            "symbol": symbol,
            "dates": hist.index.tolist()
        }
    except:
        return None

# ========== Nana 波段策略 ==========
class NanaStrategy:
    """Nana 波段策略（已驗證參數）"""
    ENTRY_RSI_MIN = 35
    ENTRY_RSI_MAX = 60
    ENTRY_SCORE_MIN = 38
    ATR_STOP = 2.0
    ATR_TP = 3.0
    HOLD_DAYS = 7
    BIAS_MAX = 3.0

    @classmethod
    def calculate_score(cls, stock_data):
        score = 0
        rsi = stock_data.get("rsi", 50)
        if 40 <= rsi <= 50:
            score += 20
        elif 50 < rsi <= 55:
            score += 10
        elif rsi < 40:
            score += 5

        foreign_net = stock_data.get("foreign_net", 0)
        if foreign_net > 1000:
            score += 25
        elif foreign_net > 500:
            score += 15

        ma20_diff = stock_data.get("ma20_diff", 0)
        if abs(ma20_diff) < 2:
            score += 15
        elif abs(ma20_diff) < cls.BIAS_MAX:
            score += 10

        momentum = stock_data.get("momentum", 0)
        if momentum > 3:
            score += 10
        elif momentum > 0:
            score += 5

        slope = stock_data.get("slope", 0)
        if slope > 1.0:
            score += 8
        elif slope > 0.5:
            score += 5
        elif slope > 0:
            score += 3

        return score

    @classmethod
    def check_entry(cls, stock_data, regime):
        rsi = stock_data.get("rsi", 50)
        score = cls.calculate_score(stock_data)
        ma20_diff = stock_data.get("ma20_diff", 0)

        if regime == "OVERBOUGHT":
            return False
        if rsi < cls.ENTRY_RSI_MIN or rsi > cls.ENTRY_RSI_MAX:
            return False
        if score < cls.ENTRY_SCORE_MIN:
            return False
        if abs(ma20_diff) > cls.BIAS_MAX:
            return False
        return True

    @classmethod
    def simulate_trade(cls, entry_idx, data, regime, holding_days=7):
        """模擬一筆波段交易"""
        closes = data["close"]
        highs = data["high"]
        lows = data["low"]

        entry_price = float(closes[entry_idx])
        atr = get_atr(highs[entry_idx:], lows[entry_idx:], closes[entry_idx:], 14)

        highest_price = entry_price
        trailing_stop = entry_price - (atr * cls.ATR_STOP)
        target_price = entry_price + (atr * cls.ATR_TP)

        exit_reason = "hold_expired"
        exit_price = float(closes[entry_idx + holding_days]) if entry_idx + holding_days < len(closes) else float(closes[-1])
        exit_day = holding_days

        for day in range(holding_days):
            if entry_idx + day >= len(closes):
                break
            cur = float(closes[entry_idx + day])
            highest_price = max(highest_price, cur)

            new_trailing = highest_price - (atr * cls.ATR_STOP)
            if new_trailing > trailing_stop:
                trailing_stop = new_trailing

            if cur < trailing_stop:
                exit_reason = "trailing_stop"
                exit_price = cur
                exit_day = day
                break
            if cur >= target_price:
                exit_reason = "take_profit"
                exit_price = cur
                exit_day = day
                break

        ret_pct = (exit_price - entry_price) / entry_price * 100
        return {
            "entry_idx": entry_idx,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "exit_reason": exit_reason,
            "hold_days": exit_day + 1,
            "return_pct": ret_pct,
            "atr": atr
        }

# ========== Leo 波段策略 ==========
class LeoStrategy:
    """Leo AI 科技股波段策略"""
    ENTRY_RSI_MAX = 60
    EXIT_RSI_MIN = 80
    TAKE_PROFIT = 0.20
    STOP_LOSS = 0.08

    @classmethod
    def check_entry(cls, stock_data, regime):
        rsi = stock_data.get("rsi", 50)
        pos_ma20 = stock_data.get("ma20_diff", 0)

        if regime == "OVERBOUGHT":
            return False
        if rsi < 40 or rsi > cls.ENTRY_RSI_MAX:
            return False
        if pos_ma20 > 15:
            return False
        return True

    @classmethod
    def simulate_trade(cls, entry_idx, data, regime, holding_days=10):
        closes = data["close"]
        entry_price = float(closes[entry_idx])
        target = entry_price * (1 + cls.TAKE_PROFIT)
        stop = entry_price * (1 - cls.STOP_LOSS)

        exit_reason = "hold_expired"
        exit_price = float(closes[entry_idx + holding_days]) if entry_idx + holding_days < len(closes) else float(closes[-1])
        exit_day = holding_days

        for day in range(holding_days):
            if entry_idx + day >= len(closes):
                break
            cur = float(closes[entry_idx + day])
            if cur >= target:
                exit_reason = "take_profit"
                exit_price = cur
                exit_day = day
                break
            if cur <= stop:
                exit_reason = "stop_loss"
                exit_price = cur
                exit_day = day
                break

        ret_pct = (exit_price - entry_price) / entry_price * 100
        return {
            "entry_idx": entry_idx,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "exit_reason": exit_reason,
            "hold_days": exit_day + 1,
            "return_pct": ret_pct,
        }

# ========== 統一回測引擎 ==========
def get_regime(closes, highs, lows):
    """判斷市場體質"""
    rsi = get_rsi(closes, 20)
    ma20 = get_ma20(closes)
    ma_slope = get_ma_slope(closes, 20, 10)

    if rsi > 85:
        return "OVERBOUGHT"
    elif rsi > 65 and ma_slope > 0.5:
        return "BULL"
    elif rsi < 30:
        return "OVERSOLD"
    else:
        return "NEUTRAL"

def run_unified_backtest(team="nana", start_date="2025-01-01", end_date="2026-04-25", scan_interval=5):
    """
    統一回測引擎
    - team: nana / leo / ray
    - start_date: 回測起始日
    - end_date: 回測結束日
    - scan_interval: 每隔幾天掃描一次進場機會
    """
    print("=" * 60)
    print(f"  Tina 統一回測引擎 — {team.upper()} 波段系統")
    print(f"  回測區間: {start_date} ~ {end_date}")
    print("=" * 60)

    if team == "leo":
        stocks = ["2330","2454","2317","2379","2376","2382","3665","3034"]
    elif team == "ray":
        # Ray DCA 主要看 ETF，不做個股波段回測
        stocks = ["0050","0056","00878","00919","00713","00646"]
        print("  [Ray DCA] 採用 Buy & Hold 回測模式")
    else:
        stocks = VALID_STOCKS

    strategy = NanaStrategy() if team in ["nana", "ray"] else LeoStrategy()

    all_trades = []
    stock_stats = {}

    for symbol in stocks:
        print(f"\n  掃描 {symbol}...", end=" ", flush=True)
        data = fetch_stock_history(symbol, days=500)
        if data is None:
            print("資料取得失敗")
            continue

        closes = data["close"]
        highs = data["high"]
        lows = data["low"]

        if len(closes) < 60:
            print(f"資料不足({len(closes)}天)")
            continue

        regime = get_regime(closes, highs, lows)

        # 滾動掃描進場點
        trades = []
        for i in range(20, len(closes) - 10, scan_interval):
            stock_data = {
                "rsi": get_rsi(closes[:i+1], 14),
                "ma20": get_ma20(closes[:i+1]),
                "ma20_diff": ((closes[i] - get_ma20(closes[:i+1])) / get_ma20(closes[:i+1])) * 100 if get_ma20(closes[:i+1]) != 0 else 0,
                "atr": get_atr(highs[:i+1], lows[:i+1], closes[:i+1], 14),
                "momentum": get_momentum(closes[:i+1], 20),
                "slope": get_ma_slope(closes[:i+1], 20, 5),
                "volume_ratio": get_volume_ratio(data["volume"][:i+1]),
                "foreign_net": 0,
            }

            if strategy.check_entry(stock_data, regime):
                result = strategy.simulate_trade(i, data, regime, holding_days=7 if team == "nana" else 10)
                result["symbol"] = symbol
                result["regime"] = regime
                result["data_rsi"] = round(stock_data["rsi"], 1)
                result["data_score"] = NanaStrategy.calculate_score(stock_data) if hasattr(strategy, 'calculate_score') else 0
                trades.append(result)

        if trades:
            stock_stats[symbol] = {
                "trades": len(trades),
                "wr": len([t for t in trades if t["return_pct"] > 0]) / len(trades) * 100,
                "avg": sum(t["return_pct"] for t in trades) / len(trades)
            }
            all_trades.extend(trades)
            print(f"{len(trades)}筆進場 (WR={stock_stats[symbol]['wr']:.0f}%)")
        else:
            print("無進場")

    # ========== 統計輸出 ==========
    print("\n" + "=" * 60)
    print(f"  回測統計 — {team.upper()}")
    print("=" * 60)

    if not all_trades:
        print("  無交易資料")
        return all_trades

    wins = [t for t in all_trades if t["return_pct"] > 0]
    losses = [t for t in all_trades if t["return_pct"] <= 0]
    wr = len(wins) / len(all_trades) * 100
    avg_ret = sum(t["return_pct"] for t in all_trades) / len(all_trades)
    avg_win = sum(t["return_pct"] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t["return_pct"] for t in losses) / len(losses) if losses else 0

    print(f"  總交易: {len(all_trades)}筆")
    print(f"  勝率: {wr:.1f}% ({len(wins)}勝/{len(losses)}負)")
    print(f"  平均報酬: {avg_ret:+.2f}%")
    print(f"  平均獲利: {avg_win:+.2f}% | 平均虧損: {avg_loss:+.2f}%")
    print(f"  最大獲利: {max(t['return_pct'] for t in all_trades):+.2f}% | 最大虧損: {min(t['return_pct'] for t in all_trades):+.2f}%")

    # 個別股票表現
    print("\n  股票表現:")
    for sym, stat in sorted(stock_stats.items(), key=lambda x: -x[1]["avg"]):
        print(f"    {sym}: {stat['trades']}筆, WR={stat['wr']:.0f}%, Avg={stat['avg']:+.2f}%")

    # 寫入 sim_trades.json
    sim_data = {
        "team": team,
        "backtest_period": f"{start_date}~{end_date}",
        "trades": all_trades,
        "stats": {
            "total_trades": len(all_trades),
            "win_rate": wr,
            "avg_return": avg_ret,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "max_gain": max(t['return_pct'] for t in all_trades),
            "max_loss": min(t['return_pct'] for t in all_trades),
            "by_stock": stock_stats
        },
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M")
    }

    if team == "nana":
        out_dir = os.path.join(BASE_DIR, "nana", "reports")
    elif team == "leo":
        out_dir = os.path.join(BASE_DIR, "leo", "reports")
    else:
        out_dir = os.path.join(BASE_DIR, "ray", "reports")

    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "sim_trades.json")
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(sim_data, f, ensure_ascii=False, indent=2)
    print(f"\n  已寫入: {out_file}")

    return all_trades


if __name__ == "__main__":
    import sys
    team = sys.argv[1] if len(sys.argv) > 1 else "nana"
    start = sys.argv[2] if len(sys.argv) > 2 else "2025-01-01"
    end = sys.argv[3] if len(sys.argv) > 3 else "2026-04-25"

    run_unified_backtest(team, start, end)
