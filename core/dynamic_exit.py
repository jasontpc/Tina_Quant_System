# -*- coding: utf-8 -*-
"""
Nana Dynamic Exit System
========================
動態出場策略:
1. 最短持有: 1天
2. 獲利了結: 次日可出
3. 多頭市場: 持有5-7天
4. 市場判斷: TWII + RSI + VIX
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np
import yfinance as yf
import sqlite3
from datetime import datetime

DB_PATH = 'skills/stock-analyzer/scripts/tina_master.db'

# ==================== 市場判斷 ====================

class MarketMood:
    """判斷市場情緒"""
    
    @staticmethod
    def get_status():
        """取得當前市場狀態"""
        try:
            # TWII
            twii = yf.download('^TWII', period='10d', auto_adjust=True, progress=False)
            if isinstance(twii.columns, pd.MultiIndex):
                twii.columns = [c[0] for c in twii.columns]
            
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
            
            # 20日漲幅
            ret_20d = (current / close[-21] - 1) * 100 if len(close) >= 21 else 0
            
            # 判斷狀態
            if rsi > 80 or (current / ma20 - 1) > 0.08:
                status = 'overbought'
                max_hold = 5
                desc = '過熱'
            elif current > ma20 and rsi > 55:
                status = 'bullish'
                max_hold = 7
                desc = '多頭'
            elif current < ma20 and rsi < 45:
                status = 'bearish'
                max_hold = 3
                desc = '空頭'
            else:
                status = 'neutral'
                max_hold = 5
                desc = '盤整'
            
            return {
                'status': status,
                'max_hold': max_hold,
                'desc': desc,
                'twii': current,
                'ma20': ma20,
                'rsi': rsi,
                'ret_20d': ret_20d
            }
        except Exception as e:
            return {
                'status': 'neutral',
                'max_hold': 5,
                'desc': '未知',
                'twii': 0,
                'ma20': 0,
                'rsi': 50,
                'ret_20d': 0
            }

# ==================== 動態出場引擎 ====================

class DynamicExit:
    """
    動態出场策略
    
    規則:
    1. 最短持有: 1天
    2. 獲利了結: 當日獲利 >= 2% 可考慮次日出
    3. 多頭市場: 最多持有 max_hold 天
    4. 虧損: 最長持有 max_hold 天強迫出
    """
    
    def __init__(self, market_status=None):
        self.status = market_status or MarketMood.get_status()
        self.max_hold = self.status['max_hold']
    
    def should_exit(self, position, current_price, rsi=None, bias=None):
        """
        判斷是否應該出场
        
        參數:
            position: {
                'entry_price': float,
                'entry_date': str,
                'days_held': int,
                'high_since_entry': float,
                'atr': float
            }
            current_price: float
            rsi: float (可選)
            bias: float (可選)
        
        返回:
            {
                'exit': bool,
                'reason': str,
                'urgency': 'high'/'medium'/'low'
            }
        """
        entry = position['entry_price']
        days = position['days_held']
        high = position.get('high_since_entry', entry)
        atr = position.get('atr', 0)
        
        profit_pct = (current_price / entry - 1) * 100
        
        # ====== 出場條件評估 ======
        
        # 1. 時間到了 (最長持有)
        if days >= self.max_hold:
            return {
                'exit': True,
                'reason': f'持有期滿 ({self.max_hold}天)',
                'urgency': 'medium' if profit_pct > 0 else 'high'
            }
        
        # 2. 虧損超過 ATR 2x
        if atr > 0:
            stop_loss = entry - (atr * 2)
            if current_price <= stop_loss:
                return {
                    'exit': True,
                    'reason': f'ATR停損 ({profit_pct:.1f}%)',
                    'urgency': 'high'
                }
        
        # 3. RSI 過熱
        if rsi and rsi >= 85:
            return {
                'exit': True,
                'reason': f'RSI過熱 ({rsi:.0f})',
                'urgency': 'medium'
            }
        
        # 4. Bias 過大
        if bias and bias >= 10:
            return {
                'exit': True,
                'reason': f'乖離過大 ({bias:.1f}%)',
                'urgency': 'medium'
            }
        
        # 5. ====== 獲利了結邏輯 ======
        
        if profit_pct >= 5:
            # 大幅獲利，考慮了結
            if self.status['status'] == 'overbought':
                # 市場過熱，先入袋
                return {
                    'exit': True,
                    'reason': f'多頭末段了結 ({profit_pct:.1f}%)',
                    'urgency': 'low'
                }
            elif profit_pct >= 8:
                # 獲利豐厚，入袋為安
                return {
                    'exit': True,
                    'reason': f'目標達成 ({profit_pct:.1f}%)',
                    'urgency': 'low'
                }
        
        elif profit_pct >= 2:
            # 小幅獲利
            if days >= 2:
                # 持有2天以上，可以考慮了結
                if self.status['status'] in ['bearish', 'neutral']:
                    return {
                        'exit': True,
                        'reason': f'盤整/空頭了結 ({profit_pct:.1f}%)',
                        'urgency': 'low'
                    }
        
        # 6. 虧損處理
        if profit_pct <= -3:
            # 虧損3%以上
            if days >= 3:
                # 持有3天以上，認賠
                return {
                    'exit': True,
                    'reason': f'認賠殺出 ({profit_pct:.1f}%)',
                    'urgency': 'high'
                }
        
        # ====== 不出场 ======
        return {
            'exit': False,
            'reason': '繼續持有',
            'urgency': None,
            'profit_pct': profit_pct,
            'max_hold': self.max_hold,
            'days_left': self.max_hold - days
        }
    
    def get_exit_priority(self, positions):
        """
        取得出场優先順序
        
        用於多檔持股時，優先了結哪些
        """
        if not positions:
            return []
        
        # 評分: 虧損 > 獲利了結 > 持有期滿
        scored = []
        for p in positions:
            score = 0
            
            # 虧損優先出
            if p.get('profit_pct', 0) < 0:
                score += 100
                score += abs(p['profit_pct'])
            else:
                score += p.get('profit_pct', 0)
            
            # 持有期滿優先出
            if p['days_held'] >= self.max_hold - 1:
                score += 50
            
            # RSI 過熱優先出
            if p.get('rsi', 50) >= 80:
                score += 30
            
            scored.append((p['symbol'], score))
        
        # 分數高的優先出
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

# ==================== 測試 ====================

def test():
    print('='*50)
    print(' Dynamic Exit System 測試')
    print('='*50)
    print()
    
    # 測試市場判斷
    mood = MarketMood.get_status()
    print(f'市場狀態: {mood["desc"]}')
    print(f'  TWII: {mood["twii"]:.0f}')
    print(f'  MA20: {mood["ma20"]:.0f}')
    print(f'  RSI: {mood["rsi"]:.1f}')
    print(f'  20日報酬: {mood["ret_20d"]:.1f}%')
    print(f'  最大持有: {mood["max_hold"]}天')
    print()
    
    # 測試出场判斷
    exit_mgr = DynamicExit(mood)
    
    test_cases = [
        # (entry, current, days, high, atr, rsi, bias, expected)
        (100, 102, 1, 102, 2, 65, 3, '繼續'),  # 小幅獲利1天
        (100, 105, 2, 105, 2, 68, 4, '繼續'),  # 獲利5% 2天
        (100, 108, 3, 108, 2, 72, 5, '了結'),  # 獲利8% 3天
        (100, 95, 3, 100, 2, 60, -3, '認賠'),  # 虧損5% 3天
        (100, 102, 5, 105, 2, 88, 8, '了結'),  # RSI過熱
        (100, 101, 7, 103, 2, 70, 5, '期滿'),  # 持有期滿
    ]
    
    print('出场測試:')
    print('-'*60)
    
    for entry, current, days, high, atr, rsi, bias, expected in test_cases:
        pos = {
            'entry_price': entry,
            'days_held': days,
            'high_since_entry': high,
            'atr': atr
        }
        
        result = exit_mgr.should_exit(pos, current, rsi, bias)
        
        status = '❌' if result['exit'] else '✅'
        print(f'{status} {entry}→{current} ({days}天) RSI={rsi} Bias={bias}')
        print(f'   {result["reason"]} (urgency: {result["urgency"]})')
        print()

if __name__ == '__main__':
    test()