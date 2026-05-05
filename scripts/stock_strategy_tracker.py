"""
stock_strategy_tracker.py
===========================
追蹤所有個股策略的表現，記錄進場/出场、計算報酬。
產出 stock_strategy_performance.csv。
"""

import csv
import json
import os
import io
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Windows cp950 UTF-8 fix
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_DIR   = Path(__file__).parent.parent.resolve()
CONFIG_DIR = BASE_DIR / "configs" / "stock_strategies"
DATA_DIR   = BASE_DIR / "data"   / "stock_strategies"
REPORT_DIR = BASE_DIR / "reports"

REPORT_DIR.mkdir(parents=True, exist_ok=True)

PERF_CSV  = REPORT_DIR / "stock_strategy_performance.csv"
TRADE_LOG = DATA_DIR   / "stock_strategy_trades.json"


# ═══════════════════════════════════════════════════════════════════════════
# 交易記錄管理
# ═══════════════════════════════════════════════════════════════════════════

def load_trades():
    if not TRADE_LOG.exists():
        return []
    try:
        with open(TRADE_LOG, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_trades(trades):
    with open(TRADE_LOG, "w", encoding="utf-8") as f:
        json.dump(trades, f, ensure_ascii=False, indent=2)


def add_trade(stock_id, entry_price, entry_date, strategy, exit_price=None, exit_date=None, reason=None, notes=""):
    """新增一筆進場記錄（尚未出场時 exit_* 為 None）。"""
    trades = load_trades()

    # 避免重複進場（相同股票有未出场倉位）
    open_pos = [t for t in trades if t["stock"] == stock_id and t.get("exit_price") is None]
    if open_pos:
        return None, f"[{stock_id}] 已有未出场倉位"

    trade = {
        "trade_id":    f"{stock_id}_{entry_date.replace('-','')}_{len(trades)+1}",
        "stock":       stock_id,
        "name":        strategy.get("name", stock_id),
        "market":      strategy.get("market", "TW"),
        "type":        strategy.get("type", "unknown"),
        "team":        strategy.get("team", "Nana"),
        "entry_price": entry_price,
        "entry_date":  entry_date,
        "exit_price":  exit_price,
        "exit_date":   exit_date,
        "reason":      reason,   # stop_loss / take_profit / max_hold / bearish_ma / manual
        "pnl_pct":     None,
        "pnl_abs":     None,
        "hold_days":   None,
        "notes":       notes,
        "created_at":  datetime.now().strftime("%Y-%m-%d %H:%M"),
        "updated_at":  datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    trades.append(trade)
    save_trades(trades)
    return trade, None


def close_trade(stock_id, exit_price, exit_date, reason, notes=""):
    """關閉倉位，計算報酬。"""
    trades = load_trades()
    # 找未出场且 stock 符合的最近一筆
    open_trades = [t for t in trades if t["stock"] == stock_id and t.get("exit_price") is None]
    if not open_trades:
        return None, f"[{stock_id}] 找不到未出场倉位"

    t = open_trades[-1]  # 應該只有一筆
    t["exit_price"] = exit_price
    t["exit_date"]  = exit_date
    t["reason"]     = reason
    t["notes"]     += f" {notes}" if notes else ""
    t["pnl_pct"]    = round((exit_price - t["entry_price"]) / t["entry_price"] * 100, 2)
    t["pnl_abs"]    = round(exit_price - t["entry_price"], 2)
    try:
        ed = datetime.strptime(t["entry_date"], "%Y-%m-%d")
        xd = datetime.strptime(exit_date, "%Y-%m-%d")
        t["hold_days"] = (xd - ed).days
    except Exception:
        t["hold_days"] = None
    t["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    save_trades(trades)
    return t, None


# ═══════════════════════════════════════════════════════════════════════════
# 績效計算
# ═══════════════════════════════════════════════════════════════════════════

def calc_performance():
    """計算整體策略績效，回傳 DataFrame-style dict list。"""
    trades = load_trades()
    if not trades:
        return [], {}

    closed = [t for t in trades if t.get("exit_price") is not None]

    # 整體統計
    total_trades   = len(closed)
    win_trades     = [t for t in closed if t.get("pnl_pct", 0) > 0]
    loss_trades    = [t for t in closed if t.get("pnl_pct", 0) <= 0]
    win_rate       = len(win_trades) / total_trades * 100 if total_trades > 0 else 0
    avg_pct        = sum(t.get("pnl_pct", 0) for t in closed) / total_trades if total_trades > 0 else 0
    avg_win        = sum(t.get("pnl_pct", 0) for t in win_trades) / len(win_trades) if win_trades else 0
    avg_loss       = sum(t.get("pnl_pct", 0) for t in loss_trades) / len(loss_trades) if loss_trades else 0
    max_win        = max((t.get("pnl_pct", 0) for t in closed), default=0)
    max_loss       = min((t.get("pnl_pct", 0) for t in closed), default=0)
    total_pnl      = sum(t.get("pnl_pct", 0) for t in closed)
    avg_hold       = sum(t.get("hold_days", 0) for t in closed) / total_trades if total_trades > 0 else 0

    summary = {
        "total_trades": total_trades,
        "win_trades":   len(win_trades),
        "loss_trades":  len(loss_trades),
        "win_rate":     round(win_rate, 1),
        "avg_pct":      round(avg_pct, 2),
        "avg_win":      round(avg_win, 2),
        "avg_loss":     round(avg_loss, 2),
        "max_win":      round(max_win, 2),
        "max_loss":     round(max_loss, 2),
        "total_pnl":    round(total_pnl, 2),
        "avg_hold_days":round(avg_hold, 1),
    }

    # 按股票分組
    stock_groups = {}
    for t in closed:
        s = t["stock"]
        if s not in stock_groups:
            stock_groups[s] = {
                "stock": s, "name": t.get("name", s),
                "market": t.get("market", "?"), "type": t.get("type", "?"),
                "trades": 0, "wins": 0, "win_rate": 0,
                "avg_pct": 0, "total_pnl": 0, "avg_hold": 0,
            }
        g = stock_groups[s]
        g["trades"]  += 1
        g["wins"]    += 1 if t.get("pnl_pct", 0) > 0 else 0
        g["avg_pct"] = (g["avg_pct"] * (g["trades"]-1) + t.get("pnl_pct", 0)) / g["trades"]
        g["total_pnl"] += t.get("pnl_pct", 0)
        hd = t.get("hold_days") or 0
        g["avg_hold"] = (g["avg_hold"] * (g["trades"]-1) + hd) / g["trades"]

    for g in stock_groups.values():
        g["win_rate"] = round(g["wins"] / g["trades"] * 100, 1) if g["trades"] > 0 else 0
        g["avg_pct"]  = round(g["avg_pct"], 2)
        g["avg_hold"] = round(g["avg_hold"], 1)

    # 按市場分組
    market_groups = {}
    for t in closed:
        m = t.get("market", "?")
        if m not in market_groups:
            market_groups[m] = {"market": m, "trades": 0, "wins": 0, "win_rate": 0, "avg_pct": 0, "total_pnl": 0}
        g = market_groups[m]
        g["trades"]  += 1
        g["wins"]    += 1 if t.get("pnl_pct", 0) > 0 else 0
        g["avg_pct"] = (g["avg_pct"] * (g["trades"]-1) + t.get("pnl_pct", 0)) / g["trades"]
        g["total_pnl"] += t.get("pnl_pct", 0)
    for g in market_groups.values():
        g["win_rate"] = round(g["wins"] / g["trades"] * 100, 1) if g["trades"] > 0 else 0
        g["avg_pct"]  = round(g["avg_pct"], 2)

    return closed, {
        "summary":    summary,
        "by_stock":   list(stock_groups.values()),
        "by_market":  list(market_groups.values()),
    }


# ═══════════════════════════════════════════════════════════════════════════
# CSV 匯出
# ═══════════════════════════════════════════════════════════════════════════

CSV_COLS = [
    "trade_id","stock","name","market","type","team",
    "entry_date","entry_price","exit_date","exit_price",
    "reason","pnl_pct","pnl_abs","hold_days","notes","created_at","updated_at",
]

def export_csv(trades):
    """將交易記錄匯出成 CSV."""
    rows = []
    for t in trades:
        row = {col: t.get(col, "") for col in CSV_COLS}
        rows.append(row)

    with open(PERF_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLS)
        writer.writeheader()
        writer.writerows(rows)


# ═══════════════════════════════════════════════════════════════════════════
# 績效報告（Markdown）
# ═══════════════════════════════════════════════════════════════════════════

def make_performance_report(closed, stats):
    lines = []
    lines.append(f"# 📈 個股策略績效報告")
    lines.append(f"**{datetime.now().strftime('%Y-%m-%d %H:%M')}**\n")

    s = stats.get("summary", {})
    lines.append(f"## 整體表現\n")
    lines.append(f"- 總交易次數：{s.get('total_trades',0)}")
    lines.append(f"- 勝率：{s.get('win_rate',0)}%")
    lines.append(f"- 平均報酬：{s.get('avg_pct',0)}%")
    lines.append(f"- 平均獲利：{s.get('avg_win',0)}%  / 平均虧損：{s.get('avg_loss',0)}%")
    lines.append(f"- 最大單筆獲利：{s.get('max_win',0)}%  最大單筆虧損：{s.get('max_loss',0)}%")
    lines.append(f"- 累計報酬：{s.get('total_pnl',0)}%")
    lines.append(f"- 平均持有天數：{s.get('avg_hold_days',0)}天\n")

    # 依市場
    lines.append(f"## 依市場\n")
    lines.append(f"| 市場 | 交易次數 | 勝率 | 平均報酬 |")
    lines.append(f"|------|----------|------|----------|")
    for g in stats.get("by_market", []):
        lines.append(f"| {g['market']} | {g['trades']} | {g['win_rate']}% | {g['avg_pct']}% |")
    lines.append("")

    # 依股票
    lines.append(f"## 依股票\n")
    lines.append(f"| 代碼 | 名稱 | 市場 | 類型 | 交易次數 | 勝率 | 平均報酬 | 累計報酬 |")
    lines.append(f"|------|------|------|------|----------|------|----------|----------|")
    for g in sorted(stats.get("by_stock", []), key=lambda x: x["total_pnl"], reverse=True):
        lines.append(
            f"| {g['stock']} | {g['name']} | {g['market']} | {g['type']} | "
            f"{g['trades']} | {g['win_rate']}% | {g['avg_pct']}% | {g['total_pnl']}% |"
        )
    lines.append("")

    # 交易明細
    if closed:
        lines.append(f"## 交易明細（共 {len(closed)} 筆）\n")
        lines.append(f"| 代碼 | 名稱 | 進場日 | 進場價 | 出場日 | 出場價 | 原因 | 報酬% | 持有天數 |")
        lines.append(f"|------|------|--------|--------|--------|--------|------|------|----------|")
        for t in closed[-30:]:  # 只顯示最近30筆
            lines.append(
                f"| {t['stock']} | {t.get('name','')} | {t.get('entry_date','')} | "
                f"{t.get('entry_price')} | {t.get('exit_date','')} | "
                f"{t.get('exit_price','')} | {t.get('reason','')} | "
                f"{t.get('pnl_pct','')}% | {t.get('hold_days','')} |"
            )
        lines.append("")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="個股策略績效追蹤器")
    parser.add_argument("--add-entry",  nargs=3, metavar=("STOCK","PRICE","DATE"), help="新增進場")
    parser.add_argument("--close",      nargs=4, metavar=("STOCK","PRICE","DATE","REASON"), help="關閉倉位")
    parser.add_argument("--report",     action="store_true", help="產出績效報告")
    parser.add_argument("--export-csv", action="store_true", help="匯出 CSV")
    args = parser.parse_args()

    if args.add_entry:
        stock_id, price, date = args.add_entry
        cfg_path = CONFIG_DIR / f"{stock_id}.json"
        if not cfg_path.exists():
            print(f"錯誤：找不到 {stock_id} 策略檔")
            sys.exit(1)
        with open(cfg_path, "r", encoding="utf-8") as f:
            strategy = json.load(f)
        trade, err = add_trade(stock_id, float(price), date, strategy)
        if err:
            print(f"❌ {err}")
        else:
            print(f"✅ 已進場：[{stock_id}] {strategy.get('name')} @ {price} ({date})")
            print(f"   trade_id={trade['trade_id']}")

    elif args.close:
        stock_id, price, date, reason = args.close
        trade, err = close_trade(stock_id, float(price), date, reason)
        if err:
            print(f"❌ {err}")
        else:
            print(f"✅ 已關閉：[{stock_id}] @ {price} ({date})  原因={reason}")
            print(f"   報酬：{trade['pnl_pct']}%  持有：{trade['hold_days']} 天")

    elif args.export_csv:
        closed, stats = calc_performance()
        export_csv(closed)
        print(f"📄 已匯出至：{PERF_CSV}（共 {len(closed)} 筆）")

    elif args.report:
        closed, stats = calc_performance()
        if not closed:
            print("尚無已关闭的交易記錄。")
            sys.exit(0)
        export_csv(closed)
        md = make_performance_report(closed, stats)
        date_str = datetime.now().strftime("%Y-%m-%d")
        rpt_path = REPORT_DIR / f"stock_strategy_performance_{date_str}.md"
        with open(rpt_path, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"📄 績效報告已寫入：{rpt_path}")
        print(md)

    else:
        closed, stats = calc_performance()
        s = stats.get("summary", {})
        print("═══ 個股策略績效概覽 ═══")
        print(f"總交易：{s.get('total_trades',0)}  勝率：{s.get('win_rate',0)}%  "
              f"平均報酬：{s.get('avg_pct',0)}%  累計：{s.get('total_pnl',0)}%")

        print("\n依市場：")
        for g in stats.get("by_market", []):
            print(f"  {g['market']}: {g['trades']}筆 勝率{g['win_rate']}% 平均{g['avg_pct']}%")

        print("\n依股票：")
        for g in sorted(stats.get("by_stock", []), key=lambda x: x["total_pnl"], reverse=True):
            print(f"  {g['stock']}({g['name']}): {g['trades']}筆 勝率{g['win_rate']}% "
                  f"平均{g['avg_pct']}% 累計{g['total_pnl']}%")


if __name__ == "__main__":
    main()