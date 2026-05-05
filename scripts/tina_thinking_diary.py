# -*- coding: utf-8 -*-
"""
Tina Thinking Diary — 思考日記
記錄每日判斷過程、追蹤準確度、從錯誤中學習
"""

import sqlite3
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
DATA_DIR = BASE_DIR / 'data'
REPORT_DIR = BASE_DIR / 'reports'
DIARY_DB = DATA_DIR / 'tina_thinking_diary.db'


class TinaThinkingDiary:
    """思考日記：記錄、驗證、學習"""

    def __init__(self):
        self.conn = sqlite3.connect(str(DIARY_DB))
        self.conn.row_factory = sqlite3.Row
        self._init_db()
        self.today = datetime.now().strftime('%Y-%m-%d')

    def _init_db(self):
        cur = self.conn.cursor()
        cur.executescript('''
            CREATE TABLE IF NOT EXISTS diary_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                time_slot TEXT,
                market_regime TEXT,
                twii_rsi REAL,
                qqq_rsi REAL,
                regime_prediction TEXT,
                confidence REAL,
                reasoning TEXT,
                tags TEXT
            );

            CREATE TABLE IF NOT EXISTS prediction_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                diary_id INTEGER,
                date TEXT,
                prediction_type TEXT,
                predicted_direction TEXT,
                actual_outcome TEXT,
                is_correct INTEGER,
                deviation TEXT,
                lesson TEXT,
                xp_change INTEGER,
                FOREIGN KEY (diary_id) REFERENCES diary_entries(id)
            );

            CREATE TABLE IF NOT EXISTS lessons_learned (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                topic TEXT,
                lesson TEXT,
                source_prediction_id INTEGER,
                importance INTEGER DEFAULT 5,
                times_applied INTEGER DEFAULT 0,
                success_rate REAL,
                last_updated TEXT
            );

            CREATE TABLE IF NOT EXISTS daily_judgment_review (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE,
                morning_prediction TEXT,
                afternoon_outcome TEXT,
                accuracy_score REAL,
                xp_from_accuracy INTEGER DEFAULT 0,
                overall_note TEXT,
                created_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_diary_date ON diary_entries(date);
            CREATE INDEX IF NOT EXISTS idx_predictions_date ON prediction_records(date);
            CREATE INDEX IF NOT EXISTS idx_lessons_topic ON lessons_learned(topic);
        ''')
        self.conn.commit()

    # ─── Writing ───────────────────────────────────────

    def write_morning_thought(self, regime_prediction: str,
                               twii_rsi: float = None, qqq_rsi: float = None,
                               confidence: float = 0.7, reasoning: str = "",
                               tags: str = "") -> int:
        """記錄早上思考"""
        cur = self.conn.cursor()
        cur.execute('''
            INSERT INTO diary_entries (date, time_slot, market_regime, twii_rsi,
                qqq_rsi, regime_prediction, confidence, reasoning, tags)
            VALUES (?, 'morning', ?, ?, ?, ?, ?, ?, ?)
        ''', (self.today, regime_prediction, twii_rsi, qqq_rsi,
              regime_prediction, confidence, reasoning, tags))
        self.conn.commit()
        return cur.lastrowid

    def record_prediction(self, diary_id: int, pred_type: str,
                          predicted_direction: str, note: str = "") -> int:
        """記錄預測"""
        cur = self.conn.cursor()
        cur.execute('''
            INSERT INTO prediction_records (diary_id, date, prediction_type,
                predicted_direction, note)
            VALUES (?, ?, ?, ?, ?)
        ''', (diary_id, self.today, pred_type, predicted_direction, note))
        self.conn.commit()
        return cur.lastrowid

    def verify_prediction(self, prediction_id: int, actual_outcome: str,
                          deviation: str = "", lesson: str = "") -> Dict:
        """驗證預測準確度"""
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM prediction_records WHERE id = ?', (prediction_id,))
        pred = dict(cur.fetchone())
        if not pred:
            return {'error': 'Prediction not found'}

        # 簡單判斷是否正確
        predicted = pred['predicted_direction'].lower()
        actual = actual_outcome.lower()

        if 'up' in predicted and 'up' in actual:
            is_correct = 1
        elif 'down' in predicted and 'down' in actual:
            is_correct = 1
        elif 'neutral' in predicted and 'neutral' in actual:
            is_correct = 1
        elif predicted == actual:
            is_correct = 1
        else:
            is_correct = 0

        xp = 10 if is_correct else -5

        cur.execute('''
            UPDATE prediction_records SET
                actual_outcome = ?, is_correct = ?,
                deviation = ?, lesson = ?, xp_change = ?
            WHERE id = ?
        ''', (actual_outcome, is_correct, deviation, lesson, xp, prediction_id))
        self.conn.commit()

        if not is_correct and lesson:
            self.record_lesson(f"判斷錯誤：{pred['prediction_type']}",
                               lesson, prediction_id)

        return {
            'prediction_id': prediction_id,
            'is_correct': is_correct,
            'xp_change': xp,
            'lesson': lesson if not is_correct else None
        }

    def write_afternoon_review(self, morning_diary_id: int,
                                actual_outcome: str, accuracy_score: float = 0.0,
                                note: str = "") -> int:
        """記錄下午驗證"""
        cur = self.conn.cursor()

        # 更新晨間預測結果
        cur.execute('''
            INSERT INTO daily_judgment_review (date, morning_prediction,
                afternoon_outcome, accuracy_score, overall_note, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (self.today, str(morning_diary_id), actual_outcome,
              accuracy_score, note, datetime.now().strftime('%Y-%m-%d %H:%M')))
        self.conn.commit()
        return cur.lastrowid

    def record_lesson(self, topic: str, lesson: str,
                      source_pred_id: int = None, importance: int = 5):
        """記錄學到的教訓"""
        cur = self.conn.cursor()

        # 檢查是否已有相同 lesson
        cur.execute('SELECT * FROM lessons_learned WHERE topic = ? AND lesson = ?',
                   (topic, lesson))
        existing = cur.fetchone()

        if existing:
            cur.execute('''
                UPDATE lessons_learned SET
                    times_applied = times_applied + 1,
                    last_updated = ?
                WHERE id = ?
            ''', (datetime.now().strftime('%Y-%m-%d %H:%M'), existing['id']))
        else:
            cur.execute('''
                INSERT INTO lessons_learned (date, topic, lesson, source_prediction_id,
                    importance, last_updated)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (self.today, topic, lesson, source_pred_id, importance,
                  datetime.now().strftime('%Y-%m-%d %H:%M')))

        self.conn.commit()

    # ─── Reading ────────────────────────────────────────

    def get_today_entry(self) -> Optional[Dict]:
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM diary_entries WHERE date = ? ORDER BY id DESC LIMIT 1',
                   (self.today,))
        r = cur.fetchone()
        return dict(r) if r else None

    def get_recent_predictions(self, days: int = 7) -> List[Dict]:
        cur = self.conn.cursor()
        start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        cur.execute('''
            SELECT * FROM prediction_records
            WHERE date >= ? ORDER BY date DESC
        ''', (start,))
        return [dict(r) for r in cur.fetchall()]

    def get_lessons(self, importance_min: int = 3) -> List[Dict]:
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM lessons_learned WHERE importance >= ? ORDER BY importance DESC, date DESC',
                   (importance_min,))
        return [dict(r) for r in cur.fetchall()]

    def get_prediction_accuracy(self, days: int = 30) -> Dict:
        cur = self.conn.cursor()
        start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        cur.execute('''
            SELECT COUNT(*) as total,
                SUM(is_correct) as correct,
                AVG(CAST(is_correct AS FLOAT)) as accuracy,
                SUM(xp_change) as total_xp
            FROM prediction_records
            WHERE date >= ?
        ''', (start,))
        r = cur.fetchone()
        return {
            'total_predictions': r['total'] or 0,
            'correct': r['correct'] or 0,
            'accuracy': round(r['accuracy'] or 0, 3),
            'total_xp': r['total_xp'] or 0,
            'period_days': days
        }

    # ─── Reporting ───────────────────────────────────────

    def generate_diary_report(self) -> str:
        """產出思考日記報告"""
        today_entry = self.get_today_entry()
        accuracy = self.get_prediction_accuracy(7)
        accuracy_month = self.get_prediction_accuracy(30)
        recent_preds = self.get_recent_predictions(7)
        lessons = self.get_lessons(4)

        lines = [
            f"# 📖 Tina 思考日記",
            f"**{datetime.now().strftime('%Y-%m-%d %H:%M')}**",
            "",
        ]

        # 今日記錄
        lines += ["## 📝 今日記錄", ""]
        if today_entry:
            lines.append(f"- 時間區間：{today_entry['time_slot']}")
            lines.append(f"- 市場格局：{today_entry['market_regime']}")
            lines.append(f"- RSI：TWII {today_entry['twii_rsi']} / QQQ {today_entry['qqq_rsi']}")
            lines.append(f"- 預測：{today_entry['regime_prediction']}（信心度：{today_entry['confidence']*100:.0f}%）")
            lines.append(f"- 推理：{today_entry['reasoning']}")
        else:
            lines.append("今日尚無記錄")

        # 預測準確度
        lines += ["", "## 🎯 預測準確度", ""]
        lines.append(f"- 近 7 天：{accuracy['accuracy']*100:.0f}%（{accuracy['correct']}/{accuracy['total_predictions']} 筆）")
        lines.append(f"- 近 30 天：{accuracy_month['accuracy']*100:.0f}%（{accuracy_month['correct']}/{accuracy_month['total_predictions']} 筆）")
        lines.append(f"- XP 變化：{accuracy_month['total_xp']:+d}")

        # 最近預測
        lines += ["", "## 📋 最近預測", ""]
        if recent_preds:
            lines.append("| 日期 | 類型 | 預測 | 結果 | XP |")
            lines.append("|------|------|------|------|----|")
            for p in recent_preds[:10]:
                result = '✅' if p['is_correct'] == 1 else '❌' if p['is_correct'] == 0 else '⏳'
                lines.append(f"| {p['date']} | {p['prediction_type']} | {p['predicted_direction']} | "
                           f"{result} | {p['xp_change']:+d} |")
        else:
            lines.append("尚無預測記錄")

        # 重要 lesson
        lines += ["", "## 🧠 學到的教訓", ""]
        if lessons:
            for l in lessons[:8]:
                lines.append(f"- 【{l['topic']}】{l['lesson']}")
                lines.append(f"  （已驗證 {l['times_applied']} 次，最後更新：{l['last_updated']}）")
        else:
            lines.append("尚無記錄")

        lines += [
            "",
            "---",
            f"*持續記錄，每日成長*",
        ]

        return "\n".join(lines)

    def save_report(self):
        """儲存思考日記報告"""
        REPORT_DIR.mkdir(exist_ok=True)
        date_str = datetime.now().strftime('%Y%m%d')
        report = self.generate_diary_report()
        path = REPORT_DIR / f'tina_thinking_diary_{date_str}.md'
        with open(path, 'w', encoding='utf-8') as f:
            f.write(report)
        return path

    def close(self):
        self.conn.close()


if __name__ == '__main__':
    diary = TinaThinkingDiary()

    # 嘗試從 tina_learning.db 的 market_context 取得今日 RSI
    try:
        import sqlite3 as sq
        lc = sq.connect(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\tina_learning.db')
        lc.row_factory = sq.Row
        c = lc.cursor()
        c.execute('SELECT twii_rsi, qqq_rsi, market_mode FROM market_context ORDER BY timestamp DESC LIMIT 1')
        r = c.fetchone()
        twii_rsi = float(r['twii_rsi']) if r and r['twii_rsi'] else None
        qqq_rsi = float(r['qqq_rsi']) if r and r['qqq_rsi'] else None
        regime = r['market_mode'] if r and r['market_mode'] else 'unknown'
        lc.close()
    except Exception:
        twii_rsi = None
        qqq_rsi = None
        regime = 'unknown'

    print("📖 Tina 思考日記...")
    print()

    # 產出報告
    report = diary.generate_diary_report()
    path = diary.save_report()
    print(f"   已儲存：{path}")
    print()
    print(report)
    print()
    print("✅ 完成")
    diary.close()
