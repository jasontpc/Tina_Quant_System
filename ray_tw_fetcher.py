# -*- coding: utf-8 -*-
"""
ray_tw_fetcher.py — 台股數據取得（twstock + FinMind 備用）
yfinance 失敗時的替代方案
"""
import sys, os, sqlite3, json, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import numpy as np

DB = 'ray_wisdom.db'
LOG_DIR = 'logs'
os.makedirs(LOG_DIR, exist_ok=True)

# ============================================================
# 方法1: twstock（首選，無需 API Key）
# ============================================================
def fetch_twstock(ticker):
    """使用 twstock 取得台股數據"""
    try:
        import twstock
        code = ticker.replace(".TW", "")
        stock = twstock.Stock(code)
        # 抓取 2024 年以來資料
        data = stock.fetch(2024, 1)  # 2024 Jan
        if not data:
            data = stock.fetch(2023, 1)
        return data
    except Exception as e:
        return None

# ============================================================
# 方法2: FinMind API（需要 Token）
# ============================================================
FINNMIND_TOKEN = None  # 請填入你的 FinMind API Token

def fetch_finmind(ticker):
    """FinMind API"""
    if not FINNMIND_TOKEN:
        return None
    try:
        import requests
        url = "https://api.finmindtrade.com/api/v4/taiwan_stock_price"
        params = {
            "dataset": "TaiwanStockPrice",
            "data_id": ticker.replace(".TW", ""),
            "start_date": "2024-01-01",
            "end_date": "2026-05-12",
            "token": FINNMIND_TOKEN
        }
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success"):
                return data.get("data", [])
    except:
        pass
    return None

# ============================================================
# 轉換為統一格式
# ============================================================
def convert_twstock(data):
    """twstock → DataFrame"""
    if not data:
        return None
    import pandas as pd
    records = []
    for d in data:
        records.append({
            "Date": d.date,
            "Open": d.open,
            "High": d.high,
            "Low": d.low,
            "Close": d.close,
            "Volume": d.transaction
        })
    return pd.DataFrame(records)

# ============================================================
# 計算指標
# ============================================================
def calc_indicators(df):
    """計算 RSI / MA / Sharpe"""
    if df is None or df.empty:
        return None
    close = df['Close'].values
    # RSI
    delta = np.diff(close)
    gain = np.clip(delta, 0, None).mean()
    loss = np.clip(-delta, 0, None).mean()
    rs = gain / loss if loss > 0 else 0
    rsi = 100 - (100 / (1 + rs)) if rs > 0 else 50
    # MA
    ma20 = df['Close'].rolling(20).mean().iloc[-1] if len(df) >= 20 else df['Close'].iloc[-1]
    # Sharpe
    returns = df['Close'].pct_change().dropna()
    sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
    return {
        "rsi": round(rsi, 1),
        "ma20": round(ma20, 2),
        "sharpe": round(sharpe, 2),
        "last_close": round(df['Close'].iloc[-1], 2),
        "volume": int(df['Volume'].iloc[-1])
    }

# ============================================================
# 主程序：取得台股數據
# ============================================================
def fetch_tw_symbol(ticker):
    """取得單一台股"""
    # 方法1: twstock
    data = fetch_twstock(ticker)
    if data:
        df = convert_twstock(data)
        ind = calc_indicators(df)
        if ind:
            ind["symbol"] = ticker
            ind["method"] = "twstock"
            return ind

    # 方法2: FinMind
    data = fetch_finmind(ticker)
    if data:
        ind = {"symbol": ticker, "method": "finmind", "data_count": len(data)}
        return ind

    return None

# ============================================================
# 批量取得
# ============================================================
def fetch_batch(tickers):
    """批量取得台股"""
    results = []
    for t in tickers:
        result = fetch_tw_symbol(t)
        if result:
            results.append(result)
            print(f"OK: {t} -> RSI={result.get('rsi')}, close={result.get('last_close')}")
        else:
            print(f"FAIL: {t}")
    return results

# ============================================================
# 寫入 DB
# ============================================================
def write_results(results):
    if not results:
        return
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    today = time.strftime("%Y-%m-%d")
    for r in results:
        c.execute('''INSERT INTO daily_performance
            (date, symbol, pnl_ratio, sharpe_1d, note)
            VALUES (?, ?, ?, ?, ?)''',
            (today, r["symbol"], 0, r.get("sharpe", 0),
             json.dumps({"rsi": r.get("rsi"), "ma20": r.get("ma20"),
                        "volume": r.get("volume"), "method": r.get("method")})))
    conn.commit()
    conn.close()

# ============================================================
# 主程序
# ============================================================
if __name__ == "__main__":
    print("=== 台股數據取得（twstock + FinMind）===")
    print()

    # 主要台股
    tw_tickers = ["2330.TW", "2454.TW", "2317.TW", "2303.TW", "2308.TW"]

    print(f"取得 {len(tw_tickers)} 檔台股...")
    results = fetch_batch(tw_tickers)

    print()
    print(f"成功: {len(results)}/{len(tw_tickers)}")

    if results:
        write_results(results)
        print(f"寫入 {len(results)} 筆到 daily_performance")

    print()
    print("=== 完成 ===")