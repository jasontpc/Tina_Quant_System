"""
Shioaji + FinMind 整合數據模組
優先使用 Shioaji 即時數據，FinMind 作為備援與法人資料來源
"""

import shioaji as sj
from datetime import datetime, timedelta

# ========================
# Shioaji 即時數據
# ========================
class ShioajiData:
    def __init__(self, api_key, secret_key):
        self.api = sj.Shioaji(simulation=False)
        self.api.login(api_key=api_key, secret_key=secret_key)
        self.connected = True
        print(f"Shioaji 已連線: {self.api.stock_account.account_id}")
    
    def get_snapshot(self, code):
        """取得即時報價快照"""
        try:
            c = self.api.Contracts.Stocks[code]
            snap = self.api.snapshots([c])[0]
            return {
                'close': float(snap.close),
                'open': float(snap.open),
                'high': float(snap.high),
                'low': float(snap.low),
                'volume': int(snap.total_volume),
                'amount': float(snap.amount),
                'change': float(snap.change_price),
                'change_rate': float(snap.change_rate)
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_kbars(self, code, days=5):
        """取得分鐘K線數據（可用於計算技術指標）"""
        try:
            c = self.api.Contracts.Stocks[code]
            end = datetime.now().strftime('%Y-%m-%d')
            start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            kb = self.api.kbars(c, start=start, end=end)
            return {
                'ts': kb.ts,
                'Open': kb.Open,
                'High': kb.High,
                'Low': kb.Low,
                'Close': kb.Close,
                'Volume': kb.Volume,
                'Amount': kb.Amount
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_tick_data(self, code, callback=None):
        """
        訂閱逐筆成交（需搭配 callback）
        Tick 包含: bid_side_total_vol, ask_side_total_vol, volume, amount, close
        """
        c = self.api.Contracts.Stocks[code]
        
        @self.api.on_tick_stk_v1
        def on_tick(exchange, tick):
            data = {
                'datetime': tick.datetime,
                'close': float(tick.close),
                'volume': tick.volume,
                'amount': float(tick.amount),
                'bid_vol': tick.bid_side_total_vol,   # 外盤
                'ask_vol': tick.ask_side_total_vol,   # 內盤
                'bid_cnt': tick.bid_side_total_cnt,
                'ask_cnt': tick.ask_side_total_cnt,
                'fixed_trade_vol': tick.fixed_trade_vol,  # 大單
                'tick_type': tick.tick_type  # 1=buy, 2=sell
            }
            if callback:
                callback(data)
        
        self.api.quote.subscribe(c, quote_type=sj.constant.QuoteType.Tick)
        return True
    
    def unsubscribe_tick(self, code):
        c = self.api.Contracts.Stocks[code]
        self.api.quote.unsubscribe(c, quote_type=sj.constant.QuoteType.Tick)
    
    def get_bidask(self, code, callback=None):
        """訂閱五檔報價（Bid/Ask）"""
        c = self.api.Contracts.Stocks[code]
        
        @self.api.on_quote_stk_v1
        def on_quote(exchange, bidask):
            data = {
                'datetime': bidask.datetime,
                'bid': [float(b) for b in bidask.bid_price],
                'ask': [float(a) for a in bidask.ask_price],
                'bid_vol': [int(v) for v in bidask.bid_volume],
                'ask_vol': [int(v) for v in bidask.ask_volume]
            }
            if callback:
                callback(data)
        
        self.api.quote.subscribe(c, quote_type=sj.constant.QuoteType.BidAsk)
        return True
    
    def logout(self):
        self.api.logout()


# ========================
# FinMind 法人數據（備援/法人）
# ========================
import urllib.request
import json

FINMIND_BASE = "https://api.finmindtrade.com/api/v4/data"
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjJ9.1LHB4yKHeZFoXStyjK2W9F6X3nZLMA1IfPWpDVlv6K0"

def fetch_institutional_finmind(code, days=5):
    """從 FinMind 取法人數據（外资/投信/自营）"""
    date_to = datetime.now().strftime('%Y-%m-%d')
    date_from = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    url = f"{FINMIND_BASE}?dataset=TaiwanStockInstitutionalInvestorsBuySell&data_id={code}&start_date={date_from}&end_date={date_to}&token={FINMIND_TOKEN}"
    
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
            rows = data.get('data', [])
            if not rows:
                return None
            
            # 取最新一天的數據
            latest_date = max(r['date'] for r in rows)
            day_rows = [r for r in rows if r['date'] == latest_date]
            
            result = {'foreign': 0, 'trust': 0, 'dealer': 0}
            for r in day_rows:
                name = r.get('name', '')
                net = r.get('buy', 0) - r.get('sell', 0)
                if name == 'Foreign_Investor':
                    result['foreign'] = net
                elif name == 'Investment_Trust':
                    result['trust'] = net
                elif 'Dealer' in name:
                    result['dealer'] += net
            
            return result
    except Exception as e:
        return {'error': str(e)}


# ========================
# 大單追蹤分析
# ========================
class BigTradeTracker:
    """大單追蹤器 - 從 Tick 資料分析大單"""
    
    def __init__(self, threshold_amount=1000000):  # 100萬/筆
        self.threshold = threshold_amount
        self.trades = []
        self.buy_big = 0   # 大單買入筆數
        self.sell_big = 0  # 大單賣出筆數
        self.buy_vol = 0   # 大單買入股數
        self.sell_vol = 0  # 大單賣出股數
    
    def process_tick(self, tick):
        """處理逐筆資料，判斷是否為大單"""
        amount = float(tick['amount'])
        if amount >= self.threshold:
            self.trades.append(tick)
            if tick['tick_type'] == 1:  # buy
                self.buy_big += 1
                self.buy_vol += tick['volume']
            else:  # sell
                self.sell_big += 1
                self.sell_vol += tick['volume']
    
    def get_stats(self):
        """取得大單統計"""
        total_big = self.buy_big + self.sell_big
        return {
            'big_trade_count': total_big,
            'big_buy_count': self.buy_big,
            'big_sell_count': self.sell_big,
            'big_buy_vol': self.buy_vol,
            'big_sell_vol': self.sell_vol,
            'net_big_flow': self.buy_vol - self.sell_vol,
            'buy_ratio': self.buy_big / total_big if total_big > 0 else 0
        }


# ========================
# 內外盤比計算
# ========================
class InOutRatio:
    """內外盤比計算器"""
    
    def __init__(self):
        self.total_bid_vol = 0  # 外盤（主動買）
        self.total_ask_vol = 0  # 內盤（主動賣）
    
    def process_tick(self, tick):
        self.total_bid_vol += tick.get('bid_vol', 0)
        self.total_ask_vol += tick.get('ask_vol', 0)
    
    def get_ratio(self):
        total = self.total_bid_vol + self.total_ask_vol
        if total == 0:
            return {'ratio': 1.0, 'bid_pct': 50, 'ask_pct': 50}
        ratio = self.total_bid_vol / self.total_ask_vol
        bid_pct = self.total_bid_vol / total * 100
        ask_pct = self.total_ask_vol / total * 100
        return {
            'ratio': ratio,
            'bid_pct': round(bid_pct, 2),
            'ask_pct': round(ask_pct, 2),
            'bid_vol': self.total_bid_vol,
            'ask_vol': self.total_ask_vol
        }


# ========================
# 整合示範
# ========================
if __name__ == "__main__":
    # Test Shioaji
    print("=== 測試 Shioaji ===")
    shioaji = ShioajiData(
        api_key="3r6UGMUX7bnxhnbrZ92sSseGVzL3C63kkBxH3WkAPsgW",
        secret_key="FCcefW9iatHvYyp3XgSYVM1VhdmZMawjQ49Mzp97WPBF"
    )
    
    # Snapshot
    snap = shioaji.get_snapshot("2330")
    print(f"2330 Snapshot: {snap}")
    
    # Kbars
    kb = shioaji.get_kbars("2330", days=1)
    print(f"Kbars rows: {len(kb.get('Close', []))}")
    
    shioaji.logout()
    
    # Test FinMind
    print("\n=== 測試 FinMind 法人 ===")
    inst = fetch_institutional_finmind("2330", days=5)
    print(f"Institutional: {inst}")