# -*- coding: utf-8 -*-
"""
Tina Self-Learning Engine — 從歷史交易中學習，動態調整策略權重
"""

import sqlite3
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
DATA_DIR = BASE_DIR / 'data'
REPORT_DIR = BASE_DIR / 'reports'
LEARNING_DB = DATA_DIR / 'tina_learning.db'
TRACKING_DB = DATA_DIR / 'stock_tracking.db'


class TinaSelfLearner:
    """自我學習引擎：分析歷史、找出規律、提出進化建議"""

    def __init__(self):
        self.conn = self._connect(LEARNING_DB)
        self.conn.row_factory = sqlite3.Row
        self.tracking_conn = self._connect(TRACKING_DB)
        self.tracking_conn.row_factory = sqlite3.Row
        self.strategy_weights = self._load_weights()

    # ─── DB helpers ───────────────────────────────────────

    def _connect(self, db_path: Path) -> sqlite3.Connection:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _load_weights(self) -> Dict[str, float]:
        weights_file = DATA_DIR / 'strategy_weights.json'
        if weights_file.exists():
            with open(weights_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return self._default_weights()

    def _save_weights(self):
        weights_file = DATA_DIR / 'strategy_weights.json'
        with open(weights_file, 'w', encoding='utf-8') as f:
            json.dump(self.strategy_weights, f, ensure_ascii=False, indent=2)

    def _default_weights(self) -> Dict[str, float]:
        return {
            'RSI_逆向': 1.0,
            'MA20_突破': 1.0,
            '均線多頭': 1.0,
            '缺口回補': 1.0,
            '法人買超': 1.0,
            '價值成長': 1.0,
            '波段反轉': 1.0,
        }

    # ─── Core Analysis ───────────────────────────────────

    def analyze_historical_trades(self) -> Dict:
        """分析所有歷史交易，計算每個策略的勝率"""
        cur = self.conn.cursor()

        # 從 tina_learning.trades 分析
        cur.execute('''
            SELECT
                strategy_used,
                COUNT(*) as total,
                SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN outcome = 'LOSS' THEN 1 ELSE 0 END) as losses,
                AVG(CASE WHEN outcome = 'WIN' THEN pnl_pct END) as avg_win,
                AVG(CASE WHEN outcome = 'LOSS' THEN pnl_pct END) as avg_loss,
                AVG(CASE WHEN outcome IS NOT NULL THEN pnl_pct END) as avg_pnl,
                AVG(hold_days) as avg_hold_days
            FROM trades
            WHERE strategy_used IS NOT NULL AND strategy_used != ''
            GROUP BY strategy_used
        ''')
        trades_data = [dict(r) for r in cur.fetchall()]

        # 也從 stock_tracking.db 讀
        cur2 = self.tracking_conn.cursor()
        try:
            cur2.execute('''
                SELECT strategy as strategy_used, COUNT(*) as total,
                    SUM(CASE WHEN profit_pct > 0 THEN 1 ELSE 0 END) as wins,
                    AVG(profit_pct) as avg_pnl
                FROM stock_tracking
                WHERE strategy IS NOT NULL AND strategy != '' AND profit_pct IS NOT NULL
                GROUP BY strategy
            ''')
            tracking_data = [dict(r) for r in cur2.fetchall()]
        except Exception:
            tracking_data = []

        return {
            'learning_trades': trades_data,
            'tracking_trades': tracking_data,
            'analyzed_at': datetime.now().strftime('%Y-%m-%d %H:%M')
        }

    def find_patterns(self) -> List[Dict]:
        """找出成功的共同模式"""
        cur = self.conn.cursor()
        patterns = []

        # 模式1：RSI 進場區間勝率
        cur.execute('''
            SELECT
                CASE
                    WHEN entry_rsi < 30 THEN 'RSI<30_超賣'
                    WHEN entry_rsi BETWEEN 30 AND 40 THEN 'RSI_30-40_低估'
                    WHEN entry_rsi BETWEEN 40 AND 60 THEN 'RSI_40-60_中性'
                    WHEN entry_rsi BETWEEN 60 AND 70 THEN 'RSI_60-70_偏高'
                    ELSE 'RSI>70_過熱'
                END as rsi_zone,
                COUNT(*) as total,
                SUM(CASE WHEN outcome = 'WIN' THEN 1.0 ELSE 0 END) / COUNT(*) as win_rate,
                AVG(CASE WHEN outcome IS NOT NULL THEN pnl_pct END) as avg_pnl
            FROM trades
            WHERE entry_rsi IS NOT NULL AND outcome IS NOT NULL
            GROUP BY rsi_zone
            ORDER BY win_rate DESC
        ''')
        for r in cur.fetchall():
            if r['total'] >= 3:
                patterns.append({
                    'type': 'RSI_ZONE',
                    'name': r['rsi_zone'],
                    'total_trades': r['total'],
                    'win_rate': round(r['win_rate'], 3),
                    'avg_pnl': round(r['avg_pnl'] or 0, 4),
                    'confidence': min(r['total'] / 20, 0.9)
                })

        # 模式2：持有天數勝率
        cur.execute('''
            SELECT
                CASE
                    WHEN hold_days <= 5 THEN '持有<5天'
                    WHEN hold_days BETWEEN 5 AND 10 THEN '持有5-10天'
                    WHEN hold_days BETWEEN 10 AND 20 THEN '持有10-20天'
                    ELSE '持有20天+'
                END as hold_zone,
                COUNT(*) as total,
                SUM(CASE WHEN outcome = 'WIN' THEN 1.0 ELSE 0 END) / COUNT(*) as win_rate,
                AVG(pnl_pct) as avg_pnl
            FROM trades
            WHERE hold_days IS NOT NULL AND outcome IS NOT NULL
            GROUP BY hold_zone
        ''')
        for r in cur.fetchall():
            if r['total'] >= 3:
                patterns.append({
                    'type': 'HOLD_PERIOD',
                    'name': r['hold_zone'],
                    'total_trades': r['total'],
                    'win_rate': round(r['win_rate'], 3),
                    'avg_pnl': round(r['avg_pnl'] or 0, 4),
                    'confidence': min(r['total'] / 20, 0.9)
                })

        # 模式3：策略勝率排名
        cur.execute('''
            SELECT strategy_used, COUNT(*) as total,
                SUM(CASE WHEN outcome = 'WIN' THEN 1.0 ELSE 0 END) / COUNT(*) as win_rate
            FROM trades
            WHERE strategy_used IS NOT NULL AND outcome IS NOT NULL
            GROUP BY strategy_used
        ''')
        for r in cur.fetchall():
            if r['total'] >= 3 and r['win_rate'] >= 0.6:
                patterns.append({
                    'type': 'STRATEGY_WIN_RATE',
                    'name': f"勝率策略:{r['strategy_used']}",
                    'total_trades': r['total'],
                    'win_rate': round(r['win_rate'], 3),
                    'avg_pnl': None,
                    'confidence': min(r['total'] / 10, 0.85)
                })

        return patterns

    def detect_failing_strategies(self) -> List[Dict]:
        """找出正在衰退的策略"""
        cur = self.conn.cursor()
        failures = []

        # 近10筆 vs 總平均比較
        cur.execute('''
            SELECT strategy_used,
                (SELECT COUNT(*) FROM trades t2 WHERE t2.strategy_used = trades.strategy_used) as total,
                SUM(CASE WHEN outcome = 'WIN' THEN 1.0 ELSE 0 END) / COUNT(*) as overall_win_rate
            FROM trades
            WHERE strategy_used IS NOT NULL AND outcome IS NOT NULL
            GROUP BY strategy_used
        ''')
        overall = {r['strategy_used']: r['overall_win_rate'] for r in cur.fetchall() if r['total'] >= 5}

        # 最近10筆勝率
        for strat, overall_wr in overall.items():
            cur.execute('''
                SELECT outcome FROM trades
                WHERE strategy_used = ? AND outcome IS NOT NULL
                ORDER BY entry_date DESC LIMIT 10
            ''', (strat,))
            recent = [r['outcome'] for r in cur.fetchall()]
            if len(recent) < 5:
                continue
            recent_wr = sum(1 for o in recent if o == 'WIN') / len(recent)
            decline = overall_wr - recent_wr

            if decline > 0.2:  # 衰退超過 20%
                failures.append({
                    'strategy': strat,
                    'overall_win_rate': round(overall_wr, 3),
                    'recent_win_rate': round(recent_wr, 3),
                    'decline': round(decline, 3),
                    'severity': 'high' if decline > 0.3 else 'medium',
                    'suggestion': f"近10筆勝率 {recent_wr*100:.0f}% vs 總平均 {overall_wr*100:.0f}%，考慮暫時降權重"
                })

        return failures

    def adjust_strategy_weights(self) -> Dict:
        """根據分析結果動態調整策略權重"""
        analysis = self.analyze_historical_trades()
        patterns = self.find_patterns()
        failures = self.detect_failing_strategies()

        new_weights = self._load_weights()
        adjustments = []

        # 根據勝率調整權重
        for t in analysis['learning_trades']:
            if t['total'] >= 5:
                strat = t['strategy_used']
                wr = t['wins'] / t['total'] if t['total'] > 0 else 0
                current = new_weights.get(strat, 1.0)

                if wr >= 0.7:
                    new_w = min(current * 1.2, 2.0)
                    adjustments.append(f"{strat}: {current:.2f}→{new_w:.2f} (勝率{wr*100:.0f}%調升)")
                elif wr < 0.4 and wr > 0:
                    new_w = max(current * 0.7, 0.3)
                    adjustments.append(f"{strat}: {current:.2f}→{new_w:.2f} (勝率{wr*100:.0f}%調降)")
                new_weights[strat] = new_w

        # 針對失敗策略降權重
        for f in failures:
            strat = f['strategy']
            if strat in new_weights:
                new_weights[strat] = max(new_weights[strat] * 0.6, 0.3)
                adjustments.append(f"[衰退]{strat}→{new_weights[strat]:.2f}")

        # 根據 RSI 模式調整
        rsi_best = [p for p in patterns if p['type'] == 'RSI_ZONE' and p['win_rate'] >= 0.6]
        rsi_worst = [p for p in patterns if p['type'] == 'RSI_ZONE' and p['win_rate'] < 0.4]
        if rsi_best:
            adjustments.append(f"最佳RSI區間: {rsi_best[0]['name']} (勝率{rsi_best[0]['win_rate']*100:.0f}%)")
        if rsi_worst:
            adjustments.append(f"最差RSI區間: {rsi_worst[0]['name']} (勝率{rsi_worst[0]['win_rate']*100:.0f}%)")

        self.strategy_weights = new_weights
        self._save_weights()

        return {
            'weights': new_weights,
            'adjustments': adjustments,
            'failures_detected': len(failures),
            'patterns_found': len(patterns),
            'adjusted_at': datetime.now().strftime('%Y-%m-%d %H:%M')
        }

    def generate_learning_insights(self) -> str:
        """產出學習洞察報告"""
        analysis = self.analyze_historical_trades()
        patterns = self.find_patterns()
        failures = self.detect_failing_strategies()
        weights = self.adjust_strategy_weights()

        lines = [
            f"# 📚 Tina 學習洞察報告",
            f"**時間：{datetime.now().strftime('%Y-%m-%d %H:%M')}**",
            "",
            "## 📊 策略勝率總覽",
        ]

        # 策略勝率表
        if analysis['learning_trades']:
            lines.append("| 策略 | 總交易 | 勝率 | 平均獲利 | 平均虧損 |")
            lines.append("|------|--------|------|---------|---------|")
            for t in sorted(analysis['learning_trades'], key=lambda x: x['wins'] / x['total'] if x['total'] > 0 else 0, reverse=True):
                wr = t['wins'] / t['total'] if t['total'] > 0 else 0
                lines.append(f"| {t['strategy_used']} | {t['total']} | {wr*100:.1f}% | {t['avg_win'] or 0:+.2f}% | {t['avg_loss'] or 0:+.2f}% |")
        else:
            lines.append("目前無足夠交易數據")

        lines += ["", "## 🧩 成功模式", ""]
        good_patterns = [p for p in patterns if p['win_rate'] >= 0.6]
        if good_patterns:
            for p in good_patterns[:5]:
                lines.append(f"- 【{p['type']}】{p['name']} — 勝率 {p['win_rate']*100:.0f}%（{p['total_trades']}筆）")
        else:
            lines.append("尚無明顯成功模式（需更多交易數據）")

        lines += ["", "## ⚠️ 衰退策略警示", ""]
        if failures:
            for f in failures:
                lines.append(f"- 【{f['severity'].upper()}】{f['strategy']}")
                lines.append(f"  - 總勝率 {f['overall_win_rate']*100:.0f}% → 近10筆 {f['recent_win_rate']*100:.0f}%（降{f['decline']*100:.0f}%）")
                lines.append(f"  - 建議：{f['suggestion']}")
        else:
            lines.append("目前無明顯衰退策略 👍")

        lines += ["", "## ⚖️ 策略權重調整", ""]
        for adj in weights['adjustments']:
            lines.append(f"- {adj}")

        lines += ["", "## 🎯 明日重點關注", ""]
        if good_patterns:
            best = good_patterns[0]
            lines.append(f"1. 最佳 RSI 進場區間：{best['name']}（勝率 {best['win_rate']*100:.0f}%）")
        if failures:
            lines.append(f"2. 需觀望策略：{', '.join([f['strategy'] for f in failures])}")
        lines.append(f"3. 目前總交易分析：{sum(t['total'] for t in analysis['learning_trades'])} 筆")

        return "\n".join(lines)

    def propose_strategy_update(self) -> List[Dict]:
        """提出策略更新建議"""
        cur = self.conn.cursor()
        proposals = []

        # RSI 區間建議
        cur.execute('''
            SELECT
                CASE WHEN entry_rsi < 35 THEN 'RSI<35'
                     WHEN entry_rsi BETWEEN 35 AND 45 THEN 'RSI_35-45'
                     WHEN entry_rsi BETWEEN 45 AND 60 THEN 'RSI_45-60'
                     WHEN entry_rsi BETWEEN 60 AND 70 THEN 'RSI_60-70'
                     ELSE 'RSI>70' END as zone,
                COUNT(*) as total,
                SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins
            FROM trades WHERE entry_rsi IS NOT NULL AND outcome IS NOT NULL
            GROUP BY zone
        ''')
        rsi_data = {r['zone']: {'total': r['total'], 'wins': r['wins']} for r in cur.fetchall()}

        # 勝率最高的 RSI 區間
        best_rsi = max(rsi_data.items(), key=lambda x: x[1]['wins'] / x[1]['total'] if x[1]['total'] >= 3 else 0, default=(None, None))
        if best_rsi[0] and best_rsi[1]['total'] >= 3:
            proposals.append({
                'type': 'RSI_Zone',
                'action': '推薦進場 RSI 區間',
                'detail': best_rsi[0],
                'win_rate': best_rsi[1]['wins'] / best_rsi[1]['total'],
                'reason': f"該區間勝率 {best_rsi[1]['wins']/best_rsi[1]['total']*100:.0f}%（{best_rsi[1]['total']}筆）"
            })

        # 持有天數優化
        cur.execute('''
            SELECT AVG(hold_days) as avg_days, AVG(pnl_pct) as avg_pnl, outcome
            FROM trades WHERE hold_days IS NOT NULL AND outcome IS NOT NULL
            GROUP BY outcome
        ''')
        hold_result = {r['outcome']: {'avg_days': r['avg_days'], 'avg_pnl': r['avg_pnl']} for r in cur.fetchall()}
        if 'WIN' in hold_result and hold_result['WIN']['avg_days']:
            proposals.append({
                'type': 'Hold_Period',
                'action': '建議波段持有天數',
                'detail': f"{hold_result['WIN']['avg_days']:.0f} 天",
                'win_rate': None,
                'reason': f"獲利交易平均持有 {hold_result['WIN']['avg_days']:.0f} 天，報酬 {hold_result['WIN']['avg_pnl']:+.2f}%"
            })

        # 更新進場條件
        if rsi_data.get('RSI>70', {}).get('total', 0) >= 3:
            rsi70_wr = rsi_data['RSI>70']['wins'] / rsi_data['RSI>70']['total']
            if rsi70_wr < 0.4:
                proposals.append({
                    'type': 'Entry_Condition',
                    'action': '限制 RSI>70 進場',
                    'detail': 'RSI>70 進場勝率過低',
                    'win_rate': rsi70_wr,
                    'reason': f"RSI>70 區間勝率僅 {rsi70_wr*100:.0f}%，建議改為等待回調"
                })

        return proposals

    def run_full_learning_cycle(self) -> str:
        """執行完整學習循環"""
        print("🔄 Tina 自我學習引擎啟動...")
        print()

        # 1. 分析歷史交易
        print("📊 分析歷史交易...")
        analysis = self.analyze_historical_trades()
        print(f"   分析了 {len(analysis['learning_trades'])} 個策略的交易數據")

        # 2. 找出模式
        print("🧩 尋找成功模式...")
        patterns = self.find_patterns()
        print(f"   發現 {len(patterns)} 個模式")

        # 3. 偵測衰退
        print("⚠️ 偵測衰退策略...")
        failures = self.detect_failing_strategies()
        print(f"   發現 {len(failures)} 個衰退策略")

        # 4. 調整權重
        print("⚖️ 調整策略權重...")
        weights = self.adjust_strategy_weights()
        print(f"   完成 {len(weights['adjustments'])} 項調整")

        # 5. 產出洞察報告
        print("📝 產出學習洞察報告...")
        report = self.generate_learning_insights()

        # 6. 儲存報告
        REPORT_DIR.mkdir(exist_ok=True)
        date_str = datetime.now().strftime('%Y%m%d_%H%M')
        report_path = REPORT_DIR / f'tina_learning_insights_{date_str}.md'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"   已儲存：{report_path}")

        # 7. 記錄學習日誌
        self._log_learning('LEARNING_CYCLE', f"完成學習循環：{len(patterns)}模式,{len(failures)}衰策略", str(report_path))

        print()
        print(report)
        print()
        print("✅ 學習循環完成")
        return report

    def _log_learning(self, event_type: str, content: str, source: str = ""):
        cur = self.conn.cursor()
        cur.execute('''
            INSERT INTO learning_log (date, event_type, content, ai_confidence, tags)
            VALUES (?, ?, ?, ?, ?)
        ''', (datetime.now().strftime('%Y-%m-%d %H:%M'), event_type, content, 0.85, source))
        self.conn.commit()

    def close(self):
        self.conn.close()
        self.tracking_conn.close()


if __name__ == '__main__':
    learner = TinaSelfLearner()
    learner.run_full_learning_cycle()
    learner.close()
