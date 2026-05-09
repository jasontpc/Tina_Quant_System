# -*- coding: utf-8 -*-
"""
Nana Autonomous Core v3.0
=========================
自主核心系統：選股 -> 評分 -> 回測 -> 學習 -> 迭代
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np
import yfinance as yf
import sqlite3
import json
import os
from datetime import datetime
from collections import defaultdict

DB_PATH = 'skills/stock-analyzer/scripts/tina_master.db'

# ==================== 市場狀態 ====================

class MarketRegime:
    """市場狀態判斷"""
    
    @staticmethod
    def get_state():
        """判斷當前市場狀態"""
        try:
            twii = yf.download('^TWII', period='5d', auto_adjust=True, progress=False)
            spy = yf.download('SPY', period='5d', auto_adjust=True, progress=False)
            
            if twii is None or len(twii) < 20:
                return 'unknown'
            
            if isinstance(twii.columns, pd.MultiIndex):
                twii.columns = [c[0] for c in twii.columns]
            if isinstance(spy.columns, pd.MultiIndex):
                spy.columns = [c[0] for c in spy.columns]
            
            close = twii['Close'].values
            ma20 = pd.Series(close).rolling(20).mean().iloc[-1]
            current = close[-1]
            
            # RSI
            delta = np.diff(close, prepend=close[0])
            gain = np.where(delta > 0, delta, 0)
            loss = np.where(delta > 0, 0, -delta)
            avg_gain = pd.Series(gain).rolling(14).mean().iloc[-1]
            avg_loss = pd.Series(loss).rolling(14).mean().iloc[-1]
            rsi = 100 - (100 / (1 + avg_gain / avg_loss)) if avg_loss > 0 else 50
            
            # 判斷
            if rsi > 80 or (current / ma20 - 1) > 0.1:
                return 'overbought'
            elif rsi < 40 or current < ma20:
                return 'bearish'
            elif current > ma20:
                return 'bullish'
            else:
                return 'neutral'
        
        except:
            return 'neutral'

# ==================== 分層股票池 ====================

class StockUniverse:
    """股票分層管理"""
    
    TIER1 = ['2330','2454','3034','2379','2303','2344','2382','3231','3717','4938',
             '2317','2353','2357','2345','3017','3324','6230','6269','3044','6213',
             '4935','4952','2401','2340','2379','2385','3526']
    
    TIER2 = ['3481','2409','6176','2412','3045','2385','6239','3374','6108','6192',
             '2471','2497','5203','2327','2492','2356','2376','2395','2308','2347']
    
    TIER3 = ['2881','2882','2884','2885','2891','2890','2801','2812','2834','2845',
             '1301','1326','2002','2105','2201','1216','1702','1722',
             '0050','0056','00662','00713','00891']
    
    ALL = list(set(TIER1 + TIER2 + TIER3))
    
    @classmethod
    def get_tier(cls, symbol):
        if symbol in cls.TIER1:
            return 1
        elif symbol in cls.TIER2:
            return 2
        elif symbol in cls.TIER3:
            return 3
        return 0
    
    @classmethod
    def get_tier_name(cls, tier):
        names = {1: '科技/AI核心', 2: '科技相關', 3: '大型藍籌', 0: '其他'}
        return names.get(tier, '其他')

# ==================== 評分引擎 ====================

class Scorer:
    """ Nana 評分系統"""
    
    def __init__(self, market_state='neutral'):
        self.state = market_state
    
    def inst_score(self, days):
        if days >= 11: return 20
        elif days >= 6: return 60
        elif days >= 4: return 50
        elif days == 3: return 40
        elif days == 2: return 15
        elif days == 1: return 10
        return 0
    
    def score(self, rsi, bias, atr_pct, ma20, ma60, f_days, t_days, ret_20d=0):
        """計算總分"""
        # 法人分 (40%)
        f_s = self.inst_score(f_days)
        t_s = self.inst_score(t_days)
        base = max(f_s, t_s)
        if f_days >= 3 and t_days >= 3:
            base += 10
        inst = min(70, base)
        
        # 技術分 (35%)
        rsi_s = 15 if 50 <= rsi <= 70 else (10 if 30 <= rsi < 50 else 5)
        bias_s = 15 if -2 <= bias <= 3 else (10 if 3 < bias <= 6 else 0)
        atr_s = 10 if atr_pct >= 0.5 else (5 if atr_pct >= 0.3 else 0)
        tech = rsi_s + bias_s + atr_s
        
        # 趨勢分 (25%)
        ma_s = 15 if ma20 > ma60 else 0
        mom_s = 15 if ret_20d > 5 else (10 if ret_20d > 0 else 5)
        trend = ma_s + mom_s
        
        total = inst * 0.40 + tech * 0.35 + trend * 0.25
        
        return {
            'total': round(total, 1),
            'inst': inst,
            'tech': tech,
            'trend': trend,
            'rsi': rsi,
            'bias': bias,
            'atr': atr_pct,
            'f_days': f_days,
            't_days': t_days
        }
    
    def should_trade(self, score_result, tier):
        """根據市場狀態和分數決定是否交易"""
        total = score_result['total']
        rsi = score_result['rsi']
        state = self.state
        
        # 基本門檻
        if total < 50:
            return False, '分數過低'
        
        # RSI 過熱
        if rsi > 85:
            return False, 'RSI過熱'
        
        # 市場狀態調整
        if state == 'overbought':
            if total < 65:
                return False, '多頭末段'
            if rsi > 75:
                return False, '多頭末段RSI高'
        
        elif state == 'bearish':
            if total < 60:
                return False, '空頭保守'
            if tier == 3:  # 藍籌比較抗跌
                return True, '藍籌抗跌'
        
        elif state == 'neutral':
            if total < 55:
                return False, '盤整低分'
        
        return True, '符合進場'

# ==================== 回測引擎 ====================

class Backtester:
    """真實交易回測"""
    
    def __init__(self, capital=1000000):
        self.capital = capital
        self.fee = 0.001425
        self.tax = 0.003
        self.slip = 0.0015
    
    def run(self, symbol, params, days=180):
        """執行回測"""
        df = yf.download(symbol + '.TW', period=f'{days}d', auto_adjust=True, progress=False)
        if df is None or len(df) < 60:
            return []
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        
        # 法人
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('SELECT date, foreign_net, trust_net FROM MarketData WHERE symbol = ? ORDER BY date DESC LIMIT ?', 
                   (symbol, days))
        rows = cur.fetchall()
        conn.close()
        inst_map = {str(r[0])[:10]: {'f': r[1] or 0, 't': r[2] or 0} for r in rows}
        
        close = df['Close'].values
        high = df['High'].values
        low = df['Low'].values
        dates = [str(d)[:10] for d in df.index]
        
        # 指標
        ma20 = pd.Series(close).rolling(20).mean().values
        ma60 = pd.Series(close).rolling(60).mean().values
        
        delta = np.diff(close, prepend=close[0])
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta > 0, 0, -delta)
        avg_gain = pd.Series(gain).rolling(14).mean().values
        avg_loss = pd.Series(loss).rolling(14).mean().values
        rs = avg_gain / np.where(avg_loss == 0, np.nan, avg_loss)
        rsi = 100 - (100 / (1 + rs))
        rsi = np.where(np.isnan(rsi), 50, rsi)
        
        tr = np.maximum(high - low, np.maximum(np.abs(high - np.roll(close, 1)), np.abs(low - np.roll(close, 1))))
        atr = pd.Series(tr).rolling(14).mean().values
        atr_pct = atr / close * 100
        
        bias = (close - ma20) / ma20 * 100
        
        # 法人
        def get_f_days(idx):
            days = 0
            for j in range(idx, max(idx - 20, -1), -1):
                if j < 0: break
                inst = inst_map.get(dates[j], {'f': 0})
                if inst['f'] > 0: days += 1
                else: break
            return days
        
        def get_t_days(idx):
            days = 0
            for j in range(idx, max(idx - 20, -1), -1):
                if j < 0: break
                inst = inst_map.get(dates[j], {'t': 0})
                if inst['t'] > 0: days += 1
                else: break
            return days
        
        scorer = Scorer()
        trades = []
        position = None
        
        p = params
        hold_days = p.get('hold_days', 7)
        exit_rsi = p.get('exit_rsi', 85)
        exit_bias = p.get('exit_bias', 10)
        
        for i in range(60, len(dates)):
            price = close[i]
            r = rsi[i]
            m20 = ma20[i] if not np.isnan(ma20[i]) else 0
            m60 = ma60[i] if not np.isnan(ma60[i]) else 0
            a = atr_pct[i] if not np.isnan(atr_pct[i]) else 0
            b = bias[i] if not np.isnan(bias[i]) else 0
            
            f_d = get_f_days(i)
            t_d = get_t_days(i)
            
            ret_20d = (close[i] / close[i-20] - 1) * 100 if i >= 20 else 0
            
            if position is None:
                s = scorer.score(r, b, a, m20, m60, f_d, t_d, ret_20d)
                tier = StockUniverse.get_tier(symbol)
                should, reason = scorer.should_trade(s, tier)
                
                if should and s['total'] >= p.get('entry_min', 55):
                    entry_cost = price * (1 + self.fee + self.slip)
                    shares = int(self.capital * 0.1 / entry_cost / 100) * 100
                    if shares >= 100:
                        position = {'entry': price, 'shares': shares, 'days': 0}
            else:
                position['days'] += 1
                
                # 出場
                exit = False
                exit_reason = 'time'
                
                if position['days'] >= hold_days:
                    exit = True
                    exit_reason = 'time'
                elif r >= exit_rsi:
                    exit = True
                    exit_reason = 'rsi'
                elif b >= exit_bias:
                    exit = True
                    exit_reason = 'bias'
                elif m20 < m60:
                    exit = True
                    exit_reason = 'ma'
                
                if exit:
                    exit_cost = price * (1 - self.tax - self.fee - self.slip)
                    pnl_pct = (exit_cost / position['entry'] - 1) * 100
                    trades.append({
                        'symbol': symbol,
                        'entry': position['entry'],
                        'exit': price,
                        'pnl_pct': pnl_pct,
                        'days': position['days'],
                        'reason': exit_reason
                    })
                    position = None
        
        return trades
    
    def analyze(self, trades):
        if not trades:
            return {'trades': 0, 'wr': 0, 'avg': 0, 'pf': 0, 'ret': 0}
        
        df = pd.DataFrame(trades)
        wins = df[df['pnl_pct'] > 0]
        losses = df[df['pnl_pct'] <= 0]
        
        wr = len(wins) / len(df) * 100
        avg = df['pnl_pct'].mean()
        
        gp = wins['pnl_pct'].sum() if len(wins) > 0 else 0
        gl = abs(losses['pnl_pct'].sum()) if len(losses) > 0 else 0
        pf = gp / gl if gl > 0 else 999
        
        return {
            'trades': len(trades),
            'wr': wr,
            'avg': avg,
            'pf': pf,
            'ret': df['pnl_pct'].sum()
        }

# ==================== 自主學習系統 ====================

class Learner:
    """失敗學習與策略改進"""
    
    def __init__(self):
        self.history = []
        self.failed_strategies = defaultdict(list)
    
    def analyze_failure(self, symbol, trades, params):
        """分析失敗原因"""
        if not trades:
            return {
                'issue': 'no_trades',
                'reason': '無交易訊號',
                'suggestion': '降低進場分數門檻'
            }
        
        df = pd.DataFrame(trades)
        
        # 勝率過低
        if df['pnl_pct'].mean() < 0:
            return {
                'issue': 'negative_return',
                'reason': f'平均報酬 {df["pnl_pct"].mean():.1f}%',
                'suggestion': '提高進場分數或縮短持有天數'
            }
        
        # 勝率過低
        wr = len(df[df['pnl_pct'] > 0]) / len(df) * 100
        if wr < 40:
            return {
                'issue': 'low_winrate',
                'reason': f'勝率 {wr:.0f}%',
                'suggestion': '加入更多過濾條件'
            }
        
        return {'issue': 'none', 'reason': '正常'}
    
    def generate_improvement(self, analysis, current_params):
        """生成改良參數"""
        if analysis['issue'] == 'no_trades':
            return {
                **current_params,
                'entry_min': current_params.get('entry_min', 55) - 5,
            }
        elif analysis['issue'] == 'negative_return':
            return {
                **current_params,
                'hold_days': min(current_params.get('hold_days', 7) + 2, 14),
                'exit_bias': current_params.get('exit_bias', 10) - 2,
            }
        elif analysis['issue'] == 'low_winrate':
            return {
                **current_params,
                'entry_min': current_params.get('entry_min', 55) + 5,
                'exit_rsi': current_params.get('exit_rsi', 85) - 5,
            }
        return current_params

# ==================== 主系統 ====================

class NanaSystem:
    """Nana 自主交易系統"""
    
    def __init__(self):
        self.name = 'Nana'
        self.scanner = None
        self.backtester = Backtester()
        self.learner = Learner()
        self.state = MarketRegime.get_state()
        self.params = {
            'rsi_min': 30,
            'rsi_max': 75,
            'atr_min': 0.003,
            'inst_min': 0,
            'entry_min': 55,
            'hold_days': 7,
            'exit_rsi': 85,
            'exit_bias': 10,
        }
        self.results = []
    
    def scan_and_rank(self, top_n=20):
        """掃描並排名所有股票"""
        print()
        print('='*60)
        print(f' Nana System v3.0 - {self.state} Market')
        print('='*60)
        print()
        
        results = []
        scorer = Scorer(self.state)
        
        for i, symbol in enumerate(StockUniverse.ALL, 1):
            try:
                df = yf.download(symbol + '.TW', period='90d', auto_adjust=True, progress=False)
                if df is None or len(df) < 60:
                    continue
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [c[0] for c in df.columns]
                
                close = df['Close'].values
                high = df['High'].values
                low = df['Low'].values
                
                ma20 = pd.Series(close).rolling(20).mean().iloc[-1]
                ma60 = pd.Series(close).rolling(60).mean().iloc[-1]
                
                rsi_vals = pd.Series(close).rolling(14).apply(
                    lambda x: 100 - 100/(1 + (np.diff(x).clip(min=0).mean() / abs(np.diff(x).clip(max=0).mean()))) 
                    if abs(np.diff(x).clip(max=0).mean()) > 0 else 50, raw=False
                ).iloc[-1]
                
                if np.isnan(rsi_vals):
                    rsi = 50
                else:
                    rsi = rsi_vals
                
                atr = np.mean(np.maximum(high - low, np.abs(high - np.roll(close, 1))))[-1]
                atr_pct = atr / close[-1] * 100
                bias = (close[-1] / ma20 - 1) * 100 if ma20 else 0
                
                # 法人
                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                cur.execute('SELECT foreign_net, trust_net FROM MarketData WHERE symbol = ? ORDER BY date DESC LIMIT 10', (symbol,))
                rows = cur.fetchall()
                conn.close()
                
                f_d = t_d = 0
                for f, t in rows:
                    if f and f > 0: f_d += 1
                    else: break
                for f, t in rows:
                    if t and t > 0: t_d += 1
                    else: break
                
                ret_20d = (close[-1] / close[-21] - 1) * 100 if len(close) >= 21 else 0
                
                s = scorer.score(rsi, bias, atr_pct, ma20, ma60, f_d, t_d, ret_20d)
                tier = StockUniverse.get_tier(symbol)
                should, reason = scorer.should_trade(s, tier)
                
                results.append({
                    'symbol': symbol,
                    'tier': tier,
                    'tier_name': StockUniverse.get_tier_name(tier),
                    'score': s['total'],
                    'inst': s['inst'],
                    'tech': s['tech'],
                    'trend': s['trend'],
                    'rsi': s['rsi'],
                    'bias': s['bias'],
                    'atr': s['atr'],
                    'f_days': s['f_days'],
                    't_days': s['t_days'],
                    'can_trade': should,
                    'trade_reason': reason,
                    'price': close[-1]
                })
                
                if i % 20 == 0:
                    print(f'  已掃描 {i}/{len(StockUniverse.ALL)}...')
                
            except Exception as e:
                continue
        
        # 排序
        results.sort(key=lambda x: x['score'], reverse=True)
        self.results = results
        
        # 顯示 Top N
        print(f' Top {top_n} 候選:')
        print('-'*70)
        print(f'{"排名":<4} {"代碼":<6} {"Tier":<12} {"總分":<6} {"法人":<5} {"技術":<5} {"趨勢":<5} {"RSI":<5} {"可交易"}')
        print('-'*70)
        
        for i, r in enumerate(results[:top_n], 1):
            tier_icons = {1: '🥇', 2: '🥈', 3: '🥉'}
            tier_icon = tier_icons.get(r['tier'], '')
            can = '✅' if r['can_trade'] else '❌'
            print(f'{i:<4} {r["symbol"]:<6} {tier_icon}{r["tier_name"]:<9} {r["score"]:<6.1f} {r["inst"]:<5.1f} {r["tech"]:<5.1f} {r["trend"]:<5.1f} {r["rsi"]:<5.1f} {can}')
        
        return results
    
    def run_backtest_on_results(self):
        """對 Top 結果執行回測"""
        print()
        print('='*60)
        print(' 開始回測驗證')
        print('='*60)
        print()
        
        all_trades = []
        
        for r in self.results[:10]:  # Top 10
            symbol = r['symbol']
            print(f' 回測 {symbol}...', end=' ')
            
            trades = self.backtester.run(symbol, self.params)
            stats = self.backtester.analyze(trades)
            
            print(f'{stats["trades"]}筆, WR={stats["wr"]:.0f}%, Ret={stats["ret"]:.1f}%')
            
            all_trades.extend([{**t, 'symbol': symbol} for t in trades])
        
        if all_trades:
            df = pd.DataFrame(all_trades)
            total_wr = len(df[df['pnl_pct'] > 0]) / len(df) * 100
            total_ret = df['pnl_pct'].sum()
            
            print()
            print('='*60)
            print(' 總結')
            print('='*60)
            print(f' 總交易: {len(all_trades)} 筆')
            print(f' 勝率: {total_wr:.1f}%')
            print(f' 總報酬: {total_ret:.1f}%')
            print()
            
            # 分析
            analysis = self.learner.analyze_failure('PORTFOLIO', all_trades, self.params)
            print(f' 分析: {analysis["reason"]}')
            print(f' 建議: {analysis["suggestion"]}')
            
            return {
                'trades': len(all_trades),
                'wr': total_wr,
                'ret': total_ret,
                'analysis': analysis
            }
        
        return None

def main():
    system = NanaSystem()
    
    # 1. 掃描排名
    system.scan_and_rank(top_n=20)
    
    # 2. 回測驗證
    result = system.run_backtest_on_results()
    
    # 3. 儲存結果
    if system.results:
        with open('Tina_Quant_System/teams/nana/system_v3_results.json', 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'market_state': system.state,
                'results': system.results[:30],
                'backtest': result
            }, f, ensure_ascii=False, indent=2)
    
    print()
    print('已儲存: system_v3_results.json')

if __name__ == '__main__':
    main()