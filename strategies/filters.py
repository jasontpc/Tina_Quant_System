"""
v3.13 過濾器模組 - 三道防火牆
Tina Quant System

使用方式:
    from filters import VolumeGuard, GapReverseFilter, RegimeFilter
    
    if VolumeGuard.check(vif, atr) and \\
       GapReverseFilter.check(open_price, current_price, time) and \\
       RegimeFilter.check(price, ma20, ma20_slope):
        # 進場信號有效
"""

import numpy as np

# === 第一道防火牆: 量能護城河 (Volume Guard) ===
class VolumeGuard:
    """VIF < 1.5 強制捨棄"""
    VIF_THRESHOLD = 1.5
    
    @classmethod
    def check(cls, vif, atr=None):
        """
        檢查量能是否足夠
        
        Args:
            vif: 主力買賣超比率
            atr: ATR 值 (可選)
        Returns:
            bool: True = 通過, False = 過濾
        """
        if vif < cls.VIF_THRESHOLD:
            return False
        
        # 額外檢查: ATR 需要足夠波動
        if atr is not None and atr < 30:
            return False
        
        return True
    
    @classmethod
    def get_score(cls, vif):
        """取得 VIF 分數 (0-100)"""
        if vif < 0.5:
            return 0
        elif vif < 1.0:
            return 30
        elif vif < 1.5:
            return 60
        elif vif < 2.0:
            return 80
        else:
            return 100


# === 第二道防火牆: 開盤陷阱過濾 (Gap-Reverse Filter) ===
class GapReverseFilter:
    """開盤跳空 >3% 且 10:00 前未站穩視為出貨盤"""
    GAP_THRESHOLD = 0.03  # 3%
    CHECK_TIME = "10:00"  # 10:00 前
    
    @classmethod
    def check(cls, open_price, current_price, current_time=None):
        """
        檢查是否為開盤陷阱
        
        Args:
            open_price: 開盤價
            current_price: 現價
            current_time: 現在時間 (字串 "HH:MM")
        Returns:
            bool: True = 正常, False = 陷阱過濾
        """
        if open_price <= 0:
            return True
        
        gap_ratio = (current_price - open_price) / open_price
        
        # 開盤跳空超過 3%
        if abs(gap_ratio) > cls.GAP_THRESHOLD:
            # 如果是跳空下跌 (低開) = 可能是反彈
            if gap_ratio < 0:
                return True
            
            # 跳空上漲 (高開) = 檢查是否站穩開盤價
            if current_price < open_price:
                return False  # 高開低走 = 出貨盤
        
        return True
    
    @classmethod
    def get_gap_ratio(cls, open_price, current_price):
        """計算跳空比率"""
        if open_price <= 0:
            return 0
        return (current_price - open_price) / open_price * 100


# === 第三道防火牆: 環境位階檢核 (Regime Filter) ===
class RegimeFilter:
    """股價在 MA20 之上且月線斜率為正"""
    MA_PERIOD = 20
    
    @classmethod
    def check(cls, price, ma20, ma20_slope=None, lookback=5):
        """
        檢查市場環境
        
        Args:
            price: 現價
            ma20: 20日均線
            ma20_slope: MA20 斜率 (可選)
            lookback: 斜率計算回溯天數
        Returns:
            bool: True = 多頭, False = 空頭
        """
        # 條件1: 股價在 MA20 之上
        if price <= ma20:
            return False
        
        # 條件2: 股價偏離 MA20 不能太遠 (RSI 保護)
        deviation = (price - ma20) / ma20 * 100
        if deviation > 20:  # 超過 MA20 20% = 過熱
            return False
        
        # 條件3: MA20 斜率為正 (可選)
        if ma20_slope is not None and ma20_slope < 0:
            return False
        
        return True
    
    @classmethod
    def calc_slope(cls, ma20_history):
        """計算 MA20 斜率"""
        if len(ma20_history) < 5:
            return 0
        recent = ma20_history[-5:]
        if np.mean(recent) == 0:
            return 0
        return (recent[-1] - recent[0]) / recent[0]


# === 綜合過濾器工廠 ===
class FilterChain:
    """串聯三道防火牆"""
    
    def __init__(self, include_volume=True, include_gap=True, include_regime=True):
        self.volume_check = include_volume
        self.gap_check = include_gap
        self.regime_check = include_regime
    
    def check(self, signal_data):
        """
        檢查信號是否通過所有過濾器
        
        Args:
            signal_data: dict {
                'vif': float,
                'atr': float,
                'open_price': float,
                'current_price': float,
                'current_time': str,
                'price': float,
                'ma20': float,
                'ma20_slope': float
            }
        Returns:
            dict: {'pass': bool, 'reason': str, 'score': int}
        """
        reasons = []
        total_score = 100
        
        # 第一道: Volume Guard
        if self.volume_check:
            if not VolumeGuard.check(signal_data.get('vif'), signal_data.get('atr')):
                reasons.append('VIF<1.5 or ATR<30')
                total_score -= 40
        
        # 第二道: Gap-Reverse Filter
        if self.gap_check:
            if not GapReverseFilter.check(
                signal_data.get('open_price'),
                signal_data.get('current_price'),
                signal_data.get('current_time')
            ):
                reasons.append('Gap-Reverse trap')
                total_score -= 30
        
        # 第三道: Regime Filter
        if self.regime_check:
            if not RegimeFilter.check(
                signal_data.get('price'),
                signal_data.get('ma20'),
                signal_data.get('ma20_slope')
            ):
                reasons.append('Below MA20 or bearish')
                total_score -= 30
        
        passed = total_score >= 70
        
        return {
            'pass': passed,
            'reasons': reasons,
            'score': total_score,
            'filters_triggered': len(reasons)
        }


# === 版本資訊 ===
__version__ = '3.13.0'
__author__ = 'Tina Quant - Quant Developer'
