# -*- coding: utf-8 -*-
"""
TW Stock Registry - SQLite Database Builder
建立台股代號與中文名稱的本地資料庫（含 Seed Data）
"""

import sqlite3
import os
import sys
from datetime import datetime

# Windows UTF-8 mode
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

DB_PATH = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\tw_stock_registry.db"

# Seed Data: 60+ 檔核心台股
SEED_DATA = [
    # === 科技股 ===
    ("2330", "台積電", "TSMC", "半導體", "TWSE", "1994-09-05"),
    ("2454", "聯發科", "MediaTek", "IC設計", "TWSE", "1998-09-01"),
    ("2382", "廣達", "Quanta", "電子代工", "TWSE", "1999-09-10"),
    ("2317", "鴻海", "Foxconn", "電子代工", "TWSE", "1991-12-12"),
    ("3034", "緯穎", "Wiwynn", "伺服器", "TWSE", "2016-06-13"),
    ("3665", "穎崴", "WinWay", "半導體封測", "TWSE", "2017-12-19"),
    ("4961", "力旺", "eMemory", "IC設計", "TWSE", "2007-07-23"),
    ("2458", "義隆", "Elan", "IC設計", "TWSE", "1998-06-08"),
    ("3037", "欣興", "Unimicron", "PCB", "TWSE", "2003-06-05"),
    ("3717", "耕興", "Global", "檢測認證", "TWSE", "2006-06-08"),
    ("3035", "智原", "Faraday", "IC設計", "TWSE", "1998-03-13"),
    ("3515", "華擎", "ASRock", "板卡", "TWSE", "2008-06-10"),
    ("2337", "旺宏", "Macronix", "記憶體", "TWSE", "1995-12-21"),
    ("2401", "凌陽", "Sunplus", "IC設計", "TWSE", "1997-03-13"),
    ("2376", "技嘉", "GIGABYTE", "板卡", "TWSE", "1999-06-07"),
    ("2377", "微星", "MSI", "板卡", "TWSE", "2002-04-02"),
    ("2353", "宏碁", "Acer", "PC", "TWSE", "1996-08-19"),
    ("2354", "藍天", "Synnex", "通路", "TWSE", "1995-07-17"),
    ("2368", "金像電", "Gold Circuit", "PCB", "TWSE", "1999-07-23"),
    ("2345", "智邦", "Accton", "網通", "TWSE", "1999-09-24"),
    ("3017", "奇鋐", "Asia Circuit", "散熱", "TWSE", "2010-07-30"),

    # === 金融股 ===
    ("2881", "富邦金", "Fubon Fin", "金控", "TWSE", "2002-01-14"),
    ("2882", "國泰金", "Cathay Fin", "金控", "TWSE", "2002-01-14"),
    ("2883", "開發金", "CDB Fin", "金控", "TWSE", "2002-01-14"),
    ("2884", "玉山金", "E.Sun Fin", "金控", "TWSE", "2002-01-14"),
    ("2885", "元大金", "Yuanta Fin", "金控", "TWSE", "2002-01-14"),
    ("2886", "兆豐金", "Mega Fin", "金控", "TWSE", "2002-01-14"),
    ("2891", "中信金", "CTBC Fin", "金控", "TWSE", "2002-01-14"),
    ("2890", "永豐金", "Sinopac Fin", "金控", "TWSE", "2002-01-14"),
    ("2892", "第一金", "First Fin", "金控", "TWSE", "2002-01-14"),
    ("2855", "統一證", "Uni Presi", "券商", "TWSE", "2002-01-14"),
    ("2890", "永豐金", "Sinopac Fin", "金控", "TWSE", "2002-01-14"),
    ("5871", "中租-KY", "Chailease", "租賃", "TWSE", "2010-12-13"),
    ("5876", "上海商銀", "Shanghai Bank", "銀行", "TWSE", "2018-11-19"),

    # === ETF ===
    ("0050", "元大台灣50", "Yuanta WTO", "ETF", "TWSE", "2003-06-30"),
    ("0056", "元大高股息", "Yuanta HTD", "ETF", "TWSE", "2007-12-26"),
    ("00646", "富邦S&P500", "Fubon S&P500", "ETF", "TWSE", "2017-09-14"),
    ("00662", "富邦NASDAQ100", "Fubon Nasdaq", "ETF", "TWSE", "2017-09-14"),
    ("00713", "元大高息低波", "Yuanta HLB", "ETF", "TWSE", "2020-07-21"),
    ("00757", "統一大FANG+", "Uni FANG+", "ETF", "TWSE", "2022-05-24"),
    ("00927", "統一手創未來", "Uni Innov", "ETF", "TWSE", "2023-06-08"),
    ("00919", "群益科技高息", "Capco Tech", "ETF", "TWSE", "2022-08-22"),
    ("00631L", "富邦VIX", "Fubon VIX", "ETF", "TWSE", "2017-03-29"),
    ("00881", "國泰5G", "Cathay 5G", "ETF", "TWSE", "2021-01-14"),

    # === 傳產龍頭 ===
    ("2303", "聯電", "UMC", "晶圓代工", "TWSE", "1985-07-10"),
    ("1301", "台塑", "Formosa Plas", "石化", "TWSE", "1963-04-16"),
    ("1326", "台化", "FCC", "石化", "TWSE", "1983-09-01"),
    ("1702", "台泥(舊)", "Taiwan Cement", "水泥", "TWSE", "1962-02-01"),
    ("1216", "統一", "Uni President", "食品", "TWSE", "1967-08-01"),
    ("2912", "統一超", "President Chain", "零售", "TWSE", "1992-02-21"),
    ("2002", "台泥", "Taiwan Cement", "水泥", "TWSE", "1962-02-01"),
    ("2103", "台橡", "TSRC", "橡膠", "TWSE", "1978-07-10"),
    ("1718", "中纖", "China Man-made", "化學", "TWSE", "1980-09-10"),
    ("1605", "華夏", "Hwa Hsia", "電線電纜", "TWSE", "1960-07-01"),

    # === 更多科技股 ===
    ("2308", "台達電", "Delta", "電源供應", "TWSE", "1988-02-17"),
    ("3231", "緯創", "Wistron", "電子代工", "TWSE", "2003-05-13"),
    ("2474", "可成", "Catcher", "機殼", "TWSE", "2002-12-10"),
    ("2421", "建準", "Sunonwealth", "風扇", "TWSE", "1990-11-21"),
    ("1582", "信錦", "S Outsourcing", "機構件", "TWSE", "2019-12-24"),
    ("2059", "川湖", "King Slide", "滑軌", "TWSE", "2016-03-04"),
    ("2070", "精華", "Jing Chuan", "光學", "TWSE", "2015-04-01"),
    ("4564", "崑鼎", "Kun Ding", "水資源", "TWSE", "2014-03-12"),
    ("6108", "瑞軒", "Juphoor", "電視", "TWSE", "2008-07-08"),
    ("8016", "矽創", "Sitronix", "IC設計", "TWSE", "2007-08-23"),
    ("6488", "GIS-KY", "GIS", "觸控", "TWSE", "2007-12-21"),
    ("4952", "凌華", "Adlink", "工業電腦", "TWSE", "2007-08-13"),
    ("6165", "耕興", "Gaining", "檢測", "TWSE", "2006-06-08"),
    ("6741", "映精", "Etertainment", "光學", "TWSE", "2014-03-01"),
    ("8072", "陞泰", "AV Tech", "光學", "TWSE", "2008-06-05"),
]


def build_db():
    """建立資料庫與 Seed Data"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 建立 stock_registry 資料表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stock_registry (
            code        TEXT PRIMARY KEY,
            name_cn     TEXT NOT NULL,
            name_en     TEXT,
            industry    TEXT,
            market      TEXT,
            listing_date TEXT,
            last_updated TEXT
        )
    """)

    # 建立 verification_log 資料表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS verification_log (
            date        TEXT,
            total_stocks INTEGER,
            valid_count INTEGER,
            issues_found TEXT,
            checked_at  TEXT
        )
    """)

    # 建立 issues 資料表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS issues (
            date        TEXT,
            code        TEXT,
            issue_type  TEXT,
            description TEXT
        )
    """)

    # 清除舊資料（重新 seed）
    cur.execute("DELETE FROM stock_registry")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 移除重複代號（保留第一筆）
    seen_codes = set()
    for row in SEED_DATA:
        code = row[0]
        if code not in seen_codes:
            seen_codes.add(code)
            cur.execute("""
                INSERT INTO stock_registry
                (code, name_cn, name_en, industry, market, listing_date, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (code, row[1], row[2], row[3], row[4], row[5], now))

    conn.commit()

    # 統計
    cur.execute("SELECT COUNT(*) FROM stock_registry")
    count = cur.fetchone()[0]

    cur.execute("SELECT code, name_cn FROM stock_registry ORDER BY code")
    all_stocks = cur.fetchall()

    conn.close()

    print(f"✅ 資料庫建立完成，共 {count} 檔股票")
    print(f"📁 路徑: {DB_PATH}")
    print()
    print("=== 資料庫內容 ===")
    for code, name in all_stocks:
        print(f"  {code}  {name}")

    return count


if __name__ == "__main__":
    build_db()
