# -*- coding: utf-8 -*-
"""
Ray Gold Miner — Tina Architecture Edition
自動從 ray_wisdom.db 中提取「高統計顯著性」的交易邏輯

篩選標準：
  Sharpe > 1.8
  MDD < 12%
  交易次數 > 20（避免隨機性）
  勝率 > 45%

輸出：SFT JSONL（instruct 格式）+ CausalSFT JSONL（帶因果鏈）
"""

import os
import sqlite3
import json
from datetime import datetime

DB_PATH  = os.path.join(os.path.dirname(__file__), "ray_wisdom.db")
OUT_GOLD = os.path.join(os.path.dirname(__file__), "ray_gold_train.jsonl")
OUT_CAUSAL = os.path.join(os.path.dirname(__file__), "ray_causal_train.jsonl")

# ── 嚴格篩選參數 ─────────────────────────────────────────────────
SHARPE_MIN   = 1.8   # 高風險調整報酬
MDD_MAX      = 0.12  # 12% 最大回撤
WIN_MIN      = 0.45  # 45% 勝率
TRADES_MIN   = 20    # 最少交易次數（避免隨機性）


class GoldMiner:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH

    def query_gold_samples(self) -> list:
        """從 DB 中提取黃金樣本"""
        conn = sqlite3.connect(self.db_path, isolation_level='IMMEDIATE')
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""
            SELECT w.axiom_json,
                   w.reflection,
                   w.model_used,
                   w.passed,
                   r.sharpe_ratio,
                   r.max_drawdown,
                   r.total_return,
                   r.win_rate,
                   r.num_trades,
                   r.strategy_name,
                   r.symbol,
                   r.indicator,
                   r.params,
                   r.avg_return,
                   w.timestamp
            FROM wisdom_logs w
            JOIN backtest_reports r ON w.backtest_id = r.id
            WHERE r.sharpe_ratio > ?
              AND r.max_drawdown < ?
              AND r.win_rate > ?
              AND r.num_trades > ?
              AND r.passed = 1
              AND w.passed = 1
            ORDER BY r.sharpe_ratio DESC
            LIMIT 500
        """, (SHARPE_MIN, MDD_MAX, WIN_MIN, TRADES_MIN))

        rows = cur.fetchall()
        conn.close()
        return rows

    def query_signals_as_fallback(self) -> list:
        """當 wisdom_logs 數據不足時，從 signals_log 補充"""
        conn = sqlite3.connect(self.db_path, isolation_level='IMMEDIATE')
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""
            SELECT symbol,
                   score,
                   sharpe_30d,
                   mdd_30d,
                   win_rate_30d,
                   signal_tag,
                   note,
                   timestamp
            FROM signals_log
            WHERE approved = 1
              AND sharpe_30d IS NOT NULL
              AND sharpe_30d > 1.8
              AND mdd_30d < 0.12
              AND win_rate_30d > 0.45
            ORDER BY sharpe_30d DESC
            LIMIT 200
        """)
        rows = cur.fetchall()
        conn.close()
        return rows

    def build_instruct_jsonl(self, rows: list) -> dict:
        """
        標準 Instruct 格式（用於普通蒸餾）
        每筆：{"instruction": "...", "input": "...", "output": "..."}
        """
        entries = []
        symbols = set()

        for row in rows:
            symbols.add(row["symbol"])
            ref = (row["reflection"] or "")[:200]
            axiom_str = row["axiom_json"] if isinstance(row["axiom_json"], str) else "{}"

            entry = {
                "instruction": (
                    "分析當前市場數據，產出結構化交易決策 JSON。"
                    "必須包含：strategy_name, indicator, params, "
                    "entry_condition, stop_loss。"
                ),
                "input": (
                    f"Symbol: {row['symbol']} | "
                    f"Sharpe: {row['sharpe_ratio']:.2f} | "
                    f"MDD: {row['max_drawdown']:.2%} | "
                    f"WinRate: {row['win_rate']:.1%} | "
                    f"Trades: {row['num_trades']} | "
                    f"Ref: {ref}"
                ),
                "output": axiom_str
            }
            entries.append(entry)

        path = OUT_GOLD
        with open(path, "w", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")

        avg_sharpe = round(sum(r['sharpe_ratio'] for r in rows) / max(len(rows), 1), 3)
        print(f"[*] Gold Instruct: {len(entries)} entries → {path}")
        print(f"[*] Avg Sharpe: {avg_sharpe}, Symbols: {len(symbols)}")
        return {"count": len(entries), "symbols": list(symbols), "avg_sharpe": avg_sharpe}

    def build_causal_jsonl(self, rows: list) -> dict:
        """
        CausalSFT 格式（用於深度蒸餾）
        每筆包含「因果鏈」而非表面 input-output
        讓 1.5B 學習「為什麼這樣判斷」，而不只是「市場數據→策略輸出」
        """
        entries = []
        symbols = set()

        for row in rows:
            symbols.add(row["symbol"])
            ref = (row["reflection"] or "")[:300]
            axiom_str = row["axiom_json"] if isinstance(row["axiom_json"], str) else "{}"

            # 重建因果鏈：市場數據 → 判斷邊界 → 最終策略
            causal_note = (
                f"分析流程：symbol={row['symbol']}, "
                f"indicator={row['indicator']}, "
                f"sharpe={row['sharpe_ratio']:.2f}(>{SHARPE_MIN}), "
                f"mdd={row['max_drawdown']:.2%}(<{MDD_MAX*100}%), "
                f"win={row['win_rate']:.1%}(>{WIN_MIN*100}%), "
                f"trades={row['num_trades']}(>{TRADES_MIN})。"
                f"判斷邊界：{'是' if row['passed'] else '否'}→產出策略。"
                f"理由：{ref}"
            )

            entry = {
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are Ray-Causal (1.5B distilled with logic chain). "
                            "Output ONLY valid JSON. Think step by step. "
                            "Schema: {\"strategy_name\":\"...\",\"indicator\":\"...\","
                            "\"params\":{},\"entry_condition\":{},\"stop_loss\":0.0}"
                        )
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Market Data:\n"
                            f"Symbol: {row['symbol']}\n"
                            f"Sharpe: {row['sharpe_ratio']:.2f} | "
                            f"MDD: {row['max_drawdown']:.2%} | "
                            f"WinRate: {row['win_rate']:.1%}\n"
                            f"Trades: {row['num_trades']} | "
                            f"Strategy: {row['strategy_name']}\n"
                            f"Logic Chain:\n{causal_note}\n"
                            f"Output JSON with reasoning."
                        )
                    },
                    {
                        "role": "assistant",
                        "content": axiom_str
                    }
                ],
                "metadata": {
                    "symbol":     row["symbol"],
                    "strategy":   row["strategy_name"],
                    "sharpe":    round(row["sharpe_ratio"], 3),
                    "mdd":       round(row["max_drawdown"], 4),
                    "win_rate":  round(row["win_rate"], 4),
                    "trades":    row["num_trades"],
                    "rationale": ref[:300],
                    "model":     row["model_used"] or "qwen2.5:7b",
                    "type":      "causal_sft"
                }
            }
            entries.append(entry)

        path = OUT_CAUSAL
        with open(path, "w", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")

        print(f"[*] Gold CausalSFT: {len(entries)} entries → {path}")
        return {"count": len(entries), "symbols": list(symbols)}

    def run(self) -> dict:
        print("=" * 60)
        print("Ray Gold Miner — Distillation Pipeline Step 1")
        print(f"DB: {self.db_path}")
        print(f"Filters: Sharpe>{SHARPE_MIN}, MDD<{MDD_MAX*100}%, "
              f"WinRate>{WIN_MIN*100}%, Trades>{TRADES_MIN}")
        print("=" * 60)

        rows = self.query_gold_samples()
        print(f"[*] Gold samples found: {len(rows)}")

        result = {}
        if len(rows) >= 50:
            r1 = self.build_instruct_jsonl(rows)
            r2 = self.build_causal_jsonl(rows)
            result = {"status": "full", "instruct": r1, "causal": r2}
        else:
            print(f"[*] Only {len(rows)} gold samples, supplementing from signals...")
            rows2 = self.query_signals_as_fallback()
            if rows2:
                fallback_entries = []
                for row in rows2:
                    note = (row["note"] or "")[:150]
                    fallback_entries.append({
                        "instruction": f"分析 {row['symbol']} 市場數據，產出策略 JSON。",
                        "input": f"S:{row['score']}/5 S:{row['sharpe_30d']:.2f} "
                                 f"MDD:{row['mdd_30d']:.2%} Win:{row['win_rate_30d']:.1%} | {note}",
                        "output": json.dumps({
                            "strategy_name": f"EXPERT_{row['symbol']}",
                            "indicator": "MOMENTUM",
                            "params": {"window": 20},
                            "entry_condition": {"operator": ">", "threshold": 0.02},
                            "stop_loss": 0.08,
                            "max_hold_days": 10
                        }, ensure_ascii=False)
                    })

                fallback_path = os.path.join(os.path.dirname(__file__),
                                              "ray_signal_fallback.jsonl")
                with open(fallback_path, "w", encoding="utf-8") as f:
                    for e in fallback_entries:
                        f.write(json.dumps(e, ensure_ascii=False) + "\n")
                print(f"[*] Fallback: {len(fallback_entries)} entries → {fallback_path}")
                result = {
                    "status": "supplemented",
                    "gold": len(rows),
                    "fallback": len(fallback_entries),
                    "paths": [OUT_GOLD, OUT_CAUSAL, fallback_path]
                }
            else:
                print("[!] No gold samples at all. Run backtests first.")
                result = {"status": "empty", "gold": 0}

        print("\n[*] Gold Miner done.")
        return result


if __name__ == "__main__":
    miner = GoldMiner()
    r = miner.run()
    print(f"\nResult: {r}")