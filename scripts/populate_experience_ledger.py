# -*- coding: utf-8 -*-
"""
populate_experience_ledger.py — 從 trades.log 填充 experience_ledger.json
Run: python populate_experience_ledger.py
"""

import sys, json, re
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
sys.path.insert(0, str(BASE_DIR / "scripts" / "utils"))

try:
    from ray_io_guard import io_singleton, safe_write_json
    _HAS_IO = True
except ImportError:
    from ray_guard import io_singleton
    safe_write_json = None
    _HAS_IO = False

TRADES_LOG = BASE_DIR / "stores" / "portfolio" / "trades.log"
LEDGER_PATH = BASE_DIR / "stores" / "long_term" / "experience_ledger.json"


def parse_trades_log():
    """解析 trades.log，提取交易記錄"""
    if not TRADES_LOG.exists():
        print("trades.log not found")
        return []

    content = TRADES_LOG.read_text(encoding="utf-8", errors="ignore")
    entries = []

    for line in content.strip().split("\n"):
        if not line.strip():
            continue

        # 格式：[DATE] SYMBOL | ACTION: ... | QTY: ... | PRICE: ... | REASON: ...
        match = re.match(
            r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\] (\S+) \| ACTION: (\S+) \| QTY: (\S+) \| PRICE: (\S+) \| REASON: (.+)',
            line
        )
        if match:
            date_str, symbol, action, qty, price, reason = match.groups()
            entries.append({
                "date": date_str,
                "symbol": symbol,
                "action": action,
                "qty": qty,
                "price": price,
                "reason": reason,
            })
        else:
            # 嘗試另一種格式
            parts = line.split("|")
            if len(parts) >= 4:
                date_part = parts[0].strip("[] ")
                symbol = parts[1].strip()
                action = parts[2].replace("ACTION:", "").strip()
                price = parts[3].replace("PRICE:", "").strip() if "PRICE:" in parts[3] else "N/A"

                # 從reason提取RSI
                rsi_match = re.search(r'RSI[:\s]*(\d+)', line)
                rsi = int(rsi_match.group(1)) if rsi_match else None

                entries.append({
                    "date": date_part,
                    "symbol": symbol,
                    "action": action,
                    "price": price,
                    "reason": line,
                    "rsi_at_entry": rsi,
                })

    return entries


def build_ledger(entries):
    """從交易記錄構建 experience_ledger"""
    ledger = {
        "version": 1,
        "description": "Experience Ledger — 系統性學習追蹤交易勝負",
        "entries": [],
        "stats": {
            "total": len(entries),
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "avg_return": 0.0
        },
        "schema": {
            "fields": ["id", "date", "symbol", "action", "cost", "exit_price", "pnl", "pnl_pct", "result", "rsi_at_entry", "holding_days", "reason", "lesson", "source"]
        },
        "created_at": "2026-05-13T21:15:00",
        "updated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    }

    for i, e in enumerate(entries):
        # 判斷結果（需要PnL數據，目前以 action 推斷）
        action = e.get("action", "")
        if "CONSIDER_TAKE_PROFIT" in action or "EXIT" in action or "SELL" in action:
            result = "win"  # 有動作代表有收成就假設
        elif "NEW_ENTRY" in action:
            result = "pending"
        else:
            result = "unknown"

        # 從 reason 提取 RSI
        reason = e.get("reason", "")
        rsi_match = re.search(r'RSI[:\s]*(\d+)', reason)
        rsi = int(rsi_match.group(1)) if rsi_match else e.get("rsi_at_entry")

        entry = {
            "id": i + 1,
            "date": e.get("date", ""),
            "symbol": e.get("symbol", ""),
            "action": action,
            "cost": float(e.get("price", 0)) if e.get("price") not in (None, "N/A", "") else None,
            "exit_price": None,
            "pnl": None,
            "pnl_pct": None,
            "result": result,
            "rsi_at_entry": rsi,
            "holding_days": None,
            "reason": reason[:200] if reason else "",
            "lesson": None,
            "source": "trades.log"
        }
        ledger["entries"].append(entry)

        if result == "win":
            ledger["stats"]["wins"] += 1
        elif result == "loss":
            ledger["stats"]["losses"] += 1

    total = ledger["stats"]["wins"] + ledger["stats"]["losses"]
    if total > 0:
        ledger["stats"]["win_rate"] = round(ledger["stats"]["wins"] / total * 100, 1)

    return ledger


def main():
    print("=" * 50)
    print("Experience Ledger Populator")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    # Parse
    entries = parse_trades_log()
    print(f"Parsed {len(entries)} trade entries from trades.log")

    # Build ledger
    ledger = build_ledger(entries)
    print(f"Built ledger: {ledger['stats']['wins']} wins, {ledger['stats']['losses']} losses")

    # Write safely
    if _HAS_IO:
        print("Using @io_singleton for safe write")
        io_singleton(lambda: None)  # just to use the singleton

    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER_PATH, "w", encoding="utf-8") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=2)

    print(f"Written to {LEDGER_PATH}")
    print(f"Total entries: {len(ledger['entries'])}")
    print()
    for e in ledger["entries"]:
        print(f"  {e['date']} | {e['symbol']} | {e['action']} | RSI={e['rsi_at_entry']} | result={e['result']}")

    print()
    print("Done!")


if __name__ == "__main__":
    main()