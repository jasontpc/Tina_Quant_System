# -*- coding: utf-8 -*-
"""
Tina Paper Trading System — 模擬交易學習系統
在真實市場驗證新策略，累積經驗值（XP）
"""

import sqlite3
import json
import os
import sys
import yfinance as yf
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
DATA_DIR = BASE_DIR / 'data'
REPORT_DIR = BASE_DIR / 'reports'
XP_DB = DATA_DIR / 'tina_xp.db'

# 經驗值系統
XP_LEVELS = {
    '見習': 0,
    '初階': 100,
    '中階': 500,
    '進階': 1000,
    '高手': 5000,
    '大師': 10000,
}

XP_REWARDS = {
    'TRADE_WIN': 10,       # 交易獲利
    'TRADE_LOSS': -5,      # 交易虧損
    'TRADE_BREAK_EVEN': 2, # 平損益
    'PATTERN_FOUND': 20,   # 發現新模式
    'STRATEGY_ADJUSTED': 15,  # 策略調整成功
    'DAILY_ANALYSIS': 5,   # 每日認真分析
    'LESSON_LEARNED': 12,  # 從錯誤學習
    'CONSISTENT_WIN': 25,  # 連續獲利
}


class TinaPaperTrader:
    """模擬交易員 — 虛擬倉位驗證策略"""

    def __init__(self):
        self.conn = sqlite3.connect(str(XP_DB))
        self.conn.row_factory = sqlite3.Row
        self._init_db()
        self.xp = self._load_xp()
        self.level = self._calc_level(self.xp)
        self.stats = self._load_stats()

    def _init_db(self):
        cur = self.conn.cursor()
        cur.executescript('''
            CREATE TABLE IF NOT EXISTS paper_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                entry_date TEXT,
                entry_price REAL,
                quantity INTEGER DEFAULT 1000,
                strategy TEXT,
                entry_rsi REAL,
                entry_note TEXT,
                status TEXT DEFAULT 'OPEN',
                exit_date TEXT,
                exit_price REAL,
                pnl_pct REAL,
                outcome TEXT,
                lesson TEXT,
                closed_at TEXT,
                xp_earned INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS xp_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                event_type TEXT,
                xp_change INTEGER,
                xp_total INTEGER,
                note TEXT,
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS daily_analysis_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE,
                regime TEXT,
                opportunity_count INTEGER,
                risk_count INTEGER,
                confidence REAL,
                analysis_done INTEGER DEFAULT 0,
                xp_earned INTEGER DEFAULT 0,
                note TEXT,
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS patterns_discovered (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_name TEXT,
                pattern_type TEXT,
                description TEXT,
                first_found_date TEXT,
                times_validated INTEGER DEFAULT 1,
                success_rate REAL,
                xp_bonus INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS strategy_adjustments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT,
                old_weight REAL,
                new_weight REAL,
                reason TEXT,
                result TEXT,
                adjustment_date TEXT,
                validated INTEGER DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_paper_trades_status ON paper_trades(status);
            CREATE INDEX IF NOT EXISTS idx_xp_log_date ON xp_log(date);
        ''')
        self.conn.commit()

    # ─── XP & Level Management ─────────────────────────

    def _load_xp(self) -> int:
        cur = self.conn.cursor()
        cur.execute('SELECT xp_total FROM xp_log ORDER BY id DESC LIMIT 1')
        r = cur.fetchone()
        return r['xp_total'] if r else 0

    def _calc_level(self, xp: int) -> str:
        prev = '見習'
        for lvl, threshold in XP_LEVELS.items():
            if xp >= threshold:
                prev = lvl
            else:
                break
        return prev

    def _next_level_xp(self) -> Tuple[int, int]:
        levels = list(XP_LEVELS.items())
        for i, (lvl, threshold) in enumerate(levels):
            if self.xp < threshold:
                if i > 0:
                    prev_lvl, prev_thresh = levels[i-1]
                else:
                    prev_lvl, prev_thresh = '見習', 0
                return prev_thresh, threshold
        # 已滿級
        return XP_LEVELS['大師'], XP_LEVELS['大師']

    def award_xp(self, event_type: str, note: str = ""):
        """給予或扣除 XP"""
        if event_type not in XP_REWARDS:
            return
        change = XP_REWARDS[event_type]
        new_xp = max(0, self.xp + change)
        old_level = self.level

        cur = self.conn.cursor()
        cur.execute('''
            INSERT INTO xp_log (date, event_type, xp_change, xp_total, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (datetime.now().strftime('%Y-%m-%d'), event_type, change, new_xp, note,
              datetime.now().strftime('%Y-%m-%d %H:%M')))
        self.conn.commit()

        self.xp = new_xp
        self.level = self._calc_level(new_xp)
        self.stats = self._load_stats()

        if self.level != old_level:
            print(f"   🎉 等級提升：{old_level} → {self.level}")

    def _load_stats(self) -> Dict:
        cur = self.conn.cursor()
        stats = {}

        cur.execute("SELECT COUNT(*) as c FROM paper_trades WHERE outcome = 'WIN'")
        stats['wins'] = cur.fetchone()['c']

        cur.execute("SELECT COUNT(*) as c FROM paper_trades WHERE outcome = 'LOSS'")
        stats['losses'] = cur.fetchone()['c']

        cur.execute("SELECT COUNT(*) as c FROM paper_trades WHERE status = 'OPEN'")
        stats['open'] = cur.fetchone()['c']

        cur.execute("SELECT COUNT(*) as c FROM paper_trades")
        stats['total'] = cur.fetchone()['c']

        cur.execute("SELECT SUM(pnl_pct) as s FROM paper_trades WHERE pnl_pct IS NOT NULL")
        stats['total_pnl'] = cur.fetchone()['s'] or 0

        if stats['total'] > 0:
            stats['win_rate'] = stats['wins'] / stats['total']
        else:
            stats['win_rate'] = 0

        return stats

    # ─── Paper Trade Management ──────────────────────────

    def open_position(self, symbol: str, entry_price: float,
                      strategy: str, entry_date: str = None,
                      entry_rsi: float = None, quantity: int = 1000,
                      note: str = "") -> int:
        """開立模擬倉位"""
        if entry_date is None:
            entry_date = datetime.now().strftime('%Y-%m-%d')

        cur = self.conn.cursor()
        cur.execute('''
            INSERT INTO paper_trades (symbol, entry_date, entry_price, quantity,
                strategy, entry_rsi, entry_note, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'OPEN')
        ''', (symbol, entry_date, entry_price, quantity, strategy, entry_rsi, note))
        self.conn.commit()
        trade_id = cur.lastrowid
        print(f"   ✅ 開倉 #{trade_id}: {symbol} @ {entry_price}")
        return trade_id

    def close_position(self, trade_id: int, exit_price: float,
                       exit_date: str = None, exit_rsi: float = None,
                       lesson: str = "") -> Dict:
        """平倉模擬倉位"""
        if exit_date is None:
            exit_date = datetime.now().strftime('%Y-%m-%d')

        cur = self.conn.cursor()
        cur.execute('SELECT * FROM paper_trades WHERE id = ?', (trade_id,))
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

        xp_earned = XP_REWARDS.get(f'TRADE_{outcome}', 0)

        cur.execute('''
            UPDATE paper_trades SET
                status = 'CLOSED', exit_date = ?, exit_price = ?,
                pnl_pct = ?, hold_days = ?, exit_rsi = ?,
                outcome = ?, lesson = ?, closed_at = ?, xp_earned = ?
            WHERE id = ?
        ''', (exit_date, exit_price, pnl_pct, hold_days, exit_rsi,
              outcome, lesson, datetime.now().strftime('%Y-%m-%d %H:%M'),
              xp_earned, trade_id))
        self.conn.commit()

        self.award_xp(f'TRADE_{outcome}', f"{trade['symbol']} {outcome} {pnl_pct*100:+.2f}%")

        # 更新 stats
        self.stats = self._load_stats()

        return {
            'trade_id': trade_id,
            'symbol': trade['symbol'],
            'pnl_pct': round(pnl_pct, 4),
            'outcome': outcome,
            'hold_days': hold_days,
            'xp_earned': xp_earned
        }

    def sync_from_leo(self, trade_key: str, exit_price: float = None,
                       reason: str = None, pnl_pct: float = None,
                       outcome: str = None) -> Dict:
        """
        從 Leo trades 同步倉位資料到 TinaPaperTrader
        trade_key 格式：'TW:2382' 或 'US:NVDA'
        """
        # 解析市場和股票
        parts = trade_key.split(':', 1)
        sym = parts[1] if len(parts) > 1 else trade_key
        mkt = parts[0] if len(parts) > 1 else 'TW'
        full_sym = f"{mkt}:{sym}"

        cur = self.conn.cursor()

        # 檢查是否已有記錄
        cur.execute(
            "SELECT * FROM paper_trades WHERE symbol = ? AND status = 'OPEN' ORDER BY entry_date DESC LIMIT 1",
            (full_sym,)
        )
        existing = cur.fetchone()

        now_str = datetime.now().strftime('%Y-%m-%d')

        if existing:
            # 已有記錄 → 更新平倉
            trade = dict(existing)
            if exit_price:
                ep = trade['entry_price']
                actual_pnl_pct = pnl_pct if pnl_pct is not None else ((exit_price - ep) / ep if ep else 0)
                actual_outcome = outcome or ('WIN' if actual_pnl_pct > 0.005 else ('LOSS' if actual_pnl_pct < -0.005 else 'BREAK_EVEN'))
                hold_days = None
                if trade.get('entry_date'):
                    try:
                        ed = datetime.strptime(trade['entry_date'], '%Y-%m-%d')
                        hold_days = (datetime.now() - ed).days
                    except:
                        hold_days = None
                xp_earned = XP_REWARDS.get(f'TRADE_{actual_outcome}', 0)
                cur.execute('''
                    UPDATE paper_trades SET
                        status='CLOSED', exit_date=?, exit_price=?,
                        pnl_pct=?, hold_days=?, outcome=?, lesson=?, closed_at=?, xp_earned=?
                    WHERE id=?
                ''', (now_str, exit_price, actual_pnl_pct, hold_days,
                      actual_outcome, reason or '',
                      datetime.now().strftime('%Y-%m-%d %H:%M'), xp_earned,
                      trade['id']))
                self.conn.commit()
                self.award_xp(f'TRADE_{actual_outcome}', f"{sym} {actual_outcome} {actual_pnl_pct*100:+.2f}")
                self.stats = self._load_stats()
                return {'synced': True, 'action': 'closed', 'trade_id': trade['id'], 'outcome': actual_outcome}
        else:
            # 沒有記錄 → 不創建（Leo 的倉位由 Leo 自己管理）
            return {'synced': False, 'reason': 'no_open_trade_found'}

    def get_open_positions(self) -> List[Dict]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM paper_trades WHERE status = 'OPEN' ORDER BY entry_date DESC")
        return [dict(r) for r in cur.fetchall()]

    def get_closed_trades(self, limit: int = 20) -> List[Dict]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM paper_trades WHERE status = 'CLOSED' ORDER BY closed_at DESC LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]

    def update_open_positions_price(self) -> List[Dict]:
        """更新未平倉的 current price"""
        positions = self.get_open_positions()
        updated = []
        for pos in positions:
            try:
                ticker = yf.Ticker(pos['symbol'])
                hist = ticker.history(days=2)
                if len(hist) > 0:
                    current_price = float(hist['Close'].iloc[-1])
                    cur_pnl = (current_price - pos['entry_price']) / pos['entry_price']
                    cur.execute('UPDATE paper_trades SET entry_note = ? WHERE id = ?',
                               (f"current={current_price} pnl={cur_pnl*100:.2f}%", pos['id']))
                    self.conn.commit()
                    updated.append({
                        'id': pos['id'],
                        'symbol': pos['symbol'],
                        'entry': pos['entry_price'],
                        'current': round(current_price, 2),
                        'pnl_pct': round(cur_pnl, 4)
                    })
            except:
                pass
        return updated

    # ─── Pattern & Strategy Tracking ───────────────────

    def record_pattern(self, name: str, ptype: str, desc: str, success_rate: float = 0.0):
        """記錄發現的模式"""
        cur = self.conn.cursor()
        cur.execute('''
            INSERT INTO patterns_discovered (pattern_name, pattern_type, description,
                first_found_date, success_rate, xp_bonus)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, ptype, desc, datetime.now().strftime('%Y-%m-%d'),
              success_rate, XP_REWARDS['PATTERN_FOUND']))
        self.conn.commit()
        self.award_xp('PATTERN_FOUND', f"新模式：{name}")

    def record_strategy_adjustment(self, name: str, old_weight: float,
                                   new_weight: float, reason: str) -> int:
        """記錄策略權重調整"""
        cur = self.conn.cursor()
        cur.execute('''
            INSERT INTO strategy_adjustments (strategy_name, old_weight, new_weight,
                reason, adjustment_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, old_weight, new_weight, reason,
              datetime.now().strftime('%Y-%m-%d')))
        self.conn.commit()
        self.award_xp('STRATEGY_ADJUSTED', f"{name}: {old_weight}→{new_weight}")
        return cur.lastrowid

    def log_daily_analysis(self, regime: str, opp_count: int,
                            risk_count: int, confidence: float, note: str = ""):
        """記錄每日分析（領 XP）"""
        cur = self.conn.cursor()
        cur.execute('''
            INSERT OR REPLACE INTO daily_analysis_log
            (date, regime, opportunity_count, risk_count, confidence, analysis_done, xp_earned, note, created_at)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)
        ''', (datetime.now().strftime('%Y-%m-%d'), regime, opp_count, risk_count,
              confidence, XP_REWARDS['DAILY_ANALYSIS'], note,
              datetime.now().strftime('%Y-%m-%d %H:%M')))
        self.conn.commit()
        self.award_xp('DAILY_ANALYSIS', f"{regime} 格局分析")

    # ─── Reporting ──────────────────────────────────────

    def generate_xp_report(self) -> str:
        """產出 XP 等級報告"""
        current_thresh, next_thresh = self._next_level_xp()
        progress = (self.xp - current_thresh) / (next_thresh - current_thresh) * 100 \
                  if next_thresh > current_thresh else 100

        lines = [
            f"# ⭐ Tina XP 等級報告",
            f"**{datetime.now().strftime('%Y-%m-%d %H:%M')}**",
            "",
            "## 🏆 等級狀態",
            f"- **當前等級:** {self.level}",
            f"- **經驗值:** {self.xp} XP",
            f"- **下一級門檻:** {next_thresh} XP",
            f"- **升級進度:** {progress:.1f}%",
            f"- **距下一級:** {next_thresh - self.xp} XP",
            "",
            "## 📊 交易統計",
            f"- 總交易筆數：{self.stats.get('total', 0)}",
            f"- 勝利：{self.stats.get('wins', 0)} | 虧損：{self.stats.get('losses', 0)}",
            f"- 勝率：{self.stats.get('win_rate', 0)*100:.1f}%",
            f"- 總報酬：{self.stats.get('total_pnl', 0)*100:+.2f}%",
            f"- 未平倉：{self.stats.get('open', 0)} 筆",
            "",
            "## 📜 等級制度",
            "```",
        ]

        for lvl, thresh in XP_LEVELS.items():
            marker = "👉 " if self.level == lvl else "   "
            lines.append(f"{marker}{lvl}: {thresh} XP")

        lines += [
            "```",
            "",
            "## 🎖️ XP 獲取規則",
        ]

        for event, xp_val in XP_REWARDS.items():
            sign = '+' if xp_val > 0 else ''
            lines.append(f"- {event}: {sign}{xp_val}")

        return "\n".join(lines)

    def generate_paper_trade_report(self) -> str:
        """產出模擬交易報告"""
        closed = self.get_closed_trades(20)

        lines = [
            f"# 📊 Tina 模擬交易報告",
            f"**{datetime.now().strftime('%Y-%m-%d %H:%M')}**",
            "",
            "## 📈 未平倉",
        ]

        open_pos = self.get_open_positions()
        if open_pos:
            lines.append("| 股票 | 進場價 | 策略 | 進場日期 |")
            lines.append("|------|--------|------|----------|")
            for p in open_pos:
                lines.append(f"| {p['symbol']} | {p['entry_price']} | {p['strategy']} | {p['entry_date']} |")
        else:
            lines.append("目前無未平倉")

        lines += ["", "## 📉 最近平倉", ""]

        if closed:
            lines.append("| 股票 | 進場 | 出場 | 報酬% | 天數 | 結果 |")
            lines.append("|------|------|------|-------|------|------|")
            for t in closed:
                lines.append(f"| {t['symbol']} | {t['entry_price']} | {t['exit_price']} | "
                           f"{t['pnl_pct']*100:+.2f}% | {t.get('hold_days', '?')} | {t['outcome']} |")
        else:
            lines.append("尚無平倉記錄")

        return "\n".join(lines)

    def run_full_cycle(self) -> str:
        """執行完整 XP 結算"""
        print("📊 Tina 模擬交易系統結算...")
        print()

        # 更新未平倉報價
        print("📡 更新未平倉報價...")
        updated = self.update_open_positions_price()
        print(f"   更新了 {len(updated)} 筆未平倉")

        # 產出報告
        print("📝 產出 XP 等級報告...")
        xp_report = self.generate_xp_report()

        REPORT_DIR.mkdir(exist_ok=True)
        date_str = datetime.now().strftime('%Y%m%d')
        xp_path = REPORT_DIR / f'tina_xp_report_{date_str}.md'
        with open(xp_path, 'w', encoding='utf-8') as f:
            f.write(xp_report)
        print(f"   已儲存：{xp_path}")

        paper_path = REPORT_DIR / f'tina_paper_trade_report_{date_str}.md'
        with open(paper_path, 'w', encoding='utf-8') as f:
            f.write(self.generate_paper_trade_report())
        print(f"   已儲存：{paper_path}")

        print()
        print(xp_report)
        print()
        print("✅ 結算完成")
        return xp_report

    def close(self):
        self.conn.close()


if __name__ == '__main__':
    trader = TinaPaperTrader()
    trader.run_full_cycle()
    trader.close()
