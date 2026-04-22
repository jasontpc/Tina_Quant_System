"""
API Gateway - Tina Quant System
統一 API 調用介面

使用方式:
    from api_gateway import TWSEClient, get_stock_price, update_watchlist
    
所有策略腳本都應從這裡導入，而不是直接 import twse_api_complete
"""

import sys
sys.path.insert(0, __file__.replace('api_gateway.py', ''))

# Re-export TWSE API functions
from twse_api_complete import (
    get_all_stocks_today,
    get_stock_info,
    get_foreign_top20,
    get_market_summary,
    get_trade_rank_top20,
    get_etf_rank,
    get_stock_pe_all,
    update_watchlist_prices,
    analyze_stock,
    get_market_status,
)

# Rate limiter (from twse_api_complete if available, otherwise inline)
import time
from collections import deque

class RateLimiter:
    """TWSE API 限流器 - 避免被封鎖"""
    def __init__(self, max_calls=5, period=1):
        self.max_calls = max_calls  # 每秒最多5次
        self.period = period
        self.calls = deque()
    
    def wait(self):
        """等待直到可以發送請求"""
        now = time.time()
        # 清除超時的記錄
        while self.calls and self.calls[0] <= now - self.period:
            self.calls.popleft()
        # 如果已達上限，等待
        if len(self.calls) >= self.max_calls:
            sleep_time = self.period - (now - self.calls[0])
            if sleep_time > 0:
                time.sleep(sleep_time)
        self.calls.append(time.time())

# 全域限流器實例
_global_limiter = RateLimiter(max_calls=5, period=1)

def rate_limited_request(func):
    """裝飾器：為 API 請求添加限流保護"""
    def wrapper(*args, **kwargs):
        _global_limiter.wait()
        return func(*args, **kwargs)
    return wrapper

# 便捷函數
def get_stock_price(code):
    """取得股票現價"""
    info = get_stock_info(code)
    return float(info['ClosingPrice']) if info else None

def get_market_overview():
    """取得大盤概況"""
    return get_market_status()

def get_top_gainers(limit=10):
    """取得熱門漲幅股"""
    data = get_all_stocks_today()
    gainers = []
    for item in data:
        try:
            close = float(item['ClosingPrice'])
            change = float(item['Change'])
            if change > 0:
                gainers.append({
                    'code': item['Code'],
                    'name': item['Name'],
                    'close': close,
                    'change': change,
                    'pct': change / (close - change) * 100
                })
        except:
            pass
    gainers.sort(key=lambda x: -x['pct'])
    return gainers[:limit]

def get_top_volume(limit=10):
    """取得成交量前几名"""
    data = get_all_stocks_today()
    volumes = []
    for item in data:
        try:
            volumes.append({
                'code': item['Code'],
                'name': item['Name'],
                'volume': int(item['TradeVolume'])
            })
        except:
            pass
    volumes.sort(key=lambda x: -x['volume'])
    return volumes[:limit]

# 版本資訊
__version__ = '1.0.0'
__author__ = 'Tina Quant System'
