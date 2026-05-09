"""
Shioaji Real-Time Data Integration for Tina Scanner
===================================================
Data flow:
  Shioaji → 即時報價 / Tick / Kbars / 內外盤比 / 大單追蹤
  FinMind → 法人數據（維持現有）

Shioaji API credentials:
  api_key: 3r6UGMUX7bnxhnbrZ92sSseGVzL3C63kkBxH3WkAPsgW
  secret_key: FCcefW9iatHvYyp3XgSYVM1VhdmZMawjQ49Mzp97WPBF
"""

import shioaji as sj
from datetime import datetime
import time

# ========================
# Shioaji Connection Manager
# ========================
class SJConnection:
    _instance = None
    _api = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def connect(self, api_key, secret_key):
        if self._api is None or not hasattr(self._api, 'stock_account'):
            self._api = sj.Shioaji(simulation=False)
            self._api.login(api_key=api_key, secret_key=secret_key)
            print(f"[Shioaji] Connected: {self._api.stock_account.account_id}")
        return self._api
    
    def get_api(self):
        return self._api
    
    def disconnect(self):
        if self._api:
            self._api.logout()
            self._api = None
            print("[Shioaji] Disconnected")

# Singleton instance
_sj_conn = SJConnection()

def get_shioaji_api():
    return _sj_conn.connect(
        api_key="3r6UGMUX7bnxhnbrZ92sSseGVzL3C63kkBxH3WkAPsgW",
        secret_key="FCcefW9iatHvYyp3XgSYVM1VhdmZMawjQ49Mzp97WPBF"
    )


# ========================
# Real-Time Quote (Snapshot)
# ========================
def sj_get_quote(code):
    """從 Shioaji 取得即時報價"""
    try:
        api = get_shioaji_api()
        c = api.Contracts.Stocks[code]
        snap = api.snapshots([c])[0]
        return {
            'close': float(snap.close),
            'open': float(snap.open),
            'high': float(snap.high),
            'low': float(snap.low),
            'volume': int(snap.total_volume),
            'amount': float(snap.amount),
            'change': float(snap.change_price),
            'change_rate': float(snap.change_rate),
            'bid': float(snap.bid_price),
            'ask': float(snap.ask_price),
            'bid_vol': int(snap.bid_volume),
            'ask_vol': int(snap.ask_volume),
        }
    except Exception as e:
        return {'error': str(e)}


# ========================
# K-Bar Historical Data
# ========================
def sj_get_kbars(code, days=5):
    """從 Shioaji 取得分鐘K線（用於技術指標計算）"""
    try:
        api = get_shioaji_api()
        c = api.Contracts.Stocks[code]
        end = datetime.now().strftime('%Y-%m-%d')
        start = (datetime.now() - __import__('datetime').timedelta(days=days)).strftime('%Y-%m-%d')
        kb = api.kbars(c, start=start, end=end)
        return {
            'ts': kb.ts,
            'Open': kb.Open,
            'High': kb.High,
            'Low': kb.Low,
            'Close': kb.Close,
            'Volume': kb.Volume,
            'Amount': kb.Amount,
        }
    except Exception as e:
        return {'error': str(e)}


# ========================
# Internal/External Ratio (內外盤比)
# ========================
class InOutRatioCalculator:
    """從 Tick 資料計算內外盤比"""
    def __init__(self):
        self.total_bid = 0  # 外盤（主動買盤）
        self.total_ask = 0  # 內盤（主動賣盤）
        self.tick_count = 0
    
    def add_tick(self, tick_data):
        """tick_data: dict with 'bid_vol' and 'ask_vol'"""
        self.total_bid += tick_data.get('bid_vol', 0)
        self.total_ask += tick_data.get('ask_vol', 0)
        self.tick_count += 1
    
    def get_ratio(self):
        total = self.total_bid + self.total_ask
        if total == 0:
            return {'ratio': 1.0, 'bid_pct': 50.0, 'ask_pct': 50.0, 'bid_vol': 0, 'ask_vol': 0}
        ratio = self.total_bid / self.total_ask if self.total_ask > 0 else 999
        return {
            'ratio': round(ratio, 2),
            'bid_pct': round(self.total_bid / total * 100, 2),
            'ask_pct': round(self.total_ask / total * 100, 2),
            'bid_vol': self.total_bid,
            'ask_vol': self.total_ask,
            'tick_count': self.tick_count
        }


# ========================
# Big Trade Tracker (大單追蹤)
# ========================
class BigTradeTracker:
    """追蹤單筆成交金額超過門檻的大單"""
    def __init__(self, threshold_amount=1_000_000):  # 預設100萬
        self.threshold = threshold_amount
        self.buy_count = 0
        self.sell_count = 0
        self.buy_vol = 0
        self.sell_vol = 0
        self.trades = []
    
    def add_tick(self, tick_data):
        """tick_data: dict with 'amount', 'volume', 'close', 'tick_type'"""
        amount = tick_data.get('amount', 0)
        if amount >= self.threshold:
            self.trades.append({
                'time': tick_data.get('datetime', ''),
                'price': tick_data.get('close', 0),
                'volume': tick_data.get('volume', 0),
                'amount': amount,
                'direction': 'buy' if tick_data.get('tick_type') == 1 else 'sell'
            })
            if tick_data.get('tick_type') == 1:
                self.buy_count += 1
                self.buy_vol += tick_data.get('volume', 0)
            else:
                self.sell_count += 1
                self.sell_vol += tick_data.get('volume', 0)
    
    def get_stats(self):
        total = self.buy_count + self.sell_count
        return {
            'threshold': self.threshold,
            'total_big_trades': total,
            'buy_count': self.buy_count,
            'sell_count': self.sell_count,
            'buy_vol': self.buy_vol,
            'sell_vol': self.sell_vol,
            'net_flow': self.buy_vol - self.sell_vol,
            'buy_ratio': round(self.buy_count / total * 100, 1) if total > 0 else 0,
            'recent_trades': self.trades[-5:]  # 最近5筆
        }


# ========================
# Tick Streaming Handler (串流封裝)
# ========================
class TickHandler:
    """封裝 Shioaji tick 串流，自動計算內外盤比和大單"""
    def __init__(self, code, inout_calc=None, big_trade_calc=None):
        self.code = code
        self.api = get_shioaji_api()
        self.inout_calc = inout_calc or InOutRatioCalculator()
        self.big_trade_calc = big_trade_calc or BigTradeTracker()
        self.tick_count = 0
        self.running = False
    
    def _tick_callback(self, exchange, tick):
        self.tick_count += 1
        tick_dict = {
            'datetime': tick.datetime,
            'close': float(tick.close),
            'volume': tick.volume,
            'amount': float(tick.amount),
            'bid_vol': tick.bid_side_total_vol,
            'ask_vol': tick.ask_side_total_vol,
            'bid_cnt': tick.bid_side_total_cnt,
            'ask_cnt': tick.ask_side_total_cnt,
            'tick_type': tick.tick_type,  # 1=buy, 2=sell
            'fixed_trade_vol': tick.fixed_trade_vol,
        }
        # 更新計算器
        self.inout_calc.add_tick(tick_dict)
        self.big_trade_calc.add_tick(tick_dict)
    
    def start(self):
        """開始訂閱 Tick"""
        if self.running:
            return
        c = self.api.Contracts.Stocks[self.code]
        
        @self.api.on_tick_stk_v1
        def on_tick(exchange, tick):
            self._tick_callback(exchange, tick)
        
        self.api.quote.subscribe(c, quote_type=sj.constant.QuoteType.Tick)
        self.running = True
        print(f"[TickHandler] Started for {self.code}")
    
    def stop(self):
        """停止訂閱"""
        if not self.running:
            return
        try:
            c = self.api.Contracts.Stocks[self.code]
            self.api.quote.unsubscribe(c, quote_type=sj.constant.QuoteType.Tick)
        except:
            pass
        self.running = False
        print(f"[TickHandler] Stopped for {self.code}")
    
    def get_results(self):
        return {
            'tick_count': self.tick_count,
            'inout': self.inout_calc.get_ratio(),
            'big_trades': self.big_trade_calc.get_stats()
        }


# ========================
# Quick Test
# ========================
if __name__ == "__main__":
    print("=== Shioaji Real-Time Test ===")
    
    # Test 1: Quote
    print("\n1. Quote (2330):")
    q = sj_get_quote("2330")
    print(f"   Close: {q.get('close')}, Vol: {q.get('volume')}, Chg: {q.get('change')}")
    
    # Test 2: Kbars
    print("\n2. Kbars (2330, 1 day):")
    kb = sj_get_kbars("2330", days=1)
    if 'error' not in kb:
        print(f"   Rows: {len(kb.get('Close', []))}")
    
    # Test 3: Tick streaming (5 seconds)
    print("\n3. Tick Stream (2330, 5 sec):")
    handler = TickHandler("2330")
    handler.start()
    time.sleep(5)
    handler.stop()
    results = handler.get_results()
    print(f"   Ticks: {results['tick_count']}")
    print(f"   InOut: {results['inout']}")
    print(f"   Big Trades: {results['big_trades']['total_big_trades']}")
    
    # Disconnect
    _sj_conn.disconnect()
    print("\n=== Done ===")