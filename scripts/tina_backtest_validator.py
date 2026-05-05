"""
Tina 回測驗證模組
=================
隔離環境中進行策略回測，驗證新參數是否達標

驗證標準：
  - 勝率 > 55%
  - 獲利因子 > 1.2
  - 最少 100 筆交易

Author: Tina AI
Date: 2026-05-02
"""

import os
import sys
import json
import sqlite3
import datetime
from pathlib import Path

WORKSPACE = Path("C:/Users/USER/.openclaw/workspace")
TINA_ROOT = WORKSPACE / "Tina_Quant_System"


class BacktestValidator:
    """回測驗證引擎"""

    def __init__(self):
        self.db_path = TINA_ROOT / "data" / "tw_history.db"
        self.config = self._load_config()

    def _load_config(self):
        try:
            config_path = TINA_ROOT / "configs" / "autonomous_config.json"
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {
                "backtest_validation": {
                    "min_win_rate": 55.0,
                    "min_profit_factor": 1.2,
                    "min_trade_count": 100
                }
            }

    def validate_strategy(self, strategy_class, symbols=None, lookback_days=180):
        """
        驗證策略表現

        Args:
            strategy_class: 策略類別（需有 should_entry, should_exit 方法）
            symbols: 測試股票池（預設：系統主要標的）
            lookback_days: 回測天數

        Returns:
            dict: 驗證結果
        """
        if symbols is None:
            symbols = ["2330", "2317", "2454", "2881", "2884"]

        print(f"🔬 回測驗證開始（{lookback_days}天回測）")
        print(f"   標的：{symbols}")

        bt_config = self.config.get("backtest_validation", {})
        min_win_rate = bt_config.get("min_win_rate", 55.0)
        min_profit_factor = bt_config.get("min_profit_factor", 1.2)
        min_trade_count = bt_config.get("min_trade_count", 100)

        all_trades = []

        for symbol in symbols:
            trades = self._backtest_symbol(strategy_class, symbol, lookback_days)
            all_trades.extend(trades)

        if not all_trades:
            return {
                "passed": False,
                "reason": "no_trades",
                "total_trades": 0,
                "win_rate": 0,
                "profit_factor": 0
            }

        wins = [t["pnl_pct"] for t in all_trades if t["pnl_pct"] > 0]
        losses = [t["pnl_pct"] for t in all_trades if t["pnl_pct"] <= 0]

        win_rate = len(wins) / len(all_trades) * 100 if all_trades else 0
        total_profit = sum(wins) if wins else 0
        total_loss = abs(sum(losses)) if losses else 0
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')

        print(f"\n📊 回測結果：")
        print(f"   總交易筆數：{len(all_trades)}")
        print(f"   勝率：{win_rate:.1f}%（門檻：{min_win_rate}%）")
        print(f"   獲利因子：{profit_factor:.2f}（門檻：{min_profit_factor}）")
        print(f"   總獲利：{total_profit:.2f}%")
        print(f"   總虧損：{total_loss:.2f}%")

        passed = (
            len(all_trades) >= min_trade_count and
            win_rate >= min_win_rate and
            profit_factor >= min_profit_factor
        )

        print(f"\n{'✅ 驗證通過' if passed else '❌ 驗證未通過'}")

        return {
            "passed": passed,
            "total_trades": len(all_trades),
            "win_rate": round(win_rate, 2),
            "profit_factor": round(profit_factor, 2),
            "total_profit": round(total_profit, 2),
            "total_loss": round(total_loss, 2),
            "wins": len(wins),
            "losses": len(losses),
            "min_trade_count": min_trade_count,
            "min_win_rate": min_win_rate,
            "min_profit_factor": min_profit_factor
        }

    def _backtest_symbol(self, strategy_class, symbol, lookback_days):
        """對單一標的進行回測"""
        trades = []

        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            start_date = (datetime.date.today() - datetime.timedelta(days=lookback_days)).isoformat()

            cur.execute("""
                SELECT date, open, high, low, close, volume
                FROM tw_stock_daily
                WHERE symbol = ? AND date >= ?
                ORDER BY date ASC
            """, (symbol, start_date))

            rows = cur.fetchall()
            conn.close()

            if len(rows) < 20:
                return trades

            closes = [row[4] for row in rows]
            rsi_values = self._calc_rsi_list(closes)

            position = None

            for i in range(14, len(rows)):
                date, open_, high, low, close, vol = rows[i]
                rsi = rsi_values[i] if i < len(rsi_values) else 50

                if position is None:
                    if strategy_class.should_entry(rsi, close, vol):
                        position = {
                            "entry_date": date,
                            "entry_price": close
                        }
                else:
                    pnl_pct = (close - position["entry_price"]) / position["entry_price"] * 100
                    if strategy_class.should_exit(rsi, close, pnl_pct):
                        trades.append({
                            "symbol": symbol,
                            "entry_date": position["entry_date"],
                            "exit_date": date,
                            "entry_price": position["entry_price"],
                            "exit_price": close,
                            "pnl_pct": round(pnl_pct, 2)
                        })
                        position = None

        except Exception as e:
            print(f"[WARN] {symbol} 回測失敗: {e}")

        return trades

    def _calc_rsi_list(self, closes, period=14):
        """計算 RSI 清單"""
        if len(closes) < period + 1:
            return [50] * len(closes)

        rsi_values = []
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains = [max(d, 0) for d in deltas]
        losses = [abs(min(d, 0)) for d in deltas]

        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        for i in range(period, len(deltas)):
            if avg_loss == 0:
                rsi_values.append(100)
            else:
                rs = avg_gain / avg_loss
                rsi_values.append(100 - (100 / (1 + rs)))

            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        # 補足前面的 NaN
        while len(rsi_values) < len(closes):
            rsi_values.insert(0, 50)

        return rsi_values


def run_validation(strategy_path=None):
    """執行驗證（可指定策略檔案路徑）"""
    print("=" * 60)
    print("Tina 回測驗證模組")
    print(f"執行時間：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    if strategy_path is None:
        # 嘗試讀取最新的 auto_patch 策略
        strategy_dir = TINA_ROOT / "strategies"
        patches = list(strategy_dir.glob("tina_v*_auto_patch.py"))
        if patches:
            strategy_path = patches[-1]
            print(f"📂 使用策略：{strategy_path.name}")

    if strategy_path:
        import importlib.util
        spec = importlib.util.spec_from_file_location("strategy", strategy_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        S = mod.get_strategy()
    else:
        print("[ERROR] 無可用策略")
        return

    validator = BacktestValidator()
    result = validator.validate_strategy(S, lookback_days=180)

    # 儲存結果
    result_path = TINA_ROOT / "autonomous" / "validation_result.json"
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n📁 結果已儲存：{result_path}")
    return result


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else None
    run_validation(path)