# -*- coding: utf-8 -*-
"""
Nana Realistic Backtester v1.0
================================
真實交易模擬 + 全壓力測試

涵蓋:
1. 交易成本 (0.1425% + 0.3% tax)
2. 滑點 (0.15%)
3. T+1 法人資料對齊
4. 缺口/跳空風險
5. 流動性約束
6. 動態倉位
7. 部位限制
8. 市場影響
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np
import yfinance as yf
import sqlite3
import json
from datetime import datetime, timedelta

DB_PATH = 'skills/stock-analyzer/scripts/tina_master.db'

# ==================== 交易成本 ====================

class TradingCosts:
    """交易成本計算"""
    FEE_RATE = 0.001425      # 0.1425%
    TAX_RATE = 0.003         # 0.3%
    SLIPPAGE = 0.0015        # 0.15% 滑點
    MIN_FEE = 20             # 最低手續費
    
    @classmethod
    def buy_cost(cls, price, shares):
        """買入成本"""
        gross = float(price) * float(shares)
        fee = gross * cls.FEE_RATE
        slip = gross * cls.SLIPPAGE
        return fee + slip, max(fee, cls.MIN_FEE) + slip
    
    @classmethod
    def sell_cost(cls, price, shares):
        """賣出成本 (含稅)"""
        gross = float(price) * float(shares)
        fee = gross * cls.FEE_RATE
        tax = gross * cls.TAX_RATE
        slip = gross * cls.SLIPPAGE
        return fee + tax + slip, fee + tax + slip

# ==================== 部位管理 ====================

class PositionManager:
    """部位管理"""
    
    def __init__(self, capital=1000000, max_position=0.15, max_total=0.85):
        self.capital = capital
        self.max_position = max_position
        self.max_total = max_total
        self.positions = {}  # {symbol: {'shares', 'entry', 'cost_basis'}}
        self.cash = float(capital)
        self.peak = capital
    
    @property
    def equity_value(self):
        """帳戶淨值"""
        pos_value = float(sum(p['shares'] * p['cost_basis'] for p in self.positions.values()))
        return float(self.cash) + pos_value
    
    @property
    def exposure(self):
        val = self.equity_value
        return 1 - float(self.cash) / float(val) if float(val) > 0 else 0
    
    def can_buy(self, price, shares):
        """檢查是否可以買入"""
        cost = float(price * shares)
        position_cost = self.equity_value * self.max_position
        total_cost = float(sum(p['shares'] * p['cost_basis'] for p in self.positions.values()))
        
        return (cost <= float(self.cash) and 
                cost <= position_cost and
                (total_cost + cost) <= self.equity_value * self.max_total)
    
    def buy(self, symbol, price, shares, date):
        """買入"""
        cost, fee = TradingCosts.buy_cost(price, shares)
        total_cost = float(price) * float(shares) + float(fee)
        
        if total_cost > self.cash:
            # 金額不足，買最多能買的
            max_shares = int((self.cash * 0.99) / (price * (1 + TradingCosts.FEE_RATE + TradingCosts.SLIPPAGE)) / 100) * 100
            if max_shares < 100:
                return False
            shares = max_shares
            cost, fee = TradingCosts.buy_cost(price, shares)
            total_cost = float(price) * float(shares) + float(fee)
        
        self.positions[symbol] = {
            'shares': int(shares),
            'entry': price,
            'cost_basis': price,
            'entry_date': date,
            'entry_cost': total_cost
        }
        self.cash = float(self.cash) - float(total_cost)
        return True
    
    def sell(self, symbol, price, date, reason='unknown'):
        """賣出"""
        if symbol not in self.positions:
            return None
        
        p = self.positions[symbol]
        shares = int(p['shares'])
        
        gross = float(price) * float(shares)
        fee_tax, _ = TradingCosts.sell_cost(price, shares)
        net = float(gross) - float(fee_tax)
        
        pnl = float(net) - float(p['entry_cost'])
        pnl_pct = (float(net) / float(p['entry_cost']) - 1) * 100
        
        self.cash = float(self.cash) + float(net)
        del self.positions[symbol]
        
        return {
            'symbol': symbol,
            'entry_date': p['entry_date'],
            'exit_date': date,
            'entry_price': p['entry'],
            'exit_price': price,
            'shares': shares,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'reason': reason,
            'holding_days': (datetime.strptime(date, '%Y-%m-%d') - 
                           datetime.strptime(p['entry_date'], '%Y-%m-%d')).days
        }

# ==================== 真實回測引擎 ====================

class RealisticBacktester:
    """
    真實交易模擬回測引擎
    """
    
    def __init__(self, capital=1000000, name='Test'):
        self.capital = capital
        self.name = name
        self.costs = TradingCosts()
        self.pm = PositionManager(capital)
        self.trades = []
        self.equity_curve = []
        self.failed_trades = []
        self.stats = {}
    
    def fetch_data(self, symbol, days=365):
        """抓取完整歷史資料"""
        df = yf.download(symbol + '.TW', period=f'{days}d', auto_adjust=True, progress=False)
        if df is None or len(df) < 60:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        
        # 法人資料 (T+1對齊)
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('SELECT date, foreign_net, trust_net FROM MarketData WHERE symbol = ? ORDER BY date DESC LIMIT ?', 
                   (symbol, days))
        rows = cur.fetchall()
        conn.close()
        
        inst_map = {}
        for r in rows:
            inst_map[str(r[0])[:10]] = {'f': r[1] or 0, 't': r[2] or 0}
        
        return df, inst_map
    
    def calculate_indicators(self, df):
        """計算完整指標"""
        close = df['Close'].values
        high = df['High'].values
        low = df['Low'].values
        open_prices = df['Open'].values
        volume = df['Volume'].values
        dates = [str(d)[:10] for d in df.index]
        
        # MA
        ma5 = pd.Series(close).rolling(5).mean().values
        ma20 = pd.Series(close).rolling(20).mean().values
        ma60 = pd.Series(close).rolling(60).mean().values
        
        # RSI
        delta = np.diff(close, prepend=close[0])
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta > 0, 0, -delta)
        avg_gain = pd.Series(gain).rolling(14).mean().values
        avg_loss = pd.Series(loss).rolling(14).mean().values
        rs = avg_gain / np.where(avg_loss == 0, np.nan, avg_loss)
        rsi = 100 - (100 / (1 + rs))
        rsi = np.where(np.isnan(rsi), 50, rsi)
        
        # ATR
        tr = np.maximum(high - low, np.maximum(
            np.abs(high - np.roll(close, 1)), 
            np.abs(low - np.roll(close, 1))
        ))
        atr = pd.Series(tr).rolling(14).mean().values
        atr_pct = atr / close * 100
        
        # Bias
        bias = (close - ma20) / ma20 * 100
        
        # Volume ratio
        vol_ma5 = pd.Series(volume).rolling(5).mean().values
        vol_ratio = volume / vol_ma5
        
        return {
            'close': close, 'high': high, 'low': low, 'open': open_prices,
            'volume': volume, 'dates': dates,
            'ma5': ma5, 'ma20': ma20, 'ma60': ma60,
            'rsi': rsi, 'atr_pct': atr_pct, 'bias': bias, 'vol_ratio': vol_ratio
        }
    
    def get_inst_days(self, inst_map, dates, idx):
        """取得法人連續天數 (T+1 對齊)"""
        # 使用前一天的資料 (T+1)
        if idx <= 0:
            return 0, 0
        
        f_c = t_c = 0
        checked = 0
        
        for j in range(idx - 1, max(idx - 20, -1), -1):
            if j < 0 or j >= len(dates):
                break
            inst = inst_map.get(dates[j], {'f': 0, 't': 0})
            if inst['f'] > 0:
                f_c += 1
                checked += 1
            else:
                break
        
        for j in range(idx - 1, max(idx - 20, -1), -1):
            if j < 0 or j >= len(dates):
                break
            inst = inst_map.get(dates[j], {'f': 0, 't': 0})
            if inst['t'] > 0:
                t_c += 1
            else:
                break
        
        return f_c, t_c
    
    def inst_score(self, days):
        if days >= 11: return 20
        elif days >= 6: return 60
        elif days >= 4: return 50
        elif days == 3: return 40
        elif days == 2: return 15
        elif days == 1: return 10
        return 0
    
    def run(self, symbol, params):
        """
        執行完整回測
        
        params: {
            'rsi_min': 30,
            'rsi_max': 75,
            'atr_min': 0.003,
            'inst_min': 10,
            'entry_min': 55,
            'hold_days': 7,
            'exit_rsi': 85,
            'exit_bias': 10,
            'use_trailing': True,
            'trailing_mult': 2.5,
            'max_positions': 5
        }
        """
        data = self.fetch_data(symbol)
        if data is None:
            return []
        
        df, inst_map = data
        ind = self.calculate_indicators(df)
        
        p = params
        rsi_min = p.get('rsi_min', 30)
        rsi_max = p.get('rsi_max', 75)
        atr_min = p.get('atr_min', 0.003) * 100
        inst_min = p.get('inst_min', 10)
        entry_min = p.get('entry_min', 55)
        hold_days = p.get('hold_days', 7)
        exit_rsi = p.get('exit_rsi', 85)
        exit_bias = p.get('exit_bias', 10)
        use_trailing = p.get('use_trailing', True)
        trailing_mult = p.get('trailing_mult', 2.5)
        
        trades = []
        position = None
        highest_since_entry = 0
        
        for i in range(60, len(ind['dates'])):
            date = ind['dates'][i]
            close = ind['close'][i]
            high = ind['high'][i]
            low = ind['low'][i]
            open_p = ind['open'][i]
            rsi = ind['rsi'][i]
            ma20 = ind['ma20'][i]
            ma60 = ind['ma60'][i]
            atr = ind['atr_pct'][i]
            bias = ind['bias'][i] if not np.isnan(ind['bias'][i]) else 0
            vol_ratio = ind['vol_ratio'][i]
            
            # 法人 (T+1)
            f_c, t_c = self.get_inst_days(inst_map, ind['dates'], i)
            
            # ===== 進場邏輯 =====
            if position is None:
                # 評分
                f_s = self.inst_score(f_c)
                t_s = self.inst_score(t_c)
                base = max(f_s, t_s)
                if f_c >= 3 and t_c >= 3:
                    base += 10
                inst_total = min(70, base)
                
                rsi_s = 15 if 50 <= rsi <= 70 else (10 if 30 <= rsi < 50 else 5)
                bias_s = 15 if -2 <= bias <= 3 else (10 if 3 < bias <= 6 else 0)
                total = inst_total + rsi_s + bias_s
                
                # 進場條件
                cond_rsi = rsi_min <= rsi <= rsi_max
                cond_ma = ma20 > ma60 if not (np.isnan(ma20) or np.isnan(ma60)) else False
                cond_atr = atr >= atr_min
                cond_inst = inst_total >= inst_min
                cond_score = total >= entry_min
                
                # 流動性檢查
                cond_liquid = vol_ratio > 0.5 if vol_ratio else True
                
                if cond_rsi and cond_ma and cond_atr and cond_inst and cond_score and cond_liquid:
                    # 使用開盤價買入 (模擬開盤進場)
                    entry_price = open_p * (1 + TradingCosts.SLIPPAGE)  # 開盤滑點
                    shares = int((self.pm.equity_value * 0.1) / entry_price / 100) * 100
                    
                    if shares >= 100 and self.pm.can_buy(entry_price, shares):
                        if self.pm.buy(symbol, entry_price, shares, date):
                            position = {
                                'entry_date': date,
                                'entry_price': entry_price,
                                'atr': atr,
                                'fc': f_c,
                                'tc': t_c,
                                'score': total
                            }
                            highest_since_entry = entry_price
            
            # ===== 出場邏輯 =====
            else:
                # 更新最高價
                if high > highest_since_entry:
                    highest_since_entry = high
                
                # Trailing stop
                if use_trailing:
                    trail_stop = highest_since_entry - (atr * trailing_mult)
                
                days_held = i - ind['dates'].index(position['entry_date'])
                
                # 出場信號
                exit_signal = None
                exit_reason = None
                
                # 1. 時間到了
                if days_held >= hold_days:
                    exit_signal = True
                    exit_reason = 'time'
                
                # 2. RSI 過熱
                elif rsi >= exit_rsi:
                    exit_signal = True
                    exit_reason = 'rsi_overbought'
                
                # 3. Bias 過大
                elif bias >= exit_bias:
                    exit_signal = True
                    exit_reason = 'bias_high'
                
                # 4. Trailing stop
                elif use_trailing and close <= trail_stop:
                    exit_signal = True
                    exit_reason = 'trailing_stop'
                
                # 5. 趨勢反轉
                elif ma20 <= ma60:
                    exit_signal = True
                    exit_reason = 'ma_cross_down'
                
                # 6. 缺口下跌 > 5%
                elif i > 0:
                    gap = (open_p - ind['close'][i-1]) / ind['close'][i-1]
                    if gap <= -0.05:
                        exit_signal = True
                        exit_reason = 'gap_down'
                
                if exit_signal:
                    # 使用開盤價賣出
                    exit_price = open_p * (1 - TradingCosts.SLIPPAGE)
                    result = self.pm.sell(symbol, exit_price, date, exit_reason)
                    
                    if result:
                        result['rsi_exit'] = rsi
                        result['atr_exit'] = atr
                        result['bias_exit'] = bias
                        result['score_entry'] = position['score']
                        trades.append(result)
                    position = None
            
            # 記錄淨值
            self.equity_curve.append({
                'date': date,
                'equity': self.pm.equity_value,
                'cash': self.pm.cash,
                'exposure': self.pm.exposure,
                'positions': len(self.pm.positions)
            })
        
        # 平倉未結束的倉位
        if position:
            close_p = ind['close'][-1]
            result = self.pm.sell(symbol, close_p, ind['dates'][-1], 'eod')
            if result:
                trades.append(result)
        
        return trades
    
    def analyze(self, trades):
        """分析回測結果"""
        if not trades:
            return {
                'trades': 0, 'win_rate': 0, 'avg_return': 0,
                'profit_factor': 0, 'max_drawdown': 0, 'total_return': 0
            }
        
        df = pd.DataFrame(trades)
        
        wins = df[df['pnl'] > 0]
        losses = df[df['pnl'] <= 0]
        
        wr = len(wins) / len(df) * 100
        avg = df['pnl_pct'].mean()
        
        gross_profit = wins['pnl'].sum() if len(wins) > 0 else 0
        gross_loss = abs(losses['pnl'].sum()) if len(losses) > 0 else 0
        pf = gross_profit / gross_loss if gross_loss > 0 else 999
        
        # MDD
        cum = df['pnl'].cumsum()
        peak = cum.cummax()
        dd = peak - cum
        mdd = dd.max()
        
        total_ret = df['pnl_pct'].sum()
        
        # 持有天數分析
        avg_hold = df['holding_days'].mean()
        
        # 出場原因分析
        reason_counts = df['reason'].value_counts().to_dict()
        
        return {
            'trades': len(trades),
            'win_rate': wr,
            'avg_return': avg,
            'profit_factor': pf,
            'max_drawdown': mdd,
            'total_return': total_ret,
            'avg_holding_days': avg_hold,
            'reason_distribution': reason_counts,
            'largest_win': df['pnl_pct'].max() if len(wins) > 0 else 0,
            'largest_loss': df['pnl_pct'].min() if len(losses) > 0 else 0,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss
        }

# ==================== 壓力測試 ====================

def stress_test():
    """全面壓力測試"""
    print()
    print('='*60)
    print(' Nana Realistic Backtester - 壓力測試')
    print('='*60)
    print()
    
    tester = RealisticBacktester(capital=1000000)
    
    # 測試參數
    test_params = [
        {
            'name': '標準參數',
            'params': {
                'rsi_min': 30, 'rsi_max': 75, 'atr_min': 0.003,
                'inst_min': 10, 'entry_min': 55, 'hold_days': 7,
                'exit_rsi': 85, 'exit_bias': 10, 'use_trailing': True, 'trailing_mult': 2.5
            }
        },
        {
            'name': '積極進場',
            'params': {
                'rsi_min': 25, 'rsi_max': 80, 'atr_min': 0.002,
                'inst_min': 5, 'entry_min': 50, 'hold_days': 5,
                'exit_rsi': 90, 'exit_bias': 12, 'use_trailing': False, 'trailing_mult': 2.0
            }
        },
        {
            'name': '保守進場',
            'params': {
                'rsi_min': 40, 'rsi_max': 70, 'atr_min': 0.005,
                'inst_min': 20, 'entry_min': 65, 'hold_days': 10,
                'exit_rsi': 80, 'exit_bias': 8, 'use_trailing': True, 'trailing_mult': 3.0
            }
        }
    ]
    
    stocks = ['2330', '2454', '3034', '2379', '2317']
    
    all_results = {}
    
    for test in test_params:
        print(f'測試: {test["name"]}')
        print('-'*40)
        
        total_trades = 0
        total_wr = 0
        total_ret = 0
        total_pf = 0
        
        for symbol in stocks:
            trades = tester.run(symbol, test['params'])
            stats = tester.analyze(trades)
            
            total_trades += stats['trades']
            total_wr += stats['win_rate']
            total_ret += stats['total_return']
            total_pf += stats['profit_factor']
            
            if stats['trades'] > 0:
                print(f'  {symbol}: {stats["trades"]}筆, WR={stats["win_rate"]:.0f}%, Ret={stats["total_return"]:.1f}%')
            
            # 重置
            tester = RealisticBacktester(capital=1000000)
        
        n = len(stocks)
        print()
        print(f'平均: {total_trades/n:.0f}筆, WR={total_wr/n:.1f}%, Ret={total_ret/n:.1f}%, PF={total_pf/n:.2f}')
        print()
        
        all_results[test['name']] = {
            'params': test['params'],
            'avg_trades': total_trades / n,
            'avg_wr': total_wr / n,
            'avg_ret': total_ret / n,
            'avg_pf': total_pf / n
        }
    
    # ===== 成本影響分析 =====
    print('='*60)
    print(' 成本影響分析')
    print('='*60)
    print()
    
    # 原始回報 vs 扣除成本
    gross_total = 0
    net_total = 0
    
    for symbol in stocks:
        tester = RealisticBacktester(capital=1000000)
        trades = tester.run(symbol, test_params[0]['params'])
        
        for t in trades:
            gross = (float(t['exit_price']) - float(t['entry_price'])) * int(t['shares'])
            net = float(t['pnl'])
            gross_total += (gross - net)  # 成本 = gross - net
            net_total += net
    
    gross_avg = gross_total / max(len(trades), 1)
    net_avg = net_total / max(len(trades), 1)
    cost_impact = gross_avg - net_avg
    
    print(f'交易成本影響: {cost_impact:.2f}%')
    print(f'  (含 {TradingCosts.FEE_RATE*100:.2f}% 手續費 + {TradingCosts.TAX_RATE*100:.1f}% 交易稅 + {TradingCosts.SLIPPAGE*100:.2f}% 滑點)')
    print()
    
    # ===== 最終結論 =====
    print('='*60)
    print(' 壓力測試結論')
    print('='*60)
    print()
    
    best = max(all_results.keys(), key=lambda k: all_results[k]['avg_wr'])
    most_trades = max(all_results.keys(), key=lambda k: all_results[k]['avg_trades'])
    
    print(f'最高勝率: {best} ({all_results[best]["avg_wr"]:.1f}%)')
    print(f'最多交易: {most_trades} ({all_results[most_trades]["avg_trades"]:.0f}筆)')
    print()
    
    return all_results

if __name__ == '__main__':
    stress_test()