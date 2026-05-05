# -*- coding: utf-8 -*-
"""
Tina Knowledge Manager — 知識庫管理系統
管理市場知識、策略知識、交易心理三大類知識
"""

import sqlite3
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
DATA_DIR = BASE_DIR / 'data'
REPORT_DIR = BASE_DIR / 'reports'
KNOWLEDGE_DB = DATA_DIR / 'tina_knowledge.db'


class TinaKnowledgeManager:
    """知識庫管理器"""

    def __init__(self):
        self.conn = sqlite3.connect(str(KNOWLEDGE_DB))
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        cur = self.conn.cursor()
        cur.executescript('''
            CREATE TABLE IF NOT EXISTS market_knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                topic TEXT,
                insight TEXT,
                confidence REAL DEFAULT 0.7,
                source TEXT,
                date_added TEXT,
                times_used INTEGER DEFAULT 0,
                usefulness REAL DEFAULT 0.5
            );

            CREATE TABLE IF NOT EXISTS strategy_knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT,
                when_works TEXT,
                when_fails TEXT,
                best_params TEXT,
                lessons TEXT,
                confidence REAL DEFAULT 0.7,
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS trading_psychology (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT,
                insight TEXT,
                importance INTEGER DEFAULT 5,
                last_updated TEXT
            );

            CREATE TABLE IF NOT EXISTS knowledge_usage_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                knowledge_type TEXT,
                knowledge_id INTEGER,
                outcome TEXT,
                helpful INTEGER DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_market_cat ON market_knowledge(category);
            CREATE INDEX IF NOT EXISTS idx_strategy_name ON strategy_knowledge(strategy_name);
            CREATE INDEX IF NOT EXISTS idx_psych_topic ON trading_psychology(topic);
        ''')
        self.conn.commit()

    # ─── Market Knowledge ────────────────────────────────

    def add_market_knowledge(self, category: str, topic: str, insight: str,
                              confidence: float = 0.7, source: str = "") -> int:
        """新增市場知識"""
        cur = self.conn.cursor()
        cur.execute('''
            INSERT INTO market_knowledge (category, topic, insight, confidence, source, date_added)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (category, topic, insight, confidence, source,
              datetime.now().strftime('%Y-%m-%d %H:%M')))
        self.conn.commit()
        return cur.lastrowid

    def search_market_knowledge(self, query: str, category: str = None) -> List[Dict]:
        """搜尋市場知識"""
        cur = self.conn.cursor()
        if category:
            cur.execute('''
                SELECT * FROM market_knowledge
                WHERE topic LIKE ? OR insight LIKE ? AND category = ?
                ORDER BY confidence DESC, times_used DESC
            ''', (f'%{query}%', f'%{query}%', category))
        else:
            cur.execute('''
                SELECT * FROM market_knowledge
                WHERE topic LIKE ? OR insight LIKE ?
                ORDER BY confidence DESC, times_used DESC
            ''', (f'%{query}%', f'%{query}%'))
        return [dict(r) for r in cur.fetchall()]

    def record_knowledge_usage(self, ktype: str, kid: int, outcome: str = "", helpful: int = 1):
        """記錄知識使用情況（用於評估知識價值）"""
        cur = self.conn.cursor()
        cur.execute('''
            INSERT INTO knowledge_usage_log (date, knowledge_type, knowledge_id, outcome, helpful)
            VALUES (?, ?, ?, ?, ?)
        ''', (datetime.now().strftime('%Y-%m-%d'), ktype, kid, outcome, helpful))

        if ktype == 'market':
            cur.execute('UPDATE market_knowledge SET times_used = times_used + 1 WHERE id = ?', (kid,))
        elif ktype == 'strategy':
            cur.execute('UPDATE strategy_knowledge SET times_used = times_used + 1 WHERE id = ?', (kid,))

        self.conn.commit()

    # ─── Strategy Knowledge ────────────────────────────

    def add_strategy_knowledge(self, name: str, when_works: str, when_fails: str,
                                 best_params: str = "", lessons: str = "",
                                 confidence: float = 0.7) -> int:
        """新增策略知識"""
        cur = self.conn.cursor()
        cur.execute('''
            INSERT INTO strategy_knowledge (strategy_name, when_works, when_fails,
                best_params, lessons, confidence, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, when_works, when_fails, best_params, lessons, confidence,
              datetime.now().strftime('%Y-%m-%d %H:%M')))
        self.conn.commit()
        return cur.lastrowid

    def get_strategy_knowledge(self, strategy_name: str = None) -> List[Dict]:
        """取得策略知識"""
        cur = self.conn.cursor()
        if strategy_name:
            cur.execute('SELECT * FROM strategy_knowledge WHERE strategy_name LIKE ?',
                       (f'%{strategy_name}%',))
        else:
            cur.execute('SELECT * FROM strategy_knowledge ORDER BY confidence DESC')
        return [dict(r) for r in cur.fetchall()]

    def update_strategy_knowledge(self, strat_id: int, lessons: str = "",
                                   confidence: float = None, best_params: str = ""):
        """更新策略知識"""
        cur = self.conn.cursor()
        updates = []
        params = []
        if lessons:
            updates.append('lessons = ?')
            params.append(lessons)
        if best_params:
            updates.append('best_params = ?')
            params.append(best_params)
        if confidence is not None:
            updates.append('confidence = ?')
            params.append(confidence)
        updates.append('updated_at = ?')
        params.append(datetime.now().strftime('%Y-%m-%d %H:%M'))
        params.append(strat_id)
        cur.execute(f"UPDATE strategy_knowledge SET {', '.join(updates)} WHERE id = ?",
                   params)
        self.conn.commit()

    # ─── Trading Psychology ───────────────────────────────

    def add_psychology_insight(self, topic: str, insight: str, importance: int = 5) -> int:
        """新增交易心理知識"""
        cur = self.conn.cursor()
        cur.execute('''
            INSERT INTO trading_psychology (topic, insight, importance, last_updated)
            VALUES (?, ?, ?, ?)
        ''', (topic, insight, importance, datetime.now().strftime('%Y-%m-%d %H:%M')))
        self.conn.commit()
        return cur.lastrowid

    def get_psychology_insights(self, topic: str = None) -> List[Dict]:
        cur = self.conn.cursor()
        if topic:
            cur.execute('SELECT * FROM trading_psychology WHERE topic LIKE ? ORDER BY importance DESC',
                       (f'%{topic}%',))
        else:
            cur.execute('SELECT * FROM trading_psychology ORDER BY importance DESC')
        return [dict(r) for r in cur.fetchall()]

    # ─── Seed Initial Knowledge ──────────────────────────

    def seed_initial_knowledge(self):
        """播種初始知識"""
        cur = self.conn.cursor()

        # 檢查是否已有知識
        cur.execute('SELECT COUNT(*) as c FROM market_knowledge')
        if cur.fetchone()['c'] > 0:
            print("   知識庫已有資料，略過播種")
            return

        market_knowledge = [
            ('RSI', 'RSI<30 超賣區', 'RSI 低於 30 表示超賣，低接成功率高，但需確認法人買超', 0.75, 'Tina 歷史交易分析'),
            ('RSI', 'RSI>70 過熱區', 'RSI 超過 70 表示過熱，進場勝率低，建議等待回調', 0.80, 'Tina 歷史交易分析'),
            ('RSI', 'RSI 40-60 中性區', 'RSI 40-60 是中性區，此時 MA20 突破策略效果較好', 0.70, 'Tina 歷史交易分析'),
            ('Market_Mode', '多頭市場', 'MA20 > MA60 且價格在 MA20 上方，多頭格局持續', 0.85, '技術分析經典'),
            ('Market_Mode', '空頭市場', 'MA20 < MA60 且價格在 MA20 下方，反彈視為賣出機會', 0.85, '技術分析經典'),
            ('VIX', '高 VIX 警訊', 'VIX > 25 表示市場恐慌，應降低倉位等待回歸正常', 0.80, '宏觀分析'),
            ('VIX', '低 VIX 貪婪', 'VIX < 15 表示市場貪婪，長線可分批布局', 0.70, '宏觀分析'),
            ('Gap', '跳空上漲', '前一日缺口向上突破，若成交量放大且 RSI < 60，可跟進', 0.65, '缺口理論'),
            ('Gap', '跳空下跌', '前一日缺口向下跌破，若 RSI < 35 可分批接刀', 0.65, '缺口理論'),
            ('Sector', '科技股連動', '美股科技股強勢時，台灣科技供應鏈同步受益', 0.75, '宏觀觀察'),
        ]

        psychology_insights = [
            ('貪婪與恐懼', '市場過熱時（RSI>75）反而是危險信號，要敢於分批了結', 9),
            ('虧損攤平陷阱', '虧損時加碼攤平是最危險的行為，應果斷停損', 10),
            ('計畫與執行', '進場前先定好止損點，盘中勿改，是紀律的核心', 10),
            ('勝率與盈虧比', '不需要 100% 勝率，只要盈虧比 > 2:1 就能獲利', 8),
            ('等待時機', '7成時間觀望，3成時間行動，耐心等待關鍵進場點', 7),
            ('認錯勇氣', '發現錯誤立刻認錯，不合理化自己的判斷', 9),
            ('過度分析癱瘓', '數據太多反而無法決策，focus 在 3-5 個關鍵指標', 6),
            ('一致性交易', '每次進場邏輯要一致，不可因情緒改變策略', 8),
        ]

        for cat, topic, insight, conf, source in market_knowledge:
            cur.execute('''
                INSERT INTO market_knowledge (category, topic, insight, confidence, source, date_added)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (cat, topic, insight, conf, source, datetime.now().strftime('%Y-%m-%d %H:%M')))

        for topic, insight, imp in psychology_insights:
            cur.execute('''
                INSERT INTO trading_psychology (topic, insight, importance, last_updated)
                VALUES (?, ?, ?, ?)
            ''', (topic, insight, imp, datetime.now().strftime('%Y-%m-%d %H:%M')))

        self.conn.commit()
        print("   已播種初始知識庫")

    # ─── Reporting ──────────────────────────────────────

    def generate_knowledge_report(self) -> str:
        """產出知識更新報告"""
        cur = self.conn.cursor()

        cur.execute('SELECT COUNT(*) as c FROM market_knowledge')
        market_count = cur.fetchone()['c']

        cur.execute('SELECT COUNT(*) as c FROM strategy_knowledge')
        strategy_count = cur.fetchone()['c']

        cur.execute('SELECT COUNT(*) as c FROM trading_psychology')
        psych_count = cur.fetchone()['c']

        cur.execute('SELECT SUM(times_used) as s FROM market_knowledge')
        total_usage = cur.fetchone()['s'] or 0

        lines = [
            f"# 📚 Tina 知識更新報告",
            f"**{datetime.now().strftime('%Y-%m-%d %H:%M')}**",
            "",
            "## 📊 知識庫概覽",
            f"- 市場知識：{market_count} 條",
            f"- 策略知識：{strategy_count} 條",
            f"- 交易心理：{psych_count} 條",
            f"- 總使用次數：{total_usage} 次",
            "",
            "## 🧠 市場知識 Top5",
        ]

        cur.execute('''
            SELECT * FROM market_knowledge
            ORDER BY confidence DESC, times_used DESC
            LIMIT 5
        ''')
        for r in cur.fetchall():
            lines.append(f"- 【{r['category']}】{r['topic']}")
            lines.append(f"  {r['insight']}")

        lines += ["", "## 📈 交易心理要點", ""]
        cur.execute('SELECT * FROM trading_psychology ORDER BY importance DESC LIMIT 5')
        for r in cur.fetchall():
            lines.append(f"- 【{r['topic']}】{r['insight']}")

        return "\n".join(lines)

    def save_knowledge_update_report(self):
        """儲存知識更新報告"""
        REPORT_DIR.mkdir(exist_ok=True)
        date_str = datetime.now().strftime('%Y%m%d')
        report = self.generate_knowledge_report()
        path = REPORT_DIR / f'tina_knowledge_update_{date_str}.md'
        with open(path, 'w', encoding='utf-8') as f:
            f.write(report)
        return path

    def close(self):
        self.conn.close()


if __name__ == '__main__':
    km = TinaKnowledgeManager()
    print("📚 Tina 知識庫管理器...")
    print()

    # 播種初始知識
    print("🌱 初始化知識庫...")
    km.seed_initial_knowledge()

    # 產出報告
    print("📝 產出知識更新報告...")
    report = km.generate_knowledge_report()
    path = km.save_knowledge_update_report()
    print(f"   已儲存：{path}")
    print()
    print(report)
    print()
    print("✅ 完成")
    km.close()
