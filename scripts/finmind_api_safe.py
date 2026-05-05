# -*- coding: utf-8 -*-
"""
FinMind API Safety Wrapper
 Adds rate limiting and safety intervals between calls
"""
import time
import requests
from datetime import datetime, timedelta

# FinMind API settings
BASE_URL = "https://api.finmindtrade.com/api/v4/data"
TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSJ9.oCdQO1qNRUCYxHZSVuRQCqlF7X2DbQ77wury5ARCKzM"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

# Rate limiting settings (per FinMind token limits)
MIN_INTERVAL = 0.2  # 最小間隔 200ms（防止過快）
MAX_PER_MINUTE = 300  # 每分鐘不超過 300 次（保守設定，低於 600 limit）
COOLDOWN_AFTER_ERROR = 3  # 錯誤後冷卻秒數

class FinMindAPI:
    def __init__(self):
        self.last_call = 0
        self.calls_this_minute = 0
        self.minute_start = time.time()
        self.total_calls = 0
        self.total_errors = 0
    
    def _wait_if_needed(self):
        """確保不超過 rate limit"""
        now = time.time()
        
        # 重置每分鐘計數
        if now - self.minute_start >= 60:
            self.calls_this_minute = 0
            self.minute_start = now
        
        # 確保最小間隔
        elapsed = now - self.last_call
        if elapsed < MIN_INTERVAL:
            time.sleep(MIN_INTERVAL - elapsed)
        
        # 確保每分鐘不超標
        if self.calls_this_minute >= MAX_PER_MINUTE:
            sleep_time = 60 - (now - self.minute_start)
            print(f"[RateLimit] Pausing {sleep_time:.1f}s to stay under limit")
            time.sleep(sleep_time)
            self.calls_this_minute = 0
            self.minute_start = time.time()
    
    def _make_request(self, dataset, params, max_retries=3):
        """安全發起請求，自動重試"""
        for attempt in range(max_retries):
            try:
                self._wait_if_needed()
                
                resp = requests.get(
                    BASE_URL,
                    params={"dataset": dataset, **params},
                    headers=HEADERS,
                    timeout=15
                )
                
                if resp.status_code == 200:
                    self.last_call = time.time()
                    self.calls_this_minute += 1
                    self.total_calls += 1
                    return resp.json()
                
                elif resp.status_code == 429:
                    # Rate limit exceeded
                    print(f"[RateLimit] 429 received, cooling down 10s...")
                    time.sleep(10)
                    continue
                
                elif resp.status_code == 404:
                    # Not found - might be holiday/no data
                    return {"data": [], "msg": "no data"}
                
                else:
                    print(f"[Error] {resp.status_code}: {resp.text[:100]}")
                    
            except Exception as e:
                print(f"[Exception] {e}")
                self.total_errors += 1
                time.sleep(COOLDOWN_AFTER_ERROR)
        
        return {"data": [], "msg": "error after retries"}
    
    def get_stock_price(self, stock_id, start_date, end_date):
        """取得股票日線資料"""
        return self._make_request("TaiwanStockPrice", {
            "data_id": stock_id,
            "start_date": start_date,
            "end_date": end_date
        })
    
    def get_stock_info(self, stock_id):
        """取得股票基本資訊"""
        return self._make_request("TaiwanStockInfo", {
            "data_id": stock_id
        })
    
    def get_institutional(self, stock_id, start_date, end_date):
        """取得法人買賣資料"""
        return self._make_request("InstitutionalInvestorsBid", {
            "data_id": stock_id,
            "start_date": start_date,
            "end_date": end_date
        })
    
    def stats(self):
        """取得 API 使用統計"""
        return {
            "total_calls": self.total_calls,
            "total_errors": self.total_errors,
            "calls_this_minute": self.calls_this_minute,
            "uptime_minutes": (time.time() - self.minute_start) / 60
        }


# =====================
# 使用範例
# =====================
if __name__ == "__main__":
    api = FinMindAPI()
    
    print("=== FinMind API Safety Wrapper ===")
    print(f"Rate limit: {MAX_PER_MINUTE} calls/min")
    print(f"Min interval: {MIN_INTERVAL}s")
    print()
    
    # 測試：取得台積電資料
    print("Testing get_stock_price for 2330...")
    data = api.get_stock_price("2330", "2026-04-28", "2026-04-30")
    
    if data.get("data"):
        print(f"Success! Got {len(data['data'])} rows")
        print(f"Latest: {data['data'][-1]}")
    else:
        print(f"No data or error: {data.get('msg')}")
    
    print()
    print("=== API Stats ===")
    for k, v in api.stats().items():
        print(f"  {k}: {v}")