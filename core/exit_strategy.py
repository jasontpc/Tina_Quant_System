# -*- coding: utf-8 -*-
"""
Exit Strategy Module - Tina 波段交易停利停損系統
=================================================

功能:
1. ATR Trailing Stop (移動停損)
2. 目標價停利
3. 固定比例停損
4. 時間停利 (持有N日)
5. RSI 過熱過濾

使用方法:
    from exit_strategy import ExitStrategy
    
    exit_mgr = ExitStrategy(entry_price=100, atr=2.5)
    
    # 檢查是否該出場
    result = exit_mgr.check_exit(current_price=105, high_price=108)
    
    if result['should_exit']:
        print(f"出場! 原因: {result['reason']}")
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple

class ExitStrategy:
    """
    波段交易出場策略管理器
    
    支援多種出場條件:
    - ATR Trailing Stop (推薦)
    - 目標價停利
    - 固定停損
    - 時間停利
    - RSI 過熱
    """
    
    def __init__(
        self,
        entry_price: float,
        atr: float,
        atr_multiplier: float = 2.5,
        target_ratio: float = 0.10,  # 目標獲利 10%
        stop_ratio: float = 0.05,     # 停損 -5%
        max_hold_days: int = 7,
        trailing_use_high: bool = True
    ):
        """
        初始化 ExitStrategy
        
        參數:
            entry_price: 進場價格
            atr: ATR 值 (實際貨幣單位)
            atr_multiplier: ATR 倍數 (default 2.5)
            target_ratio: 目標獲利比例 (default 10%)
            stop_ratio: 停損比例 (default 5%)
            max_hold_days: 最大持有天數 (default 7)
            trailing_use_high: 是否用歷史高點計算 trailing
        """
        self.entry_price = entry_price
        self.atr = atr
        self.atr_multiplier = atr_multiplier
        self.target_ratio = target_ratio
        self.stop_ratio = stop_ratio
        self.max_hold_days = max_hold_days
        self.trailing_use_high = trailing_use_high
        
        # 內部狀態
        self.highest_price = entry_price
        self.lowest_price = entry_price
        self.trailing_stop = entry_price - (atr * atr_multiplier)
        self.target_price = entry_price * (1 + target_ratio)
        self.stop_price = entry_price * (1 - stop_ratio)
        self.hold_days = 0
        
        # 記錄進場資訊
        self.entry_date = None
        self.signals = []
    
    def update(self, current_price: float, high_price: float = None, hold_days: int = 0):
        """
        更新價格資訊，重新計算 trailing stop
        
        參數:
            current_price: 目前價格
            high_price: 區間最高價 (用於 trailing stop 計算)
            hold_days: 持有天數
        """
        self.hold_days = hold_days
        
        if high_price and high_price > self.highest_price:
            self.highest_price = high_price
        
        # ATR Trailing Stop 只會往上移動
        if self.trailing_use_high and high_price:
            new_trailing = high_price - (self.atr * self.atr_multiplier)
        else:
            new_trailing = current_price - (self.atr * self.atr_multiplier)
        
        # Trailing stop 只往上，不往下
        if new_trailing > self.trailing_stop:
            self.trailing_stop = new_trailing
    
    def check_exit(
        self,
        current_price: float,
        rsi: float = None,
        bias: float = None,
        volume_ratio: float = None,
        market_status: str = 'normal'
    ) -> Dict:
        """
        檢查是否應該出场
        
        參數:
            current_price: 目前價格
            rsi: RSI 值 (可選)
            bias: Bias 值 (可選)
            volume_ratio: 量比 (可選)
            market_status: 市場狀態 ('normal', 'bull', 'bear')
        
        返回:
            Dict with keys:
                - should_exit: bool, 是否該出场
                - reason: str, 出场原因
                - exit_type: str, 'profit'/'stop'/'trailing'/'time'/'signal'
                - profit_pct: float, 預計獲利%
                - atr_triggered: bool, 是否 ATR trailing 觸發
        """
        result = {
            'should_exit': False,
            'reason': '持有中',
            'exit_type': None,
            'profit_pct': (current_price / self.entry_price - 1) * 100,
            'atr_triggered': False,
            'details': {}
        }
        
        # 1. ATR Trailing Stop 檢查 (最推薦)
        if current_price <= self.trailing_stop:
            result['should_exit'] = True
            result['reason'] = f'ATR Trail觸發 (${self.trailing_stop:.2f})'
            result['exit_type'] = 'trailing'
            result['atr_triggered'] = True
            result['details']['trailing_stop'] = self.trailing_stop
            return result
        
        # 2. 固定停損檢查
        if current_price <= self.stop_price:
            result['should_exit'] = True
            result['reason'] = f'停損觸發 (${self.stop_price:.2f})'
            result['exit_type'] = 'stop'
            return result
        
        # 3. 目標價停利檢查
        if current_price >= self.target_price:
            # 在多頭市場可以續抱
            if market_status == 'bull' and rsi and rsi < 80:
                pass  # 續抱
            else:
                result['should_exit'] = True
                result['reason'] = f'目標價觸發 (${self.target_price:.2f})'
                result['exit_type'] = 'profit'
                return result
        
        # 4. 時間停利檢查 (持有過久)
        if self.hold_days >= self.max_hold_days:
            result['should_exit'] = True
            result['reason'] = f'持有期滿 ({self.max_hold_days}日)'
            result['exit_type'] = 'time'
            return result
        
        # 5. RSI 過熱檢查
        if rsi and rsi >= 85:
            result['should_exit'] = True
            result['reason'] = f'RSI過熱 ({rsi:.1f})'
            result['exit_type'] = 'signal'
            result['details']['rsi'] = rsi
            return result
        
        # 6. Bias 過大檢查 (可選)
        if bias and bias > 10:
            result['should_exit'] = True
            result['reason'] = f'Bias過大 ({bias:.1f}%)'
            result['exit_type'] = 'signal'
            result['details']['bias'] = bias
            return result
        
        return result
    
    def get_status(self, current_price: float) -> Dict:
        """取得目前部位的詳細狀態"""
        profit_pct = (current_price / self.entry_price - 1) * 100
        profit_amt = current_price - self.entry_price
        
        return {
            'entry_price': self.entry_price,
            'current_price': current_price,
            'highest_price': self.highest_price,
            'profit_pct': profit_pct,
            'profit_amt': profit_amt,
            'target_price': self.target_price,
            'stop_price': self.stop_price,
            'trailing_stop': self.trailing_stop,
            'distance_to_target': (self.target_price / current_price - 1) * 100 if current_price > 0 else 0,
            'distance_to_stop': (current_price / self.stop_price - 1) * 100 if current_price > 0 else 0,
            'atr': self.atr,
            'atr_multiplier': self.atr_multiplier,
            'hold_days': self.hold_days,
            'max_hold_days': self.max_hold_days
        }
    
    def should_add_position(
        self,
        current_price: float,
        rsi: float = None,
        atr_pct: float = None
    ) -> Dict:
        """
        檢查是否適合加碼
        
        條件:
        - RSI 在 50-65 區間 (健康回調)
        - ATR >= 0.5% (有波動)
        - 距離目標價還有空間
        """
        result = {
            'should_add': False,
            'reason': None,
            'max_additions': 0
        }
        
        profit_pct = (current_price / self.entry_price - 1) * 100
        
        # 已獲利 > 5% 才考慮加碼
        if profit_pct < 5:
            result['reason'] = '尚未獲利'
            return result
        
        # RSI 過熱
        if rsi and rsi >= 70:
            result['reason'] = f'RSI過熱({rsi:.1f})'
            return result
        
        # ATR 太小
        if atr_pct and atr_pct < 0.005:
            result['reason'] = f'ATR太小({atr_pct:.2%})'
            return result
        
        # 距離目標價
        if current_price >= self.target_price * 0.95:
            result['reason'] = '接近目標價'
            return result
        
        # 可以加碼
        result['should_add'] = True
        result['reason'] = '健康回調，適合加碼'
        result['max_additions'] = 2  # 最多加2次
        
        return result


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """
    計算 ATR (Average True Range)
    
    標準 ATR 計算:
    TR = max(H-L, |H-PC|, |L-PC|)
    ATR = SMA(TR, period)
    """
    pc = close.shift(1)
    tr1 = high - low
    tr2 = (high - pc).abs()
    tr3 = (low - pc).abs()
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    return atr


def atr_trailing_stop(
    df: pd.DataFrame,
    atr_period: int = 14,
    multiplier: float = 2.5,
    column: str = 'Close'
) -> pd.DataFrame:
    """
    為 DataFrame 計算 ATR Trailing Stop 欄位
    
    適合用於回測
    """
    df = df.copy()
    
    # 計算 ATR
    df['ATR'] = calculate_atr(df['High'], df['Low'], df[column], atr_period)
    
    # 初始化 trailing stop
    df['Trail_Stop'] = np.nan
    
    # 第一天使用收盤價 - ATR * 倍數
    df.loc[df.index[0], 'Trail_Stop'] = df.loc[df.index[0], column] - (df.loc[df.index[0], 'ATR'] * multiplier)
    
    # 計算 trailing stop (只往上)
    for i in range(1, len(df)):
        high = df.loc[df.index[i], 'High']
        prev_close = df.loc[df.index[i-1], column]
        prev_ts = df.loc[df.index[i-1], 'Trail_Stop']
        atr = df.loc[df.index[i], 'ATR']
        
        # 用最高價計算新的 trailing stop
        potential_ts = high - (atr * multiplier)
        
        # 只往上移動
        if potential_ts > prev_ts:
            df.loc[df.index[i], 'Trail_Stop'] = potential_ts
        else:
            df.loc[df.loc[df.index[i], 'Trail_Stop'] > prev_ts]
    
    return df


# ==================== 快速測試 ====================

def quick_test():
    """快速測試 Exit Strategy"""
    print('='*50)
    print(' Exit Strategy 模組測試')
    print('='*50)
    print()
    
    # 情境: 進場價 100, ATR=2.5
    exit_mgr = ExitStrategy(
        entry_price=100,
        atr=2.5,
        atr_multiplier=2.5,
        target_ratio=0.10,  # 10% 目標
        stop_ratio=0.05,     # 5% 停損
        max_hold_days=7
    )
    
    print(f'進場價格: ${exit_mgr.entry_price}')
    print(f'目標價格: ${exit_mgr.target_price} (+{exit_mgr.target_ratio*100:.0f}%)')
    print(f'停損價格: ${exit_mgr.stop_price} (-{exit_mgr.stop_ratio*100:.0f}%)')
    print(f'初始 ATR Trail: ${exit_mgr.trailing_stop}')
    print()
    
    # 模擬價格走勢
    trades = [
        (103, 105, 1, 68),   # Day 1: 小漲, RSI 68
        (106, 108, 2, 71),   # Day 2: 續漲, RSI 71
        (110, 112, 3, 78),   # Day 3: 大漲, RSI 78
        (112, 114, 4, 83),   # Day 4: 續漲, RSI 83 (接近過熱)
        (108, 115, 5, 82),   # Day 5: 回調但高點更高, RSI 82
        (106, 116, 6, 80),   # Day 6: 又回調, RSI 80
        (105, 117, 7, 78),   # Day 7: 持有期滿, RSI 78
    ]
    
    for price, high, day, rsi in trades:
        exit_mgr.update(price, high, day)
        result = exit_mgr.check_exit(price, rsi=rsi)
        
        status = exit_mgr.get_status(price)
        print(f'Day {day}: ${price} | Trail: ${exit_mgr.trailing_stop:.2f} | Profit: {status["profit_pct"]:.1f}%', end='')
        
        if result['should_exit']:
            print(f' | ❌ 出場: {result["reason"]}')
        else:
            print(f' | ✅ 持有')
    
    print()
    
    # 測試 ATR Trailing 觸發情境
    print('--- ATR Trail 觸發測試 ---')
    exit_mgr2 = ExitStrategy(entry_price=100, atr=2.0, atr_multiplier=2.5)
    
    prices = [102, 105, 108, 106, 104]  # 108 是高點，之後下跌
    for price in prices:
        exit_mgr2.update(price, price, 1)
        result = exit_mgr2.check_exit(price)
        print(f'${price} | Trail: ${exit_mgr2.trailing_stop:.2f}', end='')
        if result['should_exit']:
            print(f' | ❌ {result["reason"]}')
        else:
            print(f' | ✅')


if __name__ == '__main__':
    quick_test()