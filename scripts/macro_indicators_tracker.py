"""
Macro Indicators Tracker
追蹤宏觀指標：VIX、美元指數、美債殖利率、TED Spread 等
"""
import requests
import sqlite3
import os
import json
import time
import logging
from datetime import datetime
from pathlib import Path

DB_PATH = "./data/macro_institutional.db"
CONFIG_PATH = "./configs/macro_config.json"
LOG_DIR = "./logs"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=f"{LOG_DIR}/macro_indicators.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def get_connection():
    return sqlite3.connect(DB_PATH)

def save_macro(date_str, indicator, value, change_pct=0, source="yfinance"):
    conn = get_connection()
    conn.execute("""
        INSERT OR REPLACE INTO macro_indicators (date, indicator, value, change_pct, source)
        VALUES (?, ?, ?, ?, ?)
    """, (date_str, indicator, value, change_pct, source))
    conn.commit()
    conn.close()

def get_yfinance_value(symbol):
    """用 yfinance 取報價"""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="5d", auto_adjust=True)
        if not hist.empty:
            last = hist["Close"].iloc[-1]
            prev = hist["Close"].iloc[-2] if len(hist) > 1 else last
            change = ((last - prev) / prev * 100) if prev else 0
            return float(last), float(change)
    except Exception as e:
        logger.warning(f"yfinance {symbol}: {e}")
    return None, None

def fetch_vix():
    """VIX 恐懼指標"""
    val, chg = get_yfinance_value("^VIX")
    if val is not None:
        save_macro(datetime.now().strftime("%Y-%m-%d"), "VIX", val, chg, "yfinance")
        return val
    return None

def fetch_dxy():
    """美元指數 DXY"""
    val, chg = get_yfinance_value("DX-Y.NYB")
    if val is not None:
        save_macro(datetime.now().strftime("%Y-%m-%d"), "DXY", val, chg, "yfinance")
        return val
    # 備援：CureNY
    val, chg = get_yfinance_value("CURE")
    return val

def fetch_us10y():
    """美國10年期公債殖利率"""
    val, chg = get_yfinance_value("^TNX")
    if val is not None:
        val = val / 100  # 轉為小數
        save_macro(datetime.now().strftime("%Y-%m-%d"), "US10Y", val, chg, "yfinance")
        return val
    return None

def fetch_us2y():
    """美國2年期公債殖利率"""
    val, chg = get_yfinance_value("^TYX")
    if val is not None:
        val = val / 100
        save_macro(datetime.now().strftime("%Y-%m-%d"), "US2Y", val, chg, "yfinance")
        return val
    return None

def fetch_ted_spread():
    """TED Spread（美元資金壓力指標）"""
    # TED = 3M LIBOR - 3M T-Bill
    # yfinance 無法直接取得，改用替代指標
    val, _ = get_yfinance_value("TED spread")
    if val is not None:
        save_macro(datetime.now().strftime("%Y-%m-%d"), "TED_SPREAD", val, 0, "yfinance")
        return val
    
    # 嘗試用利率差計算
    # 透過 yfinance 抓取相關利率
    try:
        import yfinance as yf
        # 嘗試抓取 ETF proxy
        spread_etf = yf.Ticker("TEDETF")
        hist = spread_etf.history(period="5d", auto_adjust=True)
        if not hist.empty:
            val = hist["Close"].iloc[-1]
            save_macro(datetime.now().strftime("%Y-%m-%d"), "TED_SPREAD", val, 0, "yfinance_proxy")
            return val
    except:
        pass
    return None

def fetch_all_macro():
    """一次抓取所有宏觀指標"""
    today = datetime.now().strftime("%Y-%m-%d")
    results = {}
    
    indicators = {
        "VIX": ("恐懼指標", lambda: fetch_vix()),
        "DXY": ("美元指數", lambda: fetch_dxy()),
        "US10Y": ("10Y殖利率", lambda: fetch_us10y()),
        "US2Y": ("2Y殖利率", lambda: fetch_us2y()),
        "TED_SPREAD": ("TED利差", lambda: fetch_ted_spread()),
    }
    
    for key, (label, func) in indicators.items():
        try:
            val = func()
            if val is not None:
                results[key] = val
                logger.info(f"  {key}: {val}")
            else:
                results[key] = None
                logger.warning(f"  {key}: failed")
        except Exception as e:
            logger.error(f"  {key} error: {e}")
            results[key] = None
    
    # 計算 2Y-10Y 殖利率利差（經濟衰退領先指標）
    if results.get("US10Y") and results.get("US2Y"):
        spread = results["US2Y"] - results["US10Y"]
        save_macro(today, "YIELD_SPREAD_2Y10Y", spread, 0, "calculated")
        results["YIELD_SPREAD"] = spread
        logger.info(f"  YIELD_SPREAD_2Y10Y: {spread:.4f}")
    
    return results

if __name__ == "__main__":
    results = fetch_all_macro()
    print(f"Macro indicators: {results}")
