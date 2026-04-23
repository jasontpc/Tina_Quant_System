# -*- coding: utf-8 -*-
"""
Nana Team v1.0 - 完整系統
第二分析團隊領導人

定位: 穩健型分析，與 Tina (v4.21) 交叉驗證
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
import yfinance as yf
import numpy as np
from datetime import datetime

DB_PATH = 'skills/stock-analyzer/scripts/tina_master.db'

# ============ 工具函數 ============

def get_rsi(prices, period=14):
    delta = np.diff(prices)
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = np.mean(gain[-period:])
    avg_loss = np.mean(loss[-period:])
    if avg_loss == 0: return 100
    return 100 - (100 / (1 + avg_gain / avg_loss))

def get_atr(h, period=14):
    if len(h) < 2:
        return 0
    trs = []
    for i in range(-period, 0):
        hi = float(h['High'].iloc[i])
        lo = float(h['Low'].iloc[i])
        cl = float(h['Close'].iloc[i-1]) if i-1 >= -len(h) else float(h['Close'].iloc[i])
        trs.append(max(hi-lo, abs(hi-cl), abs(lo-cl)))
    return np.mean(trs) if trs else 0

def get_inst_data(symbol, days=5):
    """取得法人資料"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        SELECT date, foreign_net, trust_net FROM MarketData 
        WHERE symbol = ? ORDER BY date DESC LIMIT ?
    ''', (symbol, days))
    rows = cur.fetchall()
    conn.close()
    return rows

# ============ Nana 評分函數 ============

def nana_inst_score(f_net, t_net, f_consec, t_consec):
    """
    Nana 法人評分 (最高80分)
    特點: 雙方同步買超加分更高
    """
    # 外資評分 (最高40分)
    if f_net > 5000:
        f_score = 40
    elif f_net > 1000:
        f_score = 30
    elif f_net > 0:
        f_score = 15
    else:
        f_score = 0
    
    # 投信評分 (最高40分)
    if t_net > 1000:
        t_score = 40
    elif t_net > 0:
        t_score = 20
    else:
        t_score = 0
    
    base = f_score + t_score
    
    # 同步加成 (雙方都買超)
    if f_net > 0 and t_net > 0:
        base += 10
    
    return min(80, base)

def nana_tech_score(rsi, bias, atr_pct, ma20, ma60):
    """
    Nana 技術評分 (最高20分)
    """
    score = 0
    
    # RSI 評分 (40-70 為最佳) - 最高10分
    if 40 <= rsi <= 70:
        score += 10
    elif 30 <= rsi < 40 or 70 < rsi <= 80:
        score += 5
    
    # MA 多頭排列 - 最高5分
    if ma20 > ma60:
        score += 5
    
    # ATR 波動性 - 最高5分
    if atr_pct >= 1.0:
        score += 5
    elif atr_pct >= 0.3:
        score += 3
    
    return min(20, score)

def check_nana_entry(rsi, atr_pct, ma20, ma60, f_net, t_net):
    """
    Nana v1.0 進場條件
    """
    # RSI 40-70 (不追過熱，不接過冷)
    if not (40 <= rsi <= 70):
        return False, 'RSI 超出 40-70 範圍'
    
    # ATR 充足
    if atr_pct < 0.3:
        return False, 'ATR 不足 0.3%'
    
    # MA 多頭排列
    if not (ma20 > ma60):
        return False, 'MA 空頭排列'
    
    # 法人同步買超 (任一方 > 0)
    if not (f_net > 0 or t_net > 0):
        return False, '法人無買超'
    
    return True, '符合進場條件'

# ============ 主分析函數 ============

def analyze(symbol):
    """完整 Nana 分析"""
    print('='*70)
    print(' Nana Team v1.0 個股分析')
    print('='*70)
    print()
    
    try:
        # 取得股價資料
        ticker = yf.Ticker(symbol + '.TW' if symbol.isdigit() else symbol)
        hist = ticker.history(period='90d')
        
        if len(hist) < 30:
            print(f' 資料不足: {symbol}')
            return None
        
        prices = list(hist['Close'].values)
        current = prices[-1]
        prev = prices[-2]
        
        # 技術指標
        ma20 = np.mean(prices[-20:])
        ma60 = np.mean(prices[-60:]) if len(prices) >= 60 else ma20
        rsi = get_rsi(prices)
        atr = get_atr(hist)
        atr_pct = atr / current * 100
        bias = (current / ma20 - 1) * 100
        
        # 法人資料
        rows = get_inst_data(symbol, 10)
        f_net_5d = sum([r[1] for r in rows[:5] if r[1]])
        t_net_5d = sum([r[2] for r in rows[:5] if r[2]])
        
        f_consec = 0
        t_consec = 0
        for r in rows:
            if r[1] and r[1] > 0: f_consec += 1
            else: break
        for r in rows:
            if r[2] and r[2] > 0: t_consec += 1
            else: break
        
        # ============ 進場條件檢查 ============
        print('【一、Nana v1.0 進場條件】')
        
        entry_ok, entry_msg = check_nana_entry(rsi, atr_pct, ma20, ma60, f_net_5d, t_net_5d)
        
        checks = [
            ('RSI 40-70', 40 <= rsi <= 70, f'{rsi:.1f}'),
            ('ATR >= 0.3%', atr_pct >= 0.3, f'{atr_pct:.2f}%'),
            ('MA20 > MA60', ma20 > ma60, f'{ma20:.0f} > {ma60:.0f}'),
            ('法人買超', f_net_5d > 0 or t_net_5d > 0, f'F={f_net_5d/1000:.0f}K, T={t_net_5d/1000:.0f}K'),
        ]
        
        for name, ok, detail in checks:
            print(f'  {name}: {"✅" if ok else "❌"} ({detail})')
        
        print(f'  結論: [{"✅ " + entry_msg if entry_ok else "❌ " + entry_msg}]')
        
        # ============ 評分 ============
        print()
        print('【二、Nana 評分】')
        
        inst_score = nana_inst_score(f_net_5d, t_net_5d, f_consec, t_consec)
        tech_score = nana_tech_score(rsi, bias, atr_pct, ma20, ma60)
        total = inst_score + tech_score
        
        print(f'  法人: {inst_score}/80')
        print(f'  技術: {tech_score}/20')
        print(f'  總分: {total}/100')
        
        # ============ 訊號 ============
        print()
        print('【三、綜合評等】')
        
        if entry_ok and total >= 80:
            signal = '⭐️ 強力買進'
        elif entry_ok and total >= 60:
            signal = '✅ 買進'
        elif entry_ok and total >= 40:
            signal = '⚠️ 觀望'
        else:
            signal = '❌ 不進場'
        
        print(f'  訊號: {signal}')
        
        if entry_ok:
            print()
            print('【四、操作建議】')
            print(f'  進場: ${current:.0f} 附近')
            print(f'  停損: 跌破 MA20 (${ma20:.0f})')
            print(f'  目標: RSI>80 或法人放緩')
        
        print()
        print('='*70)
        
        return {
            'symbol': symbol,
            'price': current,
            'rsi': rsi,
            'atr_pct': atr_pct,
            'ma20': ma20,
            'ma60': ma60,
            'bias': bias,
            'f_net': f_net_5d,
            't_net': t_net_5d,
            'inst_score': inst_score,
            'tech_score': tech_score,
            'total': total,
            'signal': signal,
            'entry_ok': entry_ok
        }
        
    except Exception as e:
        print(f' 錯誤: {e}')
        return None

def scan_watchlist():
    """掃描觀察名單"""
    print()
    print('='*70)
    print(' Nana v1.0 觀察名單掃描')
    print('='*70)
    print()
    
    watchlist = ['2330', '2454', '2317', '3034', '2382', '2379', '2451', '2881', '2891', '3008']
    
    results = []
    for code in watchlist:
        print(f' 掃描 {code}...')
        r = analyze(code)
        if r:
            results.append(r)
        print()
    
    # 排序
    results.sort(key=lambda x: x['total'], reverse=True)
    
    print()
    print('='*70)
    print(' Nana 觀察名單排名')
    print('='*70)
    print()
    print('%-6s %-8s %-8s %-8s %-8s %-10s' % ('代碼', '現價', 'RSI', '法人', '總分', '訊號'))
    print('-'*60)
    
    for r in results:
        print('%-6s %-8.0f %-8.1f %-8.0f %-8d %-10s' % (
            r['symbol'], r['price'], r['rsi'], 
            (r['f_net']+r['t_net'])/1000,
            r['total'], r['signal']))
    
    print()
    print('='*70)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == '--scan':
            scan_watchlist()
        else:
            analyze(sys.argv[1])
    else:
        print('使用: python nana.py [代碼] 或 python nana.py --scan')