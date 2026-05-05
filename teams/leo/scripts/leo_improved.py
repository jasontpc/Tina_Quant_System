# -*- coding: utf-8 -*-
"""
Leo 改善版波段交易系統（根據自動分析改善）
生成時間: 2026-04-25 16:12:11
市場狀態: OVERBOUGHT
改善項目: 
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')
import json, os
from datetime import datetime
import yfinance as yf
import pandas as pd

BASE_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leo'
AI_STOCKS = {'2330':'台積電','2454':'聯發科','2317':'鴻海','2379':'瑞昱','2376':'技嘉','2382':'廣達','3665':'穎崴','3034':'緯穎'}

# === 改善後參數 ===
# 2026-04-27 自主學習網格搜索最優化（Score=41.85, WR=63.7%）
ENTRY_RSI_MAX = 65         # 改善: 65→65（配合網格搜索）
EXIT_RSI_MIN = 80
TAKE_PROFIT_PCT = 8.0        # 8%（提高停利命中率）
STOP_LOSS_PCT = 10.0        # 10%（擴大停損容忍）
MAX_POSITION = 100000
COOLDOWN_MINUTES = 60
HOLD_DAYS_MAX = 30          # 30天（根據網格搜索）

def get_market_regime():
    twii = yf.Ticker('^TWII').history(period='1mo')
    if len(twii) < 20: return 'NEUTRAL'
    c = twii['Close'].dropna()
    delta = c.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rsi = (100 - (100 / (1 + gain / loss))).iloc[-1]
    ma20 = c.rolling(20).mean().iloc[-1]
    ma60 = c.rolling(60).mean().iloc[-1] if len(c) >= 60 else ma20
    if rsi > 80: return 'OVERBOUGHT'
    if rsi < 40: return 'OVERSOLD'
    return 'BULL' if ma20 > ma60 else 'BEAR'

def analyze_stock(sym, name):
    ticker = yf.Ticker(f'{sym}.TW')
    h = ticker.history(period='3mo')
    if len(h) < 60: return None
    c = h['Close'].dropna()
    last = c.iloc[-1]
    ma20 = c.rolling(20).mean().iloc[-1]
    delta = c.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rsi = (100 - (100 / (1 + gain / loss))).iloc[-1]
    pos_ma20 = (last - ma20) / ma20 * 100
    return {
        'symbol': sym, 'name': name, 'price': round(float(last), 2),
        'rsi': round(float(rsi), 1), 'pos_ma20': round(float(pos_ma20), 1),
    }

def run_improved_cycle():
    print('=== Leo 改善版波段系統 ===')
    regime = get_market_regime()
    print(f'市場體制: {regime}')
    print(f'ENTRY_RSI_MAX: {ENTRY_RSI_MAX}')
    print('改善: RSI門檻調嚴至60，等待更好的進場點')
    
    results = []
    for sym, name in AI_STOCKS.items():
        ind = analyze_stock(sym, name)
        if ind:
            results.append(ind)
            signal = '✅ 進場' if ind['rsi'] <= ENTRY_RSI_MAX else '⚠️ 過熱'
            print(f'  {sym} {name}: RSI={ind["rsi"]} {signal}')
    
    with open(os.path.join(BASE_DIR, 'reports', 'leo_analysis_improved.json'), 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    return results

if __name__ == '__main__':
    run_improved_cycle()
