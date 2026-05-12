# -*- coding: utf-8 -*-
"""
ray_fetch_alternatives.py
yfinance 失敗時，改用 FinMind / Shioaji 取得台股數據
"""
import sys, os, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("=== yfinance 失敗股票修復 ===")
print()

# 1. 列出 yfinance 失敗的台股範圍（2330-3000.TW）
failed_range = []
for i in range(2330, 3001):
    failed_range.append(f"{i}.TW")

print(f"待修復: {len(failed_range)} 檔")
print(f"範例: {failed_range[:5]} ... {failed_range[-5:]}")
print()

# 2. 嘗試 FinMind API
print("=== 嘗試 FinMind API ===")

def try_finmind(ticker):
    """FinMind API（免費）"""
    try:
        import requests
        # FinMind 基本資料
        url = f"https://api.finmindtrade.com/api/v4/taiwan_stock_info"
        params = {
            "dataset": "TaiwanStockInfo",
            "data_id": ticker,
            "start_date": "2024-01-01",
            "end_date": "2024-12-31"
        }
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success"):
                return True, data.get("data", [])
    except:
        pass
    return False, []

# 3. 嘗試 Shioaji（永豐金 API）
print()
print("=== 嘗試 Shioaji（永豐金）===")

def try_shioaji(ticker):
    """永豐金 Shioaji API"""
    try:
        import shioaji as sj
        api = sj.Shioaji()
        # 嘗試登入（需要憑證）
        # api.login(person_id='YOUR_ID', passwd='YOUR_PASS')
        contract = api.Contracts.Stocks[ticker]
        kbars = api.kbars(contract, start="2024-01-01", end="2024-12-31")
        return True, kbars
    except Exception as e:
        return False, str(e)

# 4. 嘗試 twstock（純 Python 方案）
print()
print("=== 嘗試 twstock（純本地）===")

def try_twstock(ticker):
    """twstock 套件"""
    try:
        import twstock
        stock = twstock.Stock(ticker.replace(".TW", ""))
        data = stock.fetch(2024, 1)  # 2024年1月
        return True, data
    except Exception as e:
        return False, str(e)

# 5. 測試各方法
print()
test_tickers = ["2330.TW", "2454.TW", "2317.TW"]

for ticker in test_tickers:
    print(f"測試 {ticker}:")

    # FinMind
    ok, data = try_finmind(ticker)
    print(f"  FinMind: {'OK' if ok else 'FAIL'}")

    # twstock
    ok, data = try_twstock(ticker)
    print(f"  twstock: {'OK' if ok else 'FAIL'} - {data if isinstance(data, str) else '成功'}")

print()
print("=== 建議 ===")
print("1. FinMind: 需要 API Token，適合大量資料")
print("2. Shioaji: 永豐金證券官方 API，需要帳號憑證")
print("3. twstock: 純本地套件，無需 API Key，但資料有限")
print()
print("推薦：先嘗試 twstock，若失敗再用 FinMind 或 Shioaji")