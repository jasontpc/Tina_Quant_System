"""
Tina Autonomous Decision Monitor
==================================
Monitor trade performance, detect when autonomous patch is needed.

Trigger conditions (any one):
  1. 5 consecutive losing trades
  2. Single trade loss > 10%
  3. Market environment invalid (RSI system failed 10 times)

Author: Tina AI
Date: 2026-05-02
"""

import os
import sys
import json
import sqlite3
import datetime
from pathlib import Path

# ===== Path Setup =====
WORKSPACE = Path("C:/Users/USER/.openclaw/workspace")
TINA_ROOT = WORKSPACE / "Tina_Quant_System"
AUTONOMOUS_DIR = TINA_ROOT / "autonomous"
AUTONOMOUS_DIR.mkdir(exist_ok=True)

CONFIG_PATH = TINA_ROOT / "configs" / "autonomous_config.json"
DB_PATH = TINA_ROOT / "data" / "tina_master.db"
TRADE_LOG_PATH = TINA_ROOT / "data" / "trade_archive.db"


class AutonomousMonitor:
    """Autonomous decision monitor trigger"""

    def __init__(self):
        self.config = self._load_config()
        self.trigger_conditions = self.config.get("trigger_conditions", {})

    def _load_config(self):
        """Load config file"""
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARNING] Cannot load config: {e}")
            return {}

    def _get_recent_trades(self, limit=20):
        """Get recent N trades from trade_archive.db"""
        trades = []
        try:
            conn = sqlite3.connect(TRADE_LOG_PATH)
            cur = conn.cursor()
            cur.execute("""
                SELECT symbol, entry_date, exit_date, entry_price, exit_price,
                       shares, pnl_pct, status, strategy_version
                FROM trades
                ORDER BY exit_date DESC
                LIMIT ?
            """, (limit,))
            rows = cur.fetchall()
            conn.close()

            for row in rows:
                trades.append({
                    "symbol": row[0],
                    "entry_date": row[1],
                    "exit_date": row[2],
                    "entry_price": row[3],
                    "exit_price": row[4],
                    "shares": row[5],
                    "pnl_pct": row[6],
                    "status": row[7],
                    "strategy_version": row[8]
                })
        except Exception as e:
            print(f"[INFO] Cannot read trade_archive.db: {e}")
        return trades

    def _get_rsi_fail_count(self, recent_trades):
        """Count RSI entry failures (losing trades)"""
        fail_count = 0
        for trade in recent_trades:
            if trade.get("pnl_pct", 0) < 0:
                fail_count += 1
        return fail_count

    def check_trigger_conditions(self):
        """Check if autonomous decision is triggered. Returns (triggered, reason)"""
        recent_trades = self._get_recent_trades(limit=20)

        if len(recent_trades) < 5:
            return False, "Insufficient trades (<5), cannot determine"

        # Condition 1: 5 consecutive losses
        consecutive_losses = 0
        max_consecutive = 0
        for trade in recent_trades:
            if trade.get("pnl_pct", 0) < 0:
                consecutive_losses += 1
                max_consecutive = max(max_consecutive, consecutive_losses)
            else:
                consecutive_losses = 0

        threshold_consecutive = self.trigger_conditions.get("consecutive_losses", {}).get("threshold", 5)
        if max_consecutive >= threshold_consecutive:
            return True, f"Consecutive {max_consecutive} losses (threshold: {threshold_consecutive})"

        # Condition 2: Single loss > 10%
        threshold_single = self.trigger_conditions.get("single_loss_threshold", {}).get("threshold_pct", -10.0)
        for trade in recent_trades:
            if trade.get("pnl_pct", 0) <= threshold_single:
                return True, f"Single loss {trade['pnl_pct']:.2f}% (threshold: {threshold_single}%)"

        # Condition 3: Market environment invalid (RSI system consecutive failures)
        rsi_fails = self._get_rsi_fail_count(recent_trades)
        rsi_fail_threshold = self.trigger_conditions.get("environment_invalid", {}).get("rsi_fail_count", 10)
        if rsi_fails >= rsi_fail_threshold:
            return True, f"RSI system failed {rsi_fails} times (threshold: {rsi_fail_threshold})"

        return False, "No trigger condition"

    def is_environment_invalid(self):
        """Determine if market environment is invalid"""
        recent_trades = self._get_recent_trades(limit=20)
        if len(recent_trades) < 10:
            return False

        rsi_fails = self._get_rsi_fail_count(recent_trades)
        fail_ratio = rsi_fails / len(recent_trades)

        # If failure ratio > 60%, environment is invalid
        return fail_ratio > 0.6

    def should_activate_autonomous_mode(self):
        """Should activate autonomous mode"""
        triggered, reason = self.check_trigger_conditions()
        return triggered, reason

    def generate_status_report(self):
        """Generate monitor status report"""
        recent_trades = self._get_recent_trades(limit=20)
        triggered, reason = self.should_activate_autonomous_mode()

        # Calculate stats
        if recent_trades:
            pnls = [t.get("pnl_pct", 0) for t in recent_trades]
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p < 0]
            win_rate = len(wins) / len(pnls) * 100 if pnls else 0
            avg_win = sum(wins) / len(wins) if wins else 0
            avg_loss = sum(losses) / len(losses) if losses else 0
            profit_factor = abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else 0
        else:
            win_rate = avg_win = avg_loss = profit_factor = 0
            wins = losses = []

        report = {
            "timestamp": datetime.datetime.now().isoformat(),
            "total_trades": len(recent_trades),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(win_rate, 2),
            "avg_win_pct": round(avg_win, 2) if avg_win else 0,
            "avg_loss_pct": round(avg_loss, 2) if avg_loss else 0,
            "profit_factor": round(profit_factor, 2) if profit_factor else 0,
            "autonomous_triggered": triggered,
            "trigger_reason": reason,
            "environment_invalid": self.is_environment_invalid()
        }

        return report


def run_monitor():
    """Execute monitor check"""
    print("=" * 60)
    print("Tina Autonomous Decision Monitor")
    print(f"Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    monitor = AutonomousMonitor()
    status = monitor.generate_status_report()

    print(f"\n[STAT] Monitor Status Report:")
    print(f"   Total trades: {status['total_trades']}")
    print(f"   Win rate: {status['win_rate']}%")
    print(f"   Avg win: {status['avg_win_pct']}%")
    print(f"   Avg loss: {status['avg_loss_pct']}%")
    print(f"   Profit factor: {status['profit_factor']}")
    print(f"   Environment invalid: {'YES' if status['environment_invalid'] else 'NO'}")

    triggered, reason = monitor.should_activate_autonomous_mode()
    print(f"\n{'>>> AUTONOMOUS MODE TRIGGERED!' if triggered else '[OK] No trigger needed'}")
    if triggered:
        print(f"   Reason: {reason}")

    # Save status
    status_path = AUTONOMOUS_DIR / "monitor_status.json"
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)
    print(f"Status saved: {status_path}")

    return triggered, status


if __name__ == "__main__":
    triggered, status = run_monitor()
    sys.exit(0 if not triggered else 1)