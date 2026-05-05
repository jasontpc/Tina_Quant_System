# -*- coding: utf-8 -*-
"""
Nana 改善版交易系統（根據自動分析改善）
生成時間: 2026-04-25 16:12:11
市場狀態: OVERBOUGHT
改善項目: 進場分數門檻: 25→35
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
ENTRY_RSI_MAX = 55          # 改善: 65→55（更嚴格進場）
ENTRY_SCORE_MIN = 35       # 改善: 25→35（過濾弱信號）
ENTRY_BIAS_MAX = 3.0       # 改善: 10%→3%（避免追漲）
ATR_STOP = 1.5
ATR_TARGET = 3.0
BIAS_EXIT = 5.0
HOLD_DAYS_MAX = 10
MAX_POSITIONS = 5
VIRTUAL_CAPITAL = 100000

def get_market_regime():
    """讀取市場體制"""
    REGIME_FILE = os.path.join(BASE_DIR, 'market_regime.json')
    if os.path.exists(REGIME_FILE):
        with open(REGIME_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('current_state', {}).get('regime', 'NEUTRAL')
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

def calculate_score(ind):
    """計算進場分數"""
    score = 0
    rsi = ind.get('rsi', 50)
    bias = ind.get('bias', 0)
    vol = ind.get('vol_ratio', 1)
    
    if 40 <= rsi < 50: score += 30
    elif 50 <= rsi < 55: score += 25  # 改善: 只有更低RSI才高分
    if bias < -3: score += 15
    elif bias < 0: score += 10
    if vol >= 1.5: score += 20
    elif vol >= 1.2: score += 15
    return score

def check_entry(ind, regime):
    """檢查進場條件（改善版）"""
    # 改善: OVERBOUGHT時全面禁止進場
    if regime == 'OVERBOUGHT':
        return False
    return (
        ind.get('rsi', 100) < ENTRY_RSI_MAX          # 改善: RSI<55
        and abs(ind.get('bias', 0)) < ENTRY_BIAS_MAX  # 改善: BIAS<3%
        and ind.get('vol_ratio', 0) >= 0.8
        and calculate_score(ind) >= ENTRY_SCORE_MIN  # 改善: 分數>=35
    )

def check_exit(ind, entry_price, entry_atr):
    """檢查出场條件"""
    cur = ind.get('close', entry_price)
    atr = ind.get('atr', entry_atr)
    bias = ind.get('bias', 0)
    stop = entry_price - (atr * ATR_STOP)
    target = entry_price + (atr * ATR_TARGET)
    return {
        'stop_loss': cur <= stop,
        'target': cur >= target,
        'bias_exit': bias > BIAS_EXIT,
        'return_pct': round(((cur - entry_price) / entry_price) * 100, 2),
    }

if __name__ == '__main__':
    print('=== Nana 改善版交易系統 ===')
    regime = get_market_regime()
    print(f'市場體制: {regime}')
    print(f'ENTRY_RSI_MAX: {ENTRY_RSI_MAX}')
    print(f'ENTRY_SCORE_MIN: {ENTRY_SCORE_MIN}')
    print(f'ENTRY_BIAS_MAX: {ENTRY_BIAS_MAX}')
    print('系統已準備就緒')
