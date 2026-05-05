"""
trade_journal.py
=================
記錄實際交易（進場/出场）、計算勝率/平均報酬，產出績效報告。
"""

import csv
import io
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_DIR  = Path(__file__).parent.parent.resolve()
DATA_DIR  = BASE_DIR / "data"
REPORT_DIR = BASE_DIR / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH  = DATA_DIR / "stock_tracking.db"
JOURNAL_CSV = REPORT_DIR / "trade_journal.csv"


# ═══════════════════════════════════════════════════════════════════════════
# 資料庫操作
# ═══════════════════════════════════════════════════════════════════════════

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def load_closed_trades():
    conn = get_db()
    rows = conn.execute("""
        SELECT date, stock_code, exit_type, price, pnl_pct, hold_days, reason
        FROM exit_signals ORDER BY date DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def load_open_positions():
    """讀取 stock_tracking 中已有 entry_price 的持仓。"""
    conn = get_db()
    rows = conn.execute("""
        SELECT stock_code, name, market, entry_price, current_price,
               stop_loss, take_profit, trailing_stop, last_updated
        FROM stock_tracking
        WHERE entry_price IS NOT NULL
          AND entry_price > 0
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════════════════
# 實際下單記錄介面（CLI）
# ═══════════════════════════════════════════════════════════════════════════

def record_entry(stock_code, entry_price, entry_date):
    """在 stock_tracking 中更新進場價。"""
    conn = get_db()
    conn.execute("""
        UPDATE stock_tracking
        SET entry_price = ?, last_updated = ?
        WHERE stock_code = ?
    """, (entry_price, datetime.now().strftime("%Y-%m-%d %H:%M"), stock_code))
    conn.commit()
    conn.close()
    print(f"✅ 進場記錄：[{stock_code}] @ {entry_price} ({entry_date})")


def record_exit(stock_code, exit_price, exit_date, reason):
    """記錄出场，更新 exit_signals，回測 PnL。"""
    conn = get_db()

    # 找持仓
    row = conn.execute("""
        SELECT name, market, entry_price, last_updated
        FROM stock_tracking WHERE stock_code = ?
    """, (stock_code,)).fetchone()

    if not row or not row["entry_price"]:
        conn.close()
        print(f"❌ [{stock_code}] 找不到進場記錄")
        return

    entry_price = row["entry_price"]
    pnl_pct     = round((exit_price - entry_price) / entry_price * 100, 2)

    try:
        last_upd   = datetime.strptime(row["last_updated"], "%Y-%m-%d %H:%M")
        exit_dt    = datetime.strptime(exit_date, "%Y-%m-%d")
        hold_days  = max(1, (exit_dt - last_upd).days)
    except Exception:
        hold_days = None

    conn.execute("""
        INSERT INTO exit_signals
        (date, stock_code, exit_type, price, pnl_pct, hold_days, reason)
        VALUES (?,?,?,?,?,?,?)
    """, (exit_date, stock_code, reason, exit_price, pnl_pct, hold_days, reason))

    # 清空 entry_price
    conn.execute("""
        UPDATE stock_tracking SET entry_price = NULL WHERE stock_code = ?
    """, (stock_code,))

    conn.commit()
    conn.close()
    print(f"✅ 出場記錄：[{stock_code}] @ {exit_price} ({exit_date})  原因={reason}  PnL={pnl_pct}%")


# ═══════════════════════════════════════════════════════════════════════════
# 績效統計
# ═══════════════════════════════════════════════════════════════════════════

def calc_stats(closed):
    if not closed:
        return {}

    total   = len(closed)
    wins    = [t for t in closed if t.get("pnl_pct", 0) > 0]
    losses  = [t for t in closed if t.get("pnl_pct", 0) <= 0]

    win_rate = round(len(wins) / total * 100, 1)
    avg_pct  = round(sum(t["pnl_pct"] for t in closed) / total, 2)
    avg_win  = round(sum(t["pnl_pct"] for t in wins) / len(wins), 2) if wins else 0
    avg_loss = round(sum(t["pnl_pct"] for t in losses) / len(losses), 2) if losses else 0
    max_win  = round(max(t["pnl_pct"] for t in closed), 2)
    max_loss = round(min(t["pnl_pct"] for t in closed), 2)
    total_pnl = round(sum(t["pnl_pct"] for t in closed), 2)

    holds = [t for t in closed if t.get("hold_days")]
    avg_hold = round(sum(t["hold_days"] for t in holds) / len(holds), 1) if holds else 0

    # 按市場
    market_groups = {}
    for t in closed:
        m = t.get("market", "?")
        if m not in market_groups:
            market_groups[m] = {"market": m, "trades": 0, "wins": 0, "total_pct": 0}
        g = market_groups[m]
        g["trades"]    += 1
        g["wins"]      += 1 if t["pnl_pct"] > 0 else 0
        g["total_pct"] += t["pnl_pct"]
    for g in market_groups.values():
        g["win_rate"] = round(g["wins"] / g["trades"] * 100, 1)
        g["avg_pct"]   = round(g["total_pct"] / g["trades"], 2)

    # 按 exit_type
    reason_groups = {}
    for t in closed:
        r = t.get("reason", "unknown")
        if r not in reason_groups:
            reason_groups[r] = {"reason": r, "trades": 0, "wins": 0, "total_pct": 0}
        g = reason_groups[r]
        g["trades"]    += 1
        g["wins"]      += 1 if t["pnl_pct"] > 0 else 0
        g["total_pct"] += t["pnl_pct"]
    for g in reason_groups.values():
        g["win_rate"] = round(g["wins"] / g["trades"] * 100, 1)
        g["avg_pct"]   = round(g["total_pct"] / g["trades"], 2)

    return {
        "total": total, "win_rate": win_rate, "avg_pct": avg_pct,
        "avg_win": avg_win, "avg_loss": avg_loss,
        "max_win": max_win, "max_loss": max_loss,
        "total_pnl": total_pnl, "avg_hold": avg_hold,
        "market_groups": sorted(market_groups.values(), key=lambda x: x["total_pct"], reverse=True),
        "reason_groups": sorted(reason_groups.values(), key=lambda x: x["total_pct"], reverse=True),
    }


def make_report(closed, stats, open_positions):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    date_str = datetime.now().strftime("%Y-%m-%d")

    lines = [
        f"# 📓 交易日誌 & 績效報告",
        f"**{now_str}**\n",
    ]

    # ── 持倉 ──
    if open_positions:
        lines += [
            f"## 💼 目前持倉（共 {len(open_positions)} 檔）\n",
            "| 代碼 | 名稱 | 進場價 | 現價 | 停損 | 停利 | 移動停損 |",
            "|------|------|--------|------|------|------|----------|",
        ]
        for p in open_positions:
            lines.append(
                f"| {p['stock_code']} | {p.get('name','')} | "
                f"{p['entry_price']} | {p.get('current_price','')} | "
                f"{p.get('stop_loss','')} | {p.get('take_profit','')} | "
                f"{p.get('trailing_stop','')} |"
            )
        lines.append("")

    # ── 整體統計 ──
    lines += [
        f"## 📊 整體表現（已结束 {stats.get('total', 0)} 筆）\n",
        f"- 勝率：{stats.get('win_rate', 0)}%",
        f"- 平均報酬：{stats.get('avg_pct', 0)}%",
        f"- 平均獲利：{stats.get('avg_win', 0)}%  / 平均虧損：{stats.get('avg_loss', 0)}%",
        f"- 最大單筆：+{stats.get('max_win', 0)}%  /  -{stats.get('max_loss', 0)}%",
        f"- 累計報酬：{stats.get('total_pnl', 0)}%",
        f"- 平均持有：{stats.get('avg_hold', 0)} 天\n",
    ]

    # ── 依市場 ──
    if stats.get("market_groups"):
        lines += [
            f"### 依市場\n",
            "| 市場 | 交易次數 | 勝率 | 平均報酬 |",
            "|------|----------|------|----------|",
        ]
        for g in stats["market_groups"]:
            lines.append(f"| {g['market']} | {g['trades']} | {g['win_rate']}% | {g['avg_pct']}% |")
        lines.append("")

    # ── 依出场原因 ──
    if stats.get("reason_groups"):
        lines += [
            f"### 依出场原因\n",
            "| 原因 | 交易次數 | 勝率 | 平均報酬 |",
            "|------|----------|------|----------|",
        ]
        for g in stats["reason_groups"]:
            lines.append(f"| {g['reason']} | {g['trades']} | {g['win_rate']}% | {g['avg_pct']}% |")
        lines.append("")

    # ── 出場明細 ──
    if closed:
        lines += [
            f"### 出場明細（共 {len(closed)} 筆）\n",
            "| 日期 | 代碼 | 出場價 | PnL% | 持有天 | 原因 |",
            "|------|------|--------|------|--------|------|",
        ]
        for t in closed[-30:]:
            lines.append(
                f"| {t.get('date','')} | {t.get('stock_code','')} | "
                f"{t.get('price','')} | {t.get('pnl_pct','')}% | "
                f"{t.get('hold_days','')} | {t.get('reason','')} |"
            )

    return "\n".join(lines)


def export_journal_csv(closed):
    cols = ["date","stock_code","exit_type","price","pnl_pct","hold_days","reason"]
    with open(JOURNAL_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(closed)
    print(f"📄 Journal CSV → {JOURNAL_CSV}")


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="交易日誌")
    parser.add_argument("--entry",  nargs=3, metavar=("STOCK","PRICE","DATE"), help="記錄進場")
    parser.add_argument("--exit",   nargs=4, metavar=("STOCK","PRICE","DATE","REASON"), help="記錄出场")
    parser.add_argument("--report", action="store_true", help="產出績效報告")
    args = parser.parse_args()

    if args.entry:
        stock_code, price, date = args.entry
        record_entry(stock_code, float(price), date)

    elif args.exit:
        stock_code, price, date, reason = args.exit
        record_exit(stock_code, float(price), date, reason)

    elif args.report:
        closed = load_closed_trades()
        open_pos = load_open_positions()
        stats    = calc_stats(closed)
        if not stats:
            print("尚無已关闭的交易記錄。")
            return
        export_journal_csv(closed)
        md = make_report(closed, stats, open_pos)
        date_str  = datetime.now().strftime("%Y-%m-%d")
        rpt_path  = REPORT_DIR / f"stock_trading_journal_{date_str}.md"
        with open(rpt_path, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"📄 報告 → {rpt_path}\n")
        print(md)

    else:
        # 概覽
        closed = load_closed_trades()
        stats  = calc_stats(closed)
        print("═══ 交易概覽 ═══")
        print(f"已关闭：{stats.get('total', 0)} 筆  勝率：{stats.get('win_rate', 0)}%  "
              f"累計：{stats.get('total_pnl', 0)}%")
        open_pos = load_open_positions()
        print(f"持倉中：{len(open_pos)} 檔")


if __name__ == "__main__":
    main()