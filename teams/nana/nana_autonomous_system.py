# -*- coding: utf-8 -*-
"""
Nana 自主開發交易系統 v59.0
自動生成時間: 2026-04-26 00:04:29
市場體制: OVERBOUGHT
基於知識: Nana_skills.json + learnings
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')
import json, os
from datetime import datetime, date
import yfinance as yf
import pandas as pd
import numpy as np

BASE_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\nana'

# === 策略參數（來自學習優化）===
ENTRY_RSI_MAX = 60
ENTRY_BIAS_MAX = 10.0
ENTRY_SCORE_MIN = 25
ATR_STOP = 1.5
ATR_TARGET = 3.0
BIAS_EXIT = 5.0
HOLD_DAYS_MAX = 10
MAX_POSITIONS = 5
VIRTUAL_CAPITAL = 100000

def get_market_regime():
    """根據學習結果自動設定市場體制"""
    REGIME_FILE = os.path.join(BASE_DIR, 'market_regime.json')
    if os.path.exists(REGIME_FILE):
        with open(REGIME_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            cs = data.get('current_state', {})
            return cs.get('regime', 'NEUTRAL'), cs.get('rsi', 50)
    return 'NEUTRAL', 50

def calculate_indicators(ticker_str):
    """計算完整技術指標"""
    try:
        ticker = yf.Ticker(ticker_str)
        h = ticker.history(period='3mo')
        if h.empty or len(h) < 30:
            return None
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
        
        # ADX
        adx = 100 - (100 / (1 + np.abs(c.diff().rolling(14).mean()) / (np.abs(c.diff().rolling(14).mean()) + 0.001)))
        
        # MACD
        ema12 = c.ewm(span=12).mean()
        ema26 = c.ewm(span=26).mean()
        macd = ema12 - ema26
        
        return {
            'close': round(float(last), 2),
            'rsi': round(float(rsi.iloc[-1]), 2),
            'bias': round(float(bias.iloc[-1]), 2),
            'atr': round(float(atr.iloc[-1]), 2),
            'ma20': round(float(ma20.iloc[-1]), 2),
            'ma60': round(float(ma60.iloc[-1]), 2) if len(c) >= 60 and not pd.isna(ma60.iloc[-1]) else None,
            'adx': round(float(adx.iloc[-1]), 2) if not pd.isna(adx.iloc[-1]) else None,
            'macd': round(float(macd.iloc[-1]), 2),
            'vol_ratio': round(float(v.iloc[-1] / vol_ma.iloc[-1]), 2) if vol_ma.iloc[-1] > 0 else 1.0,
        }
    except Exception as e:
        return None

def calculate_score(ind, regime):
    """根據市場體制動態評分"""
    score = 0
    rsi = ind.get('rsi', 50)
    bias = ind.get('bias', 0)
    vol = ind.get('vol_ratio', 1)
    
    # RSI評分（動態門檻）
    entry_rsi_max = 60
    if 40 <= rsi < 50:
        score += 30
    elif 50 <= rsi < entry_rsi_max:
        score += 25 if rsi < 60 else 15
    
    # BIAS評分
    if bias < -5: score += 20
    elif bias < 0: score += 15
    elif bias < 5: score += 10
    
    # Vol評分
    if vol >= 1.5: score += 25
    elif vol >= 1.2: score += 20
    elif vol >= 0.8: score += 10
    
    # ADX評分
    if ind.get('adx', 0) > 25: score += 15
    
    # MACD方向評分
    if ind.get('macd', 0) > 0: score += 10
    
    return score

def check_entry(ind, regime):
    """檢查進場條件"""
    entry_rsi_max = 60
    return (
        ind.get('rsi', 100) < entry_rsi_max
        and abs(ind.get('bias', 100)) < 10.0
        and ind.get('vol_ratio', 0) >= 0.8
        and regime != 'OVERBOUGHT'
    )

def check_exit(ind, entry_price, entry_atr, entry_date_str=None):
    """檢查出場條件"""
    cur = ind.get('close', entry_price)
    atr = ind.get('atr', entry_atr)
    bias = ind.get('bias', 0)
    
    stop = entry_price - (atr * 1.5)
    target = entry_price + (atr * 3.0)
    
    days = 0
    if entry_date_str:
        try:
            days = (datetime.now().date() - datetime.strptime(entry_date_str, '%Y-%m-%d').date()).days
        except:
            days = 0
    
    return {
        'stop_loss': cur <= stop,
        'target': cur >= target,
        'bias_exit': bias > 5.0,
        'hold_max': days >= 10,
        'stop_price': round(stop, 2),
        'target_price': round(target, 2),
        'return_pct': round(((cur - entry_price) / entry_price) * 100, 2),
        'hold_days': days,
    }

if __name__ == '__main__':
    print('=== Nana 自主開發系統 v59.0 ===')
    regime, market_rsi = get_market_regime()
    print(f'市場體制: {regime} | RSI: {market_rsi}')
    print('系統已準備就緒')
