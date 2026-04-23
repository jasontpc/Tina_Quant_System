# -*- coding: utf-8 -*-
"""
Nana + Tina 聯合分析報告 v1.0
標準化格式輸出
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
import yfinance as yf
import numpy as np
from datetime import datetime

DB_PATH = 'skills/stock-analyzer/scripts/tina_master.db'

def get_rsi(prices, period=14):
    delta = np.diff(prices)
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = np.mean(gain[-period:])
    avg_loss = np.mean(loss[-period:])
    if avg_loss == 0: return 100
    return 100 - (100 / (1 + avg_gain / avg_loss))

def analyze_joint(symbol):
    """Tina + Nana 聯合分析"""
    print('='*70)
    print(' 個股分析報告 - Tina + Nana 聯合')
    print('='*70)
    print()
    
    try:
        ticker = yf.Ticker(symbol + '.TW' if symbol.isdigit() else symbol)
        hist = ticker.history(period='90d')
        
        if len(hist) < 30:
            print(f' 資料不足: {symbol}')
            return
        
        prices = list(hist['Close'].values)
        current_price = prices[-1]
        prev_price = prices[-2]
        
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
            if r[1] and r[1] > 0: f_consec += 1
            else: break
        for r in rows:
            if r[2] and r[2] > 0: t_consec += 1
            else: break
        
        print('【一、v4.21 進場門檻檢查】')
        ma_ok = ma20 > ma60
        rsi_ok = rsi < 70
        atr_ok = atr_pct >= 0.5
        inst_ok = f_net_5d > 0 or t_net_5d > 0
        
        print(f'  MA20 > MA60: {"✅" if ma_ok else "❌"} ({ma20:.0f} > {ma60:.0f})')
        print(f'  RSI < 70: {"✅" if rsi_ok else "❌"} (RSI={rsi:.1f})')
        print(f'  ATR >= 0.5%: {"✅" if atr_ok else "❌"} (ATR={atr_pct:.2f}%)')
        print(f'  法人任一買超: {"✅" if inst_ok else "❌"} (F={f_net_5d/1000:.0f}K, T={t_net_5d/1000:.0f}K)')
        
        all_ok = ma_ok and rsi_ok and atr_ok and inst_ok
        print()
        print(f'  結論: [{"✅ 合格" if all_ok else "❌ 不合格"}] — {"准予進入評分階段" if all_ok else "不予進場"}')
        
        print()
        print('【二、量化評分】')
        
        # Tina 分數 (法人70 + 技術30)
        tina_inst = min(70, 10 * min(f_consec, 7) if f_consec > 0 else 0)
        tina_tech = (15 if 50 <= rsi <= 70 else 5 if 30 <= rsi < 50 else 5)
        tina_tech += (15 if -2 <= bias <= 3 else 10 if 3 < bias <= 6 else 0 if bias > 10 else 5)
        tina_total = tina_inst + tina_tech
        
        # Nana 分數 (法人80 + 技術20)
        nana_inst = 0
        if f_net_5d > 5000: nana_inst += 40
        elif f_net_5d > 0: nana_inst += 15
        if t_net_5d > 1000: nana_inst += 40
        elif t_net_5d > 0: nana_inst += 20
        if f_net_5d > 0 and t_net_5d > 0: nana_inst += 10
        nana_inst = min(80, nana_inst)
        
        nana_tech = 10 if 40 <= rsi <= 70 else 5
        nana_tech += 5 if ma20 > ma60 else 0
        nana_tech += 5 if atr_pct >= 1.0 else 3 if atr_pct >= 0.5 else 0
        nana_total = nana_inst + nana_tech
        
        print()
        print('  Tina (v4.21) 評分:')
        print(f'    法人: {tina_inst}/70 | 技術: {tina_tech}/30 | 總分: {tina_total}/100')
        print()
        print('  Nana (v1.0) 評分:')
        print(f'    法人: {nana_inst}/80 | 技術: {nana_tech}/20 | 總分: {nana_total}/100')
        
        print()
        print('【三、綜合評等】')
        
        if tina_total >= 80 and nana_total >= 60:
            rating = '⭐️ 強力買進'
        elif tina_total >= 60 or nana_total >= 60:
            rating = '✅ 買進'
        elif tina_total >= 40 or nana_total >= 40:
            rating = '⚠️ 觀望'
        else:
            rating = '❌ 不進場'
        
        print(f'  評等: {rating}')
        print(f'  Tina: {tina_total}/100 | Nana: {nana_total}/100')
        
        print()
        print('【四、操作建議】')
        if all_ok:
            print(f'  進場區間: ${current_price:.0f} 附近 ~ MA20 支撐 ${ma20:.0f}')
            print(f'  停損設定: 跌破 MA20 或近日低點')
            print(f'  目標獲利: RSI>80 或 法人連買放緩')
        else:
            print('  當前不符合進場條件，建議觀望')
        
        print()
        print('='*70)
        
    except Exception as e:
        print(f' 錯誤: {e}')

if __name__ == '__main__':
    if len(sys.argv) > 1:
        analyze_joint(sys.argv[1])
    else:
        print('使用: python joint_report.py 2330')