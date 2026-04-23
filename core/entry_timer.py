# -*- coding: utf-8 -*-
"""
Entry Timer Module - Tina 波段交易進場時機系統
=============================================

功能:
1. 盤中起漲點偵測
2. 價格突破確認
3. 量價配合確認
4. 內外盤比例分析

使用方法:
    from entry_timer import EntryTimer
    
    timer = EntryTimer(symbol='2330')
    result = timer.check_entry()
    
    if result['entry_signal']:
        print(f"進場! 原因: {result['reason']}")
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, time
from typing import Dict, Optional

class EntryTimer:
    """
    進場時機偵測系統
    
    偵測時機:
    1. 價格突破 (Price Breakout)
    2. 量價配合 (Volume Confirmation)
    3. 支撐回測 (Support Retest)
    4. 內外盤強勢 (Bid-Ask Strength)
    """
    
    def __init__(
        self,
        symbol: str,
        exchange: str = 'TW',
        lookback_days: int = 20,
        volume_ma_period: int = 5
    ):
        """
        初始化 EntryTimer
        
        參數:
            symbol: 股票代碼
            exchange: 交易所 ('TW' for 台股)
            lookback_days: 往前看多少天
            volume_ma_period: 成交量MA週期
        """
        self.symbol = symbol
        self.exchange = exchange
        self.lookback_days = lookback_days
        self.volume_ma_period = volume_ma_period
        
        # 前一日收盤價
        self.prev_close = None
        self.prev_high = None
        self.prev_low = None
        self.prev_volume = None
        self.volume_ma5 = None
        
        # 今日開盤價
        self.today_open = None
        self.today_high = None
        self.today_low = None
        self.today_close = None
        self.today_volume = None
        
        # 今日開盤狀態
        self.is_gap_up = False
        self.is_gap_down = False
        self.gap_pct = 0
    
    def fetch_data(self, today_only: bool = False) -> bool:
        """
        抓取股價資料
        
        返回:
            bool: 是否成功
        """
        ticker = f"{self.symbol}.{'TW' if self.exchange == 'TW' else ''}"
        
        try:
            if today_only:
                # 只抓今日 (使用一小時區間)
                df = yf.download(ticker, period='5d', interval='1h', auto_adjust=True, progress=False)
            else:
                df = yf.download(ticker, period=f'{self.lookback_days + 10}d', auto_adjust=True, progress=False)
            
            if df is None or len(df) < 5:
                return False
            
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] for c in df.columns]
            
            # 前一日資料
            prev = df.iloc[-2]
            self.prev_close = prev['Close']
            self.prev_high = prev['High']
            self.prev_low = prev['Low']
            self.prev_volume = prev['Volume']
            
            # 今日資料 (如果存在)
            today = df.iloc[-1]
            self.today_open = today.get('Open', today['Close'])
            self.today_high = today['High']
            self.today_low = today.get('Low', today['Close'])
            self.today_close = today['Close']
            self.today_volume = today['Volume']
            
            # 計算量能MA
            self.volume_ma5 = df['Volume'].rolling(5).mean().iloc[-1]
            
            # 缺口判斷
            if self.today_open and self.prev_close:
                gap = (self.today_open - self.prev_close) / self.prev_close
                if gap > 0.005:
                    self.is_gap_up = True
                    self.gap_pct = gap
                elif gap < -0.005:
                    self.is_gap_down = True
                    self.gap_pct = gap
            
            return True
        
        except Exception as e:
            return False
    
    def check_price_breakout(self) -> Dict:
        """
        價格突破偵測
        
        條件:
        - 今日突破昨日高點
        - 成交量 > 5日均量 1.5倍
        """
        result = {
            'breakout': False,
            'type': None,  # 'high', 'open', 'resistance'
            'strength': 0
        }
        
        if not all([self.today_high, self.prev_high, self.today_volume, self.volume_ma5]):
            return result
        
        # 突破昨日高點
        if self.today_high > self.prev_high:
            vol_ratio = self.today_volume / self.volume_ma5 if self.volume_ma5 > 0 else 0
            
            result['breakout'] = True
            result['type'] = 'high'
            result['strength'] = min(1.0, vol_ratio / 2)
        
        # 跳空高開
        if self.is_gap_up:
            result['breakout'] = True
            result['type'] = 'gap_up'
            result['strength'] = min(1.0, self.gap_pct * 5)
        
        return result
    
    def check_volume_confirm(self) -> Dict:
        """
        量價配合確認
        
        條件:
        - 價格上漲 + 成交量增加
        - 或價格回調 + 成交量萎縮 (健康)
        """
        result = {
            'confirmed': False,
            'type': None,  # 'strong', 'healthy', 'weak'
            'vol_ratio': 0
        }
        
        if not all([self.today_volume, self.volume_ma5, self.today_close, self.prev_close]):
            return result
        
        vol_ratio = self.today_volume / self.volume_ma5 if self.volume_ma5 > 0 else 0
        price_change = (self.today_close - self.prev_close) / self.prev_close if self.prev_close else 0
        
        result['vol_ratio'] = vol_ratio
        
        # 價漲量增 (強勢)
        if price_change > 0 and vol_ratio > 1.5:
            result['confirmed'] = True
            result['type'] = 'strong'
        
        # 價跌量縮 (健康回調)
        elif price_change < 0 and vol_ratio < 0.7:
            result['confirmed'] = True
            result['type'] = 'healthy'
        
        # 價漲量縮 (背離 - 弱)
        elif price_change > 0 and vol_ratio < 0.8:
            result['confirmed'] = False
            result['type'] = 'divergence'
        
        return result
    
    def check_support_retest(self, entry_price: float) -> Dict:
        """
        支撐回測確認
        
        條件:
        - 價格回測到關鍵支撐 (MA20, 昨日低點)
        - 出现支撐反應
        """
        result = {
            'retested': False,
            'support_level': None,
            'bounced': False
        }
        
        if not self.today_low or not self.prev_low:
            return result
        
        # 回測MA20 或 昨日低點
        support = min(self.today_low, self.prev_low)
        
        # 計算偏離
        if entry_price:
            dev_pct = (entry_price - support) / entry_price * 100
            result['support_level'] = support
            
            # 回測幅度 < 2%
            if dev_pct < 2:
                result['retested'] = True
        
        # 支撐反應: 從支撐反彈
        if self.today_close and self.today_low:
            bounce = (self.today_close - self.today_low) / self.today_low * 100
            if bounce > 0.5:
                result['bounced'] = True
        
        return result
    
    def check_intraday_entry(self, current_price: float) -> Dict:
        """
        盤中進場時機偵測
        
        這是核心邏輯，結合所有指標
        """
        result = {
            'entry_signal': False,
            'entry_score': 0,
            'reason': None,
            'details': {}
        }
        
        # 1. 價格突破
        breakout = self.check_price_breakout()
        result['details']['breakout'] = breakout
        
        # 2. 量價確認
        vol_confirm = self.check_volume_confirm()
        result['details']['volume'] = vol_confirm
        
        # 評分
        score = 0
        
        # 突破 (40分)
        if breakout['breakout']:
            score += 40 * breakout['strength']
        
        # 量價配合 (30分)
        if vol_confirm['confirmed']:
            if vol_confirm['type'] == 'strong':
                score += 30
            elif vol_confirm['type'] == 'healthy':
                score += 20
        
        # 缺口過濾 (扣分)
        if self.is_gap_up and self.gap_pct > 0.03:
            score -= 20  # 跳空太多不追
        
        if self.is_gap_down:
            score -= 30  # 跳空下跌不進
        
        # 盤中回測支撐 (加分)
        if current_price and self.today_low:
            dev = (current_price - self.today_low) / current_price * 100
            if dev < 1.5:
                score += 15
        
        result['entry_score'] = min(100, max(0, score))
        
        # 進場訊號: >= 60分
        if result['entry_score'] >= 60:
            result['entry_signal'] = True
            result['reason'] = self._get_entry_reason(breakout, vol_confirm)
        
        return result
    
    def _get_entry_reason(self, breakout: Dict, vol: Dict) -> str:
        """生成進場原因描述"""
        reasons = []
        
        if breakout['breakout']:
            reasons.append(f"突破{breakout['type']}")
        
        if vol['confirmed']:
            reasons.append(f"量{vol['type']}")
        
        if self.is_gap_up:
            reasons.append(f"跳空+{self.gap_pct*100:.1f}%")
        
        return ' + '.join(reasons) if reasons else '综合信号'
    
    def check_premarket(self) -> Dict:
        """
        盤前掃描 (9:00 前)
        
        根據昨日收盤和今日預期開盤判斷
        """
        result = {
            'action': 'watch',  # 'buy', 'watch', 'avoid'
            'score': 0,
            'reasons': []
        }
        
        if not self.prev_close:
            return result
        
        # Gap Up (观望)
        if self.is_gap_up:
            if self.gap_pct > 0.02:
                result['action'] = 'avoid'
                result['reasons'].append(f'跳空過大+{self.gap_pct*100:.1f}%')
            else:
                result['action'] = 'watch'
                result['reasons'].append(f'小幅跳空+{self.gap_pct*100:.1f}%')
        
        # Gap Down (有機會)
        if self.is_gap_down:
            if self.gap_pct < -0.02:
                result['score'] += 30
                result['reasons'].append(f'跌出機會{self.gap_pct*100:.1f}%')
        
        # 價格突破
        if self.today_high and self.today_high > self.prev_high:
            result['score'] += 25
            result['reasons'].append('突破昨日高點')
        
        return result
    
    def get_entry_price(self, strategy: str = 'limit') -> float:
        """
        取得建議進場價格
        
        策略:
        - 'limit': 限價 (參考今日低點 + 0.5%)
        - 'market': 市價
        - 'aggressive': 激进 (今日收盤價)
        """
        if strategy == 'limit':
            if self.today_low:
                return self.today_low * 1.005
            return self.prev_close * 1.002
        
        elif strategy == 'market':
            return self.today_close if self.today_close else self.prev_close
        
        else:  # aggressive
            return self.today_high if self.today_high else self.prev_close


def quick_test():
    """快速測試 Entry Timer"""
    print('='*50)
    print(' Entry Timer 模組測試')
    print('='*50)
    print()
    
    timer = EntryTimer(symbol='2330')
    
    if timer.fetch_data():
        print(f'昨日收盤: ${timer.prev_close}')
        print(f'今日開盤: ${timer.today_open}')
        print(f'今日高點: ${timer.today_high}')
        print(f'今日低點: ${timer.today_low}')
        print(f'今日收盤: ${timer.today_close}')
        print(f'量比: {timer.today_volume/timer.volume_ma5:.2f}x')
        print()
        
        # 價格突破
        breakout = timer.check_price_breakout()
        print(f'價格突破: {breakout}')
        print()
        
        # 量價確認
        vol = timer.check_volume_confirm()
        print(f'量價確認: {vol}')
        print()
        
        # 盤中進場
        if timer.today_close:
            entry = timer.check_intraday_entry(timer.today_close)
            print(f'盤中進場訊號: {entry}')
    
    else:
        print('無法取得資料')


if __name__ == '__main__':
    quick_test()