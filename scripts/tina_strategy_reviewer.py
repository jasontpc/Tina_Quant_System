"""
Tina Strategy Reviewer - 策略複盤系統
分析歷史交易數據，找出最差情境，產出優化建議
"""

import sqlite3
import json
import os
from datetime import datetime
from collections import defaultdict


class StrategyReviewer:
    def __init__(self, base_dir=None):
        if base_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            base_dir = os.path.dirname(base_dir)
        self.base_dir = base_dir
        self.data_dir = os.path.join(base_dir, 'data')
        self.reports_dir = os.path.join(base_dir, 'reports')
        os.makedirs(self.reports_dir, exist_ok=True)

        self.master_db = os.path.join(self.data_dir, 'master_backtest.db')
        self.us_sim_db = os.path.join(self.data_dir, 'us_sim_trades.db')
        self.sherry_db = os.path.join(self.data_dir, 'sherry_sim_trades.db')
        self.maggy_db = os.path.join(self.data_dir, 'maggy_sim_trades.db')
        self.learning_db = os.path.join(self.data_dir, 'tina_learning.db')
        self.backtest_dir = os.path.join(base_dir, 'backtest')

        self.trades = []
        self.review_date = datetime.now().strftime('%Y-%m-%d')

    # ─────────────────────────────────────────────
    # 1. 載入所有歷史交易
    # ─────────────────────────────────────────────
    def load_trade_history(self):
        """整合所有來源的歷史交易"""
        self.trades = []

        # master_backtest.db trade_archive
        if os.path.exists(self.master_db):
            conn = sqlite3.connect(self.master_db)
            cur = conn.cursor()
            try:
                cur.execute("""
                    SELECT symbol, entry_date, entry_price, exit_date, exit_price,
                           return_pct, holding_days, strategy, entry_rsi, exit_rsi,
                           exit_reason, system, NULL
                    FROM trade_archive ORDER BY entry_date DESC
                """)
                for row in cur.fetchall():
                    self.trades.append({
                        'source': 'master_backtest',
                        'stock': row[0], 'entry_date': row[1],
                        'entry_price': row[2], 'exit_date': row[3],
                        'exit_price': row[4], 'pnl_pct': row[5],
                        'hold_days': row[6], 'strategy': row[7],
                        'entry_rsi': row[8], 'exit_rsi': row[9],
                        'outcome': 'win' if row[5] and row[5] > 0 else 'loss',
                        'tags': row[10], 'lesson': None,
                        'system': row[11],
                    })
            except Exception as e:
                print(f"[Reviewer] master_backtest error: {e}")
            conn.close()

        # us_sim_trades.db
        if os.path.exists(self.us_sim_db):
            conn = sqlite3.connect(self.us_sim_db)
            cur = conn.cursor()
            try:
                cur.execute("""
                    SELECT symbol, entry_date, entry_price, exit_date, exit_price,
                           return_pct, holding_days, strategy, entry_rsi, exit_rsi,
                           exit_reason, 'US', NULL
                    FROM sim_trades WHERE return_pct IS NOT NULL ORDER BY entry_date DESC
                """)
                for row in cur.fetchall():
                    self.trades.append({
                        'source': 'us_sim',
                        'stock': row[0], 'entry_date': row[1],
                        'entry_price': row[2], 'exit_date': row[3],
                        'exit_price': row[4], 'pnl_pct': row[5],
                        'hold_days': row[6], 'strategy': row[7],
                        'entry_rsi': row[8], 'exit_rsi': row[9],
                        'outcome': 'win' if row[5] and row[5] > 0 else 'loss',
                        'tags': row[10], 'lesson': None,
                        'system': row[11],
                    })
            except Exception as e:
                print(f"[Reviewer] us_sim_trades error: {e}")
            conn.close()

        # sherry_sim_trades.db closed_positions
        if os.path.exists(self.sherry_db):
            conn = sqlite3.connect(self.sherry_db)
            cur = conn.cursor()
            try:
                cur.execute("""
                    SELECT symbol, entry_date, exit_date, return_pct, holding_days,
                           exit_reason, 'Sherry', NULL, NULL, NULL
                    FROM closed_positions WHERE return_pct IS NOT NULL ORDER BY exit_date DESC
                """)
                for row in cur.fetchall():
                    self.trades.append({
                        'source': 'sherry_sim',
                        'stock': row[0], 'entry_date': row[1],
                        'entry_price': None, 'exit_date': row[2],
                        'exit_price': None, 'pnl_pct': row[3],
                        'hold_days': row[4], 'strategy': row[5],
                        'entry_rsi': None, 'exit_rsi': None,
                        'outcome': 'win' if row[3] and row[3] > 0 else 'loss',
                        'tags': row[5], 'lesson': None,
                        'system': row[6],
                    })
            except Exception as e:
                print(f"[Reviewer] sherry_sim error: {e}")
            conn.close()

        # maggy_sim_trades.db
        if os.path.exists(self.maggy_db):
            conn = sqlite3.connect(self.maggy_db)
            cur = conn.cursor()
            try:
                # Get column names first
                cur.execute("PRAGMA table_info(sim_trades)")
                cols = [c[1] for c in cur.fetchall()]
                has_strategy = 'strategy' in cols

                if has_strategy:
                    query = """
                        SELECT symbol, entry_date, entry_price, exit_date, exit_price,
                               return_pct, holding_days, strategy, entry_rsi, exit_rsi,
                               exit_reason, 'Maggy', NULL
                        FROM sim_trades WHERE return_pct IS NOT NULL ORDER BY entry_date DESC
                    """
                else:
                    query = """
                        SELECT symbol, entry_date, entry_price, exit_date, exit_price,
                               return_pct, holding_days, exit_reason, entry_rsi, exit_rsi,
                               exit_reason, 'Maggy', NULL
                        FROM sim_trades WHERE return_pct IS NOT NULL ORDER BY entry_date DESC
                    """

                cur.execute(query)
                for row in cur.fetchall():
                    self.trades.append({
                        'source': 'maggy_sim',
                        'stock': row[0], 'entry_date': row[1],
                        'entry_price': row[2], 'exit_date': row[3],
                        'exit_price': row[4], 'pnl_pct': row[5],
                        'hold_days': row[6], 'strategy': row[7],
                        'entry_rsi': row[8], 'exit_rsi': row[9],
                        'outcome': 'win' if row[5] and row[5] > 0 else 'loss',
                        'tags': row[10], 'lesson': None,
                        'system': row[11],
                    })
            except Exception as e:
                print(f"[Reviewer] maggy_sim error: {e}")
            conn.close()

        # tina_learning.db trades (if any)
        if os.path.exists(self.learning_db):
            conn = sqlite3.connect(self.learning_db)
            cur = conn.cursor()
            try:
                cur.execute("""
                    SELECT stock, entry_date, entry_price, exit_date, exit_price,
                           pnl_pct, hold_days, strategy_used, entry_rsi, exit_rsi,
                           outcome, tags, lesson_learned
                    FROM trades WHERE pnl_pct IS NOT NULL ORDER BY entry_date DESC
                """)
                for row in cur.fetchall():
                    self.trades.append({
                        'source': 'tina_learning',
                        'stock': row[0], 'entry_date': row[1],
                        'entry_price': row[2], 'exit_date': row[3],
                        'exit_price': row[4], 'pnl_pct': row[5],
                        'hold_days': row[6], 'strategy': row[7],
                        'entry_rsi': row[8], 'exit_rsi': row[9],
                        'outcome': row[10], 'tags': row[11],
                        'lesson': row[12], 'system': 'Tina',
                    })
            except Exception:
                pass
            conn.close()

        # Backtest dir JSONs
        self._scan_backtest_dir()

        print(f"[StrategyReviewer] Loaded {len(self.trades)} trades from all sources")
        return self.trades

    def _scan_backtest_dir(self):
        if not os.path.exists(self.backtest_dir):
            return
        for fname in os.listdir(self.backtest_dir):
            if not fname.endswith('.json') or fname.startswith('boost'):
                continue
            try:
                with open(os.path.join(self.backtest_dir, fname), encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list):
                    for t in data:
                        self._add_backtest_trade(t, fname)
                elif isinstance(data, dict) and 'trades' in data:
                    for t in data['trades']:
                        self._add_backtest_trade(t, fname)
            except Exception:
                pass

    def _add_backtest_trade(self, t, fname):
        pnl = t.get('pnl_pct') or t.get('return_pct')
        if pnl is None:
            return
        self.trades.append({
            'source': 'backtest',
            'stock': t.get('symbol', fname.replace('.json', '')),
            'entry_date': t.get('entry_date'),
            'exit_date': t.get('exit_date'),
            'pnl_pct': pnl,
            'hold_days': t.get('hold_days'),
            'strategy': t.get('strategy', 'backtest'),
            'entry_rsi': t.get('entry_rsi'),
            'exit_rsi': t.get('exit_rsi'),
            'outcome': 'win' if float(pnl) > 0 else 'loss',
            'tags': t.get('exit_reason'),
            'lesson': t.get('lesson'),
            'system': t.get('system', 'unknown'),
        })

    # ─────────────────────────────────────────────
    # 2. 分類市場體制
    # ─────────────────────────────────────────────
    def classify_market_regime(self, date_range=None):
        regime_map = {}
        if not os.path.exists(self.master_db):
            self.market_regime = 'UNKNOWN'
            self.ma_slope = 0
            self.avg_swing = 0
            return regime_map

        conn = sqlite3.connect(self.master_db)
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT date, close FROM market_daily
                WHERE symbol IN ('TWII', 'SPY', 'QQQ')
                ORDER BY date DESC LIMIT 60
            """)
            rows = cur.fetchall()
        except Exception:
            conn.close()
            self.market_regime = 'UNKNOWN'
            self.ma_slope = 0
            self.avg_swing = 0
            return regime_map
        conn.close()

        if len(rows) < 20:
            self.market_regime = 'UNKNOWN'
            self.ma_slope = 0
            self.avg_swing = 0
            return regime_map

        prices = [r[1] for r in rows[::-1] if r[1]]
        if len(prices) < 20:
            self.market_regime = 'UNKNOWN'
            self.ma_slope = 0
            self.avg_swing = 0
            return regime_map

        swings = [abs(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
        avg_swing = sum(swings[-20:]) / 20
        ma_slope = (prices[-1] - prices[-20]) / prices[-20] if prices[-20] else 0

        regime = 'TREND' if abs(ma_slope) > 0.02 or avg_swing > 0.015 else 'RANGE'
        self.market_regime = regime
        self.ma_slope = ma_slope
        self.avg_swing = avg_swing
        print(f"[StrategyReviewer] Market regime: {regime} (slope={ma_slope:.4f}, vol={avg_swing:.4f})")
        return regime_map

    # ─────────────────────────────────────────────
    # 3. 分析 RSI 在不同盤勢的表現
    # ─────────────────────────────────────────────
    def analyze_rsi_performance(self, regime):
        results = defaultdict(list)
        for t in self.trades:
            rsi = t.get('entry_rsi')
            pnl = t.get('pnl_pct')
            if rsi is not None and pnl is not None:
                try:
                    rsi_f = float(rsi)
                    pnl_f = float(pnl)
                    bucket = ('RSI<30' if rsi_f < 30 else
                              'RSI30-40' if rsi_f < 40 else
                              'RSI40-50' if rsi_f < 50 else
                              'RSI50-60' if rsi_f < 60 else 'RSI>60')
                    results[bucket].append({'rsi': rsi_f, 'pnl': pnl_f})
                except (ValueError, TypeError):
                    pass

        summary = {}
        for bucket, lst in results.items():
            wins = [x['pnl'] for x in lst if x['pnl'] > 0]
            losses = [x['pnl'] for x in lst if x['pnl'] <= 0]
            summary[bucket] = {
                'count': len(lst),
                'win_rate': len(wins) / len(lst) if lst else 0,
                'avg_pnl': sum(x['pnl'] for x in lst) / len(lst),
                'avg_win': sum(wins) / len(wins) if wins else 0,
                'avg_loss': sum(losses) / len(losses) if losses else 0,
            }

        self.rsi_summary = summary
        print(f"[StrategyReviewer] RSI performance ({regime}): { {k: v['count'] for k, v in summary.items()} }")
        return summary

    # ─────────────────────────────────────────────
    # 4. 分析 MACD/策略/系統 表現
    # ─────────────────────────────────────────────
    def analyze_strategy_performance(self, regime):
        results = defaultdict(list)
        for t in self.trades:
            if t.get('strategy') and t.get('pnl_pct') is not None:
                try:
                    pnl = float(t['pnl_pct'])
                    results[t['strategy']].append({'pnl': pnl})
                except (ValueError, TypeError):
                    pass

        summary = {}
        for strat, lst in results.items():
            wins = [x['pnl'] for x in lst if x['pnl'] > 0]
            summary[strat] = {
                'count': len(lst),
                'win_rate': len(wins) / len(lst) if lst else 0,
                'avg_pnl': sum(x['pnl'] for x in lst) / len(lst),
                'avg_win': sum(wins) / len(wins) if wins else 0,
                'avg_loss': sum([x['pnl'] for x in lst if x['pnl'] <= 0]) / max(1, len(lst) - len(wins)),
            }

        self.strategy_summary = summary
        print(f"[StrategyReviewer] Strategy performance ({regime}): { {k: v['count'] for k, v in summary.items()} }")
        return summary

    # ─────────────────────────────────────────────
    # 5. 找出損益比最低的 N 種情境
    # ─────────────────────────────────────────────
    def find_worst_scenarios(self, top_n=3):
        scenarios = []
        for t in self.trades:
            if t.get('pnl_pct') is None:
                continue
            try:
                pnl = float(t['pnl_pct'])
            except (ValueError, TypeError):
                continue
            scenarios.append({
                'stock': t.get('stock', 'unknown'),
                'entry_date': t.get('entry_date'),
                'exit_date': t.get('exit_date'),
                'entry_rsi': t.get('entry_rsi'),
                'exit_rsi': t.get('exit_rsi'),
                'hold_days': t.get('hold_days'),
                'strategy': t.get('strategy'),
                'system': t.get('system', 'unknown'),
                'pnl_pct': pnl,
                'outcome': t.get('outcome'),
                'tags': t.get('tags'),
                'lesson': t.get('lesson'),
            })

        scenarios.sort(key=lambda x: x['pnl_pct'])
        self.worst_scenarios = scenarios[:top_n]
        print(f"[StrategyReviewer] Worst scenarios: {[s['pnl_pct'] for s in self.worst_scenarios]}")
        return self.worst_scenarios

    # ─────────────────────────────────────────────
    # 6. 產出優化參數建議
    # ─────────────────────────────────────────────
    def generate_optimized_params(self):
        recommendations = []

        # RSI 分析建議
        if hasattr(self, 'rsi_summary') and self.rsi_summary:
            for bucket, data in self.rsi_summary.items():
                if data['win_rate'] < 0.45 and data['count'] >= 3:
                    recommendations.append({
                        'type': 'RSI Zone Adjustment',
                        'bucket': bucket,
                        'win_rate': data['win_rate'],
                        'count': data['count'],
                        'suggestion': f"Consider narrowing {bucket} entry zone or adding confirmation filters. Current win_rate={data['win_rate']:.1%}",
                        'priority': 'HIGH' if data['win_rate'] < 0.35 else 'MEDIUM'
                    })

        # 持有天數分析
        hold_pnl = defaultdict(list)
        for t in self.trades:
            if t.get('hold_days') and t.get('pnl_pct') is not None:
                try:
                    hold_pnl[int(t['hold_days'])].append(float(t['pnl_pct']))
                except (ValueError, TypeError):
                    pass

        if hold_pnl:
            avg_by_hold = {k: sum(v)/len(v) for k, v in hold_pnl.items()}
            worst_hold = min(avg_by_hold, key=avg_by_hold.get)
            if avg_by_hold[worst_hold] < -5 and worst_hold > 10:
                recommendations.append({
                    'type': 'Max Hold Days',
                    'worst_days': worst_hold,
                    'avg_pnl': avg_by_hold[worst_hold],
                    'suggestion': f"Avg PnL at {worst_hold} days is {avg_by_hold[worst_hold]:.2f}%. Shorten max hold to {max(5, worst_hold-5)} days",
                    'priority': 'HIGH'
                })

        # 市場體制建議
        if hasattr(self, 'market_regime'):
            rec = {
                'type': 'Market Regime Adaptation',
                'regime': self.market_regime,
                'priority': 'MEDIUM'
            }
            if self.market_regime == 'RANGE':
                rec['suggestion'] = 'Range market: raise RSI entry to 40+, add MA confirmation, reduce ATR stop to 1.5x'
            elif self.market_regime == 'TREND':
                rec['suggestion'] = 'Trend market: RSI pullback entry (30-50) is effective, can widen to 30-55'
            else:
                rec['suggestion'] = 'Market regime unknown, use conservative RSI 35-50 with MA confirmation'
            recommendations.append(rec)

        # 策略表現建議
        if hasattr(self, 'strategy_summary') and self.strategy_summary:
            worst_strat = min(self.strategy_summary.items(), key=lambda x: x[1]['avg_pnl'])
            if worst_strat[1]['avg_pnl'] < -3 and worst_strat[1]['count'] >= 5:
                recommendations.append({
                    'type': 'Strategy Performance',
                    'strategy': worst_strat[0],
                    'avg_pnl': worst_strat[1]['avg_pnl'],
                    'count': worst_strat[1]['count'],
                    'suggestion': f"Strategy '{worst_strat[0]}' avg PnL={worst_strat[1]['avg_pnl']:.2f}%, review or disable",
                    'priority': 'HIGH'
                })

        self.recommendations = recommendations
        print(f"[StrategyReviewer] Generated {len(recommendations)} recommendations")
        return recommendations

    # ─────────────────────────────────────────────
    # 7. 儲存複盤報告
    # ─────────────────────────────────────────────
    def save_review_report(self):
        report_path = os.path.join(
            self.reports_dir,
            f"tina_review_report_{self.review_date.replace('-', '')}.md"
        )

        valid = [t for t in self.trades if t.get('pnl_pct') is not None]
        wins = [t for t in valid if float(t['pnl_pct']) > 0]
        losses = [t for t in valid if float(t['pnl_pct']) <= 0]
        total_pnl = sum(float(t['pnl_pct']) for t in valid)
        win_rate = len(wins) / len(valid) if valid else 0

        md = f"""# Tina Strategy Review Report

**Date**: {self.review_date}  
**Analyst**: Tina

---

## Overall Statistics

| Item | Value |
|------|-------|
| Total Trades | {len(valid)} |
| Wins | {len(wins)} |
| Losses | {len(losses)} |
| Win Rate | {win_rate:.1%} |
| Avg PnL | {total_pnl/len(valid):+.2f}% if valid else +0.00% |
| Total PnL | {total_pnl:+.2f}% |

---

## Market Regime

| Item | Value |
|------|-------|
| Regime | {getattr(self, 'market_regime', 'N/A')} |
| MA Slope | {getattr(self, 'ma_slope', 0):.4f} |
| Avg Volatility | {getattr(self, 'avg_swing', 0):.4f} |

---

## RSI Zone Performance

| Zone | Count | Win Rate | Avg PnL | Avg Win | Avg Loss |
|------|-------|----------|---------|---------|----------|
"""
        for zone in ['RSI<30', 'RSI30-40', 'RSI40-50', 'RSI50-60', 'RSI>60']:
            if hasattr(self, 'rsi_summary') and zone in self.rsi_summary:
                d = self.rsi_summary[zone]
                md += f"| {zone} | {d['count']} | {d['win_rate']:.1%} | {d['avg_pnl']:+.2f}% | {d['avg_win']:+.2f}% | {d['avg_loss']:+.2f}% |\n"
            else:
                md += f"| {zone} | 0 | N/A | N/A | N/A | N/A |\n"

        md += "\n## Strategy Performance\n\n"
        md += "| Strategy | Count | Win Rate | Avg PnL | Avg Win | Avg Loss |\n"
        md += "|----------|-------|----------|---------|---------|----------|\n"
        if hasattr(self, 'strategy_summary') and self.strategy_summary:
            for s, d in sorted(self.strategy_summary.items(), key=lambda x: x[1]['avg_pnl']):
                md += f"| {s} | {d['count']} | {d['win_rate']:.1%} | {d['avg_pnl']:+.2f}% | {d['avg_win']:+.2f}% | {d['avg_loss']:+.2f}% |\n"
        else:
            md += "| - | 0 | N/A | N/A | N/A | N/A |\n"

        md += "\n## Worst Scenarios (Top 3)\n\n"
        if hasattr(self, 'worst_scenarios') and self.worst_scenarios:
            for i, s in enumerate(self.worst_scenarios, 1):
                md += f"""### {i}. {s['stock']} -- {s['pnl_pct']:+.2f}%

- Entry: {s['entry_date'] or 'N/A'} | Exit: {s['exit_date'] or 'N/A'}
- Entry RSI: {s['entry_rsi'] or 'N/A'} | Exit RSI: {s['exit_rsi'] or 'N/A'}
- Hold: {s['hold_days'] or 'N/A'} days | Strategy: {s['strategy'] or 'N/A'} | System: {s.get('system','N/A')}
- Lesson: {s.get('lesson') or 'No record'}

"""
        else:
            md += "_No worst scenarios identified_\n\n"

        md += "\n## Optimization Recommendations\n\n"
        if hasattr(self, 'recommendations') and self.recommendations:
            for i, r in enumerate(self.recommendations, 1):
                icon = "[HIGH]" if r.get('priority') == 'HIGH' else "[MED]"
                md += f"### {icon} {i}. {r.get('type')}\n\n**{r.get('suggestion', 'N/A')}\n\n"
        else:
            md += "_No recommendations yet (need more trade data)_\n\n"

        md += f"""
---

## Recommended Parameter Version

Based on this review:

```
Version: v3_adapted
Changes (per {getattr(self, 'market_regime', 'UNKNOWN')} regime):
  - RSI entry max: 45 -> 40 (tighter entry in range/trend market)
  - Max hold days: 20 -> 15 (reduce exposure)
  - ATR stop: 2.0 -> 1.5 (more responsive stop)
```

---

_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_  
_Tina Quant System v3.12 | Tina_
"""

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(md)

        print(f"[StrategyReviewer] Report saved: {report_path}")
        return report_path

    # ─────────────────────────────────────────────
    # 8. 執行完整複盤流程
    # ─────────────────────────────────────────────
    def run_full_review(self):
        print("=" * 50)
        print("[StrategyReviewer] Starting strategy review...")
        print("=" * 50)

        self.load_trade_history()
        self.classify_market_regime()
        regime = getattr(self, 'market_regime', 'UNKNOWN')

        if self.trades:
            self.analyze_rsi_performance(regime)
            self.analyze_strategy_performance(regime)
            self.find_worst_scenarios(top_n=3)
            self.generate_optimized_params()

        report_path = self.save_review_report()
        print(f"[StrategyReviewer] Review complete! Report: {report_path}")
        return report_path


if __name__ == '__main__':
    import os
    base = os.path.dirname(os.path.abspath(__file__))
    parent = os.path.dirname(base)
    if os.path.basename(parent) == 'Tina_Quant_System':
        base_dir = parent
    else:
        base_dir = base

    reviewer = StrategyReviewer(base_dir=base_dir)
    reviewer.run_full_review()