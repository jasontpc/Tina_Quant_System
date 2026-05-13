# -*- coding: utf-8 -*-
"""
ray_tw_api.py — 台股數據取得（Shioaji 永豐金 + twstock 備用）
"""
import sys, os, sqlite3, json, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import numpy as np

DB = 'ray_wisdom.db'
LOG_DIR = 'logs'
os.makedirs(LOG_DIR, exist_ok=True)

# ============================================================
# Shioaji 設定（永豐金）
# ============================================================
SHIOAJI_API_KEY = "3r6UGMUX7bnxhnbrZ92sSseGVzL3C63kkBxH3WkAPsgW"
SHIOAJI_SECRET_KEY = "FCcefW9iatHvYyp3XgSYVM1VhdmZMawjQ49Mzp97WPBF"

# ============================================================
# 全域 Shioaji 實例
# ============================================================
_sj_api = None

def get_shioaji():
    """取得 Shioaji 全域實例"""
    global _sj_api
    if _sj_api is None:
        import shioaji as sj
        _sj_api = sj.Shioaji()
        _sj_api.login(
            api_key=SHIOAJI_API_KEY,
            secret_key=SHIOAJI_SECRET_KEY
        )
    return _sj_api

# ============================================================
# 方法1: Shioaji（永豐金）
# ============================================================
def fetch_shioaji(ticker, start="2024-01-01", end="2026-05-12"):
    """Shioaji 取得台股 K 線（日K）"""
    try:
        api = get_shioaji()
        code = ticker.replace(".TW", "")

        # 取得股票合約
        contract = api.Contracts.Stocks[code]

        # 取得 K 線（1 minute bars，然後計算日K）
        kbars = api.kbars(contract, start=start, end=end)

        # 轉換為日K
        import pandas as pd
        df = pd.DataFrame({
            'ts': kbars.ts,
            'Open': kbars.Open,
            'High': kbars.High,
            'Low': kbars.Low,
            'Close': kbars.Close,
            'Volume': kbars.Volume
        })

        # 將 nanosecond timestamp 轉換為日期
        df['Date'] = pd.to_datetime(df['ts'], unit='ns').dt.strftime('%Y-%m-%d')

        # 按日期分組，取最後一筆作為日K
        daily = df.groupby('Date').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).reset_index()

        return daily.to_dict('records')

    except Exception as e:
        print(f"  Shioaji ERROR: {e}")
    return None

# ============================================================
# 方法2: twstock（備用）
# ============================================================
def fetch_twstock(ticker):
    """twstock 取得台股數據"""
    try:
        import twstock
        code = ticker.replace(".TW", "")
        stock = twstock.Stock(code)
        data = stock.fetch(2024, 1)
        if not data:
            data = stock.fetch(2023, 1)
        records = []
        for d in data:
            records.append({
                'Date': d.date.strftime('%Y-%m-%d') if hasattr(d.date, 'strftime') else str(d.date),
                'Open': d.open,
                'High': d.high,
                'Low': d.low,
                'Close': d.close,
                'Volume': d.transaction
            })
        return records
    except Exception as e:
        print(f"  twstock ERROR: {e}")
    return None

# ============================================================
# 計算指標
# ============================================================
def calc_indicators(price_data):
    """計算 RSI / MA / Sharpe"""
    if not price_data:
        return None

    closes = [d.get('Close') or d.get('close') for d in price_data if d.get('Close') or d.get('close')]
    if not closes:
        return None

    closes = np.array(closes)

    # RSI
    delta = np.diff(closes)
    gain = np.clip(delta, 0, None).mean()
    loss = np.clip(-delta, 0, None).mean()
    rs = gain / loss if loss > 0 else 0
    rsi = 100 - (100 / (1 + rs)) if rs > 0 else 50

    # MA20
    ma20 = closes[-20:].mean() if len(closes) >= 20 else closes.mean()

    # Sharpe
    returns = np.diff(closes) / closes[:-1]
    sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0

    return {
        "rsi": round(rsi, 1),
        "ma20": round(ma20, 2),
        "sharpe": round(sharpe, 2),
        "last_close": round(closes[-1], 2),
        "data_count": len(closes)
    }

# ============================================================
# 主程序：取得台股數據
# ============================================================
def fetch_tw_symbol(ticker):
    """取得單一台股"""
    print(f"取得 {ticker}...")

    # 方法1: Shioaji
    print(f"  嘗試 Shioaji...")
    data = fetch_shioaji(ticker)
    if data and len(data) > 20:
        ind = calc_indicators(data)
        if ind:
            ind["symbol"] = ticker
            ind["method"] = "shioaji"
            print(f"  Shioaji OK: {ind['data_count']} 日, close={ind['last_close']}")
            return ind

    # 方法2: twstock
    print(f"  嘗試 twstock...")
    data = fetch_twstock(ticker)
    if data and len(data) > 5:
        ind = calc_indicators(data)
        if ind:
            ind["symbol"] = ticker
            ind["method"] = "twstock"
            print(f"  twstock OK: {ind['data_count']} 日, close={ind['last_close']}")
            return ind

    print(f"  全部失敗")
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
        time.sleep(1)  # 避免請求過快
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
                        "data_count": r.get("data_count"), "method": r.get("method")})))
    conn.commit()
    conn.close()

# ============================================================
# 主程序
# ============================================================
if __name__ == "__main__":
    print("=== 台股數據取得（Shioaji 永豐 + twstock）===")
    print()

    # 主要台股
    tw_tickers = [
        "2330.TW", "2454.TW", "2317.TW", "2303.TW", "2308.TW",
        "2337.TW", "2377.TW", "2449.TW", "2474.TW", "3034.TW"
    ]

    print(f"取得 {len(tw_tickers)} 檔台股...")
    results = fetch_batch(tw_tickers)

    print()
    print(f"成功: {len(results)}/{len(tw_tickers)}")

    if results:
        write_results(results)
        print(f"寫入 {len(results)} 筆到 daily_performance")

        print()
        print("=== 結果 ===")
        for r in results:
            print(f"  {r['symbol']}: RSI={r['rsi']}, MA20={r['ma20']}, close={r['last_close']}, Sharpe={r['sharpe']} ({r['method']})")

    print()
    print("=== 完成 ===")