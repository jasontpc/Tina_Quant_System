# -*- coding: utf-8 -*-
"""
Financial Data Fetcher - Tina Quant System v2
Fetches quarterly/annual financials via FinMind API.
Correctly maps Revenue, GrossProfit, OperatingIncome, NetIncome, EPS.
Stores to data/financial_history.db
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import sqlite3
import time
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

BASE = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System"
DATA_DIR = f"{BASE}\\data"
sys.path.insert(0, f"{BASE}\\scripts")

# FinMind API
FINMIND_BASE = "https://api.finmindtrade.com/api/v4/data"
TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjF9.ivums9mfJUrM2MYazJiOEg49RiYLOJMZtejqX79YWS8"

# Target stocks
TW_STOCKS = ["2330", "2382", "2454", "2317", "3034", "3665", "4961"]

# Rate limiting
_last_call = 0
MIN_INTERVAL = 0.4

def rate_limited_get(dataset, data_id, start_date, end_date, retries=3):
    global _last_call
    import requests
    for attempt in range(retries):
        elapsed = time.time() - _last_call
        if elapsed < MIN_INTERVAL:
            time.sleep(MIN_INTERVAL - elapsed)
        _last_call = time.time()

        params = {"dataset": dataset, "data_id": data_id,
                  "start_date": start_date, "end_date": end_date, "token": TOKEN}
        try:
            resp = requests.get(FINMIND_BASE, params=params, timeout=20)
            if resp.status_code == 200:
                return resp.json()
            log.warning(f"  HTTP {resp.status_code} for {dataset}/{data_id}")
        except Exception as e:
            log.warning(f"  Attempt {attempt+1} failed: {e}")
        time.sleep(2)
    return {"status": 500, "data": []}


def init_db(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS quarterly_financials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock TEXT NOT NULL, quarter TEXT NOT NULL,
            revenue REAL, gross_profit REAL, operating_income REAL,
            net_income REAL, eps REAL,
            gross_margin REAL, operating_margin REAL, net_margin REAL,
            fetched_at TEXT,
            UNIQUE(stock, quarter))
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS annual_financials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock TEXT NOT NULL, year INTEGER NOT NULL,
            revenue REAL, gross_profit REAL, operating_income REAL,
            net_income REAL, eps REAL,
            gross_margin REAL, operating_margin REAL, net_margin REAL,
            fetched_at TEXT,
            UNIQUE(stock, year))
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fetch_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock TEXT, fetch_date TEXT, success INTEGER, rows INTEGER, error TEXT
        )
    """)
    conn.commit()
    conn.close()


def parse_financials(raw_data, stock_id):
    """Parse FinMind TaiwanStockFinancialStatements into structured records.

    Correct field mapping based on actual API response:
    - Revenue = 營收
    - GrossProfit = 毛利
    - OperatingIncome = 營業利益
    - IncomeAfterTaxes = 稅後純益 (used for net_income)
    - EPS = 每股盈餘
    """
    records = {}  # quarter -> {field: value}

    for row in raw_data:
        date_str = row.get("date", "")
        if not date_str:
            continue
        year = int(date_str[:4])
        month = int(date_str[5:7])
        quarter = f"Q{(month - 1) // 3 + 1}"
        qkey = f"{year}{quarter}"

        if qkey not in records:
            records[qkey] = {"quarter": qkey, "year": year, "stock": stock_id}

        ftype = row.get("type", "")
        val = row.get("value")

        if ftype == "Revenue":
            records[qkey]["revenue"] = val
        elif ftype == "GrossProfit":
            records[qkey]["gross_profit"] = val
        elif ftype == "OperatingIncome":
            records[qkey]["operating_income"] = val
        elif ftype == "IncomeAfterTaxes":
            records[qkey]["net_income"] = val
        elif ftype == "EPS":
            records[qkey]["eps"] = val

    return list(records.values())


def compute_margins(rec):
    """Add margin calculations to a record"""
    rev = rec.get("revenue")
    if rev and rev > 0:
        rec["gross_margin"] = round(rec.get("gross_profit", 0) / rev * 100, 2)
        rec["operating_margin"] = round(rec.get("operating_income", 0) / rev * 100, 2)
        rec["net_margin"] = round(rec.get("net_income", 0) / rev * 100, 2)
    else:
        rec["gross_margin"] = rec["operating_margin"] = rec["net_margin"] = None
    return rec


def save_quarterly(conn, records, stock_id):
    cur = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for rec in records:
        compute_margins(rec)
        rec["stock"] = stock_id  # preserve for save_annual
        cur.execute("""
            INSERT OR REPLACE INTO quarterly_financials
            (stock, quarter, revenue, gross_profit, operating_income, net_income,
             eps, gross_margin, operating_margin, net_margin, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (stock_id, rec["quarter"],
              rec.get("revenue"), rec.get("gross_profit"),
              rec.get("operating_income"), rec.get("net_income"),
              rec.get("eps"),
              rec.get("gross_margin"), rec.get("operating_margin"), rec.get("net_margin"),
              now))
    conn.commit()


def save_annual(conn, records):
    """Aggregate quarterly into annual"""
    by_year = {}
    for rec in records:
        yr = rec["year"]
        if yr not in by_year:
            by_year[yr] = {"revenue": 0, "gross_profit": 0,
                           "operating_income": 0, "net_income": 0}
        for f in ("revenue", "gross_profit", "operating_income", "net_income"):
            by_year[yr][f] += (rec.get(f) or 0)

    cur = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for yr, vals in by_year.items():
        rev = vals["revenue"]
        if rev > 0:
            gm = round(vals["gross_profit"] / rev * 100, 2)
            om = round(vals["operating_income"] / rev * 100, 2)
            nm = round(vals["net_income"] / rev * 100, 2)
        else:
            gm = om = nm = None

        # Find EPS (latest quarter EPS for annual)
        eps_val = None
        for rec in records:
            if rec["year"] == yr and rec.get("eps") is not None:
                eps_val = rec["eps"]

        # Find stock from records
        stock_val = None
        for rec in records:
            if rec.get("stock"):
                stock_val = rec["stock"]
                break

        cur.execute("""
            INSERT OR REPLACE INTO annual_financials
            (stock, year, revenue, gross_profit, operating_income, net_income,
             eps, gross_margin, operating_margin, net_margin, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (stock_val or "UNKNOWN", yr,
              rev, vals["gross_profit"], vals["operating_income"], vals["net_income"],
              eps_val, gm, om, nm, now))
    conn.commit()


def fetch_stock(stock_id, conn):
    log.info(f"  Fetching {stock_id}...")
    try:
        data = rate_limited_get(
            "TaiwanStockFinancialStatements", stock_id,
            start_date="2020-01-01", end_date=datetime.now().strftime("%Y-%m-%d")
        )

        if data.get("status") != 200 or not data.get("data"):
            log.warning(f"  No data for {stock_id}")
            cur = conn.cursor()
            cur.execute("INSERT INTO fetch_log (stock, fetch_date, success, rows) VALUES (?, ?, 0, 0)",
                        (stock_id, datetime.now().strftime("%Y-%m-%d")))
            conn.commit()
            return 0

        records = parse_financials(data["data"], stock_id)
        if not records:
            log.warning(f"  No parsed records for {stock_id}")
            return 0

        save_quarterly(conn, records, stock_id)
        save_annual(conn, records)

        cur = conn.cursor()
        cur.execute("INSERT INTO fetch_log (stock, fetch_date, success, rows) VALUES (?, ?, 1, ?)",
                    (stock_id, datetime.now().strftime("%Y-%m-%d"), len(records)))
        conn.commit()
        log.info(f"  {stock_id}: {len(records)} quarters saved")
        return len(records)

    except Exception as e:
        log.error(f"  {stock_id} failed: {e}")
        cur = conn.cursor()
        cur.execute("INSERT INTO fetch_log (stock, fetch_date, success, error) VALUES (?, ?, 0, ?)",
                    (stock_id, datetime.now().strftime("%Y-%m-%d"), str(e)))
        conn.commit()
        return 0


def main():
    log.info("=== Financial Data Fetcher v2 ===")
    start = datetime.now()

    db_path = f"{DATA_DIR}\\financial_history.db"
    init_db(db_path)

    conn = sqlite3.connect(db_path)
    total = 0
    for stock in TW_STOCKS:
        cnt = fetch_stock(stock, conn)
        total += cnt
        time.sleep(0.5)

    conn.close()
    elapsed = (datetime.now() - start).total_seconds()
    log.info(f"Done. {total} quarters from {len(TW_STOCKS)} stocks | Time={elapsed:.1f}s")
    return {"total_quarters": total, "stocks": TW_STOCKS, "elapsed_s": elapsed}


if __name__ == "__main__":
    result = main()
    print(f"Result: {result}")