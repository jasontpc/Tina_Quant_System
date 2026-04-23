# -*- coding: utf-8 -*-
"""
MDD Monitor Module - Tina 波段交易最大回落監控系統
===================================================

功能:
1. 追蹤資金曲線最大回落 (Max Drawdown)
2. 單日最大回落預警
3. 連續虧損監控
4. 風險評估儀表板

使用方法:
    from mdd_monitor import MDDMonitor
    
    monitor = MDDMonitor(total_capital=3_000_000)
    monitor.update_equity(current_value=2_900_000)
    
    status = monitor.get_status()
    if status['mdd_warning']:
        print(f"MDD 警告: {status['mdd_pct']:.1f}%")
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional

class MDDMonitor:
    """
    最大回落監控系統
    
    監控指標:
    - Max Drawdown (MDD)
    - Current Drawdown
    - Recovery Factor
    - Risk Level
    """
    
    def __init__(
        self,
        total_capital: float,
        mdd_threshold: float = 0.15,
        daily_loss_threshold: float = 0.03,
        consecutive_loss_limit: int = 3
    ):
        """
        初始化 MDDMonitor
        
        參數:
            total_capital: 初始資金
            mdd_threshold: MDD 警告閾值 (default 15%)
            daily_loss_threshold: 單日損失警告 (default 3%)
            consecutive_loss_limit: 連續虧損警告 (default 3次)
        """
        self.initial_capital = total_capital
        self.total_capital = total_capital
        self.mdd_threshold = mdd_threshold
        self.daily_loss_threshold = daily_loss_threshold
        self.consecutive_loss_limit = consecutive_loss_limit
        
        # 歷史記錄
        self.equity_curve = []  # [{date, equity, drawdown}]
        self.peak = total_capital
        self.current_equity = total_capital
        
        # MDD 計算
        self.max_drawdown = 0
        self.max_drawdown_pct = 0
        self.current_drawdown = 0
        self.current_drawdown_pct = 0
        
        # 交易記錄
        self.trades = []  # [{date, pnl, pnl_pct}]
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        
        # 警告狀態
        self.mdd_warning = False
        self.daily_loss_warning = False
        self.loss_streak_warning = False
    
    def update_equity(self, current_value: float, date: str = None):
        """
        更新資金曲線
        
        參數:
            current_value: 目前帳戶價值
            date: 日期 (可選)
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        self.current_equity = current_value
        
        # 更新峰值
        if current_value > self.peak:
            self.peak = current_value
        
        # 計算回落
        self.current_drawdown = self.peak - current_value
        self.current_drawdown_pct = self.current_drawdown / self.peak if self.peak > 0 else 0
        
        # 更新 MDD
        if self.current_drawdown_pct > self.max_drawdown_pct:
            self.max_drawdown_pct = self.current_drawdown_pct
            self.max_drawdown = self.current_drawdown
        
        # 記錄
        self.equity_curve.append({
            'date': date,
            'equity': current_value,
            'peak': self.peak,
            'drawdown': self.current_drawdown,
            'drawdown_pct': self.current_drawdown_pct
        })
        
        # 檢查警告
        self._check_warnings()
    
    def add_trade(self, pnl: float, pnl_pct: float, date: str = None):
        """
        記錄交易結果
        
        參數:
            pnl: 絕對盈虧
            pnl_pct: 百分比盈虧
            date: 日期
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        trade = {
            'date': date,
            'pnl': pnl,
            'pnl_pct': pnl_pct
        }
        
        self.trades.append(trade)
        
        # 更新連續虧損/獲利
        if pnl < 0:
            self.consecutive_losses += 1
            self.consecutive_wins = 0
        else:
            self.consecutive_wins += 1
            self.consecutive_losses = 0
        
        self._check_warnings()
    
    def _check_warnings(self):
        """檢查各種警告條件"""
        # MDD 警告
        self.mdd_warning = self.current_drawdown_pct >= self.mdd_threshold
        
        # 單日損失警告
        if len(self.equity_curve) >= 2:
            prev_equity = self.equity_curve[-2]['equity']
            daily_change = (self.current_equity - prev_equity) / prev_equity
            self.daily_loss_warning = daily_change <= -self.daily_loss_threshold
        
        # 連續虧損警告
        self.loss_streak_warning = self.consecutive_losses >= self.consecutive_loss_limit
    
    def get_status(self) -> Dict:
        """
        取得目前監控狀態
        
        返回:
            Dict with all monitoring indicators
        """
        total_return = (self.current_equity - self.initial_capital) / self.initial_capital
        total_return_pct = total_return * 100
        
        # 勝率
        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        win_rate = len(winning_trades) / len(self.trades) if self.trades else 0
        
        # 平均獲利/虧損
        avg_win = np.mean([t['pnl_pct'] for t in winning_trades]) if winning_trades else 0
        losing_trades = [t for t in self.trades if t['pnl'] <= 0]
        avg_loss = np.mean([t['pnl_pct'] for t in losing_trades]) if losing_trades else 0
        
        # Recovery Factor
        recovery_factor = self.total_capital / self.max_drawdown if self.max_drawdown > 0 else float('inf')
        
        # 風險等級
        risk_level = 'LOW'
        if self.current_drawdown_pct >= 0.10:
            risk_level = 'MEDIUM'
        if self.current_drawdown_pct >= 0.15:
            risk_level = 'HIGH'
        if self.current_drawdown_pct >= 0.20:
            risk_level = 'CRITICAL'
        
        return {
            'initial_capital': self.initial_capital,
            'current_equity': self.current_equity,
            'total_return_pct': total_return_pct,
            'peak': self.peak,
            'max_drawdown': self.max_drawdown,
            'max_drawdown_pct': self.max_drawdown_pct * 100,
            'current_drawdown_pct': self.current_drawdown_pct * 100,
            'recovery_factor': recovery_factor,
            'risk_level': risk_level,
            'total_trades': len(self.trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate * 100,
            'avg_win_pct': avg_win * 100,
            'avg_loss_pct': abs(avg_loss) * 100,
            'consecutive_losses': self.consecutive_losses,
            'consecutive_wins': self.consecutive_wins,
            'mdd_warning': self.mdd_warning,
            'daily_loss_warning': self.daily_loss_warning,
            'loss_streak_warning': self.loss_streak_warning,
            'warnings': self._get_warning_messages()
        }
    
    def _get_warning_messages(self) -> List[str]:
        """取得警告訊息列表"""
        messages = []
        
        if self.mdd_warning:
            messages.append(f'⚠️ MDD 已達 {self.current_drawdown_pct*100:.1f}% (閾值: {self.mdd_threshold*100:.0f}%)')
        
        if self.daily_loss_warning:
            messages.append(f'⚠️ 單日損失過大 ({self.current_drawdown_pct*100:.1f}%)')
        
        if self.loss_streak_warning:
            messages.append(f'⚠️ 連續虧損 {self.consecutive_losses} 次')
        
        return messages
    
    def get_equity_curve_df(self) -> pd.DataFrame:
        """取得資金曲線 DataFrame"""
        if not self.equity_curve:
            return pd.DataFrame()
        
        return pd.DataFrame(self.equity_curve)
    
    def get_trades_df(self) -> pd.DataFrame:
        """取得交易記錄 DataFrame"""
        if not self.trades:
            return pd.DataFrame()
        
        return pd.DataFrame(self.trades)
    
    def should_reduce_position(self) -> bool:
        """
        是否應該減碼
        
        條件:
        - MDD > 10%
        - 連續虧損 >= 2次
        """
        if self.current_drawdown_pct >= 0.10:
            return True
        
        if self.consecutive_losses >= 2:
            return True
        
        return False
    
    def should_pause_trading(self) -> bool:
        """
        是否應該暫停交易
        
        條件:
        - MDD > 15%
        - 連續虧損 >= 3次
        """
        if self.current_drawdown_pct >= 0.15:
            return True
        
        if self.consecutive_losses >= 3:
            return True
        
        return False
    
    def reset(self):
        """重置監控 (新策略開始時)"""
        self.equity_curve = []
        self.trades = []
        self.peak = self.initial_capital
        self.current_equity = self.initial_capital
        self.max_drawdown = 0
        self.max_drawdown_pct = 0
        self.current_drawdown = 0
        self.current_drawdown_pct = 0
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        self.mdd_warning = False
        self.daily_loss_warning = False
        self.loss_streak_warning = False


def quick_test():
    """快速測試 MDD Monitor"""
    print('='*50)
    print(' MDD Monitor 模組測試')
    print('='*50)
    print()
    
    # 初始資金 300萬
    monitor = MDDMonitor(
        total_capital=3_000_000,
        mdd_threshold=0.15,
        daily_loss_threshold=0.03
    )
    
    # 模擬資金曲線
    values = [3_000_000, 3_100_000, 3_200_000, 3_150_000, 3_100_000, 
              3_050_000, 2_900_000, 2_850_000, 2_900_000, 3_000_000]
    
    for i, v in enumerate(values):
        monitor.update_equity(v, f'2026-04-{i+1:02d}')
    
    # 模擬交易
    pnls = [15000, -5000, 20000, -10000, -15000]
    for pnl in pnls:
        monitor.add_trade(pnl, pnl/3_000_000)
    
    # 狀態
    status = monitor.get_status()
    
    print(f'初始資金: ${status["initial_capital"]:,.0f}')
    print(f'目前資金: ${status["current_equity"]:,.0f}')
    print(f'總報酬: {status["total_return_pct"]:.2f}%')
    print()
    print(f'Max DD: {status["max_drawdown_pct"]:.2f}%')
    print(f'目前 DD: {status["current_drawdown_pct"]:.2f}%')
    print(f'風險等級: {status["risk_level"]}')
    print()
    print(f'總交易: {status["total_trades"]}')
    print(f'勝率: {status["win_rate"]:.1f}%')
    print()
    print(f'應減碼: {"是" if monitor.should_reduce_position() else "否"}')
    print(f'應暫停: {"是" if monitor.should_pause_trading() else "否"}')
    
    if status['warnings']:
        print()
        for w in status['warnings']:
            print(w)


if __name__ == '__main__':
    quick_test()