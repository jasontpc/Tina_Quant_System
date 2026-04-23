# -*- coding: utf-8 -*-
"""
Nana v1.0 Backtrader 框架 - 簡化版
示範核心概念
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import backtrader as bt
import yfinance as yf
import numpy as np
from datetime import datetime

class NanaStrategy(bt.Strategy):
    """
    Nana v1.0 評分策略
    評分邏輯:
    - 法人評分 (70分): 連買天數階梯
    - 技術評分 (30分): RSI + Bias
    """
    params = (
        ('rsi_period', 14),
        ('ma_fast', 20),
        ('ma_slow', 60),
        ('entry_threshold', 80),
        ('exit_threshold', 40),
        ('stop_loss', 0.07),  # 7%
        ('take_profit', 0.15),  # 15%
    )
    
    def __init__(self):
        # 技術指標
        self.rsi = bt.indicators.RSI(self.data.close, period=self.p.rsi_period)
        self.ma20 = bt.indicators.SimpleMovingAverage(self.data.close, period=self.p.ma_fast)
        self.ma60 = bt.indicators.SimpleMovingAverage(self.data.close, period=self.p.ma_slow)
        
        # 乖離率
        self.bias = (self.data.close - self.ma20) / self.ma20 * 100
    
    def log(self, txt):
        dt = self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}, {txt}')
    
    def next(self):
        """每根K線執行一次"""
        # 模擬法人數據 (實際應用需串接資料庫)
        f_consec = 3  # 假設連續買超3天
        t_consec = 1
        
        # ===== 計算 Nana 評分 =====
        score = 0
        
        # --- 法人評分 (最高70分) ---
        if f_consec == 1:
            score += 10
        elif f_consec == 2:
            score += 15
        elif f_consec == 3:
            score += 40
        elif 4 <= f_consec <= 5:
            score += 50
        elif 6 <= f_consec <= 10:
            score += 60
        elif f_consec > 10:
            score += 20
        
        if t_consec >= 3:
            score += 10
        
        # --- 技術評分 (最高30分) ---
        if 50 <= self.rsi[0] <= 70:
            score += 15
        elif 30 <= self.rsi[0] < 50:
            score += 10
        else:
            score += 5
        
        if -2 <= self.bias[0] <= 3:
            score += 15
        elif 3 < self.bias[0] <= 6:
            score += 10
        else:
            score += 0
        
        # ===== v4.21 進場門檻 =====
        ma_trend = self.ma20[0] > self.ma60[0]
        rsi_ok = self.rsi[0] < 70
        inst_ok = f_consec >= 1
        
        condition_met = ma_trend and rsi_ok and inst_ok
        
        # ===== 交易 =====
        if not self.position:
            if score >= self.p.entry_threshold and condition_met:
                self.log(f'⭐️ 買進 | 分數: {score} | 價格: {self.data.close[0]:.2f}')
                size = 1000
                self.buy(size=size)
                self.entry_price = self.data.close[0]
        
        else:
            pnl_pct = (self.data.close[0] / self.entry_price - 1) * 100
            
            if pnl_pct <= -self.p.stop_loss * 100 or pnl_pct >= self.p.take_profit * 100 or score < self.p.exit_threshold:
                self.log(f'❌ 賣出 | 分數: {score} | 損益: {pnl_pct:.1f}%')
                self.close()

def run_simple_backtest(symbol, start='2024-01-01', end='2024-12-31'):
    """簡化回測"""
    print('='*50)
    print(f' 回測 {symbol}')
    print('='*50)
    
    try:
        # 取得數據
        ticker = yf.Ticker(symbol + '.TW')
        h = ticker.history(period='1y')  # 改用 period
        
        if len(h) < 60:
            print(' 資料不足')
            return None
        
        # 篩選日期
        h = h[h.index >= start]
        if len(h) < 30:
            h = ticker.history(period='2y')
        
        # 轉為 pandas
        df = h.reset_index()
        df.columns = [c.lower() for c in df.columns]
        
        # 餵給 backtrader
        data = bt.feeds.PandasData(dataname=df, datetime=0, open=1, high=2, low=3, close=4, volume=5)
        
        cerebro = bt.Cerebro()
        cerebro.adddata(data)
        cerebro.addstrategy(NanaStrategy)
        
        # 初始資金 1000萬
        cerebro.broker.setcash(10_000_000)
        cerebro.broker.setcommission(commission=0.001425)
        
        print(f' 初始資金: {cerebro.broker.getcash():,.0f}')
        
        cerebro.run()
        
        final = cerebro.broker.getvalue()
        print(f' 期末資金: {final:,.0f}')
        print(f' 報酬率: {(final/10000000-1)*100:.2f}%')
        
        return final
    
    except Exception as e:
        print(f' 錯誤: {e}')
        return None

if __name__ == '__main__':
    print('='*50)
    print(' Nana v1.0 Backtrader 框架')
    print('='*50)
    print()
    
    # 測試單一股票
    run_simple_backtest('2330')
    
    print()
    print('='*50)
    print(' 框架就緒')
    print('='*50)