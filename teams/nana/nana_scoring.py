# -*- coding: utf-8 -*-
"""
Nana 系統 - 加權評分 v1.0
第二分析團隊領導人

與 Tina 的差異:
- 法人: 同步買超 (雙條件)
- 持有: 7天
- RSI: 40-70 (避開過熱/過冷)
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta

DB_PATH = 'skills/stock-analyzer/scripts/tina_master.db'

def get_rsi(prices, period=14):
    delta = np.diff(prices)
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = np.mean(gain[-period:])
    avg_loss = np.mean(loss[-period:])
    if avg_loss == 0: return 100
    return 100 - (100 / (1 + avg_gain / avg_loss))

def calculate_inst_score_nana(f_net, t_net, f_consec, t_consec):
    """
    Nana 法人評分 (最高80分)
    特點: 同步買超加分更高
    """
    base_score = 0
    
    # 外資分數 (最高40分)
    if f_net > 5000:
        f_score = 40
    elif f_net > 1000:
        f_score = 30
    elif f_net > 0:
        f_score = 15
    else:
        f_score = 0
    
    # 投信分數 (最高40分)
    if t_net > 1000:
        t_score = 40
    elif t_net > 0:
        t_score = 20
    else:
        t_score = 0
    
    base_score = f_score + t_score
    
    # 同步加分: 雙方都 > 0 →額外 +10分
    if f_net > 0 and t_net > 0:
        base_score += 10
    
    return min(80, base_score)

def calculate_tech_score_nana(rsi, bias, atr_pct, ma20, ma60):
    """
    Nana 技術評分 (最高20分)
    """
    score = 0
    
    # RSI (40-70 最佳) - 最高10分
    if 40 <= rsi <= 70:
        score += 10
    elif 30 <= rsi < 40 or 70 < rsi <= 80:
        score += 5
    else:
        score += 0
    
    # MA 多頭排列 - 最高5分
    if ma20 > ma60:
        score += 5
    
    # ATR 充足 (波動性) - 最高5分
    if atr_pct >= 1.0:
        score += 5
    elif atr_pct >= 0.5:
        score += 3
    else:
        score += 0
    
    return min(20, score)

def analyze_symbol_nana(symbol):
    """Nana 團隊分析"""
    print('=' * 70)
    print(' Nana 系統 v1.0 - 分析')
    print('=' * 70)
    
    try:
        # 抓 Yahoo Finance 資料
        ticker = yf.Ticker(symbol + '.TW' if symbol.isdigit() else symbol)
        hist = ticker.history(period='90d')
        
        if len(hist) < 30:
            print(f' 資料不足: {symbol}')
            return None
        
        prices = list(hist['Close'].values)
        current_price = prices[-1]
        prev_price = prices[-2]
        
        # 技術指標
        ma20 = np.mean(prices[-20:])
        ma60 = np.mean(prices[-60:]) if len(prices) >= 60 else ma20
        rsi = get_rsi(prices)
        
        hi = float(hist['High'].iloc[-1])
        lo = float(hist['Low'].iloc[-1])
        cl_prev = float(hist['Close'].iloc[-2])
        atr = max(hi-lo, abs(hi-cl_prev), abs(lo-cl_prev))
        atr_pct = atr / current_price * 100
        
        bias = (current_price / ma20 - 1) * 100
        
        # 法人資料
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('''
            SELECT date, foreign_net, trust_net FROM MarketData 
            WHERE symbol = ? ORDER BY date DESC LIMIT 10
        ''', (symbol,))
        rows = cur.fetchall()
        conn.close()
        
        f_net_5d = sum([r[1] for r in rows[:5] if r[1]])
        t_net_5d = sum([r[2] for r in rows[:5] if r[2]])
        
        # 計算連續天數
        f_consec = 0
        t_consec = 0
        for r in rows:
            if r[1] and r[1] > 0:
                f_consec += 1
            else:
                break
        for r in rows:
            if r[2] and r[2] > 0:
                t_consec += 1
            else:
                break
        
        # Nana 評分
        inst_score = calculate_inst_score_nana(f_net_5d, t_net_5d, f_consec, t_consec)
        tech_score = calculate_tech_score_nana(rsi, bias, atr_pct, ma20, ma60)
        total_score = inst_score + tech_score
        
        # 顯示結果
        print(f' 股票: {symbol}')
        print(f' 現價: {current_price:.2f}')
        print(f' RSI: {rsi:.1f}')
        print(f' ATR: {atr_pct:.2f}%')
        print(f' MA20: {ma20:.2f} | MA60: {ma60:.2f}')
        print(f' Bias: {bias:.2f}%')
        print(f' 外資5日: {f_net_5d:,.0f} | 投信5日: {t_net_5d:,.0f}')
        print()
        print(f' Nana 分數: {total_score}/100')
        print(f'   法人: {inst_score}/80')
        print(f'   技術: {tech_score}/20')
        
        # 訊號
        if total_score >= 80:
            signal = '⭐ 強力買進'
        elif total_score >= 60:
            signal = '✅ 買進'
        elif total_score >= 40:
            signal = '⚠️ 觀望'
        else:
            signal = '❌ 不進場'
        
        print(f' 訊號: {signal}')
        print('=' * 70)
        
        return {
            'symbol': symbol,
            'price': current_price,
            'rsi': rsi,
            'atr_pct': atr_pct,
            'inst_score': inst_score,
            'tech_score': tech_score,
            'total_score': total_score,
            'signal': signal
        }
        
    except Exception as e:
        print(f' 錯誤: {e}')
        return None

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        for symbol in sys.argv[1:]:
            analyze_symbol_nana(symbol)
    else:
        print('使用方法: python nana_scoring.py 2330 2454 2317')