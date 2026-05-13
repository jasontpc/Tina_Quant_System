import json, yfinance as yf, numpy as np, sqlite3
from datetime import datetime, timedelta
from ray_data_center import RayDataCenter
from ray_engine import RayEngine
from ray_nl2code import NL2CodeValidator

CANDIDATE_STRATEGIES = [
    {"strategy_name": "EMA_CROSS_9_21",   "indicator": "EMA_CROSS",     "params": {"fast": 9,  "slow": 21},  "entry_condition": {"operator": "CROSS_ABOVE", "threshold": 0}, "stop_loss": 0.08},
    {"strategy_name": "EMA_CROSS_12_26",  "indicator": "EMA_CROSS",     "params": {"fast": 12, "slow": 26},  "entry_condition": {"operator": "CROSS_ABOVE", "threshold": 0}, "stop_loss": 0.08},
    {"strategy_name": "EMA_CROSS_20_60",  "indicator": "EMA_CROSS",     "params": {"fast": 20, "slow": 60},  "entry_condition": {"operator": "CROSS_ABOVE", "threshold": 0}, "stop_loss": 0.10},
    {"strategy_name": "EMA_CROSS_50_200", "indicator": "EMA_CROSS",    "params": {"fast": 50, "slow": 200}, "entry_condition": {"operator": "CROSS_ABOVE", "threshold": 0}, "stop_loss": 0.12},
    {"strategy_name": "MOMENTUM_5",        "indicator": "MOMENTUM",       "params": {"window": 5},           "entry_condition": {"operator": ">", "threshold": 0.02}, "stop_loss": 0.10},
    {"strategy_name": "MOMENTUM_20",       "indicator": "MOMENTUM",      "params": {"window": 20},          "entry_condition": {"operator": ">", "threshold": 0.02}, "stop_loss": 0.10},
    {"strategy_name": "MOMENTUM_60",       "indicator": "MOMENTUM",      "params": {"window": 60},          "entry_condition": {"operator": ">", "threshold": 0.02}, "stop_loss": 0.12},
    {"strategy_name": "VEGAS_144_576",      "indicator": "VEGAS_TUNNEL", "params": {"fast": 144, "slow": 576}, "entry_condition": {"operator": "CROSS_ABOVE", "threshold": 0}, "stop_loss": 0.08},
    {"strategy_name": "VEGAS_169_676",      "indicator": "VEGAS_TUNNEL", "params": {"fast": 169, "slow": 676}, "entry_condition": {"operator": "CROSS_ABOVE", "threshold": 0}, "stop_loss": 0.08},
    {"strategy_name": "RSI2_CONNORS",       "indicator": "RSI2",          "params": {"period": 2},          "entry_condition": {"operator": "<", "threshold": 30},  "stop_loss": 0.08},
    {"strategy_name": "RSI_14_OVERSOLD",   "indicator": "RSI",           "params": {"period": 14},         "entry_condition": {"operator": "<", "threshold": 35},  "stop_loss": 0.08},
]

class RayEvolutionCore:
    def __init__(self, db_path=None):
        self.db        = RayDataCenter(db_path)
        self.validator = NL2CodeValidator()
        self.learned_count  = 0
        self.rejected_count = 0

    def set_relaxed_mode(self, engine):
        """Relax thresholds for daily learning (still logged, but not 'passed' gold)"""
        engine.SHARPE_MIN = 0.8
        engine.MDD_MAX    = 0.20
        engine.WIN_MIN    = 0.35

    def autonomous_learning_cycle(self, symbol, lookback_days=730, relaxed=False):
        print(f"[RayEvolution] Learning {symbol} (relaxed={relaxed})...")

        try:
            df = yf.Ticker(symbol).history(period=f"{lookback_days}d", interval="1d", auto_adjust=True)
            if df is None or len(df) < 200:
                return {"status": "error", "symbol": symbol, "reason": "insufficient data"}
        except Exception as e:
            return {"status": "error", "symbol": symbol, "reason": str(e)}

        # Use relaxed engine if requested
        engine = RayEngine(market_type="US")
        if relaxed:
            self.set_relaxed_mode(engine)

        passed_strategies = []
        for axiom in CANDIDATE_STRATEGIES:
            is_valid, parsed, errors = self.validator.validate(axiom)
            if not is_valid:
                self.db.log_wisdom(
                    axiom_json=json.dumps(axiom),
                    reflection=f"NL2Code rejected: {errors[0] if errors else 'unknown'}",
                    passed=False, model_used="nl2code_validator",
                )
                continue

            report = engine.run_backtest(df, axiom)
            backtest_id = self.db.log_backtest(
                strategy_name=axiom["strategy_name"], symbol=symbol, indicator=axiom["indicator"],
                params=axiom["params"], sharpe=report.get("sharpe", 0), mdd=report.get("mdd", 999),
                total_ret=report.get("total_ret", 0), win_rate=report.get("win_rate", 0),
                avg_return=report.get("avg_return", 0), num_trades=report.get("num_trades", 0),
                note=report.get("reason", ""),
            )

            self.db.log_wisdom(
                axiom_json=json.dumps(axiom),
                reflection=f"{'PASSED' if report['passed'] else 'FAILED'} sharpe={report.get('sharpe',0):.2f} mdd={report.get('mdd',0):.2%} win={report.get('win_rate',0):.1%}",
                backtest_id=backtest_id, passed=report["passed"], model_used="ray_engine",
            )

            if report["passed"]:
                passed_strategies.append({**report, "axiom": axiom})

        if passed_strategies:
            best = sorted(passed_strategies, key=lambda x: -x["sharpe"])[0]
            self.learned_count += 1
            print(f"[RayEvolution] PASS {symbol}: {len(passed_strategies)} passed, best Sharpe={best['sharpe']:.2f}")
            return {"status": "success", "symbol": symbol, "best_strategy": best["axiom"]["strategy_name"], "sharpe": best["sharpe"], "mdd": best["mdd"], "passed_count": len(passed_strategies)}
        else:
            self.rejected_count += 1
            print(f"[RayEvolution] REJ {symbol}: all {len(CANDIDATE_STRATEGIES)} rejected")
            return {"status": "rejected", "symbol": symbol, "attempted": len(CANDIDATE_STRATEGIES)}

    def batch_learning(self, symbols, lookback_days=730, relaxed=False):
        results = []
        for sym in symbols:
            r = self.autonomous_learning_cycle(sym, lookback_days, relaxed)
            results.append(r)
        return results

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="learn")
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--symbols", default=None)
    parser.add_argument("--relaxed", action="store_true", help="Use relaxed thresholds (Sharpe>0.8 MDD<20%)")
    args = parser.parse_args()

    core = RayEvolutionCore()

    if args.mode == "stats":
        conn = sqlite3.connect(core.db.db_path)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM wisdom_logs'); wl = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM backtest_reports'); br = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM wisdom_corrections'); wc = c.fetchone()[0]
        print(f"wisdom_logs={wl}, backtest_reports={br}, wisdom_corrections={wc}")
        conn.close()
    else:
        if args.symbols:
            syms = [s.strip() for s in args.symbols.split(",")]
            results = core.batch_learning(syms, relaxed=args.relaxed)
            for r in results:
                print(r)
        elif args.symbol:
            result = core.autonomous_learning_cycle(args.symbol, relaxed=args.relaxed)
            print(result)