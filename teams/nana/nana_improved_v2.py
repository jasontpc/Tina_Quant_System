# -*- coding: utf-8 -*-
"""
Nana 改善版交易系統 v2.0
根據自動分析改善，專注提高勝率
生成時間: 2026-04-25 23:29:30
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')
import json, os
from datetime import datetime, date
import yfinance as yf
import pandas as pd
import numpy as np

BASE_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\nana'

# === 改善後參數 ===
ENTRY_RSI_MAX = 55          # 改善: 65→55
ENTRY_SCORE_MIN = 35        # 改善: 25→35
ENTRY_BIAS_MAX = 3.0        # 新增: BIAS<3%
ATR_STOP = 1.0               # 改善: 1.5→1.0（更嚴格停損）
ATR_TARGET = 3.0
HOLD_DAYS_MAX = 7            # 改善: 10→7
MAX_POSITIONS = 5
VIRTUAL_CAPITAL = 100000
REGIME_FILTER = True         # OVERBOUGHT禁止進場

def get_market_regime():
    """檢查市場體制"""
    REGIME_FILE = os.path.join(BASE_DIR, 'market_regime.json')
    if os.path.exists(REGIME_FILE):
        with open(REGIME_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            regime = data.get('current_state', {}).get('regime', 'NEUTRAL')
            return regime
    return 'NEUTRAL'

def calculate_indicators(ticker_str):
    """計算技術指標"""
    try:
        ticker = yf.Ticker(ticker_str)
        h = ticker.history(period='3mo')
        if h.empty or len(h) < 30: return None
        c = h['Close'].dropna()
        h2 = h['High'].dropna()
        l = h['Low'].dropna()
        v = h['Volume'].dropna()
        
        last = c.iloc[-1]
        ma20 = c.rolling(20).mean()
        ma60 = c.rolling(60).mean()
        delta = c.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + gain / loss))
        bias = ((c - ma20) / ma20) * 100
        vol_ma = v.rolling(20).mean()
        tr1 = h2 - l
        tr2 = abs(h2 - c.shift())
        tr3 = abs(l - c.shift())
        atr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1).rolling(14).mean()
        
        return {
            'close': round(float(last), 2),
            'rsi': round(float(rsi.iloc[-1]), 2),
            'bias': round(float(bias.iloc[-1]), 2),
            'atr': round(float(atr.iloc[-1]), 2),
            'ma20': round(float(ma20.iloc[-1]), 2),
            'ma60': round(float(ma60.iloc[-1]), 2) if len(c) >= 60 else None,
            'vol_ratio': round(float(v.iloc[-1] / vol_ma.iloc[-1]), 2) if vol_ma.iloc[-1] > 0 else 1.0,
        }
    except: return None

def calculate_entry_score(ind):
    """計算進場分數"""
    score = 0
    rsi = ind.get('rsi', 50)
    bias = ind.get('bias', 0)
    vol = ind.get('vol_ratio', 1)
    
    # RSI評分（改善：只在40-55區間高分）
    if 40 <= rsi < 50: score += 35  # 最佳進場區間
    elif 50 <= rsi < 55: score += 25
    elif 55 <= rsi < 65: score += 10  # 降低分數
    
    # BIAS評分（改善：更嚴格）
    if abs(bias) < 2: score += 20
    elif abs(bias) < 3: score += 15
    
    # Vol評分
    if vol >= 1.5: score += 15
    elif vol >= 1.2: score += 10
    
    return score

def check_entry(ind, regime):
    """檢查進場條件（改善版）"""
    # OVERBOUGHT禁止進場
    if REGIME_FILTER and regime == 'OVERBOUGHT':
        return False, 'OVERBOUGHT禁止進場'
    
    # RSI條件
    if ind.get('rsi', 100) >= ENTRY_RSI_MAX:
        return False, 'RSI=' + str(ind.get('rsi')) + '過高'
    
    # BIAS條件
    if abs(ind.get('bias', 0)) > ENTRY_BIAS_MAX:
        return False, 'BIAS=' + str(abs(ind.get('bias'))) + '過大'
    
    # 分數條件
    score = calculate_entry_score(ind)
    if score < ENTRY_SCORE_MIN:
        return False, '分數不足=' + str(score)
    
    return True, '進場'

def check_exit(ind, entry_price, entry_atr, hold_days=0):
    """檢查出场條件（改善版）"""
    cur = ind.get('close', entry_price)
    atr = ind.get('atr', entry_atr)
    bias = ind.get('bias', 0)
    
    # 停損（改善：更嚴格）
    stop_price = entry_price - (atr * ATR_STOP)
    if cur <= stop_price:
        pct = round((cur - entry_price) / entry_price * 100, 2)
        return 'stop_loss', cur, pct
    
    # 停利
    target_price = entry_price + (atr * ATR_TARGET)
    if cur >= target_price:
        pct = round((cur - entry_price) / entry_price * 100, 2)
        return 'take_profit', cur, pct
    
    # BIAS離場（改善：5%→3%）
    if bias > 3.0:
        pct = round((cur - entry_price) / entry_price * 100, 2)
        return 'bias_exit', cur, pct
    
    # 持有期滿
    if hold_days >= HOLD_DAYS_MAX:
        pct = round((cur - entry_price) / entry_price * 100, 2)
        return 'hold_max', cur, pct
    
    return None, cur, round((cur - entry_price) / entry_price * 100, 2)

def run_improved_trading():
    """執行改善版交易"""
    print('=== Nana 改善版交易系統 v2.0 ===')
    regime = get_market_regime()
    print('市場體制: ' + str(regime))
    print('ENTRY_RSI_MAX: ' + str(ENTRY_RSI_MAX))
    print('ENTRY_SCORE_MIN: ' + str(ENTRY_SCORE_MIN))
    print('ENTRY_BIAS_MAX: ' + str(ENTRY_BIAS_MAX) + '%')
    print('ATR停損: ' + str(ATR_STOP) + 'x')
    print('HOLD_DAYS_MAX: ' + str(HOLD_DAYS_MAX) + '天')
    print()
    print('改善重點：')
    print('1. 勝率目標: 50%+（改善前: 29%）')
    print('2. 進場區間: RSI 40-55（最佳性價比）')
    print('3. ATR停損: 1.0x（更嚴格）')
    print('4. OVERBOUGHT禁止進場')
    print('5. BIAS<3%嚴格執行')
    return True

if __name__ == '__main__':
    run_improved_trading()
