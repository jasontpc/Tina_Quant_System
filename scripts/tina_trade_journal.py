# -*- coding: utf-8 -*-
"""
Tina Trade Journal — 交易日記系統
記錄每筆進場/出場，自動計算勝率，產出績效報告
"""

import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
DATA_DIR = BASE_DIR / 'data'
REPORT_DIR = BASE_DIR / 'reports'
DB_PATH = DATA_DIR / 'tina_learning.db'


class TinaTradeJournal:
    """交易日記"""

    def __init__(self):
        self.conn = sqlite3.connect(str(DB_PATH))
        self.conn.row_factory = sqlite3.Row

    def add_entry(self, stock: str, entry_date: str, entry_price: float,
                  strategy: str, entry_rsi: float = None,
                  reason: str = "", tags: str = "") -> int:
        """新增進場記錄"""
        cur = self.conn.cursor()
        cur.execute('''
            INSERT INTO trades (stock, entry_date, entry_price, strategy_used, entry_rsi, tags, lesson_learned)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (stock, entry_date, entry_price, strategy, entry_rsi, tags, reason))
        self.conn.commit()
        return cur.lastrowid

    def close_entry(self, trade_id: int, exit_date: str, exit_price: float,
                    exit_rsi: float = None, lesson: str = "") -> dict:
        """平倉記錄"""
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM trades WHERE id = ?', (trade_id,))
        trade = dict(cur.fetchone())
        if not trade:
            return {'error': 'Trade not found'}

        pnl_pct = (exit_price - trade['entry_price']) / trade['entry_price']
        outcome = 'WIN' if pnl_pct > 0.005 else ('LOSS' if pnl_pct < -0.005 else 'BREAK_EVEN')

        hold_days = None
        if trade['entry_date']:
            try:
                ed = datetime.strptime(trade['entry_date'], '%Y-%m-%d')
                xd = datetime.strptime(exit_date, '%Y-%m-%d')
                hold_days = (xd - ed).days
            except:
                hold_days = None

        cur.execute('''
            UPDATE trades SET
                exit_date = ?, exit_price = ?, pnl_pct = ?,
                hold_days = ?, exit_rsi = ?, outcome = ?, lesson_learned = ?
            WHERE id = ?
        ''', (exit_date, exit_price, pnl_pct, hold_days, exit_rsi, outcome, lesson, trade_id))
        self.conn.commit()
        return {'trade_id': trade_id, 'stock': trade['stock'], 'pnl_pct': pnl_pct, 'outcome': outcome}

    def get_stats(self, days: int = 30) -> dict:
        """計算統計數據"""
        cur = self.conn.cursor()
        since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        cur.execute('''
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN outcome = 'LOSS' THEN 1 ELSE 0 END) as losses,
                AVG(CASE WHEN outcome = 'WIN' THEN pnl_pct END) as avg_win,
                AVG(CASE WHEN outcome = 'LOSS' THEN pnl_pct END) as avg_loss,
                AVG(pnl_pct) as avg_all,
                SUM(pnl_pct) as total_pnl
            FROM trades
            WHERE outcome IS NOT NULL AND exit_date >= ?
        ''', (since,))
        row = cur.fetchone()

        total = row['total'] or 0
        wins = row['wins'] or 0
        return {
            'period_days': days,
            'total_trades': total,
            'wins': wins,
            'losses': row['losses'] or 0,
            'win_rate': wins / total if total > 0 else 0,
            'avg_win_pct': row['avg_win'] or 0,
            'avg_loss_pct': row['avg_loss'] or 0,
            'avg_pnl': row['avg_all'] or 0,
            'total_pnl': row['total_pnl'] or 0
        }

    def get_strategy_stats(self) -> list:
        """計算策略維度統計"""
        cur = self.conn.cursor()
        cur.execute('''
            SELECT strategy_used as strategy,
                COUNT(*) as total,
                SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
                AVG(CASE WHEN outcome = 'WIN' THEN pnl_pct END) as avg_win,
                AVG(CASE WHEN outcome = 'LOSS' THEN pnl_pct END) as avg_loss,
                AVG(pnl_pct) as avg_pnl
            FROM trades
            WHERE outcome IS NOT NULL AND strategy_used IS NOT NULL
            GROUP BY strategy_used
            ORDER BY avg_pnl DESC
        ''')
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            r['win_rate'] = r['wins'] / r['total'] if r['total'] > 0 else 0
        return rows

    def generate_trade_log(self, days: int = 7) -> str:
        """產出交易記錄 Markdown"""
        cur = self.conn.cursor()
        since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        cur.execute('''
            SELECT * FROM trades
            WHERE exit_date >= ? OR entry_date >= ?
            ORDER BY entry_date DESC
        ''', (since, since))
        trades = [dict(r) for r in cur.fetchall()]

        stats = self.get_stats(days)

        lines = [
            f"# 📔 Tina 交易記錄",
            f"**統計區間：過去 {days} 天**",
            f"**生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M')}**",
            "",
            "## 📊 績效總結",
            f"- 交易筆數：{stats['total_trades']}",
            f"- 勝率：{stats['win_rate']*100:.1f}%",
            f"- 平均獲利：{stats['avg_win_pct']*100:.2f}%" if stats['avg_win_pct'] else "- 平均獲利：N/A",
            f"- 平均虧損：{stats['avg_loss_pct']*100:.2f}%" if stats['avg_loss_pct'] else "- 平均虧損：N/A",
            f"- 總報酬：{stats['total_pnl']*100:.2f}%",
            "",
            "## 📋 交易明細",
            ""
        ]

        if not trades:
            lines.append("_暫無交易記錄_")
        else:
            for t in trades:
                emoji = "🟢" if t['outcome'] == 'WIN' else ("🔴" if t['outcome'] == 'LOSS' else "⚪")
                hold = t.get('hold_days', '?') or '?'
                pnl = t['pnl_pct'] * 100 if t['pnl_pct'] else 0
                entry_rsi = f"RSI {t['entry_rsi']:.0f}" if t.get('entry_rsi') else ""
                exit_rsi = f"RSI {t['exit_rsi']:.0f}" if t.get('exit_rsi') else ""

                lines.append(f"### {emoji} {t['stock']}")
                lines.append(f"- 進場：{t['entry_date']} @ {t['entry_price']} ({entry_rsi})")
                if t.get('exit_date'):
                    lines.append(f"- 出場：{t['exit_date']} @ {t['exit_price']} ({exit_rsi})")
                    lines.append(f"- 結果：{t['outcome']} {pnl:+.2f}%（持有 {hold} 天）")
                else:
                    lines.append(f"- 持倉中（已 {hold} 天）")
                if t.get('strategy_used'):
                    lines.append(f"- 策略：{t['strategy_used']}")
                if t.get('lesson_learned'):
                    lines.append(f"- Lesson：{t['lesson_learned']}")
                if t.get('tags'):
                    lines.append(f"- 標籤：{t['tags']}")
                lines.append("")

        report = "\n".join(lines)

        REPORT_DIR.mkdir(exist_ok=True)
        path = REPORT_DIR / f"tina_trade_log_{datetime.now().strftime('%Y%m%d')}.md"
        with open(path, 'w', encoding='utf-8') as f:
            f.write(report)

        return report

    def generate_weekly_report(self) -> str:
        """產出每週回顧報告"""
        # 這週是第幾週
        today = datetime.now()
        week_num = today.isocalendar()[1]
        year = today.year

        stats_7 = self.get_stats(7)
        stats_30 = self.get_stats(30)
        strategy_stats = self.get_strategy_stats()

        lines = [
            f"# 📈 Tina 每週回顧 {year}-W{week_num:02d}",
            f"**生成時間：{today.strftime('%Y-%m-%d %H:%M')}**",
            "",
            "## 📊 績效總結",
            "",
            "### 本週（7天）",
            f"- 交易筆數：{stats_7['total_trades']}",
            f"- 勝率：{stats_7['win_rate']*100:.1f}%",
            f"- 總報酬：{stats_7['total_pnl']*100:.2f}%",
            "",
            "### 本月（30天）",
            f"- 交易筆數：{stats_30['total_trades']}",
            f"- 勝率：{stats_30['win_rate']*100:.1f}%",
            f"- 總報酬：{stats_30['total_pnl']*100:.2f}%",
            "",
            "## 🎯 策略表現",
            ""
        ]

        if strategy_stats:
            lines.append("| 策略 | 筆數 | 勝率 | 平均獲利 | 平均虧損 | 備註 |")
            lines.append("|------|------|------|----------|----------|------|")
            for s in strategy_stats:
                wr = f"{s['win_rate']*100:.0f}%" if s.get('win_rate') else "N/A"
                aw = f"{s['avg_win']*100:.1f}%" if s.get('avg_win') else "N/A"
                al = f"{s['avg_loss']*100:.1f}%" if s.get('avg_loss') else "N/A"
                note = "✅ 優秀" if s['win_rate'] >= 0.6 else ("⚠️ 需檢討" if s['win_rate'] < 0.45 else "➡️ 持平")
                lines.append(f"| {s['strategy']} | {s['total']} | {wr} | {aw} | {al} | {note} |")
        else:
            lines.append("_暫無策略數據_")

        lines.append("")
        lines.append("## 💡 本週學習")
        lines.append("")

        # 讀取本週的 learning_log
        cur = self.conn.cursor()
        week_start = (today - timedelta(days=7)).strftime('%Y-%m-%d')
        cur.execute('''
            SELECT * FROM learning_log
            WHERE date >= ? AND event_type IN ('TRADE_REVIEW', 'STRATEGY_UPDATE')
            ORDER BY date DESC LIMIT 10
        ''', (week_start,))
        logs = [dict(r) for r in cur.fetchall()]

        if logs:
            for log in logs:
                lines.append(f"- [{log['event_type']}] {log['content']}")
        else:
            lines.append("_本週無新的學習記錄_")

        lines.append("")
        lines.append("## 🔧 下週策略調整")
        lines.append("")
        lines.append("1. 持續監控勝率低於 45% 的策略")
        lines.append("2. 記錄每筆交易的 lesson learned")
        lines.append("3. 根據市場模式調整進場條件")

        report = "\n".join(lines)

        REPORT_DIR.mkdir(exist_ok=True)
        path = REPORT_DIR / f"tina_weekly_review_{today.strftime('%Y%m%d')}.md"
        with open(path, 'w', encoding='utf-8') as f:
            f.write(report)

        return report

    def close(self):
        self.conn.close()


if __name__ == '__main__':
    journal = TinaTradeJournal()
    print("📔 Tina Trade Journal 啟動...")
    print()

    print("📝 產出交易記錄...")
    log = journal.generate_trade_log(days=7)
    print(log[:1000])
    print("...")
    print()

    print("📈 產出每週回顧...")
    report = journal.generate_weekly_report()
    print(report[:1000])
    print("...")
    print()

    print("✅ 完成")
    journal.close()