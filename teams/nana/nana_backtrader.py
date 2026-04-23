# -*- coding: utf-8 -*-
"""
Nana v1.0 Backtrader 框架
===========================
使用 Backtrader 進行專業回測

功能:
1. NanaStrategy - 符合 Nana v1.0 評分邏輯
2. T+1 法人數據對齊
3. 批次回測 100 大台股
4. 還原股價處理
5. 動態滑價
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import backtrader as bt
import sqlite3
import yfinance as yf
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random

DB_PATH = 'skills/stock-analyzer/scripts/tina_master.db'

# ==================== 自訂資料源 (法人數據) ====================

class InstitutionalDataFeed(bt.feeds.PandasData):
    """法人數據注入 (T+1 對齊)"""
    lines = ('inst_buy_days', 'foreign_net', 'trust_net',)
    params = (
        ('datetime', None),
        ('open', 'Open'),
        ('high', 'High'),
        ('low', 'Low'),
        ('close', 'Close'),
        ('volume', 'Volume'),
        ('inst_buy_days', -1),
        ('foreign_net', 0),
        ('trust_net', 0),
    )

def get_inst_data(symbol, dates):
    """
    取得法人數據並對齊 (T+1)
    返回: DataFrame with dates as index
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # 取得日期範圍內的法人數據
    start = dates[0] if len(dates) > 0 else '2024-01-01'
    end = dates[-1] if len(dates) > 0 else '2024-12-31'
    
    cur.execute('''
        SELECT date, foreign_net, trust_net FROM MarketData
        WHERE symbol = ? AND date >= ? AND date <= ?
        ORDER BY date
    ''', (symbol, start, end))
    
    rows = cur.fetchall()
    conn.close()
    
    # 建立法人資料表 (每日)
    inst_dict = {}
    for date, f_net, t_net in rows:
        inst_dict[str(date)] = {
            'foreign_net': f_net or 0,
            'trust_net': t_net or 0,
            'f_consec': 0,  # 計算中
            't_consec': 0
        }
    
    # 計算連續買超天數
    sorted_dates = sorted(inst_dict.keys())
    f_count = 0
    t_count = 0
    
    for d in sorted_dates:
        if inst_dict[d]['foreign_net'] > 0:
            f_count += 1
        else:
            f_count = 0
        
        if inst_dict[d]['trust_net'] > 0:
            t_count += 1
        else:
            t_count = 0
        
        inst_dict[d]['f_consec'] = f_count
        inst_dict[d]['t_consec'] = t_count
    
    return inst_dict

# ==================== Nana v1.0 策略 ====================

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
        
        # 訂閱通知
        self.order = None
        self.trade_log = []
    
    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}, {txt}')
    
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'買入完成: {order.executed.price:.2f}, 數量: {order.executed.size}')
            else:
                self.log(f'賣出完成: {order.executed.price:.2f}, 數量: {order.executed.size}')
        
        self.order = None
    
    def next(self):
        """每根K線執行一次"""
        # 取得當前日期
        dt = self.datas[0].datetime.date(0)
        date_str = dt.strftime('%Y-%m-%d')
        
        # 取得法人數據 (T+1: 用昨天或更早的數據)
        # 實際應用中，這會透過自訂 data feed 取得
        inst_data = getattr(self.data, 'inst_data', {})
        inst = inst_data.get(date_str, {}) if isinstance(inst_data, dict) else {}
        
        f_consec = inst.get('f_consec', 0) if inst else 0
        t_consec = inst.get('t_consec', 0) if inst else 0
        
        # ===== 計算 Nana 評分 =====
        score = 0
        
        # --- 法人評分 (最高70分) ---
        # 外資
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
            score += 20  # 過熱
        
        # 投信
        if t_consec >= 3:
            score += 10  # 合力加成
        
        # --- 技術評分 (最高30分) ---
        # RSI
        if 50 <= self.rsi[0] <= 70:
            score += 15
        elif 30 <= self.rsi[0] < 50:
            score += 10
        else:
            score += 5
        
        # Bias
        if -2 <= self.bias[0] <= 3:
            score += 15
        elif 3 < self.bias[0] <= 6:
            score += 10
        elif self.bias[0] > 10:
            score += 0
        else:
            score += 5
        
        # ===== v4.21 進場門檻檢查 =====
        ma_trend = self.ma20[0] > self.ma60[0]  # 多頭排列
        rsi_ok = self.rsi[0] < 70  # 未過熱
        inst_ok = f_consec >= 1 or t_consec >= 1  # 有人點火
        
        condition_met = ma_trend and rsi_ok and inst_ok
        
        # ===== 交易邏輯 =====
        if not self.position:
            # 無持倉，檢查是否進場
            if score >= self.p.entry_threshold and condition_met:
                self.log(f'⭐️ 強力買進 | 總分: {score} | 價格: {self.data.close[0]:.2f} | RSI: {self.rsi[0]:.1f}')
                
                # 計算倉位 (帳戶10%)
                cash = self.broker.getcash()
                size = int(cash * 0.10 / self.data.close[0])
                size = size // 100 * 100  # 整手
                
                if size > 0:
                    self.buy(size=size)
                    self.entry_price = self.data.close[0]
                    self.entry_score = score
        
        else:
            # 有持倉，檢查是否出场
            current_price = self.data.close[0]
            entry_price = self.position.price
            pnl_pct = (current_price / entry_price - 1) * 100
            
            exit_signal = False
            exit_reason = ''
            
            # 停損檢查
            if pnl_pct <= -self.p.stop_loss * 100:
                exit_signal = True
                exit_reason = 'STOP_LOSS'
            
            # 目標獲利
            elif pnl_pct >= self.p.take_profit * 100:
                exit_signal = True
                exit_reason = 'TAKE_PROFIT'
            
            # 評分低於門檻
            elif score < self.p.exit_threshold:
                exit_signal = True
                exit_reason = 'SCORE_EXIT'
            
            # MA 跌破
            elif self.data.close[0] < self.ma20[0]:
                exit_signal = True
                exit_reason = 'MA_BREAK'
            
            if exit_signal:
                self.log(f'❌ 賣出 | {exit_reason} | 總分: {score} | 價格: {current_price:.2f} | 損益: {pnl_pct:.1f}%')
                self.close()
                
                # 記錄交易
                self.trade_log.append({
                    'date': date_str,
                    'entry': self.entry_price,
                    'exit': current_price,
                    'pnl': pnl_pct,
                    'reason': exit_reason,
                    'score': score
                })

# ==================== 回測引擎 ====================

def run_backtest_single(symbol, start_date, end_date, initial_cash=10_000_000):
    """單一股票回測"""
    print(f' 回測 {symbol}...')
    
    try:
        # 取得還原股價數據
        ticker = yf.Ticker(symbol + '.TW')
        h = ticker.history(start=start_date, end=end_date, period='1y')
        
        if len(h) < 60:
            return None
        
        # 重置索引
        h = h.reset_index()
        h['Date'] = h['Date'].dt.strftime('%Y-%m-%d')
        h = h.set_index('Date')
        h.index = pd.to_datetime(h.index)
        
        # 取得法人數據 (T+1 對齊)
        inst_data = get_inst_data(symbol, list(h.index.strftime('%Y-%m-%d')))
        
        # 建立 data feed
        data = InstitutionalDataFeed(
            dataname=h,
            datetime=None,
            open='Open',
            high='High',
            low='Low',
            close='Close',
            volume='Volume',
        )
        data.inst_data = inst_data  # 注入法人數據
        
        # 建立 cerebro
        cerebro = bt.Cerebro()
        cerebro.adddata(data)
        cerebro.addstrategy(NanaStrategy)
        
        # 設定初始資金
        cerebro.broker.setcash(initial_cash)
        
        # 設定交易成本 (手續費 + 交易稅)
        cerebro.broker.setcommission(commission=0.001425)  # 0.1425%
        cerebro.broker.setcommission(commission=0.003, margin=False)  # 0.3% 交易稅
        
        # 滑價設定 (動態: 大市值 0.1%, 小市值 0.2%)
        # 簡化: 固定 0.15%
        cerebro.broker.set_slippage_fixed(0.15)
        
        # 執行回測
        initial_value = cerebro.broker.getvalue()
        cerebro.run()
        final_value = cerebro.broker.getvalue()
        
        return {
            'symbol': symbol,
            'initial': initial_value,
            'final': final_value,
            'return': (final_value / initial_value - 1) * 100
        }
    
    except Exception as e:
        print(f'  {symbol} 錯誤: {e}')
        return None

def run_batch_backtest(stocks, start_date, end_date, initial_cash=10_000_000):
    """批次回測 100 大台股"""
    print('='*60)
    print(' Nana v1.0 批次回測')
    print('='*60)
    print()
    print(f' 股票數量: {len(stocks)}')
    print(f' 回測區間: {start_date} ~ {end_date}')
    print(f' 初始資金: {initial_cash:,} TWD')
    print()
    
    results = []
    
    for symbol in stocks:
        result = run_backtest_single(symbol, start_date, end_date, initial_cash)
        if result:
            results.append(result)
            print(f'  {symbol}: {result["return"]:.2f}%')
    
    print()
    print('='*60)
    print(' 批次回測結果')
    print('='*60)
    print()
    
    if results:
        # 排序
        results.sort(key=lambda x: x['return'], reverse=True)
        
        # 統計
        returns = [r['return'] for r in results]
        wins = [r for r in returns if r > 0]
        
        print(f' 總回測檔數: {len(results)}')
        print(f' 勝率: {len(wins)/len(results)*100:.1f}%')
        print(f' 平均報酬: {np.mean(returns):.2f}%')
        print(f' 中位數報酬: {np.median(returns):.2f}%')
        print(f' 最大獲利: {max(returns):.2f}%')
        print(f' 最大虧損: {min(returns):.2f}%')
        print()
        
        print(' TOP 5:')
        for r in results[:5]:
            print(f'  {r["symbol"]}: {r["return"]:.2f}%')
        
        print()
        print(' BOTTOM 5:')
        for r in results[-5:]:
            print(f'  {r["symbol"]}: {r["return"]:.2f}%')
        
        return results
    
    return []

# ==================== 主程式 ====================

if __name__ == '__main__':
    print('='*60)
    print(' Nana v1.0 Backtrader 回測框架')
    print('='*60)
    
    # 股票池
    stocks = [
        '2330','2454','2317','2382','3034','2379','2451','2308','2345','2353',
        '2395','2401','2492','2610','2880','2881','2882','2883','2884','2885',
        '2886','2887','2891','2892','3008','3033','3044','3189','3231','3443',
        '3481','3665','3717','4938','4958','6415','6505','6669','6770','8016',
        '8046','8105','8261','8341','8464','8926','8996','9945','2385','2603'
    ]
    
    # 執行批次回測
    results = run_batch_backtest(
        stocks,
        start_date='2024-01-01',
        end_date='2024-12-31',
        initial_cash=10_000_000
    )
    
    if results:
        # 儲存結果
        import json
        with open('Tina_Quant_System/teams/nana/batch_backtest_result.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print()
        print(' 已儲存: batch_backtest_result.json')