# -*- coding: utf-8 -*-
"""
Ray Evolution Core - Tina Architecture Edition
Qwen Integration: Autonomous Learning Loop

Workflow:
  1. Try multiple strategy parameters (grid search)
  2. NL2Code validation -> format check before backtest
  3. RayEngine run Sharpe/MDD gate
  4. Write passed to backtest_reports + wisdom_logs
  5. Failed also logged in wisdom_logs (for future reference)
  6. Qwen 7B does attribution analysis

Added 2026-05-12:
  - daily_self_correction(): analyze yesterday losses, wake 7B
  - strengthen_gold_wisdom(): Sharpe > 1.8 -> weight * 1.2
  - wisdom_decay(): stale strategies weight decay (x 0.95)
  - daily_performance table: daily PnL records for self-correction fuel
"""

import json
import yfinance as yf
import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from ray_data_center import RayDataCenter
from ray_engine import RayEngine
from ray_nl2code import NL2CodeValidator, sanitize_llm_output


# Strategy grid candidates
CANDIDATE_STRATEGIES = [
    # EMA Cross
    {"strategy_name": "EMA_CROSS_9_21",   "indicator": "EMA_CROSS",     "params": {"fast": 9,  "slow": 21},  "entry_condition": {"operator": "CROSS_ABOVE", "threshold": 0}, "stop_loss": 0.08, "max_hold_days": 10},
    {"strategy_name": "EMA_CROSS_12_26",  "indicator": "EMA_CROSS",     "params": {"fast": 12, "slow": 26},  "entry_condition": {"operator": "CROSS_ABOVE", "threshold": 0}, "stop_loss": 0.08, "max_hold_days": 15},
    {"strategy_name": "EMA_CROSS_20_60",  "indicator": "EMA_CROSS",     "params": {"fast": 20, "slow": 60},  "entry_condition": {"operator": "CROSS_ABOVE", "threshold": 0}, "stop_loss": 0.10, "max_hold_days": 20},
    {"strategy_name": "EMA_CROSS_50_200", "indicator": "EMA_CROSS",     "params": {"fast": 50, "slow": 200}, "entry_condition": {"operator": "CROSS_ABOVE", "threshold": 0}, "stop_loss": 0.12, "max_hold_days": 30},
    # Momentum
    {"strategy_name": "MOMENTUM_5",       "indicator": "MOMENTUM",       "params": {"window": 5},           "entry_condition": {"operator": ">", "threshold": 0.02}, "stop_loss": 0.10, "max_hold_days": 5},
    {"strategy_name": "MOMENTUM_20",      "indicator": "MOMENTUM",      "params": {"window": 20},          "entry_condition": {"operator": ">", "threshold": 0.02}, "stop_loss": 0.10, "max_hold_days": 20},
    {"strategy_name": "MOMENTUM_60",      "indicator": "MOMENTUM",      "params": {"window": 60},          "entry_condition": {"operator": ">", "threshold": 0.02}, "stop_loss": 0.12, "max_hold_days": 60},
    # Vegas Tunnel
    {"strategy_name": "VEGAS_144_576",     "indicator": "VEGAS_TUNNEL",  "params": {"fast": 144, "slow": 576}, "entry_condition": {"operator": "CROSS_ABOVE", "threshold": 0}, "stop_loss": 0.08, "max_hold_days": 10},
    {"strategy_name": "VEGAS_169_676",     "indicator": "VEGAS_TUNNEL",  "params": {"fast": 169, "slow": 676}, "entry_condition": {"operator": "CROSS_ABOVE", "threshold": 0}, "stop_loss": 0.08, "max_hold_days": 10},
    # RSI Threshold
    {"strategy_name": "RSI_THRESHOLD_30", "indicator": "RSI2", "params": {"period": 2},        "entry_condition": {"operator": "<", "threshold": 30},  "stop_loss": 0.08, "max_hold_days": 15},
    # KDJ Cross
    {"strategy_name": "KDJ_CROSS_9",      "indicator": "KDJ_CROSS",     "params": {"period": 9},          "entry_condition": {"operator": "CROSS_ABOVE", "threshold": 20}, "stop_loss": 0.10, "max_hold_days": 10},
]


class RayEvolutionCore:
    def __init__(self, db_path: str = None):
        self.db        = RayDataCenter(db_path)
        self.engine    = RayEngine(market_type="US", db_path=db_path)
        self.validator = NL2CodeValidator()
        self.learned_count  = 0
        self.rejected_count = 0

    # Ensure schema has weight column and daily_performance table
    def ensure_schema(self):
        conn = sqlite3.connect(self.db.db_path)
        c = conn.cursor()
        c.execute("PRAGMA table_info(wisdom_logs)")
        cols = [col[1] for col in c.fetchall()]
        if "weight" not in cols:
            c.execute("ALTER TABLE wisdom_logs ADD COLUMN weight REAL DEFAULT 1.0")
            print("[*] Added weight column to wisdom_logs")
        c.execute("""
            CREATE TABLE IF NOT EXISTS daily_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                axiom_id INTEGER,
                symbol TEXT,
                pnl_ratio REAL,
                sharpe_1d REAL,
                note TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    # Daily self-correction: analyze yesterday failures, wake 7B
    def daily_self_correction(self) -> dict:
        self.ensure_schema()
        conn = sqlite3.connect(self.db.db_path, isolation_level='IMMEDIATE')
        c = conn.cursor()
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        c.execute("""
            SELECT axiom_id, symbol, pnl_ratio
              FROM daily_performance
             WHERE date = ? AND pnl_ratio < -0.02""", (yesterday,))
        failures = c.fetchall()

        corrections = []
        for axiom_id, symbol, pnl in failures:
            c.execute("UPDATE wisdom_logs SET weight = weight * 0.8 WHERE id = ?", (axiom_id,))
            c.execute("SELECT axiom_json, reflection FROM wisdom_logs WHERE id = ?", (axiom_id,))
            row = c.fetchone()
            if row:
                corrections.append({
                    "axiom_id": axiom_id,
                    "symbol":   symbol,
                    "old_pnl":  pnl,
                    "axiom_json": row[0],
                    "old_reflection": row[1],
                })
            print(f"[*] Self-correction: axiom={axiom_id}, symbol={symbol}, pnl={pnl:.2%} -> weight decayed")

        conn.commit()
        conn.close()
        return {
            "date": yesterday,
            "failures_found": len(failures),
            "corrections": corrections,
        }

    # Strengthen gold wisdoms: Sharpe > 1.8 -> weight * 1.2
    def strengthen_gold_wisdom(self) -> dict:
        self.ensure_schema()
        conn = sqlite3.connect(self.db.db_path, isolation_level='IMMEDIATE')
        c = conn.cursor()
        c.execute("""
            UPDATE wisdom_logs
               SET weight = weight * 1.2
             WHERE id IN (
                 SELECT w.id FROM wisdom_logs w
                 JOIN backtest_reports r ON w.backtest_id = r.id
                 WHERE r.sharpe_ratio > 1.8
                   AND r.win_rate > 0.45
                   AND w.passed = 1
                   AND w.weight < 5.0
             )""")
        rows_affected = c.rowcount
        conn.commit()
        conn.close()
        print(f"[*] Strengthened {rows_affected} gold wisdoms (weight * 1.2)")
        return {"strengthened": rows_affected}

    # Wisdom decay: stale strategies weight evaporation
    def wisdom_decay(self, decay_rate: float = 0.95, min_weight: float = 0.01) -> dict:
        self.ensure_schema()
        conn = sqlite3.connect(self.db.db_path, isolation_level='IMMEDIATE')
        c = conn.cursor()
        c.execute("""
            UPDATE wisdom_logs
               SET weight = CASE
                 WHEN weight * ? < ? THEN ?
                 ELSE weight * ?
               END
             WHERE passed = 0
                OR id IN (
                    SELECT w.id FROM wisdom_logs w
                    LEFT JOIN backtest_reports r ON w.backtest_id = r.id
                    WHERE r.sharpe_ratio < 1.0 OR r.sharpe_ratio IS NULL
                )""", (decay_rate, min_weight, min_weight, decay_rate))
        rows_affected = c.rowcount
        conn.commit()
        conn.close()
        print(f"[*] Decayed {rows_affected} stale wisdoms (weight * {decay_rate})")
        return {"decayed": rows_affected}

    # Log daily performance for future self-correction
    def log_daily_performance(self, symbol: str, axiom_id: int, pnl_ratio: float,
                               sharpe_1d: float = None, note: str = ""):
        self.ensure_schema()
        conn = sqlite3.connect(self.db.db_path, isolation_level='IMMEDIATE')
        c = conn.cursor()
        c.execute("""
            INSERT INTO daily_performance
                   (date, axiom_id, symbol, pnl_ratio, sharpe_1d, note)
            VALUES (date('now'), ?, ?, ?, ?, ?)""",
                  (axiom_id, symbol, pnl_ratio, sharpe_1d, note))
        conn.commit()
        conn.close()

    # Autonomous learning cycle (single symbol)
    def autonomous_learning_cycle(self, symbol: str,
                                   lookback_days: int = 730,
                                   min_sharpe: float = 0.8,
                                   max_mdd: float = 0.20) -> Dict:
        print(f"[RayEvolution] Learning {symbol}...")
        try:
            df = yf.Ticker(symbol).history(period=f"{lookback_days}d",
                                           interval="1d", auto_adjust=True)
            if df is None or len(df) < 200:
                return {"status": "error", "symbol": symbol, "reason": "insufficient data"}
        except Exception as e:
            return {"status": "error", "symbol": symbol, "reason": str(e)}

        passed_strategies = []
        for axiom in CANDIDATE_STRATEGIES:
            is_valid, parsed, errors = self.validator.validate(axiom)
            if not is_valid:
                self.db.log_wisdom(
                    axiom_json = json.dumps(axiom),
                    reflection = f"NL2Code rejected: {errors[0] if errors else 'unknown'}",
                    passed     = False,
                    model_used = "nl2code_validator",
                )
                continue

            report = self.engine.run_backtest(df, axiom)
            if report["passed"]:
                passed_strategies.append({**report, "axiom": axiom})
                backtest_id = self.db.log_backtest(
                    strategy_name = axiom["strategy_name"],
                    symbol        = symbol,
                    indicator     = axiom["indicator"],
                    params        = axiom["params"],
                    sharpe        = report["sharpe"],
                    mdd           = report["mdd"],
                    total_ret     = report["total_ret"],
                    win_rate      = report["win_rate"],
                    avg_return    = report["avg_return"],
                    num_trades    = report["num_trades"],
                    note          = f"auto_learned | cost={report.get('cost_pct',0.15)}%",
                )
                self.db.log_wisdom(
                    axiom_json   = json.dumps(axiom),
                    reflection   = f"PASSED Sharpe={report['sharpe']:.2f} MDD={report['mdd']:.2%}",
                    backtest_id  = backtest_id,
                    passed       = True,
                    model_used   = "ray_engine",
                )
                # Strengthen gold wisdom after each success
                self.strengthen_gold_wisdom()
            else:
                self.db.log_wisdom(
                    axiom_json = json.dumps(axiom),
                    reflection = f"FAILED {report.get('reason', 'backtest rejected')}",
                    passed     = False,
                    model_used = "ray_engine",
                )

        if passed_strategies:
            best = sorted(passed_strategies, key=lambda x: -x["sharpe"])[0]
            self.learned_count += 1
            print(f"[RayEvolution] PASS {symbol}: {len(passed_strategies)} passed, best Sharpe={best['sharpe']:.2f}")
            return {
                "status":        "success",
                "symbol":        symbol,
                "best_strategy": best["axiom"]["strategy_name"],
                "indicator":     best["axiom"]["indicator"],
                "sharpe":        best["sharpe"],
                "mdd":          best["mdd"],
                "total_ret":    best["total_ret"],
                "win_rate":     best["win_rate"],
                "num_trades":   best["num_trades"],
                "passed_count": len(passed_strategies),
            }
        else:
            self.rejected_count += 1
            print(f"[RayEvolution] REJ {symbol}: all {len(CANDIDATE_STRATEGIES)} rejected")
            return {
                "status":    "rejected",
                "symbol":    symbol,
                "attempted": len(CANDIDATE_STRATEGIES),
            }

    # Batch learning
    def batch_learning(self, symbols: List[str], lookback_days: int = 730) -> List[Dict]:
        results = []
        for sym in symbols:
            r = self.autonomous_learning_cycle(sym, lookback_days)
            results.append(r)
        return results

    # Get approved strategies
    def get_approved_strategies(self, limit: int = 20) -> List[Dict]:
        return self.db.get_approved_backtests(limit=limit)

    # Learning stats
    def get_learning_stats(self) -> Dict:
        recent   = self.db.get_recent_backtests(days=7)
        approved = [r for r in recent if r.get("passed")]
        wids     = self.db.get_wisdom_logs(limit=100)
        return {
            "total_learned":    self.learned_count,
            "total_rejected":   self.rejected_count,
            "recent_backtests": len(recent),
            "recent_approved":  len(approved),
            "avg_sharpe":       round(sum(r["sharpe_ratio"] for r in approved) / max(len(approved), 1), 2),
            "avg_mdd":          round(sum(r["max_drawdown"] for r in approved) / max(len(approved), 1), 4),
            "wisdom_logs":      len(wids),
            "failed_wisdoms":   len([w for w in wids if not w.get("passed")]),
        }

    # Failed learning context for 7B attribution
    def get_failed_learning_context(self, symbol: str) -> str:
        failed = self.db.get_failed_wisdoms(limit=20)
        sym_failed = [f for f in failed if symbol in f.get("axiom_json", "")]
        lines = [f"- {w['reflection']}" for w in sym_failed]
        return "\n".join(lines) if lines else "No failed strategies found"


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ray Evolution Core CLI")
    parser.add_argument("--mode", default="learn",
                        choices=["learn", "self_correct", "update_weights", "stats", "decay"])
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--symbols", default=None)  # comma-separated list
    args = parser.parse_args()

    core = RayEvolutionCore()

    if args.mode == "self_correct":
        print("[*] Running daily self-correction...")
        result = core.daily_self_correction()
        print(f"Result: {result}")

    elif args.mode == "update_weights":
        print("[*] Running weight update (strengthen + decay)...")
        r1 = core.strengthen_gold_wisdom()
        r2 = core.wisdom_decay()
        print(f"Strengthened: {r1}")
        print(f"Decayed: {r2}")

    elif args.mode == "decay":
        r = core.wisdom_decay()
        print(f"Decay result: {r}")

    elif args.mode == "stats":
        stats = core.get_learning_stats()
        print(f"Stats: {stats}")

    else:  # learn
        if args.symbols:
            syms = [s.strip() for s in args.symbols.split(",")]
            print(f"[*] Batch learning: {syms}")
            results = core.batch_learning(syms)
            for r in results:
                print(r)
        elif args.symbol:
            result = core.autonomous_learning_cycle(args.symbol)
            print(f"Result: {result}")
        else:
            print("Usage: python ray_evolution.py --mode learn --symbol NVDA")
            print("       python ray_evolution.py --mode self_correct")
            print("       python ray_evolution.py --mode update_weights")
            print("       python ray_evolution.py --mode stats")
            print("       python ray_evolution.py --mode decay")
