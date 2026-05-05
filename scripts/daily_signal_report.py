"""
daily_signal_report.py
=======================
快速每日訊號摘要（整合 stock_signal_scanner + email/telegram 格式輸出）。
用法：python daily_signal_report.py
"""

import io
import sys
from datetime import datetime
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_DIR   = Path(__file__).parent.parent.resolve()
SUMMARY_CSV = BASE_DIR / "data" / "stock_strategies_summary.csv"
REPORT_DIR  = BASE_DIR / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    date_str = datetime.now().strftime("%Y-%m-%d")

    print(f"\n{'═'*55}")
    print(f"  daily_signal_report.py  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'═'*55}\n")

    if not SUMMARY_CSV.exists():
        print(f"❌ 找不到 {SUMMARY_CSV}，請先執行 stock_signal_scanner.py")
        sys.exit(1)

    import csv
    rows = []
    with open(SUMMARY_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    entry_long  = [r for r in rows if r.get("signal") == "ENTRY_LONG"]
    entry_watch = [r for r in rows if r.get("signal") == "ENTRY_WATCH"]
    holds       = [r for r in rows if r.get("signal") == "HOLD"]

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    print(f"📡 每日訊號摘要  {now_str}")
    print(f"   掃描：{len(rows)} 檔 | 🚀 ENTRY_LONG: {len(entry_long)} | 👀 ENTRY_WATCH: {len(entry_watch)} | 觀望: {len(holds)}\n")

    if entry_long:
        print("🚀 ENTRY_LONG:")
        for r in sorted(entry_long, key=lambda x: float(x.get("score", 0)), reverse=True):
            print(f"   [{r['stock']}] {r['name']}  price={r['current_price']}  RSI={r['current_rsi']}  bias={r['bias20']}  ma={r['ma_status']}  score={r.get('score','')}")

    if entry_watch:
        print("\n👀 ENTRY_WATCH:")
        for r in sorted(entry_watch, key=lambda x: float(x.get("score", 0)), reverse=True):
            print(f"   [{r['stock']}] {r['name']}  price={r['current_price']}  RSI={r['current_rsi']}  bias={r['bias20']}  ma={r['ma_status']}  score={r.get('score','')}")

    if not entry_long and not entry_watch:
        print("今日無進場訊號。")

    # 寫入 Markdown
    lines = [
        f"# 📡 每日訊號摘要",
        f"**{now_str}**  掃描 {len(rows)} 檔\n",
    ]

    if entry_long:
        lines += [
            f"## 🚀 ENTRY_LONG（共 {len(entry_long)} 檔）\n",
            "| 代碼 | 名稱 | 市場 | 現價 | 漲跌% | RSI | BIAS20 | MA | 分數 |",
            "|------|------|------|------|------|-----|--------|---|------|",
        ]
        for r in sorted(entry_long, key=lambda x: float(x.get("score", 0)), reverse=True):
            lines.append(
                f"| {r['stock']} | {r['name']} | {r['market']} | "
                f"{r['current_price']} | {r.get('change_pct','')}% | "
                f"{r['current_rsi']} | {r['bias20']} | {r['ma_status']} | "
                f"{r.get('score','')} |"
            )
        lines.append("")

    if entry_watch:
        lines += [
            f"## 👀 ENTRY_WATCH（共 {len(entry_watch)} 檔）\n",
            "| 代碼 | 名稱 | 市場 | 現價 | 漲跌% | RSI | BIAS20 | MA | 分數 |",
            "|------|------|------|------|------|-----|--------|---|------|",
        ]
        for r in sorted(entry_watch, key=lambda x: float(x.get("score", 0)), reverse=True):
            lines.append(
                f"| {r['stock']} | {r['name']} | {r['market']} | "
                f"{r['current_price']} | {r.get('change_pct','')}% | "
                f"{r['current_rsi']} | {r['bias20']} | {r['ma_status']} | "
                f"{r.get('score','')} |"
            )
        lines.append("")

    rpt_path = REPORT_DIR / f"daily_signal_summary_{date_str}.md"
    with open(rpt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n📄 摘要報告 → {rpt_path}")
    print("✅ 完成！")


if __name__ == "__main__":
    main()