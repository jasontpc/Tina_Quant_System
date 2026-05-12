# -*- coding: utf-8 -*-
"""
ray_data_center.py — 經濟型數據中心
利用 32GB RAM 做本地快取，減少 API 請求次數
"""
import sys, sqlite3, json, time, logging
from datetime import datetime, timedelta
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import yfinance as yf
import pandas as pd
import numpy as np

DB = 'ray_wisdom.db'
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

_log = logging.getLogger("ray_data_center")
_log.setLevel(logging.INFO)
if not _log.handlers:
    h = logging.FileHandler(str(LOG_DIR / "ray_data_center.log"), encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    _log.addHandler(h)

# ============================================================
# 經濟型數據緩存中心
# ============================================================
class RayDataCenter:
    def __init__(self):
        self.cache = {}  # RAM 快取
        self.cache_ttl = 60  # 60 秒 TTL
        self.last_request_time = {}  # 防止過度請求

    def _make_cache_key(self, symbol, interval="1d", period="1y"):
        return f"{symbol}_{interval}_{period}"

    def get_cached(self, symbol, interval="1d", period="1y"):
        """檢查 RAM 快取是否有效"""
        key = self._make_cache_key(symbol, interval, period)
        if key in self.cache:
            ts, df = self.cache[key]
            if (datetime.now() - ts).total_seconds() < self.cache_ttl:
                return df
        return None

    def set_cached(self, symbol, interval, period, df):
        """寫入 RAM 快取"""
        key = self._make_cache_key(symbol, interval, period)
        self.cache[key] = (datetime.now(), df)
        _log.debug(f"Cached: {key} ({len(df)} rows)")

    def get_live_data(self, symbol, interval="1d", period="1y"):
        """
        經濟型抓取：60秒內不重複請求
        """
        # 檢查快取
        cached = self.get_cached(symbol, interval, period)
        if cached is not None:
            _log.debug(f"Cache hit: {symbol}")
            return cached

        # 防過度請求（每 5 秒最多一次）
        now = time.time()
        last = self.last_request_time.get(symbol, 0)
        if now - last < 5:
            _log.debug(f"Rate limit: {symbol}, wait {int(5-(now-last))}s")
            return None

        self.last_request_time[symbol] = now

        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            if not df.empty:
                self.set_cached(symbol, interval, period, df)
                return df
        except Exception as e:
            _log.warning(f"Fetch failed: {symbol} -> {e}")

        return None

    def get_clean_kline(self, df, rows=5):
        """
        Token 節約：只取最新 N 根 K 線
        """
        if df is None or df.empty:
            return ""
        tail = df.tail(rows)[['Open', 'High', 'Low', 'Close', 'Volume']]
        return tail.to_string()

    def get_indicators(self, df):
        """
        計算基本指標（本地執行，不消耗 Token）
        """
        if df is None or df.empty:
            return {}

        close = df['Close']
        close_arr = close.values if hasattr(close, 'values') else np.array(close)

        # RSI
        delta = np.diff(close_arr)
        gain = np.clip(delta, 0, None).mean()
        loss = np.clip(-delta, 0, None).mean()
        rs = gain / loss if loss > 0 else 0
        rsi = 100 - (100 / (1 + rs)) if rs > 0 else 50

        # MA
        ma5 = close.rolling(5).mean().iloc[-1] if len(close) >= 5 else close.iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1] if len(close) >= 20 else close.iloc[-1]
        ma60 = close.rolling(60).mean().iloc[-1] if len(close) >= 60 else close.iloc[-1]

        return {
            "rsi": round(rsi, 1),
            "ma5": round(ma5, 2),
            "ma20": round(ma20, 2),
            "ma60": round(ma60, 2),
            "price": round(close.iloc[-1], 2),
            "volume": int(df['Volume'].iloc[-1]),
            "change_pct": round((close.iloc[-1] / close.iloc[-2] - 1) * 100, 2) if len(close) >= 2 else 0
        }

# ============================================================
# 寫入 daily_performance
# ============================================================
def write_daily_perf(symbol, price, change_pct, rsi, sharpe=0, mdd=0):
    """將每日數據寫入 DB"""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    today = time.strftime("%Y-%m-%d")
    try:
        c.execute('''INSERT INTO daily_performance
            (date, symbol, pnl_ratio, sharpe_1d, note)
            VALUES (?, ?, ?, ?, ?)''',
            (today, symbol, change_pct / 100, sharpe,
             json.dumps({"price": price, "rsi": rsi, "mdd": mdd})))
        conn.commit()
        _log.info(f"Written: {symbol} {price} RSI:{rsi}")
    except Exception as e:
        _log.error(f"Write failed: {e}")
    conn.close()

# ============================================================
# 多標的批量更新
# ============================================================
def batch_update(symbols, interval="1d", period="1y"):
    """
    批量更新多個標的（異步非阻塞概念）
    """
    dc = RayDataCenter()
    results = []

    for sym in symbols:
        df = dc.get_live_data(sym, interval, period)
        if df is not None:
            ind = dc.get_indicators(df)
            ind["symbol"] = sym
            ind["df"] = df
            results.append(ind)
            # 寫入 daily_performance
            write_daily_perf(
                sym, ind["price"], ind["change_pct"],
                ind["rsi"]
            )
            _log.info(f"Updated: {sym} price={ind['price']} RSI={ind['rsi']}")

    return results

# ============================================================
# 主要標的列表
# ============================================================
US_SYMBOLS = ["VTI", "VOO", "QQQ", "BND", "VEA", "SPY", "GLD", "NVDA", "AMD", "TSLA"]
TW_SYMBOLS = ["2330.TW", "2454.TW"]  # 有限支援

def run_data_center():
    _log.info("=== Ray Data Center 啟動 ===")

    all_symbols = US_SYMBOLS + TW_SYMBOLS
    results = batch_update(all_symbols)

    print()
    print("=== 數據中心更新結果 ===")
    for r in results:
        print(f"  {r['symbol']}: price={r['price']} RSI={r['rsi']} MA20={r['ma20']} change={r['change_pct']}%")

    print()
    print(f"更新完成: {len(results)}/{len(all_symbols)} 檔")
    return results

if __name__ == "__main__":
    run_data_center()