# -*- coding: utf-8 -*-
"""
Position Sizing Module - Tina 波段交易倉位管理系統
===================================================

功能:
1. Kelly Criterion 動態倉位計算
2. 風險平價倉位管理
3. 固定比例倉位
4. 變動倉位 (根據信心度)

使用方法:
    from position_sizing import PositionSizer
    
    ps = PositionSizer(
        total_capital=3000000,  # 300萬
        max_position=0.15,     # 單一標的上限 15%
        risk_per_trade=0.02    # 每筆風險 2%
    )
    
    # 計算進場倉位
    size = ps.calculate_size(entry_price=100, stop_loss=95)
    
    print(f"建議買入: {size} 股")
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple

class PositionSizer:
    """
    倉位管理系統
    
    支援:
    - Kelly Criterion (推薦)
    - 固定比例風險
    - 信心度調整
    - 產業分散
    """
    
    def __init__(
        self,
        total_capital: float,
        max_position_ratio: float = 0.15,
        max_total_exposure: float = 0.85,
        risk_per_trade: float = 0.02,
        win_rate: float = None,
        avg_win: float = None,
        avg_loss: float = None,
        min_shares: int = 100
    ):
        """
        初始化 PositionSizer
        
        參數:
            total_capital: 總資金
            max_position_ratio: 單一標的最大占比 (default 15%)
            max_total_exposure: 總倉位上限 (default 85%)
            risk_per_trade: 每筆交易願意承受的風險比例 (default 2%)
            win_rate: 預期勝率 (可從歷史數據計算)
            avg_win: 平均獲利
            avg_loss: 平均虧損
            min_shares: 最小買入單位 (100股)
        """
        self.total_capital = total_capital
        self.max_position_ratio = max_position_ratio
        self.max_total_exposure = max_total_exposure
        self.risk_per_trade = risk_per_trade
        self.win_rate = win_rate
        self.avg_win = avg_win
        self.avg_loss = avg_loss
        self.min_shares = min_shares
        
        # 當前持倉
        self.positions = {}  # {symbol: {'shares': N, 'entry': price, 'current': price}}
        self.position_value = 0
        
        # 歷史表現
        self.trade_history = []
    
    @property
    def available_capital(self) -> float:
        """可用資金"""
        return self.total_capital * (1 - self.position_value / self.total_capital)
    
    @property
    def current_exposure(self) -> float:
        """目前總曝險"""
        return self.position_value / self.total_capital
    
    def kelly_fraction(self) -> float:
        """
        計算 Kelly Criterion 倉位比例
        
        Kelly % = W - (1-W)/R
        其中:
            W = 勝率
            R = 盈虧比 (avg_win / avg_loss)
        
        實際使用建議: Kelly * 0.5 (半 Kelly 降低波動)
        """
        if self.win_rate is None or self.avg_win is None or self.avg_loss is None:
            # 使用預設值或系統勝率
            return 0.10  # 預設 10%
        
        if self.avg_loss == 0 or pd.isna(self.avg_loss) or np.isinf(self.avg_win / self.avg_loss):
            return 0.10
        
        win_loss_ratio = self.avg_win / abs(self.avg_loss)
        if not np.isfinite(win_loss_ratio) or win_loss_ratio <= 0:
            return 0.10
        
        kelly = self.win_rate - ((1 - self.win_rate) / win_loss_ratio)
        
        # 半 Kelly (降低波動)
        kelly = kelly * 0.5
        
        # 限制在合理範圍
        kelly = max(0.02, min(0.25, kelly))
        
        return kelly
    
    def calculate_size(
        self,
        symbol: str,
        entry_price: float,
        stop_loss: float,
        confidence: float = 1.0,
        use_kelly: bool = True,
        sector: str = None
    ) -> Dict:
        """
        計算建議買入數量
        
        參數:
            symbol: 股票代碼
            entry_price: 進場價格
            stop_loss: 停損價格
            confidence: 信心度 (0.5-1.5)
            use_kelly: 是否使用 Kelly (False 則用固定風險)
            sector: 產業類別 (用於分散)
        
        返回:
            Dict with keys:
                - shares: 建議買入股數
                - investment: 投入金額
                - risk_amount: 風險金額
                - position_ratio: 占比
                - kelly_ratio: Kelly 計算的比例
                - warning: 警告訊息
        """
        result = {
            'symbol': symbol,
            'shares': 0,
            'investment': 0,
            'risk_amount': 0,
            'position_ratio': 0,
            'kelly_ratio': 0,
            'stop_loss': stop_loss,
            'entry_price': entry_price,
            'warning': None
        }
        
        # 0. 價格有效性檢查
        if not np.isfinite(entry_price) or entry_price <= 0:
            result['warning'] = f'進場價異常: {entry_price}'
            return result
        
        if not np.isfinite(stop_loss) or stop_loss <= 0:
            result['warning'] = f'停損價異常: {stop_loss}'
            return result
        
        # 1. 計算風險金額
        risk_amount = self.total_capital * self.risk_per_trade * confidence
        
        # 2. 計算每股票風險
        price_risk = abs(entry_price - stop_loss)
        
        if price_risk == 0:
            result['warning'] = '停損價=進場價，無法計算'
            return result
        
        # 3. 計算股數 (基本)
        shares_by_risk = int(risk_amount / price_risk)
        
        # 4. Kelly 計算
        if use_kelly and self.win_rate and self.avg_win and self.avg_loss:
            kelly = self.kelly_fraction()
            kelly_shares = int((self.total_capital * kelly * confidence) / entry_price)
            shares_by_risk = min(shares_by_risk, kelly_shares)
            result['kelly_ratio'] = kelly
        else:
            result['kelly_ratio'] = self.risk_per_trade
        
        # 5. 取最小單位
        shares = max(self.min_shares, int(shares_by_risk / self.min_shares) * self.min_shares)
        
        # 6. 檢查單一標的上限
        max_shares_by_ratio = int((self.total_capital * self.max_position_ratio) / entry_price)
        shares = min(shares, max_shares_by_ratio)
        
        # 7. 檢查總曝險上限
        current_used = self.position_value + (shares * entry_price)
        if current_used > self.total_capital * self.max_total_exposure:
            available = self.total_capital * self.max_total_exposure - self.position_value
            shares = max(0, int(available / entry_price / self.min_shares) * self.min_shares)
            if shares == 0:
                result['warning'] = '已達總曝險上限'
        
        # 8. 產業分散檢查
        if sector:
            sector_exposure = self.get_sector_exposure(sector)
            if sector_exposure >= 0.30:
                result['warning'] = f'{sector}產業已達30%上限'
        
        # 計算最終數值
        investment = shares * entry_price
        actual_risk = shares * price_risk
        position_ratio = investment / self.total_capital
        
        result['shares'] = shares
        result['investment'] = investment
        result['risk_amount'] = actual_risk
        result['position_ratio'] = position_ratio
        
        return result
    
    def get_sector_exposure(self, sector: str) -> float:
        """取得某產業的曝險"""
        sector_value = 0
        for sym, pos in self.positions.items():
            if pos.get('sector') == sector:
                sector_value += pos['shares'] * pos.get('current', pos['entry'])
        
        return sector_value / self.total_capital if self.total_capital > 0 else 0
    
    def add_position(
        self,
        symbol: str,
        shares: int,
        entry_price: float,
        stop_loss: float = None,
        sector: str = None
    ):
        """新增持倉"""
        self.positions[symbol] = {
            'shares': shares,
            'entry': entry_price,
            'current': entry_price,
            'stop_loss': stop_loss,
            'sector': sector,
            'entry_date': pd.Timestamp.now()
        }
        self.position_value += shares * entry_price
    
    def update_position(self, symbol: str, current_price: float):
        """更新持倉報價"""
        if symbol in self.positions:
            old_value = self.positions[symbol]['shares'] * self.positions[symbol]['current']
            self.positions[symbol]['current'] = current_price
            new_value = self.positions[symbol]['shares'] * current_price
            self.position_value += (new_value - old_value)
    
    def close_position(self, symbol: str, exit_price: float, reason: str = 'manual') -> Dict:
        """結算持倉"""
        if symbol not in self.positions:
            return {'error': '無此持倉'}
        
        pos = self.positions[symbol]
        entry = pos['entry']
        shares = pos['shares']
        
        pnl = (exit_price - entry) * shares
        pnl_pct = (exit_price / entry - 1) * 100
        
        # 記錄交易
        self.trade_history.append({
            'symbol': symbol,
            'entry': entry,
            'exit': exit_price,
            'shares': shares,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'reason': reason,
            'exit_date': pd.Timestamp.now()
        })
        
        # 移除持倉
        self.position_value -= shares * pos['current']
        del self.positions[symbol]
        
        return {
            'symbol': symbol,
            'entry': entry,
            'exit': exit_price,
            'shares': shares,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'reason': reason
        }
    
    def get_portfolio_status(self) -> Dict:
        """取得投資組合狀態"""
        total_pnl = sum(t['pnl'] for t in self.trade_history)
        winning_trades = [t for t in self.trade_history if t['pnl'] > 0]
        losing_trades = [t for t in self.trade_history if t['pnl'] <= 0]
        
        return {
            'total_capital': self.total_capital,
            'position_value': self.position_value,
            'available_capital': self.available_capital,
            'current_exposure': self.current_exposure,
            'positions_count': len(self.positions),
            'total_trades': len(self.trade_history),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / len(self.trade_history) if self.trade_history else 0,
            'total_pnl': total_pnl,
            'positions': self.positions
        }
    
    def get_stop_loss_price(self, entry_price: float, max_loss_pct: float = 0.05) -> float:
        """計算建議停損價 (預設 -5%)"""
        return entry_price * (1 - max_loss_pct)
    
    def get_target_price(self, entry_price: float, min_gain_pct: float = 0.08) -> float:
        """計算建議目標價 (預設 +8%)"""
        return entry_price * (1 + min_gain_pct)


def quick_test():
    """快速測試 Position Sizing"""
    print('='*50)
    print(' Position Sizing 模組測試')
    print('='*50)
    print()
    
    # 情境: 300萬資金
    ps = PositionSizer(
        total_capital=3_000_000,
        max_position_ratio=0.15,
        risk_per_trade=0.02,
        win_rate=0.54,  # v4.21 勝率
        avg_win=0.0142, # 平均獲利 1.42%
        avg_loss=-0.01
    )
    
    print(f'總資金: ${ps.total_capital:,.0f}')
    print(f'Kelly 倉位: {ps.kelly_fraction()*100:.1f}%')
    print()
    
    # 情境 1: 進場價 100, 停損 95
    result = ps.calculate_size(
        symbol='2330',
        entry_price=100,
        stop_loss=95,
        confidence=1.0
    )
    
    print('情境 1: 2330 @ $100, 停損 $95')
    print(f'  建議買入: {result["shares"]} 股')
    print(f'  投入金額: ${result["investment"]:,.0f}')
    print(f'  風險金額: ${result["risk_amount"]:,.0f}')
    print(f'  占比: {result["position_ratio"]*100:.1f}%')
    print()
    
    # 情境 2: 信心度 1.5
    result2 = ps.calculate_size(
        symbol='2330',
        entry_price=100,
        stop_loss=95,
        confidence=1.5
    )
    
    print('情境 2: 信心度 1.5x')
    print(f'  建議買入: {result2["shares"]} 股')
    print(f'  投入金額: ${result2["investment"]:,.0f}')
    print()
    
    # 新增持倉測試
    ps.add_position('2330', result['shares'], 100, stop_loss=95)
    print(f'已新增持倉, 目前曝險: {ps.current_exposure*100:.1f}%')
    print(f'可用資金: ${ps.available_capital:,.0f}')


if __name__ == '__main__':
    quick_test()