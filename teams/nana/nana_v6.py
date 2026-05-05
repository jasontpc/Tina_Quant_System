# -*- coding: utf-8 -*-
"""
Nana v6.2 — 台股前100大市值波段交易核心系統 (修正版)
動態進場 / 獲利浮動機制 / 主動分析優化 / 回測模擬
⚠️ 修復：隨機模擬 → 市場報價 (yfinance)
⚠️ 修復：移除已下市股票（42檔）提高掃描效率
⚠️ 修復：放寬法人進場條件，改為計分制非封鎖制
"""

import sys
import json
import os
import warnings
from datetime import datetime
from datetime import timedelta

# 抑制 yfinance 警告
warnings.filterwarnings('ignore')

sys.stdout.reconfigure(encoding='utf-8')

try:
    import yfinance as yf
    import numpy as np
    import pandas as pd
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False

try:
    from FinMind.data import DataLoader
    HAS_FINMIND = True
except ImportError:
    HAS_FINMIND = False

# ============ FinMind Token ============
FINMIND_TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSJ9.oCdQO1qNRUCYxHZSVuRQCqlF7X2DbQ77wury5ARCKzM'

# ============ 台股前100大市值股票池（已驗證可取得報價）===========
VALID_STOCKS = [
    "2330","2317","2454","2303","2382","2408","2376","2379","3034","3045",
    "3665","3711","2308","2345","2388","2441","2451","2474","2498","2542",
    "2615","2633","2881","2882","2883","2884","2885","2886","2887","2891",
    "2892","2912","2939","3008","3037","3231","3443","3481","3530","3673",
    "3702","3711","4155","4164","4306","4532","4746","4770","4938","4952",
    "4961","5203","5215","5234","5388","5471","5538","5871","5876","5880",
    "6116","6139","6176","6183","6230","6257","6285","6409","6415","6446",
    "6533","6550","6552","6579","6581","6770","6789","8016","8028","8046",
    "8081","8131","8150","8261","8454","8464","8478","8481"
]

# 已下市或無報價股票（42檔）- 排除
INVALID_STOCKS = set([
    "3682","3908","4001","4002","4004","4005","4013","4014","4044","4433",
    "4767","4821","4979","4984","5227","5264","5287","5439","5483","5904",
    "6023","6055","6104","6455","6488","6622","6643","6650","6702","6747",
    "6820","8109","8200","8406","8410","8506","8527","8570","8624","8648",
    "8674","8698"
])

TOP100_STOCKS = VALID_STOCKS

# ============ 核心策略參數 ============
ENTRY_RSI_MIN = 35          # 順勢進場下限
ENTRY_RSI_MAX = 55          # 順勢進場上限
ENTRY_SCORE_MIN = 35        # 進場分數門檻
ATR_STOP_LOSS = 1.5         # ATR 停損
ATR_TAKE_PROFIT = 4.0       # ATR 目標獲利
TRAILING_ATR = 2.0          # 移動停損 ATR 倍數
HOLD_DAYS_MAX = 10           # 最大持有天數
BIAS_MAX = 3.0             # 偏離MA20上限%
REGIME_FILTER = True        # Regime 過濾
FOREIGN_NET_MIN = 500       # 法人買超最小額


def get_rsi(prices, period=14):
    """計算 RSI"""
    if len(prices) < period + 1:
        return 50.0
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def get_atr(highs, lows, closes, period=14):
    """計算 ATR"""
    if len(closes) < period + 1:
        return 5.0
    trs = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )
        trs.append(tr)
    return np.mean(trs[-period:]) if trs else 5.0


def get_ma20(closes):
    """計算 MA20"""
    if len(closes) < 20:
        return closes[-1] if len(closes) > 0 else 100
    return np.mean(closes[-20:])


def get_ma_slope(closes, period=20, bars=5):
    """計算 MA 斜率 (% over N bars)"""
    if len(closes) < period + bars:
        return 0.0
    ma_now = np.mean(closes[-period:])
    ma_prev = np.mean(closes[-(period+bars):-bars])
    return ((ma_now - ma_prev) / ma_prev) * 100 if ma_prev != 0 else 0.0


def get_momentum(closes, period=20):
    """計算動量 (% price change)"""
    if len(closes) < period + 1:
        return 0.0
    return ((closes[-1] / closes[-period]) - 1) * 100


def get_taiwan_index_regime():
    """分析大盤體質 (使用 ^TWII)"""
    if not HAS_YFINANCE:
        return "BULL", 50.0, 90.0

    try:
        twii = yf.Ticker("^TWII")
        hist = twii.history(period="60d")
        if len(hist) < 30:
            return "BULL", 50.0, 90.0

        closes = hist['Close'].values
        highs = hist['High'].values
        lows = hist['Low'].values

        rsi = get_rsi(closes, 20)
        slope = get_ma_slope(closes, 20, 10)

        # Regime 判斷
        if rsi > 85:
            regime = "OVERBOUGHT"
        elif rsi > 65 and slope > 0.5:
            regime = "BULL"
        elif rsi < 30:
            regime = "OVERSOLD"
        else:
            regime = "NEUTRAL"

        return regime, rsi, slope
    except Exception as e:
        print(f"  [警告] 大盤資料取得失敗: {e}")
        return "BULL", 50.0, 90.0


def fetch_stock_data_yf(symbol, days=60):
    """"使用 yfinance 取得真實股價資料"""
    if not HAS_YFINANCE:
        return None

    try:
        ticker = yf.Ticker(f"{symbol}.TW")
        # 確保取得足夠資料（取 days*2 應涵盖週末和休市）
        hist = ticker.history(period=f"{days}d")
        if hist.empty:
            return None

        # 回測需要至少 10 根K棒（覆蓋5天回測 + 緩衝）
        min_bars = max(10, days)
        if len(hist) < min_bars:
            return None

        return {
            "close": hist['Close'].values,
            "open": hist['Open'].values,
            "high": hist['High'].values,
            "low": hist['Low'].values,
            "volume": hist['Volume'].values,
            "symbol": symbol
        }
    except Exception:
        return None


def analyze_stock_real(symbol):
    """使用真實市場資料分析股票"""
    data = fetch_stock_data_yf(symbol, days=60)
    if data is None:
        return None

    closes = data['close']
    highs = data['high']
    lows = data['low']
    volumes = data['volume']

    # 技術指標計算至少需要 30 根K棒
    if len(closes) < 30:
        return None

    rsi = get_rsi(closes, 14)
    ma20 = get_ma20(closes)
    atr = get_atr(highs, lows, closes, 14)
    slope = get_ma_slope(closes, 20, 5)
    momentum = get_momentum(closes, 20)
    current_price = closes[-1]
    ma20_diff = ((current_price - ma20) / ma20) * 100 if ma20 != 0 else 0

    stock_data = {
        "symbol": symbol,
        "close": current_price,
        "rsi": rsi,
        "ma20": ma20,
        "ma20_diff": ma20_diff,
        "atr": atr,
        "slope": slope,
        "momentum": momentum,
        "foreign_net": 0,
        "volume": volumes[-1] if len(volumes) > 0 else 0,
        "data_source": "yfinance"
    }

    return stock_data


class NanaCore:
    def __init__(self):
        self.name = "Nana v6.2 Core (Real Market Data)"
        self.positions = []
        self.trades = []
        self.learning_log = []
        self.config = self.load_config()

    def load_config(self):
        config_path = os.path.join(os.path.dirname(__file__), 'nana_v6_config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def get_market_regime(self):
        """分析市場體質"""
        regime, rsi, slope = get_taiwan_index_regime()
        return regime

    def calculate_score(self, stock_data):
        """計算進場分數（100分制）"""
        score = 0

        # RSI 條件（30分）
        rsi = stock_data.get("rsi", 50)
        if 40 <= rsi <= 50:
            score += 20
        elif 50 < rsi <= 55:
            score += 10
        elif rsi < 40:
            score += 5

        # 法人條件（40分）- 改為參考性，不直接封鎖
        foreign_net = stock_data.get("foreign_net", 0)
        if foreign_net > 1000:
            score += 25
        elif foreign_net > FOREIGN_NET_MIN:
            score += 15
        # 低於門檻不扣分，只是不加分

        # 技術面條件（30分）
        ma20_diff = stock_data.get("ma20_diff", 0)
        if abs(ma20_diff) < 2:
            score += 15
        elif abs(ma20_diff) < BIAS_MAX:
            score += 10

        # 動量加分（最多15分）— 順勢市場多頭動能重要
        momentum = stock_data.get("momentum", 0)
        if momentum > 5:
            score += 10
        elif momentum > 3:
            score += 7
        elif momentum > 1:
            score += 5
        elif momentum > 0:
            score += 3

        # MA 斜率加分（最多10分）
        slope = stock_data.get("slope", 0)
        if slope > 1.0:
            score += 8
        elif slope > 0.5:
            score += 5
        elif slope > 0:
            score += 3

        return score

    def check_entry(self, stock_data, regime):
        """檢查進場條件"""
        rsi = stock_data.get("rsi", 50)
        score = stock_data.get("score", 0)
        ma20_diff = stock_data.get("ma20_diff", 0)

        # Regime 過濾
        if REGIME_FILTER and regime == "OVERBOUGHT":
            return False, "OVERBOUGHT市場禁止進場"

        # RSI 條件（改為更寬鬆，順勢市場允許 higher RSI）
        if rsi < 35 or rsi > 60:
            return False, f"RSI={rsi:.1f}不在合理區間"

        if rsi > 55 and regime == "BULL":
            return False, "BULL市場RSI>55過高，禁止追漲"

        # 分數條件
        if score < ENTRY_SCORE_MIN:
            return False, f"分數={score}低於門檻{ENTRY_SCORE_MIN}"

        # BIAS 條件
        if abs(ma20_diff) > BIAS_MAX:
            return False, f"BIAS={ma20_diff:.1f}%超過{BIAS_MAX}%"

        return True, "符合進場條件"

    def check_trailing_exit(self, entry_price, current_price, highest_price, atr, hold_days):
        """浮動獲利退出機制"""
        trailing_stop = highest_price - (atr * TRAILING_ATR)
        if current_price < trailing_stop:
            return True, "移動停損觸發", trailing_stop

        target = entry_price + (atr * ATR_TAKE_PROFIT)
        if current_price >= target:
            new_trailing = current_price * 0.95
            return True, f"達標獲利了結({target:.2f})", new_trailing

        if hold_days >= HOLD_DAYS_MAX:
            return True, f"持有期滿({hold_days}天)", current_price

        return False, "持續持有", None

    def analyze_stock(self, symbol):
        """分析單一股票（優先使用真實資料）"""
        stock_data = analyze_stock_real(symbol)
        if stock_data is None:
            return None

        stock_data["score"] = self.calculate_score(stock_data)
        return stock_data

    def run_dynamic_entry(self, regime):
        """動態進場掃描"""
        candidates = []
        failed = []

        for symbol in TOP100_STOCKS:
            data = self.analyze_stock(symbol)
            if data is None:
                failed.append(symbol)
                continue

            can_enter, reason = self.check_entry(data, regime)
            if can_enter:
                data["reason"] = reason
                candidates.append(data)

        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:10], failed

    def run_backtest_simulation(self, candidates, days=5):
        """回測模擬（使用真實歷史資料）"""
        print(f"\n【回測模擬 — 真實資料 {days}天】")

        if not candidates:
            print("  無進場候選，跳過回測")
            return []

        results = []
        for stock in candidates[:5]:
            symbol = stock["symbol"]
            data = fetch_stock_data_yf(symbol, days=days + 20)
            if data is None:
                continue

            closes = data['close']
            highs = data['high']

            if len(closes) < 10:
                continue

            # 從倒數第6根K棒進場（可用closes[-6]到closes[-1]，共5根）
            entry_price = closes[-6]
            atr = stock.get("atr", 5)
            highest_price = entry_price

            trades = []
            for day in range(5):
                current_price = closes[-5 + day]  # closes[-5] 到 closes[-1]
                highest_price = max(highest_price, current_price)

                exit_flag, exit_reason, exit_price = self.check_trailing_exit(
                    entry_price, current_price, highest_price, atr, day + 1
                )

                if exit_flag:
                    trades.append({
                        "symbol": symbol,
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "exit_reason": exit_reason,
                        "hold_days": day + 1,
                        "return_pct": ((exit_price - entry_price) / entry_price) * 100
                    })
                    break

            if not trades:
                final_price = closes[-1]
                trades.append({
                    "symbol": symbol,
                    "entry_price": entry_price,
                    "exit_price": final_price,
                    "exit_reason": "模擬期滿",
                    "hold_days": 5,
                    "return_pct": ((final_price - entry_price) / entry_price) * 100
                })

            results.extend(trades)

        if results:
            wins = [r for r in results if r["return_pct"] > 0]
            losses = [r for r in results if r["return_pct"] <= 0]
            win_rate = len(wins) / len(results) * 100 if results else 0
            avg_return = sum(r["return_pct"] for r in results) / len(results)

            print(f"  總交易: {len(results)}筆")
            print(f"  勝率: {win_rate:.1f}%")
            print(f"  平均報酬: {avg_return:.2f}%")
            print(f"  勝: {len(wins)}筆, 負: {len(losses)}筆")

            for r in results:
                status = "✅" if r["return_pct"] > 0 else "❌"
                print(f"    {status} {r['symbol']}: {r['return_pct']:+.2f}% ({r['exit_reason']})")

        return results

    def run_strategy_optimization(self, candidates, regime):
        """主動策略優化分析"""
        print("\n【主動策略優化分析】")

        market_analysis = {
            "regime": regime,
            "candidate_count": len(candidates),
            "avg_score": sum(c.get("score", 0) for c in candidates) / len(candidates) if candidates else 0,
            "avg_rsi": sum(c.get("rsi", 0) for c in candidates) / len(candidates) if candidates else 0
        }

        print(f"  Regime: {market_analysis['regime']}")
        print(f"  候選數量: {market_analysis['candidate_count']}檔")
        print(f"  平均分數: {market_analysis['avg_score']:.1f}")
        print(f"  平均RSI: {market_analysis['avg_rsi']:.1f}")

        suggestions = []

        if regime == "OVERBOUGHT":
            suggestions.append("市場過熱，全面封鎖進場，等待回調")
        elif regime == "BULL":
            if len(candidates) < 3:
                suggestions.append("多頭市場但候選不足，降低分數門檻5分")
            if market_analysis['avg_score'] > 45:
                suggestions.append("整體分數偏高，等待更好的進場點")
        elif regime == "NEUTRAL":
            suggestions.append("中性市場，維持當前策略，耐心等待")

        for i, s in enumerate(suggestions, 1):
            print(f"  💡 建議{i}: {s}")

        return suggestions

    def execute_cycle(self):
        """執行完整分析循環"""
        print("=" * 60)
        print("  Nana v6.2 — 台股前100大市值波段交易核心系統")
        print(f"  時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("  資料來源: yfinance (真實市場報價)")
        print("=" * 60)

        # Step 1: 市場體質分析
        print("\n【Step 1】市場體質分析")
        regime = self.get_market_regime()
        print(f"  Regime: {regime}")
        self.learning_log.append(f"Regime: {regime}")

        # Step 2: 動態進場掃描
        print("\n【Step 2】動態進場掃描")
        candidates, failed = self.run_dynamic_entry(regime)
        print(f"  發現 {len(candidates)} 檔進場候選")
        if failed:
            print(f"  資料取得失敗: {len(failed)} 檔")

        if candidates:
            print("\n  前5名候選:")
            for i, c in enumerate(candidates[:5], 1):
                print(f"    {i}. {c['symbol']}: RSI={c['rsi']:.1f}, Score={c['score']}, BIAS={c['ma20_diff']:.1f}%")

        # Step 3: 回測模擬
        print("\n【Step 3】回測模擬")
        backtest_results = self.run_backtest_simulation(candidates, days=5)

        # Step 4: 策略優化
        print("\n【Step 4】策略優化")
        suggestions = self.run_strategy_optimization(candidates, regime)

        # 總結
        print("\n" + "=" * 60)
        print("  分析完成")
        print(f"  學習記錄: {len(self.learning_log)}筆")
        print("=" * 60)

        return {
            "regime": regime,
            "candidates": len(candidates),
            "backtest_results": len(backtest_results),
            "suggestions": suggestions
        }


def main():
    nana = NanaCore()
    result = nana.execute_cycle()
    return result


if __name__ == "__main__":
    main()
