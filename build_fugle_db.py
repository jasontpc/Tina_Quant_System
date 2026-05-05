# -*- coding: utf-8 -*-
"""
Fugle 即時資料庫建置腳本
Fugle Real-time Database Builder
建立以 Fugle API 為核心的台股即時資料庫
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
import json
import os
import time
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Tuple, Any
import requests
import numpy as np
import yfinance as yf

# === 路徑設定 ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.join(SCRIPT_DIR, "teams", "nana")
DB_PATH = os.path.join(SCRIPT_DIR, "data", "fugle.db")
STOCK_FILE = os.path.join(BASE_DIR, "stock_names.json")

# Fugle API 設定
FUGLE_API_TOKEN = "ZjEwNWVkNjMtMWNmNi00ZmI0LWI5MzEtZmQyZDJmNGM4M2E1"
FUGLE_BASE = "https://api.fugle.tw/marketdata/v1.0"
HEADERS = {"X-API-KEY": FUGLE_API_TOKEN}

# RSI 分區
RSI_ZONES = {
    "OVERBOUGHT": 70,
    "NEUTRAL_HIGH": 60,
    "NEUTRAL_LOW": 40,
    "OVERSOLD": 30,
}

def get_rsi_zone(rsi: float) -> str:
    if rsi is None: return "UNKNOWN"
    if rsi >= RSI_ZONES["OVERBOUGHT"]: return "OVERBOUGHT"
    elif rsi <= RSI_ZONES["OVERSOLD"]: return "OVERSOLD"
    elif rsi >= RSI_ZONES["NEUTRAL_HIGH"]: return "NEUTRAL_HIGH"
    elif rsi <= RSI_ZONES["NEUTRAL_LOW"]: return "NEUTRAL_LOW"
    return "NEUTRAL"

def get_stock_list():
    """取得股票名單"""
    with open(STOCK_FILE, encoding='utf-8') as f:
        stocks = json.load(f)
    exclude = {'2888', '5882', '3008', '2330'}  # 已下市/表現差
    return [(k, v) for k, v in stocks.items() if k not in exclude]

# === Fugle API 呼叫 ===
def fugle_get(endpoint: str, symbol_id: str = None, params: Dict = None) -> Optional[Dict]:
    """呼叫 Fugle MarketData API（使用 X-API-KEY header）"""
    url = f"{FUGLE_BASE}/{endpoint}"
    if symbol_id:
        url = f"{url}/{symbol_id}"
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        if r.status_code == 200:
            return r.json()
        elif r.status_code == 401:
            print(f"[AUTH ERROR] Fugle API 401 Unauthorized - Token可能過期")
            return None
        elif r.status_code == 404:
            # 路徑不存在，但API可達
            return None
        else:
            print(f"[HTTP {r.status_code}] {endpoint}/{symbol_id}")
            return None
    except Exception as e:
        print(f"[NET ERROR] {endpoint}/{symbol_id}: {e}")
        return None

def init_db():
    """初始化 Fugle 資料庫"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 個股基本資料
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stocks (
            symbol TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            industry TEXT,
            type TEXT,
            last_updated TEXT
        )
    """)

    # 即時報價（最新一筆）
    cur.execute("""
        CREATE TABLE IF NOT EXISTS quote_latest (
            symbol TEXT PRIMARY KEY,
            price REAL,
            change REAL,
            change_percent REAL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            tick_type TEXT,
            bid_price REAL,
            ask_price REAL,
            rsi_14 REAL,
            zone TEXT,
            updated_at TEXT
        )
    """)

    # 分鐘K線（每檔股票最近幾天）
    cur.execute("""
        CREATE TABLE IF NOT EXISTS candles_minute (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            UNIQUE(symbol, date, time)
        )
    """)

    # 日K線
    cur.execute("""
        CREATE TABLE IF NOT EXISTS candles_daily (
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            change REAL,
            change_percent REAL,
            foreign_net INTEGER,
            trust_net INTEGER,
            dealer_net INTEGER,
            RSI_5 REAL,
            RSI_14 REAL,
            RSI_20 REAL,
            MA5 REAL,
            MA10 REAL,
            MA20 REAL,
            MA60 REAL,
            PRIMARY KEY(symbol, date)
        )
    """)

    # 法人買賣（每日）
    cur.execute("""
        CREATE TABLE IF NOT EXISTS institutional (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            foreign_net INTEGER,
            trust_net INTEGER,
            dealer_net INTEGER,
            total_net INTEGER,
            foreign_consecutive INTEGER,
            trust_consecutive INTEGER,
            UNIQUE(symbol, date)
        )
    """)

    # 技術指標快取
    cur.execute("""
        CREATE TABLE IF NOT EXISTS technical (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            indicator_type TEXT NOT NULL,
            -- SMA, RSI, KDJ, MACD, BB
            period INTEGER,
            value REAL,
            signal_line REAL,
            upper_band REAL,
            lower_band REAL,
            UNIQUE(symbol, date, indicator_type, period)
        )
    """)

    # 成交明顯（當日）
    cur.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            price REAL,
            volume INTEGER,
            tick_type TEXT,
            UNIQUE(date, time)
        )
    """)

    # 版本追蹤
    cur.execute("""
        CREATE TABLE IF NOT EXISTS db_version (
            id INTEGER PRIMARY KEY,
            version TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("INSERT OR IGNORE INTO db_version (id, version) VALUES (1, 'v1.0 Fugle Real-time Database')")

    # 指數
    cur.execute("CREATE INDEX IF NOT EXISTS idx_candles_minute_symbol ON candles_minute(symbol)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_candles_daily_symbol ON candles_daily(symbol)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_institutional_symbol ON institutional(symbol)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_technical_symbol ON technical(symbol)")

    conn.commit()
    return conn

def calc_rsi(closes: np.ndarray, period: int) -> np.ndarray:
    """計算 RSI"""
    closes = np.array(closes, dtype=float)
    if len(closes) < period + 1:
        return np.full_like(closes, np.nan)
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.convolve(gains, np.ones(period)/period, mode='valid')
    avg_loss = np.convolve(losses, np.ones(period)/period, mode='valid')
    rs = avg_gain / (avg_loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    return np.concatenate([np.full(period, np.nan), rsi])

def calc_sma(closes: np.ndarray, period: int) -> np.ndarray:
    """計算 SMA"""
    closes = np.array(closes, dtype=float)
    sma = np.full_like(closes, np.nan)
    for i in range(period - 1, len(closes)):
        sma[i] = np.mean(closes[i - period + 1:i + 1])
    return sma

def calc_kd(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, n: int = 9) -> Tuple[np.ndarray, np.ndarray]:
    """計算 KDJ"""
    closes = np.array(closes, dtype=float)
    highs = np.array(highs, dtype=float)
    lows = np.array(lows, dtype=float)
    k = np.full_like(closes, 50.0)
    d = np.full_like(closes, 50.0)
    for i in range(n, len(closes)):
        low_n = np.min(lows[i - n + 1:i + 1])
        high_n = np.max(highs[i - n + 1:i + 1])
        rsv = 100 * (closes[i] - low_n) / (high_n - low_n + 1e-10)
        k[i] = 2/3 * k[i-1] + 1/3 * rsv
        d[i] = 2/3 * d[i-1] + 1/3 * k[i]
    return k, d

def fetch_stock_info(conn: sqlite3.Connection, symbol: str, name: str) -> bool:
    """存入個股基本資料（來自 stock_names.json）"""
    cur = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO stocks (symbol, name, last_updated)
        VALUES (?, ?, ?)
    """, (symbol, name, datetime.now().isoformat()))
    conn.commit()
    return True

def fetch_quote(conn: sqlite3.Connection, symbol: str, name: str) -> bool:
    """抓取即時報價（使用 yfinance）"""
    try:
        ticker = yf.Ticker(f"{symbol}.TW")
        info = ticker.info
        price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
        prev_close = info.get("previousClose") or 0
        change = price - prev_close if price and prev_close else 0
        change_pct = (change / prev_close * 100) if prev_close else 0
        
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO quote_latest 
            (symbol, price, change, change_percent, open, high, low, close, volume, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            symbol,
            price or 0,
            change or 0,
            change_pct or 0,
            info.get("open"),
            info.get("dayHigh"),
            info.get("dayLow"),
            info.get("regularMarketPrice") or price,
            info.get("volume"),
            datetime.now().isoformat()
        ))
        conn.commit()
        return True
    except Exception as e:
        return False

def fetch_candles_daily(conn: sqlite3.Connection, symbol: str, days: int = 90) -> int:
    """抓取日K線（使用 yfinance）"""
    try:
        ticker = yf.Ticker(f"{symbol}.TW")
        hist = ticker.history(period=f"{min(days, 365)}d")
        if hist.empty or len(hist) < 20:
            return 0
        
        closes = hist["Close"].values
        highs = hist["High"].values
        lows = hist["Low"].values
        opens = hist["Open"].values
        volumes = hist["Volume"].values
        dates = [d.strftime("%Y-%m-%d") for d in hist.index]
        
        # 計算技術指標
        rsi_14 = calc_rsi(closes, 14)
        rsi_5 = calc_rsi(closes, 5)
        rsi_20 = calc_rsi(closes, 20)
        ma5 = calc_sma(closes, 5)
        ma10 = calc_sma(closes, 10)
        ma20 = calc_sma(closes, 20)
        ma60 = calc_sma(closes, 60)
        
        cur = conn.cursor()
        inserted = 0
        prev_close = None
        for i, (d, o, h, l, c, v) in enumerate(zip(dates, opens, highs, lows, closes, volumes)):
            chg = c - prev_close if prev_close is not None else 0
            chg_pct = (chg / prev_close * 100) if prev_close else 0
            
            cur.execute("""
                INSERT OR REPLACE INTO candles_daily 
                (symbol, date, open, high, low, close, volume, change, change_percent,
                 RSI_5, RSI_14, RSI_20, MA5, MA10, MA20, MA60)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol, d,
                float(o), float(h), float(l), float(c), int(v),
                round(chg, 2), round(chg_pct, 2),
                round(float(rsi_5[i]), 2) if not np.isnan(rsi_5[i]) else None,
                round(float(rsi_14[i]), 2) if not np.isnan(rsi_14[i]) else None,
                round(float(rsi_20[i]), 2) if not np.isnan(rsi_20[i]) else None,
                round(float(ma5[i]), 2) if not np.isnan(ma5[i]) else None,
                round(float(ma10[i]), 2) if not np.isnan(ma10[i]) else None,
                round(float(ma20[i]), 2) if not np.isnan(ma20[i]) else None,
                round(float(ma60[i]), 2) if not np.isnan(ma60[i]) else None,
            ))
            prev_close = c
            inserted += 1
        
        conn.commit()
        return inserted
    except Exception as e:
        print(f"[ERR] candles {symbol}: {e}")
        return 0

def fetch_technical(conn: sqlite3.Connection, symbol: str) -> int:
    """從 candles_daily 計算並存入技術指標（使用 yfinance 數據）"""
    try:
        ticker = yf.Ticker(f"{symbol}.TW")
        hist = ticker.history(period="1y")
        if hist.empty or len(hist) < 60:
            return 0
        
        closes = np.array(hist["Close"].values, dtype=float)
        highs = np.array(hist["High"].values, dtype=float)
        lows = np.array(hist["Low"].values, dtype=float)
        dates = [d.strftime("%Y-%m-%d") for d in hist.index]
        
        cur = conn.cursor()
        inserted = 0
        
        # SMA (5, 10, 20, 60)
        for period in [5, 10, 20, 60]:
            sma = calc_sma(closes, period)
            for i, d in enumerate(dates):
                if not np.isnan(sma[i]):
                    cur.execute("""
                        INSERT OR IGNORE INTO technical (symbol, date, indicator_type, period, value)
                        VALUES (?, ?, 'SMA', ?, ?)
                    """, (symbol, d, period, round(float(sma[i]), 2)))
                    inserted += 1
        
        # RSI (5, 14, 20)
        for period in [5, 14, 20]:
            rsi = calc_rsi(closes, period)
            for i, d in enumerate(dates):
                if not np.isnan(rsi[i]):
                    cur.execute("""
                        INSERT OR IGNORE INTO technical (symbol, date, indicator_type, period, value)
                        VALUES (?, ?, 'RSI', ?, ?)
                    """, (symbol, d, period, round(float(rsi[i]), 2)))
                    inserted += 1
        
        # KDJ (9,3,3)
        k, d = calc_kd(highs, lows, closes, 9)
        for i, d_str in enumerate(dates):
            if not np.isnan(k[i]):
                cur.execute("""
                    INSERT OR IGNORE INTO technical (symbol, date, indicator_type, period, value, signal_line)
                    VALUES (?, ?, 'KDJ', ?, ?, ?)
                """, (symbol, d_str, 9, round(float(k[i]), 2), round(float(d[i]), 2)))
                inserted += 1
        
        # MACD (12, 26, 9)
        ema12 = calc_sma(closes, 12)  # 簡化用 SMA
        ema26 = calc_sma(closes, 26)
        macd = ema12 - ema26
        signal = calc_sma(macd[~np.isnan(macd)], 9) if not np.all(np.isnan(macd)) else np.full_like(macd, np.nan)
        # Pad signal
        signal = np.concatenate([np.full(26 + 8, np.nan), signal])
        for i, d_str in enumerate(dates):
            if not np.isnan(macd[i]) and not np.isnan(signal[i]):
                cur.execute("""
                    INSERT OR IGNORE INTO technical (symbol, date, indicator_type, period, value, signal_line)
                    VALUES (?, ?, 'MACD', ?, ?, ?)
                """, (symbol, d_str, 12, round(float(macd[i]), 4), round(float(signal[i]), 4)))
                inserted += 1
        
        # Bollinger Bands (20)
        sma20 = calc_sma(closes, 20)
        std20 = np.array([np.std(closes[max(0,i-19):i+1]) for i in range(len(closes))])
        ubb = sma20 + 2 * std20
        lbb = sma20 - 2 * std20
        for i, d_str in enumerate(dates):
            if not np.isnan(sma20[i]):
                cur.execute("""
                    INSERT OR IGNORE INTO technical (symbol, date, indicator_type, period, value, upper_band, lower_band)
                    VALUES (?, ?, 'BB', ?, ?, ?, ?)
                """, (symbol, d_str, 20, round(float(sma20[i]), 2),
                      round(float(ubb[i]), 2), round(float(lbb[i]), 2)))
                inserted += 1
        
        conn.commit()
        return inserted
    except Exception as e:
        print(f"[ERR] tech {symbol}: {e}")
        return 0

def fetch_intraday_candles(conn: sqlite3.Connection, symbol: str) -> int:
    """抓取分鐘K線（今日）"""
    params = {"apiToken": FUGLE_API_TOKEN}
    data = fugle_get("intraday/candles", symbol, params)
    if not data or "data" not in data:
        return 0
    
    candles = data["data"].get("candles", [])
    if not candles:
        return 0
    
    cur = conn.cursor()
    inserted = 0
    today = date.today().isoformat()
    for c in candles:
        time_str = c.get("time", "")[11:]  # 去掉日期部分
        cur.execute("""
            INSERT OR IGNORE INTO candles_minute 
            (symbol, date, time, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (symbol, today, time_str, c.get("open"), c.get("high"),
              c.get("low"), c.get("close"), c.get("volume")))
        inserted += 1
    conn.commit()
    return inserted

def print_stats(conn: sqlite3.Connection):
    """印出資料庫統計"""
    cur = conn.cursor()
    print("\n=== Fugle 資料庫統計 ===")
    
    cur.execute("SELECT COUNT(*) FROM stocks")
    print(f"股票資料: {cur.fetchone()[0]} 檔")
    
    cur.execute("SELECT COUNT(*) FROM quote_latest")
    print(f"即時報價: {cur.fetchone()[0]} 檔")
    
    cur.execute("SELECT COUNT(DISTINCT symbol) FROM candles_daily")
    print(f"日K線: {cur.fetchone()[0]} 檔")
    
    cur.execute("SELECT COUNT(*) FROM candles_daily")
    print(f"日K線記錄: {cur.fetchone()[0]} 筆")
    
    cur.execute("SELECT COUNT(DISTINCT symbol) FROM technical")
    print(f"技術指標: {cur.fetchone()[0]} 檔")
    
    cur.execute("SELECT indicator_type, COUNT(*) FROM technical GROUP BY indicator_type")
    print("\n技術指標分布:")
    for itype, cnt in cur.fetchall():
        print(f"  {itype}: {cnt}")
    
    cur.execute("SELECT signal_line, COUNT(*) FROM technical WHERE signal_line IS NOT NULL GROUP BY signal_line")
    
    conn.close()

def main():
    print("=== Fugle 即時資料庫建置 ===")
    print(f"時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    conn = init_db()
    stocks = get_stock_list()
    print(f"股票數量: {len(stocks)}")
    
    # 先測試 Fugle MarketData API 是否正常
    test = fugle_get("stock/snapshot/actives/TSE", params={"trade": "value"})
    if not test:
        print("[WARN] Fugle MarketData API 無法存取（401/404），將使用 yfinance 作為主要資料來源")
        FUGLE_AVAILABLE = False
    else:
        print(f"[OK] Fugle MarketData API 連線成功")
        FUGLE_AVAILABLE = True
    
    total_quotes = 0
    total_daily = 0
    total_tech = 0
    
    # 限制並批次處理
    stocks_to_fetch = stocks[:30]  # 先做30檔
    for i, (sym, name) in enumerate(stocks_to_fetch):
        print(f"[{i+1}/{len(stocks_to_fetch)}] {sym} {name}...", end=" ")
        
        # 即時報價
        q = fetch_quote(conn, sym, name)
        total_quotes += 1 if q else 0
        
        # 日K線（90天）
        d = fetch_candles_daily(conn, sym, 90)
        total_daily += d
        if d > 0:
            # 技術指標
            t = fetch_technical(conn, sym)
            total_tech += t
        
        if (i+1) % 10 == 0:
            print(f"\n  → 已處理 {i+1} 檔")
        
        # 避免 API 限制
        time.sleep(0.3)
    
    print(f"\n總計:")
    print(f"  即時報價: {total_quotes} 檔")
    print(f"  日K線: {total_daily} 筆")
    print(f"  技術指標: {total_tech} 筆")
    
    print_stats(conn)
    print(f"\n資料庫路徑: {DB_PATH}")
    print("=== 完成 ===")

if __name__ == "__main__":
    main()
