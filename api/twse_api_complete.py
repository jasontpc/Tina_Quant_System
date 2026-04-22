"""
TWSE OpenAPI Complete Integration for Tina System
臺灣證券交易所 OpenAPI 完整整合
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')
import requests
import json
import sqlite3
import time
from datetime import datetime, timedelta
from collections import deque

# ============================================
# Rate Limiter - TWSE API 限流保護
# ============================================
class RateLimiter:
    def __init__(self, max_calls=5, period=1):
        self.max_calls = max_calls
        self.period = period
        self.calls = deque()

    def wait(self):
        now = time.time()
        while self.calls and self.calls[0] <= now - self.period:
            self.calls.popleft()
        if len(self.calls) >= self.max_calls:
            sleep_time = self.period - (now - self.calls[0])
            if sleep_time > 0:
                time.sleep(sleep_time)
        self.calls.append(time.time())

rate_limiter = RateLimiter(max_calls=5, period=1)

BASE_URL = 'https://openapi.twse.com.tw/v1'
DB_PATH = 'skills/stock-analyzer/scripts/tina_master.db'

# ============================================
# 基本查詢功能
# ============================================

def get_all_stocks_today():
    """取得今日所有股票成交資訊 (1351檔)"""
    url = f'{BASE_URL}/exchangeReport/STOCK_DAY_ALL'
    rate_limiter.wait()
    resp = requests.get(url, timeout=10)
    return resp.json()

def get_stock_info(code):
    """取得特定股票資訊"""
    data = get_all_stocks_today()
    for item in data:
        if item['Code'] == code:
            return item
    return None

def get_foreign_top20():
    """取得外資持股前20名"""
    url = f'{BASE_URL}/fund/MI_QFIIS_sort_20'
    rate_limiter.wait()
    resp = requests.get(url, timeout=10)
    return resp.json()

def get_foreign_by_industry():
    """取得外资類股持股比率"""
    url = f'{BASE_URL}/fund/MI_QFIIS_cat'
    rate_limiter.wait()
    resp = requests.get(url, timeout=10)
    return resp.json()

def get_market_summary():
    """取得大盤統計資訊"""
    url = f'{BASE_URL}/exchangeReport/MI_INDEX'
    rate_limiter.wait()
    resp = requests.get(url, timeout=10)
    return resp.json()

def get_trade_rank_top20():
    """取得每日成交量前20名"""
    url = f'{BASE_URL}/exchangeReport/MI_INDEX20'
    rate_limiter.wait()
    resp = requests.get(url, timeout=10)
    return resp.json()

# ============================================
# 個股分析功能
# ============================================

def get_stock_pe_all():
    """取得全體股票本益比/殖利率/淨值比"""
    url = f'{BASE_URL}/exchangeReport/BWIBBU_ALL'
    rate_limiter.wait()
    resp = requests.get(url, timeout=10)
    return resp.json()

def get_stock_daily_avg_all():
    """取得個股日收盤價及月平均價"""
    url = f'{BASE_URL}/exchangeReport/STOCK_DAY_AVG_ALL'
    rate_limiter.wait()
    resp = requests.get(url, timeout=10)
    return resp.json()

# ============================================
# ETF 功能
# ============================================

def get_etf_rank():
    """取得ETF定期定額交易戶數統計排行"""
    url = f'{BASE_URL}/ETFReport/ETFRank'
    rate_limiter.wait()
    resp = requests.get(url, timeout=10)
    return resp.json()

# ============================================
# 指數功能
# ============================================

def get_taiwan50_index():
    """取得臺灣50指數歷史資料"""
    url = f'{BASE_URL}/indicesReport/TAI50I'
    rate_limiter.wait()
    resp = requests.get(url, timeout=10)
    return resp.json()

def get_index_historical():
    """取得發行量加權股價指數歷史資料"""
    url = f'{BASE_URL}/indicesReport/MI_5MINS_HIST'
    rate_limiter.wait()
    resp = requests.get(url, timeout=10)
    return resp.json()

# ============================================
# 券商/經紀功能
# ============================================

def get_broker_list():
    """取得證券商總公司基本資料"""
    url = f'{BASE_URL}/brokerService/brokerList'
    rate_limiter.wait()
    resp = requests.get(url, timeout=10)
    return resp.json()

def get_broker_sdr():
    """取得開辦定期定額業務證券商名單"""
    url = f'{BASE_URL}/brokerService/secRegData'
    rate_limiter.wait()
    resp = requests.get(url, timeout=10)
    return resp.json()

# ============================================
# 市場統計功能
# ============================================

def get_market_activity():
    """取得集中市場每日市場成交資訊"""
    url = f'{BASE_URL}/exchangeReport/FMTQIK'
    rate_limiter.wait()
    resp = requests.get(url, timeout=10)
    return resp.json()

def get_bi_index():
    """取得大盤統計資訊 (BI指數)"""
    url = f'{BASE_URL}/exchangeReport/BFI61U'
    rate_limiter.wait()
    resp = requests.get(url, timeout=10)
    return resp.json()

# ============================================
# 更新 watchlist 現價
# ============================================

def update_watchlist_prices(watchlist_path='skills/stock-monitor/scripts/watchlist.json'):
    """更新 watchlist 中的現價"""
    with open(watchlist_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    watchlist = data['watchlist']
    stocks = get_all_stocks_today()
    stock_dict = {s['Code']: s for s in stocks}
    
    updated = []
    for item in watchlist:
        code = item['symbol'].replace('.TW', '')
        if code in stock_dict:
            s = stock_dict[code]
            old_price = item.get('currentPrice', 0)
            new_price = float(s['ClosingPrice'])
            change = float(s['Change'])
            item['currentPrice'] = new_price
            item['change'] = change
            item['lastUpdate'] = datetime.now().strftime('%Y-%m-%d %H:%M')
            updated.append({
                'code': code,
                'old': old_price,
                'new': new_price,
                'change': change
            })
    
    with open(watchlist_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return updated

# ============================================
# 分析功能
# ============================================

def analyze_stock(code):
    """完整分析單一股票"""
    info = get_stock_info(code)
    if not info:
        return None
    
    pe_data = get_stock_pe_all()
    pe_info = None
    for item in pe_data:
        if item['Code'] == code:
            pe_info = item
            break
    
    return {
        'info': info,
        'pe_info': pe_info
    }

def get_market_status():
    """取得大盤狀態"""
    try:
        summary = get_market_summary()
        if summary and len(summary) > 0:
            return summary[0]
    except:
        pass
    return None

# ============================================
# 主程式測試
# ============================================

if __name__ == '__main__':
    print('TWSE OpenAPI 完整整合測試')
    print('=' * 60)
    
    # 1. 全體股票
    print('\n1. 取得今日所有股票成交資訊...')
    data = get_all_stocks_today()
    print(f'   共有 {len(data)} 檔股票')
    
    # 2. 大盤概況
    print('\n2. 大盤統計資訊...')
    summary = get_market_summary()
    if summary:
        print(f'   已取得大盤資料')
    
    # 3. 外資持股前20
    print('\n3. 外資持股前20名...')
    foreign = get_foreign_top20()
    for i, item in enumerate(foreign[:3], 1):
        print(f'   {i}. {item["Code"]} {item["Name"]}: {item["SharesHeldPer"]}%')
    
    # 4. 成交量前20
    print('\n4. 每日成交量前20名...')
    top20 = get_trade_rank_top20()
    print(f'   已取得成交量前20')
    
    # 5. ETF排行
    print('\n5. ETF定期定額排行...')
    etf_rank = get_etf_rank()
    print(f'   已取得 ETF 排行')
    
    # 6. 本益比資料
    print('\n6. 個股本益比/殖利率/淨值比...')
    pe_data = get_stock_pe_all()
    print(f'   共有 {len(pe_data)} 檔股票資料')
    
    # 7. 更新 watchlist
    print('\n7. 更新 watchlist 現價...')
    updated = update_watchlist_prices()
    print(f'   已更新 {len(updated)} 檔')
    
    print('\n' + '=' * 60)
    print('TWSE OpenAPI 整合完成!')
    print('=' * 60)