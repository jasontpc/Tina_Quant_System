# -*- coding: utf-8 -*-
"""
TW Stock Registry Updater
從 FinMind API 抓取最新股票列表，比對並更新本地資料庫
"""

import sqlite3
import os
import sys
import re
import json
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# Windows UTF-8
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

DB_PATH = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\tw_stock_registry.db"
FINMIND_BASE = "https://api.finmindtrade.com/api/v4/data"
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSJ9.oCdQO1qNRUCYxHZSVuRQCqlF7X2DbQ77wury5ARCKzM"


def fetch_finmind_taiwan_stockinfo():
    """從 FinMind API 抓取 TaiwanStockInfo（所有上市/上櫃股票）"""
    url = FINMIND_BASE
    params = {
        "dataset": "TaiwanStockInfo",
        "api_key": FINMIND_TOKEN,
        "data_id": "",  # 空=抓全部
    }

    query = "&".join(f"{k}={v}" for k, v in params.items())
    full_url = f"{url}?{query}"

    try:
        req = Request(full_url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (URLError, HTTPError, json.JSONDecodeError, Exception) as e:
        print(f"⚠️ FinMind API 抓取失敗: {e}")
        return None

    if data.get("status") == 200 and "data" in data:
        return data["data"]
    else:
        print(f"⚠️ FinMind API 回傳失敗: {data.get('msg', 'unknown error')}")
        return None


def fetch_finmind_taiwan_stockprice(stock_id):
    """驗證單一股票代號是否存在（嘗試抓取近期價格）"""
    params = {
        "dataset": "TaiwanStockPrice",
        "api_key": FINMIND_TOKEN,
        "data_id": stock_id,
        "start_date": "2026-01-01",
        "end_date": "2026-01-10",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    full_url = f"{FINMIND_BASE}?{query}"
    try:
        req = Request(full_url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("success") is True and bool(data.get("data"))
    except Exception:
        return False


def update_registry(dry_run=False):
    """比對 FinMind 與本地資料庫，更新差異"""
    print("📡 從 FinMind 抓取 TaiwanStockInfo...")
    fm_data = fetch_finmind_taiwan_stockinfo()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT code, name_cn FROM stock_registry")
    local_rows = cur.fetchall()
    local_codes = {row[0]: row[1] for row in local_rows}

    changes = {
        "added": [],      # 新的（FinMind 有，本地沒有）
        "removed": [],    # 被移除的（本地有，FinMind 沒有）
        "name_changed": [],  # 名稱變更
    }

    if fm_data is not None:
        # FinMind 回傳格式: {stock_id, stock_name, type, industry, market}
        fm_codes = {}
        for row in fm_data:
            sid = str(row.get("stock_id", "")).strip()
            sname = str(row.get("stock_name", "")).strip()
            stype = str(row.get("type", "")).strip()
            industry = str(row.get("industry", "")).strip()
            market = str(row.get("market", "")).strip()
            if sid and len(sid) >= 4:
                fm_codes[sid] = {
                    "name_cn": sname,
                    "type": stype,
                    "industry": industry,
                    "market": market,
                }

        # 找出新的
        for code, info in fm_codes.items():
            if code not in local_codes:
                changes["added"].append((code, info["name_cn"], info["industry"], info["market"]))

        # 檢查名稱變更
        for code, local_name in local_codes.items():
            if code in fm_codes and fm_codes[code]["name_cn"] != local_name:
                changes["name_changed"].append((code, local_name, fm_codes[code]["name_cn"]))

        # 找出被下市的（本地有，FinMind 沒有）- 必須是4-6位數字
        numeric_local = [c for c in local_codes if re.match(r"^\d{4,6}$", c)]
        for code in numeric_local:
            if code not in fm_codes:
                changes["removed"].append((code, local_codes[code]))

    else:
        print("⚠️ 無法抓取 FinMind，改用本地邏輯檢查...")

    print()
    print(f"=== 變更摘要 ===")
    print(f"  🆕 新增: {len(changes['added'])} 檔")
    for code, name, industry, market in changes["added"]:
        print(f"     {code}  {name}  ({industry})")
    print(f"  🔁 名稱變更: {len(changes['name_changed'])} 檔")
    for code, old, new in changes["name_changed"]:
        print(f"     {code}: {old} → {new}")
    print(f"  🗑️  可能下市: {len(changes['removed'])} 檔")
    for code, name in changes["removed"]:
        print(f"     {code}  {name}")

    if dry_run:
        print("\n🔸 Dry-run 模式：只顯示變更，不寫入資料庫")
        conn.close()
        return changes

    # 寫入資料庫
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_added = 0

    for code, name, industry, market in changes["added"]:
        cur.execute("""
            INSERT OR IGNORE INTO stock_registry
            (code, name_cn, industry, market, last_updated)
            VALUES (?, ?, ?, ?, ?)
        """, (code, name, industry or "其他", market or "TWSE", now_str))
        total_added += 1

    for code, old_name, new_name in changes["name_changed"]:
        cur.execute("""
            UPDATE stock_registry SET name_cn = ?, last_updated = ?
            WHERE code = ?
        """, (new_name, now_str, code))

    conn.commit()
    cur.execute("SELECT COUNT(*) FROM stock_registry")
    total = cur.fetchone()[0]
    conn.close()

    print(f"\n✅ 更新完成")
    print(f"   新增 {total_added} 檔，資料庫共 {total} 檔")
    print(f"   名稱更新 {len(changes['name_changed'])} 檔")

    return changes


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    update_registry(dry_run=dry)
