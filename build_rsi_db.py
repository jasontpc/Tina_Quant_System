# -*- coding: utf-8 -*-
"""
Nana RSI 數據驗證資料庫建置腳本
RSI Data Verification Database Builder
建立獨立的 RSI 驗證資料庫，支援 RSI 信號回測與準確度追蹤
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
import json
import os
import time
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Tuple

import yfinance as yf
import numpy as np

# === 路徑設定 ===
BASE_DIR = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\nana"
DB_PATH = os.path.join(BASE_DIR, "..", "data", "rsi_verification.db")
STOCK_FILE = os.path.join(BASE_DIR, "stock_names.json")

# RSI 參數
RSI_PERIODS = [5, 14, 20]
HISTORY_YEARS = 2  # 回溯2年資料

# RSI 分區門檻
RSI_ZONES = {
    "OVERBOUGHT": 70,
    "NEUTRAL_HIGH": 60,
    "NEUTRAL_LOW": 40,
    "OVERSOLD": 30,
}

def get_rsi_listed_stocks():
    """取得股票名單（排除已下市/問題股）"""
    with open(STOCK_FILE, encoding='utf-8') as f:
        stocks = json.load(f)
    exclude = {'2888', '5882', '3008', '2330'}  # 已下市/表現差
    return [(k, v) for k, v in stocks.items() if k not in exclude]

def calc_rsi(closes: np.ndarray, period: int) -> np.ndarray:
    """計算 RSI"""
    closes = np.array(closes, dtype=float)  # 確保為 float
    if len(closes) < period + 1:
        return np.full_like(closes, np.nan)
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.convolve(gains, np.ones(period)/period, mode='valid')
    avg_loss = np.convolve(losses, np.ones(period)/period, mode='valid')
    rs = avg_gain / (avg_loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    # Pad 前 period 筆為 nan
    rsi = np.concatenate([np.full(period, np.nan), rsi])
    return rsi

def get_rsi_zone(rsi: float) -> str:
    """判斷 RSI 分區"""
    if np.isnan(rsi):
        return "UNKNOWN"
    if rsi >= RSI_ZONES["OVERBOUGHT"]:
        return "OVERBOUGHT"
    elif rsi <= RSI_ZONES["OVERSOLD"]:
        return "OVERSOLD"
    elif rsi >= RSI_ZONES["NEUTRAL_HIGH"]:
        return "NEUTRAL_HIGH"
    elif rsi <= RSI_ZONES["NEUTRAL_LOW"]:
        return "NEUTRAL_LOW"
    return "NEUTRAL"

def init_db():
    """初始化 RSI 驗證資料庫"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # RSI 每日數據表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS rsi_daily (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            close REAL NOT NULL,
            rsi_5 REAL,
            rsi_14 REAL,
            rsi_20 REAL,
            zone_14 TEXT,
            UNIQUE(symbol, date)
        )
    """)
    
    # RSI 信號表（記錄進場/出场信號）
    cur.execute("""
        CREATE TABLE IF NOT EXISTS rsi_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            rsi_value REAL NOT NULL,
            zone TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            -- signal_type: ENTRY_OVERSOLD, ENTRY_NEUTRAL, EXIT_OVERBOUGHT, EXIT_NEUTRAL, CROSS_ABOVE_50, CROSS_BELOW_50
            price REAL NOT NULL,
            expected_direction TEXT,
            -- expected_direction: UP, DOWN, SIDEWAYS
            verified INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, date, signal_type)
        )
    """)
    
    # RSI 信號驗證表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS rsi_verification (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            entry_date TEXT NOT NULL,
            exit_date TEXT,
            entry_price REAL NOT NULL,
            exit_price REAL,
            hold_days INTEGER,
            return_pct REAL,
            outcome TEXT,
            -- outcome: WIN, LOSS, PENDING, TIMEOUT
            verification_status TEXT DEFAULT 'PENDING',
            FOREIGN KEY(signal_id) REFERENCES rsi_signals(id),
            UNIQUE(signal_id)
        )
    """)
    
    # RSI 分區歷史表（追蹤何時進入/離開超買/超賣）
    cur.execute("""
        CREATE TABLE IF NOT EXISTS rsi_zone_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            zone TEXT NOT NULL,
            rsi_value REAL NOT NULL,
            entered_zone_date TEXT,
            days_in_zone INTEGER DEFAULT 0,
            UNIQUE(symbol, date, zone)
        )
    """)
    
    # 指數/大盤 RSI 參考表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS market_rsi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            close REAL,
            rsi_14 REAL,
            zone TEXT,
            UNIQUE(symbol, date)
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
    cur.execute("INSERT OR IGNORE INTO db_version (id, version) VALUES (1, 'v1.0 RSI Verification Database')")
    
    # 指數
    cur.execute("CREATE INDEX IF NOT EXISTS idx_rsi_daily_symbol ON rsi_daily(symbol)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_rsi_daily_date ON rsi_daily(date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_rsi_signals_symbol ON rsi_signals(symbol)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_rsi_verification_signal ON rsi_verification(signal_id)")
    
    conn.commit()
    return conn

def fetch_and_store_stock(conn: sqlite3.Connection, symbol: str, name: str, period_years: int = 2) -> Tuple[int, int]:
    """抓取股票 RSI 數據並存入資料庫"""
    ticker_str = f"{symbol}.TW"
    try:
        ticker = yf.Ticker(ticker_str)
        hist = ticker.history(period=f"{period_years}y")
        if hist.empty or len(hist) < 60:
            return 0, 0
        
        closes = hist["Close"].values
        dates = [d.strftime("%Y-%m-%d") for d in hist.index]
        
        rsi_5 = calc_rsi(closes, 5)
        rsi_14 = calc_rsi(closes, 14)
        rsi_20 = calc_rsi(closes, 20)
        
        cur = conn.cursor()
        inserted = 0
        signals = 0
        
        prev_rsi_zone = {}
        
        for i, (d, c) in enumerate(zip(dates, closes)):
            r5, r14, r20 = rsi_5[i], rsi_14[i], rsi_20[i]
            zone = get_rsi_zone(r14)
            
            # 寫入每日 RSI
            cur.execute("""
                INSERT OR REPLACE INTO rsi_daily (symbol, date, close, rsi_5, rsi_14, rsi_20, zone_14)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (symbol, d, float(c), float(r5) if not np.isnan(r5) else None,
                  float(r14) if not np.isnan(r14) else None,
                  float(r20) if not np.isnan(r20) else None, zone))
            inserted += 1
            
            # 產生信號（RSI 從超賣區反轉、突破50等）
            if not np.isnan(r14):
                prev_rsi = prev_rsi_zone.get(symbol, None)
                if prev_rsi is not None:
                    if prev_rsi == "OVERSOLD" and zone in ("NEUTRAL_LOW", "NEUTRAL", "NEUTRAL_HIGH"):
                        # RSI 離開超賣 → 潛在進場信號
                        cur.execute("""
                            INSERT OR IGNORE INTO rsi_signals (symbol, date, rsi_value, zone, signal_type, price, expected_direction)
                            VALUES (?, ?, ?, ?, 'ENTRY_OVERSOLD', ?, 'UP')
                        """, (symbol, d, float(r14), zone, float(c)))
                        signals += 1
                    elif prev_rsi == "OVERBOUGHT" and zone in ("NEUTRAL", "NEUTRAL_HIGH", "NEUTRAL_LOW"):
                        # RSI 離開超買 → 潛在出场信號
                        cur.execute("""
                            INSERT OR IGNORE INTO rsi_signals (symbol, date, rsi_value, zone, signal_type, price, expected_direction)
                            VALUES (?, ?, ?, ?, 'EXIT_OVERBOUGHT', ?, 'DOWN')
                        """, (symbol, d, float(r14), zone, float(c)))
                        signals += 1
                    elif prev_rsi not in ("OVERSOLD", "UNKNOWN") and r14 >= 50 and prev_rsi_zone.get(symbol + '_rsi', 0) < 50:
                        # RSI 突破 50
                        cur.execute("""
                            INSERT OR IGNORE INTO rsi_signals (symbol, date, rsi_value, zone, signal_type, price, expected_direction)
                            VALUES (?, ?, ?, ?, 'CROSS_ABOVE_50', ?, 'UP')
                        """, (symbol, d, float(r14), zone, float(c)))
                        signals += 1
                    elif prev_rsi not in ("OVERBOUGHT", "UNKNOWN") and r14 <= 50 and prev_rsi_zone.get(symbol + '_rsi', 100) > 50:
                        # RSI 跌破 50
                        cur.execute("""
                            INSERT OR IGNORE INTO rsi_signals (symbol, date, rsi_value, zone, signal_type, price, expected_direction)
                            VALUES (?, ?, ?, ?, 'CROSS_BELOW_50', ?, 'DOWN')
                        """, (symbol, d, float(r14), zone, float(c)))
                        signals += 1
                
                prev_rsi_zone[symbol] = zone
                prev_rsi_zone[symbol + '_rsi'] = float(r14)
        
        conn.commit()
        return inserted, signals
        
    except Exception as e:
        print(f"[ERROR] {symbol} {name}: {e}")
        return 0, 0

def fetch_market_rsi(conn: sqlite3.Connection):
    """抓取大盤指數 RSI"""
    indices = [
        ("^TWII", "台灣加權"),
        ("^TWII", "TWII"),
    ]
    for ticker_str, label in indices:
        try:
            ticker = yf.Ticker(ticker_str)
            hist = ticker.history(period="2y")
            if hist.empty:
                continue
            closes = hist["Close"].values
            dates = [d.strftime("%Y-%m-%d") for d in hist.index]
            rsi_14 = calc_rsi(closes, 14)
            
            cur = conn.cursor()
            for i, (d, c) in enumerate(zip(dates, closes)):
                if not np.isnan(rsi_14[i]):
                    zone = get_rsi_zone(rsi_14[i])
                    cur.execute("""
                        INSERT OR IGNORE INTO market_rsi (symbol, date, close, rsi_14, zone)
                        VALUES (?, ?, ?, ?, ?)
                    """, (label, d, float(c), float(rsi_14[i]), zone))
            conn.commit()
            print(f"[OK] {label} market RSI stored")
        except Exception as e:
            print(f"[ERROR] {label}: {e}")

def verify_signals(conn: sqlite3.Connection, holding_days: int = 5):
    """驗證已產生的 RSI 信號"""
    cur = conn.cursor()
    
    # 找出未驗證的信號
    cur.execute("""
        SELECT s.id, s.symbol, s.date, s.price, s.signal_type, s.expected_direction,
               d.close
        FROM rsi_signals s
        JOIN rsi_daily d ON s.symbol = d.symbol AND s.date = d.date
        WHERE s.verified = 0 AND s.signal_type IN ('ENTRY_OVERSOLD', 'CROSS_ABOVE_50')
        ORDER BY s.date DESC
        LIMIT 500
    """)
    signals = cur.fetchall()
    
    verified = 0
    for sig in signals:
        sig_id, symbol, entry_date, entry_price, sig_type, exp_dir, _ = sig
        
        # 找出進場後 N 天的價格
        cur.execute("""
            SELECT close, date FROM rsi_daily
            WHERE symbol = ? AND date > ? AND date <= ?
            ORDER BY date LIMIT ?
        """, (symbol, entry_date, (datetime.strptime(entry_date, "%Y-%m-%d") + timedelta(days=holding_days+2)).strftime("%Y-%m-%d"), holding_days))
        future_rows = cur.fetchall()
        
        if len(future_rows) >= holding_days:
            exit_price = future_rows[holding_days-1][0]
            exit_date = future_rows[holding_days-1][1]
            ret_pct = ((exit_price - entry_price) / entry_price) * 100
            
            outcome = "WIN" if (exp_dir == "UP" and ret_pct > 0) or (exp_dir == "DOWN" and ret_pct < 0) else "LOSS"
            
            cur.execute("""
                INSERT OR REPLACE INTO rsi_verification (signal_id, symbol, entry_date, exit_date, entry_price, exit_price, hold_days, return_pct, outcome, verification_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'VERIFIED')
            """, (sig_id, symbol, entry_date, exit_date, entry_price, exit_price, holding_days, round(ret_pct, 2), outcome))
            
            cur.execute("UPDATE rsi_signals SET verified = 1 WHERE id = ?", (sig_id,))
            verified += 1
    
    conn.commit()
    return verified

def print_stats(conn: sqlite3.Connection):
    """印出資料庫統計"""
    cur = conn.cursor()
    
    print("\n=== RSI 驗證資料庫統計 ===")
    
    cur.execute("SELECT COUNT(*) FROM rsi_daily")
    print(f"RSI 每日記錄: {cur.fetchone()[0]}")
    
    cur.execute("SELECT COUNT(DISTINCT symbol) FROM rsi_daily")
    print(f"股票數量: {cur.fetchone()[0]}")
    
    cur.execute("SELECT COUNT(DISTINCT date) FROM rsi_daily")
    print(f"日期範圍: {cur.fetchone()[0]} 個交易日")
    
    cur.execute("SELECT COUNT(*) FROM rsi_signals")
    print(f"RSI 信號總數: {cur.fetchone()[0]}")
    
    cur.execute("SELECT signal_type, COUNT(*) FROM rsi_signals GROUP BY signal_type")
    print("\n信號分布:")
    for stype, cnt in cur.fetchall():
        print(f"  {stype}: {cnt}")
    
    cur.execute("SELECT COUNT(*) FROM rsi_verification")
    print(f"\n已驗證信號: {cur.fetchone()[0]}")
    
    cur.execute("SELECT outcome, COUNT(*), AVG(return_pct) FROM rsi_verification WHERE outcome IN ('WIN','LOSS') GROUP BY outcome")
    print("\n驗證結果:")
    for outcome, cnt, avg_ret in cur.fetchall():
        print(f"  {outcome}: {cnt}筆, Avg={avg_ret:+.2f}%")
    
    cur.execute("SELECT zone_14, COUNT(*) FROM rsi_daily GROUP BY zone_14")
    print("\n當前 RSI 分區分布:")
    for zone, cnt in cur.fetchall():
        print(f"  {zone}: {cnt}")
    
    conn.close()

def main():
    print("=== Nana RSI 數據驗證資料庫建置 ===")
    print(f"時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    conn = init_db()
    stocks = get_rsi_listed_stocks()
    print(f"股票數量: {len(stocks)}")
    
    # 抓取個股 RSI 數據
    total_inserted = 0
    total_signals = 0
    
    for i, (sym, name) in enumerate(stocks[:50]):  # 先做50檔
        ins, sig = fetch_and_store_stock(conn, sym, name, HISTORY_YEARS)
        total_inserted += ins
        total_signals += sig
        if (i+1) % 10 == 0:
            print(f"  [{i+1}/{min(50, len(stocks))}] {sym}... inserted={ins}, signals={sig}")
    
    print(f"\n總計: {total_inserted} 筆 RSI 數據, {total_signals} 個信號")
    
    # 抓取大盤 RSI
    fetch_market_rsi(conn)
    
    # 驗證信號
    verified = verify_signals(conn, holding_days=5)
    print(f"驗證了 {verified} 個信號")
    
    # 印統計
    print_stats(conn)
    
    print(f"\n資料庫路徑: {DB_PATH}")
    print("=== 完成 ===")

if __name__ == "__main__":
    main()
