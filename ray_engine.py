# -*- coding: utf-8 -*-
"""
Ray 回測引擎 - Tina Engine 移植版
摩擦成本實體化 + Sharpe/MDD 數學把關

把關門檻：
  Sharpe > 1.5   — 風險調整後報酬達標
  MDD < 15%      — 最大本金回撤可控
  Win Rate > 45% — 統計勝率基礎
"""

import pandas as pd
import numpy as np
import json
import sqlite3
from typing import Dict, Optional, List
from ray_data_center import RayDataCenter

# ── 摩擦成本設定（美股）──────────────────────────────────────────────
COST_US_STOCK = 0.0015   # 0.15% per trade（含券商+監管+滑價）
COST_US_ETF   = 0.0005   # 0.05% ETF 更低
COST_TW_STOCK = 0.0054   # 0.54% 台股


class RayEngine:
    def __init__(self, market_type: str = "US", db_path: str = None):
        self.market_type = market_type
        if market_type == "US":
            self.cost = COST_US_STOCK
        elif market_type == "TW":
            self.cost = COST_TW_STOCK
        else:
            self.cost = COST_US_STOCK

        # Sharpe / MDD 把關門檻（可覆寫）
        self.SHARPE_MIN = 1.5
        self.MDD_MAX    = 0.15    # 15%
        self.WIN_MIN    = 0.45    # 45%

    # ── 核心：運行單次回測 ──────────────────────────────────────────
    def run_backtest(self, df: pd.DataFrame, axiom: Dict) -> Dict:
        """
        輸入：df（OHLCV）, axiom（策略參數）
        輸出：{sharpe, mdd, total_ret, win_rate, num_trades, avg_return, passed}
        """
        try:
            indicator = axiom.get("indicator", "EMA_CROSS")
            params    = axiom.get("params", {})
            entry_op  = axiom.get("entry_condition", {}).get("operator", ">")
            entry_thr = axiom.get("entry_condition", {}).get("threshold", 0)
            stop_loss = axiom.get("stop_loss", 0.08)

            # ── 指標計算 ──────────────────────────────────────────
            if indicator == "EMA_CROSS":
                fast = params.get("fast", 12)
                slow = params.get("slow", 26)
                df = df.copy()
                df["fast_ma"] = df["Close"].ewm(span=fast, adjust=False).mean()
                df["slow_ma"] = df["Close"].ewm(span=slow, adjust=False).mean()
                df["ind"] = df["fast_ma"] - df["slow_ma"]

            elif indicator == "FOREIGN_BUY":
                window = params.get("window", 5)
                df = df.copy()
                if "foreign_net" in df.columns:
                    df["ind"] = df["foreign_net"].rolling(window=window).sum()
                else:
                    df["ind"] = df["Close"] * 0

            elif indicator == "VEGAS_TUNNEL":
                df = df.copy()
                df["ema144"] = df["Close"].ewm(span=144, adjust=False).mean()
                df["ema169"] = df["Close"].ewm(span=169, adjust=False).mean()
                df["ema576"] = df["Close"].ewm(span=576, adjust=False).mean()
                df["ema676"] = df["Close"].ewm(span=676, adjust=False).mean()
                df["ind"] = df["ema144"] - df["ema169"]

            elif indicator == "MOMENTUM":
                window = params.get("window", 20)
                df = df.copy()
                df["ind"] = df["Close"].pct_change(periods=window)

            # ── RSI 指標（康諾斯均值回歸專用）────────────────────────
            elif indicator == "RSI":
                period = params.get("period", 14)
                df = df.copy()
                delta = df["Close"].diff()
                gain = delta.clip(lower=0).rolling(window=period).mean()
                loss = (-delta.clip(upper=0)).rolling(window=period).mean()
                rs = gain / loss
                df["ind"] = 100 - (100 / (1 + rs))

            elif indicator == "RSI2":
                # 康諾斯 RSI(2) 均值回歸策略
                period = params.get("period", 2)
                df = df.copy()
                delta = df["Close"].diff()
                gain = delta.clip(lower=0).rolling(window=period).mean()
                loss = (-delta.clip(upper=0)).rolling(window=period).mean()
                rs = gain / loss
                df["ind"] = 100 - (100 / (1 + rs))

            else:
                return {"passed": False, "reason": f"unknown indicator: {indicator}"}

            # ── 去除 NA ──────────────────────────────────────────
            df = df.dropna(subset=["ind", "Close"]).copy()
            if len(df) < 30:
                return {"passed": False, "reason": "insufficient data (<30 rows)"}

            # ── 訊號產生 ──────────────────────────────────────────
            if entry_op == ">":
                df["signal"] = (df["ind"] > entry_thr).astype(int)
            elif entry_op == "<":
                df["signal"] = (df["ind"] < entry_thr).astype(int)
            elif entry_op == "CROSS_ABOVE":
                df["signal"] = ((df["ind"] > entry_thr) & (df["ind"].shift(1) <= entry_thr)).astype(int)
            elif entry_op == "CROSS_BELOW":
                df["signal"] = ((df["ind"] < entry_thr) & (df["ind"].shift(1) >= entry_thr)).astype(int)
            else:
                df["signal"] = (df["ind"] > entry_thr).astype(int)

            # ── 報酬計算（含成本）───────────────────────────────
            df["ret"]       = df["Close"].pct_change().fillna(0)
            df["strat_ret"] = df["signal"].shift(1) * df["ret"]
            df["cost_fee"]  = df["signal"].diff().abs() * self.cost
            df["strat_ret"] = df["strat_ret"] - df["cost_fee"]

            # ── 停損模擬 ──────────────────────────────────────────
            stop = stop_loss
            df["strat_ret"] = np.where(
                df["ret"] < -stop,
                -stop - self.cost,
                df["strat_ret"]
            )

            # ── 績效指標 ──────────────────────────────────────────
            total_ret = float((1 + df["strat_ret"]).prod() - 1)
            mean_ret  = float(df["strat_ret"].mean())
            std_ret   = float(df["strat_ret"].std())
            sharpe    = (mean_ret / std_ret * np.sqrt(252)) if std_ret > 0 else 0.0

            cum = df["strat_ret"].cumsum()
            cummax = cum.cummax()
            mdd = float((cummax - cum).max())

            trades = int(df["signal"].diff().abs().sum() / 2)
            win_trades = int((df["strat_ret"] > 0).sum())
            win_rate = win_trades / max(len(df), 1)
            avg_ret  = float(df["strat_ret"][df["strat_ret"] != 0].mean()) if win_trades > 0 else 0.0

            passed = (
                sharpe > self.SHARPE_MIN and
                mdd    < self.MDD_MAX    and
                win_rate >= self.WIN_MIN
            )

            return {
                "sharpe":       round(sharpe, 3),
                "mdd":          round(mdd, 4),
                "total_ret":    round(total_ret, 4),
                "win_rate":     round(win_rate, 4),
                "avg_return":   round(avg_ret, 4),
                "num_trades":   trades,
                "passed":       passed,
                "cost_pct":     self.cost * 100,
                "reason":       "" if passed else f"sharpe={sharpe:.2f}<{self.SHARPE_MIN} or mdd={mdd:.2%}>{self.MDD_MAX:.2%}"
            }

        except Exception as e:
            return {"passed": False, "reason": str(e)}

    # ── 批量回測（多參數網格）───────────────────────────────────────
    def grid_search(self, df: pd.DataFrame, indicator: str,
                     param_grid: List[Dict], entry_op: str = ">",
                     stop_loss: float = 0.08) -> List[Dict]:
        results = []
        for params in param_grid:
            axiom = {
                "indicator":       indicator,
                "params":          params,
                "entry_condition": {"operator": entry_op, "threshold": 0},
                "stop_loss":       stop_loss,
            }
            r = self.run_backtest(df, axiom)
            r["params"] = params
            r["indicator"] = indicator
            results.append(r)
        passed = [x for x in results if x["passed"]]
        passed.sort(key=lambda x: -x["sharpe"])
        return passed

    # ── 30日滾動 Sharpe/MDD ───────────────────────────────────────
    def calc_rolling_stats(self, df: pd.DataFrame, window: int = 30) -> Dict:
        if len(df) < window:
            return {"sharpe": None, "mdd": None, "win_rate": None}
        ret = df["Close"].pct_change().dropna()
        rolling = ret.tail(window)
        mean_ret = float(rolling.mean())
        std_ret  = float(rolling.std())
        sharpe   = (mean_ret / std_ret * np.sqrt(252)) if std_ret > 0 else 0.0
        cum   = rolling.cumsum()
        cummax = cum.cummax()
        mdd   = float((cummax - cum).max())
        win_rate = float((rolling > 0).sum() / len(rolling))
        return {"sharpe": round(sharpe, 3), "mdd": round(mdd, 4), "win_rate": round(win_rate, 4)}

    # ── 一鍵回測 + 寫入 DB ─────────────────────────────────────────
    def backtest_and_save(self, symbol: str, df: pd.DataFrame,
                           strategy_name: str, indicator: str,
                           params: Dict, db_path: str = None) -> Dict:
        axiom = {
            "strategy_name":  strategy_name,
            "indicator":      indicator,
            "params":         params,
            "entry_condition": {"operator": ">", "threshold": 0},
            "stop_loss":      0.08,
        }
        report = self.run_backtest(df, axiom)
        db = RayDataCenter(db_path)
        backtest_id = db.log_backtest(
            strategy_name = strategy_name, symbol=symbol, indicator=indicator,
            params=params, sharpe=report.get("sharpe", 0), mdd=report.get("mdd", 999),
            total_ret=report.get("total_ret", 0), win_rate=report.get("win_rate", 0),
            avg_return=report.get("avg_return", 0), num_trades=report.get("num_trades", 0),
            note=report.get("reason", ""),
        )
        report["backtest_id"] = backtest_id
        return report


if __name__ == "__main__":
    import yfinance as yf
    df = yf.Ticker("NVDA").history(period="2y", interval="1d", auto_adjust=True)
    engine = RayEngine(market_type="US")
    result = engine.run_backtest(df, {
        "indicator": "EMA_CROSS",
        "params": {"fast": 12, "slow": 26},
        "entry_condition": {"operator": ">", "threshold": 0},
        "stop_loss": 0.08
    })
    print(f"NVDA EMA_CROSS(12,26): {result}")