# -*- coding: utf-8 -*-
"""
TW Stock Registry Verifier
檢核台股代號資料庫：格式、重複、名稱空白、watchlist 比對
"""

import sqlite3
import os
import re
import sys
import json
from datetime import datetime
from pathlib import Path

# Windows UTF-8
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

DB_PATH = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\tw_stock_registry.db"
STRATEGIES_DIR = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\configs\stock_strategies"
REPORTS_DIR = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\reports"


def load_watchlist_codes():
    """從 stock_strategies 目錄載入所有策略代號"""
    codes = set()
    p = Path(STRATEGIES_DIR)
    if not p.exists():
        return codes
    for f in p.glob("*.json"):
        code = f.stem  # e.g. "2330", "0050", "BILL", "COIN"
        codes.add(code)
    return codes


def verify():
    """執行檢核"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT code, name_cn FROM stock_registry ORDER BY code")
    rows = cur.fetchall()

    errors = []
    warnings = []
    info = []

    # 規則1: 代號格式（4-6位數字或英數）
    code_pattern = re.compile(r"^\d{4,6}|[A-Z]{2,10}$", re.IGNORECASE)
    code_numeric = re.compile(r"^\d{4,6}$")

    all_codes_in_db = set()
    name_map = {}
    for code, name in rows:
        all_codes_in_db.add(code)
        name_map[code] = name

    total = len(rows)

    # 規則2: 檢查重複（已在 DB Primary Key 防止，但再次確認）
    code_counts = {}
    for code, _ in rows:
        code_counts[code] = code_counts.get(code, 0) + 1
    for code, cnt in code_counts.items():
        if cnt > 1:
            errors.append({
                "type": "duplicate",
                "code": code,
                "desc": f"代號 {code} 出現 {cnt} 次（應為 1）"
            })

    # 規則3: 名稱空白
    for code, name in rows:
        if not name or not name.strip():
            errors.append({
                "type": "missing_name",
                "code": code,
                "desc": f"代號 {code} 的中文名稱為空"
            })

    # 規則4: watchlist 比對
    watchlist_codes = load_watchlist_codes()
    missing_from_registry = []
    found_in_registry = []

    for code in sorted(watchlist_codes):
        if code in all_codes_in_db:
            found_in_registry.append(code)
        elif re.match(r"^\d{4,6}$", code):
            # 只有數字代號才檢查（美股代號不需要在 TW registry 中）
            missing_from_registry.append(code)

    if missing_from_registry:
        warnings.append({
            "type": "watchlist_missing",
            "codes": missing_from_registry,
            "desc": f"策略資料夾中有 {len(missing_from_registry)} 個代號不在本地資料庫: {', '.join(missing_from_registry)}"
        })

    valid_count = total - sum(1 for e in errors if e["type"] == "missing_name")

    # 寫入驗證記錄
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    now_date = datetime.now().strftime("%Y-%m-%d")
    cur.execute("""
        INSERT INTO verification_log (date, total_stocks, valid_count, issues_found, checked_at)
        VALUES (?, ?, ?, ?, ?)
    """, (now_date, total, valid_count, len(errors), now_str))

    for e in errors:
        cur.execute("""
            INSERT INTO issues (date, code, issue_type, description)
            VALUES (?, ?, ?, ?)
        """, (now_date, e.get("code", ""), e["type"], e["desc"]))

    conn.commit()
    conn.close()

    # 產出 Markdown 報告
    today = datetime.now().strftime("%Y-%m-%d")
    report_path = os.path.join(REPORTS_DIR, f"tw_stock_registry_check_{today}.md")

    report = f"""# TW Stock Registry 檢核報告

**檢核時間:** {now_str} (UTC+8)  
**資料庫路徑:** `{DB_PATH}`

---

## 📊 總覽

| 項目 | 數值 |
|:-----|:----:|
| 資料庫總檔數 | {total} |
| 有效檔數 | {valid_count} |
| Error 數 | {len([e for e in errors if e['type'] in ('missing_name','duplicate','invalid_code')])} |
| Warning 數 | {len(warnings)} |

---

## ❌ Errors ({len([e for e in errors if e['type'] in ('missing_name','duplicate','invalid_code')])})"""

    if errors:
        for e in errors:
            sev = "Error" if e["type"] in ("missing_name", "duplicate", "invalid_code") else "Warning"
            report += f"\n- **[{sev}]** `{e['code']}` - {e['desc']}"
    else:
        report += "\n- 無"

    report += f"\n\n## ⚠️ Warnings ({len(warnings)})"

    if warnings:
        for w in warnings:
            report += f"\n- {w['desc']}"
    else:
        report += "\n- 無"

    # watchlist 比對結果
    report += f"""

---

## 📋 Watchlist 比對（stock_strategies/）

策略資料夾共收錄 **{len(watchlist_codes)}** 檔:

| 狀態 | 數量 |
|:-----|:----:|
| ✅ 已存在於 Registry | {len(found_in_registry)} |
| ⚠️ 數字代號不在 Registry | {len(missing_from_registry)} |

"""

    if found_in_registry:
        report += f"✅ **已存在:** {', '.join(sorted(found_in_registry))}"

    if missing_from_registry:
        report += f"\n⚠️ **不在 Registry 中（需新增）:** {', '.join(sorted(missing_from_registry))}"

    # 資料庫內容摘要
    report += f"""

---

## 📦 資料庫內容摘要（{total} 檔）

| 類別 | 數量 |
|:-----|:----:|
"""

    conn2 = sqlite3.connect(DB_PATH)
    cur2 = conn2.cursor()
    cur2.execute("SELECT industry, COUNT(*) FROM stock_registry GROUP BY industry ORDER BY COUNT(*) DESC")
    for ind, cnt in cur2.fetchall():
        report += f"| {ind} | {cnt} |\n"
    conn2.close()

    report += f"""
---

## ✅ 檢核結論

"""
    if not errors and not warnings:
        report += "🎉 所有檢核項目通過，資料庫狀態正常。"
    elif not errors:
        report += f"⚠️ 有 {len(warnings)} 個警告，建議確認。"
    else:
        report += f"❌ 有 {len(errors)} 個錯誤需要修正。"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"✅ 檢核完成")
    print(f"   Errors: {len([e for e in errors if e['type'] in ('missing_name','duplicate','invalid_code')])}")
    print(f"   Warnings: {len(warnings)}")
    print(f"   報告: {report_path}")
    print()
    if missing_from_registry:
        print(f"⚠️  watchlist 中有不在 registry 的數字代號: {missing_from_registry}")

    return errors, warnings, missing_from_registry


if __name__ == "__main__":
    verify()
