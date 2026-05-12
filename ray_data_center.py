# -*- coding: utf-8 -*-
"""
Ray Data Center - Tina Architecture Edition
Fixed for Windows SQLite: use isolation_level=None + explicit commit
"""

import sqlite3, json, os
from datetime import datetime
from contextlib import closing
from typing import Optional, List, Dict

DB_PATH = os.path.join(os.path.dirname(__file__), "ray_wisdom.db")


def _conn(db_path):
    """Get connection with autocommit on Windows for reliability"""
    c = sqlite3.connect(db_path, isolation_level=None)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA synchronous=NORMAL")
    return c


class RayDataCenter:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        self._init_db()

    def _init_db(self):
        with closing(_conn(self.db_path)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS signals_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    symbol TEXT NOT NULL,
                    source TEXT NOT NULL,
                    score REAL, sharpe_30d REAL, mdd_30d REAL, win_rate_30d REAL,
                    signal_tag TEXT,
                    approved BOOLEAN DEFAULT 0,
                    pushed BOOLEAN DEFAULT 0,
                    note TEXT
                )""")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS positions_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_date DATE NOT NULL, symbol TEXT NOT NULL,
                    entry_price REAL NOT NULL, shares INTEGER,
                    stop_loss REAL, target_price REAL,
                    status TEXT DEFAULT 'open',
                    close_date DATE, close_price REAL, close_reason TEXT,
                    pnl_pct REAL, rsi_entry REAL, note TEXT
                )""")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trades_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    symbol TEXT NOT NULL, action TEXT NOT NULL, price REAL NOT NULL,
                    shares INTEGER, amount REAL, strategy TEXT,
                    pnl_pct REAL, pnl_abs REAL, holding_days INTEGER,
                    close_reason TEXT, note TEXT
                )""")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS performance_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    log_date DATE UNIQUE NOT NULL,
                    portfolio_value REAL, daily_return_pct REAL,
                    weekly_return_pct REAL, monthly_return_pct REAL, ytd_return_pct REAL,
                    open_positions INTEGER, closed_today INTEGER, total_trades INTEGER,
                    win_rate_today REAL, best_trade_pct REAL, worst_trade_pct REAL, note TEXT
                )""")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS backtest_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    strategy_name TEXT, symbol TEXT, indicator TEXT,
                    params TEXT, sharpe_ratio REAL, max_drawdown REAL,
                    total_return REAL, win_rate REAL, avg_return REAL,
                    num_trades INTEGER, passed BOOLEAN, note TEXT
                )""")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sop_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    update_date DATE DEFAULT (date('now')),
                    version TEXT, content TEXT, changelog TEXT
                )""")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS wisdom_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    axiom_json TEXT NOT NULL,
                    reflection TEXT,
                    backtest_id INTEGER,
                    passed BOOLEAN,
                    model_used TEXT,
                    note TEXT
                )""")

    def _write(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute write SQL with auto-commit on Windows"""
        conn = _conn(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute(sql, params)
            conn.commit()
            return cur
        finally:
            conn.close()

    def _read(self, sql: str, params: tuple = ()) -> List[Dict]:
        """Execute read SQL"""
        conn = _conn(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.cursor()
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()

    # ── Signal Operations ───────────────────────────────────────────
    def log_signal(self, symbol: str, source: str, score: float,
                   sharpe: float = None, mdd: float = None, win_rate: float = None,
                   signal_tag: str = None, note: str = None) -> int:
        approved = 1 if (sharpe is not None and sharpe > 1.5 and mdd is not None and mdd < 0.15) else 0
        cur = self._write("""
            INSERT INTO signals_log
            (symbol, source, score, sharpe_30d, mdd_30d, win_rate_30d, signal_tag, approved, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (symbol, source, score, sharpe, mdd, win_rate, signal_tag, approved, note))
        return cur.lastrowid

    def get_unpushed_approved_signals(self, source: str = None, limit: int = 20) -> List[Dict]:
        sql = "SELECT * FROM signals_log WHERE approved=1 AND pushed=0"
        if source: sql += f" AND source='{source}'"
        sql += " ORDER BY sharpe_30d DESC LIMIT ?"
        return self._read(sql, (limit,))

    def mark_signals_pushed(self, ids: List[int]):
        if not ids: return
        placeholders = ",".join("?" * len(ids))
        self._write(f"UPDATE signals_log SET pushed=1 WHERE id IN ({placeholders})", tuple(ids))

    # ── Position Operations ─────────────────────────────────────────
    def open_position(self, symbol: str, entry_price: float, shares: int,
                       stop_loss: float = None, target: float = None,
                       rsi_entry: float = None, note: str = None) -> int:
        cur = self._write("""
            INSERT INTO positions_log (entry_date, symbol, entry_price, shares,
                stop_loss, target_price, rsi_entry, note)
            VALUES (date('now'), ?, ?, ?, ?, ?, ?, ?)""",
            (symbol, entry_price, shares, stop_loss, target, rsi_entry, note))
        return cur.lastrowid

    def close_position(self, symbol: str, close_price: float,
                        reason: str, pnl_pct: float = None) -> int:
        cur = self._write("""
            UPDATE positions_log SET status='closed', close_date=date('now'),
            close_price=?, close_reason=?, pnl_pct=?
            WHERE symbol=? AND status='open'
            ORDER BY entry_date DESC LIMIT 1""",
            (close_price, reason, pnl_pct, symbol))
        return cur.rowcount

    def get_open_positions(self) -> List[Dict]:
        return self._read("SELECT * FROM positions_log WHERE status='open' ORDER BY entry_date DESC")

    def get_position_by_symbol(self, symbol: str) -> Optional[Dict]:
        rows = self._read("SELECT * FROM positions_log WHERE symbol=? AND status='open' ORDER BY entry_date DESC LIMIT 1", (symbol,))
        return rows[0] if rows else None

    # ── Trade Operations ─────────────────────────────────────────────
    def log_trade(self, symbol: str, action: str, price: float,
                   shares: int = None, amount: float = None,
                   strategy: str = None, pnl_pct: float = None,
                   holding_days: int = None, close_reason: str = None,
                   note: str = None) -> int:
        cur = self._write("""
            INSERT INTO trades_log
            (symbol, action, price, shares, amount, strategy, pnl_pct, holding_days, close_reason, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (symbol, action, price, shares, amount, strategy, pnl_pct, holding_days, close_reason, note))
        return cur.lastrowid

    # ── Performance Operations ───────────────────────────────────────
    def log_performance(self, portfolio_value: float = None,
                         daily_return: float = None, open_positions: int = None,
                         note: str = None) -> int:
        conn = _conn(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute("""SELECT COUNT(*), AVG(pnl_pct) FROM trades_log
                           WHERE date(trade_date)=date('now') AND action IN ('SELL','EXIT')""")
            closed, avg_ret = cur.fetchone()
            cur.execute("""
                INSERT INTO performance_log
                (log_date, portfolio_value, daily_return_pct, open_positions, closed_today, win_rate_today, note)
                VALUES (date('now'), ?, ?, ?, ?, ?, ?)""",
                (portfolio_value, daily_return, open_positions, closed, avg_ret, note))
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def get_performance_summary(self, days: int = 30) -> Dict:
        rows = self._read(f"""SELECT * FROM performance_log
                               WHERE log_date >= date('now', '-{days} days')
                               ORDER BY log_date ASC""")
        if not rows: return {}
        total_return = sum(r.get('daily_return_pct', 0) or 0 for r in rows)
        wins = [r for r in rows if r.get('daily_return_pct', 0) > 0]
        return {
            'days': len(rows),
            'total_return_pct': round(total_return * 100, 2),
            'win_days': len(wins),
            'win_rate': round(len(wins)/len(rows)*100, 1) if rows else 0,
            'avg_return': round(total_return/len(rows)*100, 4) if rows else 0,
        }

    # ── Backtest Reports ────────────────────────────────────────────
    def log_backtest(self, strategy_name: str, symbol: str,
                      indicator: str, params: Dict,
                      sharpe: float, mdd: float, total_ret: float,
                      win_rate: float, avg_return: float,
                      num_trades: int, note: str = None) -> int:
        passed = 1 if (sharpe > 1.5 and mdd < 0.15) else 0
        cur = self._write("""
            INSERT INTO backtest_reports
            (strategy_name, symbol, indicator, params, sharpe_ratio, max_drawdown,
             total_return, win_rate, avg_return, num_trades, passed, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (strategy_name, symbol, indicator, json.dumps(params),
             sharpe, mdd, total_ret, win_rate, avg_return, num_trades, passed, note))
        return cur.lastrowid

    def get_recent_backtests(self, symbol: str = None, days: int = 30) -> List[Dict]:
        sql = "SELECT * FROM backtest_reports WHERE timestamp >= datetime('now', ?)"
        params = [f'-{days} days']
        if symbol: sql += f" AND symbol='{symbol}'"
        sql += " ORDER BY timestamp DESC LIMIT 50"
        return self._read(sql, params)

    def get_approved_backtests(self, limit: int = 20) -> List[Dict]:
        return self._read("SELECT * FROM backtest_reports WHERE passed=1 ORDER BY sharpe_ratio DESC LIMIT ?", (limit,))

    # ── Wisdom Logs ─────────────────────────────────────────────────
    def log_wisdom(self, axiom_json: str, reflection: str = None,
                   backtest_id: int = None, passed: bool = None,
                   model_used: str = None, note: str = None) -> int:
        cur = self._write("""
            INSERT INTO wisdom_logs
            (axiom_json, reflection, backtest_id, passed, model_used, note)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (axiom_json, reflection, backtest_id, passed, model_used, note))
        return cur.lastrowid

    def get_wisdom_logs(self, limit: int = 50) -> List[Dict]:
        return self._read("SELECT * FROM wisdom_logs ORDER BY timestamp DESC LIMIT ?", (limit,))

    def get_failed_wisdoms(self, limit: int = 20) -> List[Dict]:
        return self._read("SELECT * FROM wisdom_logs WHERE passed=0 ORDER BY timestamp DESC LIMIT ?", (limit,))

    # ── Query Helpers ────────────────────────────────────────────────
    def get_latest_signal(self, symbol: str, source: str = None) -> Optional[Dict]:
        sql = "SELECT * FROM signals_log WHERE symbol=?"
        params = [symbol]
        if source: sql += " AND source=?"
        sql += " ORDER BY timestamp DESC LIMIT 1"
        if source: params.append(source)
        rows = self._read(sql, params)
        return rows[0] if rows else None

    def get_signal_stats(self) -> Dict:
        rows = self._read("SELECT COUNT(*) total, SUM(approved) approved FROM signals_log")
        if rows: return {"total_signals": rows[0]['total'] or 0, "approved_signals": rows[0]['approved'] or 0}
        return {"total_signals": 0, "approved_signals": 0}


if __name__ == "__main__":
    db = RayDataCenter()
    print(f"[RayDataCenter] DB: {db.db_path}")
    stats = db.get_signal_stats()
    print(f"Signals: {stats['approved_signals']}/{stats['total_signals']} approved")
    sid = db.log_signal('AAPL', 'test', 5.0, 2.0, 0.10, 0.55, 'BUY', 'auto test')
    print(f"Inserted signal id={sid}")
    print(f"Stats after: {db.get_signal_stats()}")