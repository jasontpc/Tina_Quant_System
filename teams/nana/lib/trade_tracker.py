# trade_tracker.py - Nana Tier 交易記錄追蹤框架
# 用於追蹤虛擬持倉與實際交易

import json
import os
import yfinance as yf
from datetime import datetime, date
from typing import Optional, Dict, List, Any

# ── 路徑設定 ──────────────────────────────────────────────
BASE_DIR = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\nana"
DB_DIR = os.path.join(BASE_DIR, "tiers")

VALID_TIERS = ["tier1", "tier2", "tier3"]


def _db_path(tier: str) -> str:
    return os.path.join(DB_DIR, tier, "database.json")


def _load_db(tier: str) -> dict:
    path = _db_path(tier)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_db(tier: str, db: dict):
    path = _db_path(tier)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


# ── 核心函式 ──────────────────────────────────────────────

def add_trade(
    tier: str,
    stock_id: str,
    entry_price: float,
    exit_price: float,
    hold_days: int,
    return_pct: float,
    quantity: int = 1000,
    trade_date: Optional[str] = None,
    trade_type: str = "virtual",  # "virtual" or "real"
) -> dict:
    """
    新增一筆交易記錄至指定 tier 的 database.json。

    Args:
        tier: tier1 / tier2 / tier3
        stock_id: 股票代碼 (e.g. "2449")
        entry_price: 進場價格
        exit_price: 出場價格
        hold_days: 持有天數
        return_pct: 報酬率 (%，e.g. 5.5 表示 +5.5%)
        quantity: 成交股數
        trade_date: 交易日期 (YYYY-MM-DD)，預設今天
        trade_type: "virtual" 虛擬交易 | "real" 實際交易

    Returns:
        新增的交易物件
    """
    if tier not in VALID_TIERS:
        raise ValueError(f"Invalid tier: {tier}. Must be one of {VALID_TIERS}")

    if trade_date is None:
        trade_date = date.today().isoformat()

    trade = {
        "trade_id": f"{stock_id}_{trade_date.replace('-', '')}_{datetime.now().strftime('%H%M%S')}",
        "stock_id": stock_id,
        "entry_price": round(entry_price, 2),
        "exit_price": round(exit_price, 2),
        "quantity": quantity,
        "hold_days": hold_days,
        "return_pct": round(return_pct, 4),
        "profit_loss": round((exit_price - entry_price) * quantity, 2),
        "trade_date": trade_date,
        "trade_type": trade_type,
        "recorded_at": datetime.now().isoformat(),
    }

    db = _load_db(tier)
    db["trades"].append(trade)

    # 更新 stats
    _recalc_stats(db)
    _save_db(tier, db)

    # 從 virtual_holdings 移除（如果有的話）
    update_virtual_holdings(tier, stock_id, action="remove")

    return trade


def update_virtual_holdings(
    tier: str,
    stock_id: str,
    current_price: Optional[float] = None,
    quantity: Optional[int] = None,
    avg_cost: Optional[float] = None,
    action: str = "add",  # "add" | "remove" | "update"
) -> dict:
    """
    新增、更新或移除虛擬持倉。

    Args:
        tier: tier1 / tier2 / tier3
        stock_id: 股票代碼
        current_price: 最新股價（若需即時更新）
        quantity: 持有股數（新增/更新時使用）
        avg_cost: 平均成本（新增/更新時使用）
        action: "add" | "remove" | "update" | "refresh"

    Returns:
        更新後的 virtual_holdings 陣列
    """
    if tier not in VALID_TIERS:
        raise ValueError(f"Invalid tier: {tier}")

    db = _load_db(tier)
    holdings = db.get("virtual_holdings", [])
    existing_idx = next(
        (i for i, h in enumerate(holdings) if h["stock_id"] == stock_id), None
    )

    if action == "refresh" and current_price is not None:
        # 只更新現有持倉的 current_price（從 yfinance 即時抓）
        if existing_idx is not None:
            ticker = yf.Ticker(f"{stock_id}.TW")
            hist = ticker.history(period="5d")
            if not hist.empty:
                holdings[existing_idx]["current_price"] = round(hist["Close"].iloc[-1], 2)
                holdings[existing_idx]["market_value"] = round(
                    holdings[existing_idx]["current_price"] * holdings[existing_idx]["quantity"], 2
                )
        db["virtual_holdings"] = holdings
        _save_db(tier, db)
        return holdings

    elif action == "add":
        if existing_idx is not None:
            # 已存在則更新數量與均價
            h = holdings[existing_idx]
            total_cost = h["avg_cost"] * h["quantity"] + avg_cost * quantity
            new_qty = h["quantity"] + quantity
            h["avg_cost"] = round(total_cost / new_qty, 2)
            h["quantity"] = new_qty
            if current_price:
                h["current_price"] = round(current_price, 2)
                h["market_value"] = round(current_price * new_qty, 2)
        else:
            if current_price is None or quantity is None or avg_cost is None:
                raise ValueError("current_price, quantity, avg_cost are required for add action")
            holdings.append({
                "stock_id": stock_id,
                "quantity": quantity,
                "avg_cost": round(avg_cost, 2),
                "current_price": round(current_price, 2),
                "market_value": round(current_price * quantity, 2),
            })
        db["virtual_holdings"] = holdings
        _save_db(tier, db)
        return holdings

    elif action == "remove":
        if existing_idx is not None:
            holdings.pop(existing_idx)
            db["virtual_holdings"] = holdings
            _save_db(tier, db)
        return holdings

    elif action == "update":
        if existing_idx is not None and current_price is not None:
            h = holdings[existing_idx]
            h["current_price"] = round(current_price, 2)
            h["market_value"] = round(current_price * h["quantity"], 2)
            if quantity is not None:
                h["quantity"] = quantity
            if avg_cost is not None:
                h["avg_cost"] = round(avg_cost, 2)
            db["virtual_holdings"] = holdings
            _save_db(tier, db)
        return holdings

    return holdings


def get_stats(tier: str) -> dict:
    """
    取得指定 tier 的交易統計。

    Returns:
        stats 物件 { total_trades, win_rate, avg_return, max_loss, max_gain, total_profit }
    """
    if tier not in VALID_TIERS:
        raise ValueError(f"Invalid tier: {tier}")
    db = _load_db(tier)
    return db.get("stats", {})


def get_virtual_holdings(tier: str) -> List[dict]:
    """取得指定 tier 的虛擬持倉明細。"""
    db = _load_db(tier)
    return db.get("virtual_holdings", [])


def get_trades(tier: str, trade_type: Optional[str] = None) -> List[dict]:
    """取得指定 tier 的交易記錄，可依類型過濾。"""
    db = _load_db(tier)
    trades = db.get("trades", [])
    if trade_type:
        trades = [t for t in trades if t.get("trade_type") == trade_type]
    return trades


def refresh_all_prices(tier: str) -> dict:
    """
    用 yfinance 更新 tier 所有虛擬持倉的 current_price。

    Returns:
        更新後的 holdings 列表
    """
    if tier not in VALID_TIERS:
        raise ValueError(f"Invalid tier: {tier}")
    db = _load_db(tier)
    holdings = db.get("virtual_holdings", [])
    updated = []
    for h in holdings:
        sid = h["stock_id"]
        try:
            ticker = yf.Ticker(f"{sid}.TW")
            hist = ticker.history(period="5d")
            if not hist.empty:
                cp = round(hist["Close"].iloc[-1], 2)
                h["current_price"] = cp
                h["market_value"] = round(cp * h["quantity"], 2)
                updated.append({"stock_id": sid, "status": "updated", "price": cp})
            else:
                updated.append({"stock_id": sid, "status": "no_data"})
        except Exception as e:
            updated.append({"stock_id": sid, "status": "error", "error": str(e)})

    db["virtual_holdings"] = holdings
    _save_db(tier, db)
    return {"holdings": holdings, "updated": updated}


def print_summary(tier: str):
    """在終端機列印 tier 的摘要報告。"""
    db = _load_db(tier)
    stats = db.get("stats", {})
    holdings = db.get("virtual_holdings", [])
    total_mv = sum(h.get("market_value", 0) for h in holdings)
    print(f"\n=== {tier.upper()} Summary ===")
    print(f"Total Trades: {stats.get('total_trades', 0)}")
    print(f"Win Rate:     {stats.get('win_rate', 0):.1f}%")
    print(f"Avg Return:   {stats.get('avg_return', 0):.2f}%")
    print(f"Max Gain:     {stats.get('max_gain', 0):.2f}%")
    print(f"Max Loss:     {stats.get('max_loss', 0):.2f}%")
    print(f"Total Market Value: NT${total_mv:,.0f}")
    print(f"\nVirtual Holdings ({len(holdings)} stocks):")
    for h in holdings:
        pnl = ((h['current_price'] - h['avg_cost']) / h['avg_cost']) * 100
        print(f"  {h['stock_id']} {h.get('name','')}: {h['quantity']} shares @ {h['current_price']} (cost {h['avg_cost']}) P/L={pnl:+.1f}%")


def _recalc_stats(db: dict):
    """內部：根據 trades 陣列重新計算 stats。"""
    trades = db.get("trades", [])
    total = len(trades)
    if total == 0:
        db["stats"] = {
            "total_trades": 0,
            "win_rate": 0,
            "avg_return": 0,
            "max_loss": 0,
            "max_gain": 0,
            "total_profit": 0,
        }
        return

    returns = [t["return_pct"] for t in trades]
    wins = [r for r in returns if r > 0]
    gains = [r for r in returns]

    db["stats"] = {
        "total_trades": total,
        "win_rate": round(len(wins) / total * 100, 2),
        "avg_return": round(sum(returns) / total, 4),
        "max_gain": round(max(gains), 4) if gains else 0,
        "max_loss": round(min(gains), 4) if gains else 0,
        "total_profit": round(sum(t.get("profit_loss", 0) for t in trades), 2),
    }


# ── 測試 ──────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    for t in VALID_TIERS:
        print_summary(t)

    print("\n--- Testing add_trade ---")
    # 模擬一筆 tier1 交易：2449 京元電子，進 280，出 290，持有 5 天，報酬 +3.57%
    trade = add_trade(
        tier="tier1",
        stock_id="2449",
        entry_price=280.0,
        exit_price=290.0,
        hold_days=5,
        return_pct=3.57,
        quantity=1000,
        trade_date="2026-04-20",
        trade_type="virtual",
    )
    print(f"Trade recorded: {trade['trade_id']} return={trade['return_pct']}% P/L={trade['profit_loss']}")

    print("\n--- Final tier1 stats ---")
    print(get_stats("tier1"))

    print("\n--- All tests passed ---")
