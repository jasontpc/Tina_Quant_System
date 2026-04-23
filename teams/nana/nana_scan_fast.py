# -*- coding: utf-8 -*-
"""
Nana v1.0 台股快速掃描腳本
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np
import yfinance as yf
import sqlite3

DB_PATH = 'skills/stock-analyzer/scripts/tina_master.db'
STOCKS = ['2330', '2454', '2317', '2382', '3034', '2379', '2451', '2308', '2345', '2353']

def get_rsi(closes):
    d = np.diff(closes)
    g = np.where(d > 0, d, 0)
    l = np.where(d > 0, 0, -d)
    ag = np.mean(g[-14:])
    al = np.mean(l[-14:])
    return 100 - (100 / (1 + ag / al)) if al != 0 else 50

def get_inst(symbol):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT foreign_net, trust_net FROM MarketData WHERE symbol = ? ORDER BY date DESC LIMIT 10', (symbol,))
    rows = cur.fetchall()
    conn.close()
    f_c = t_c = 0
    for f, t in rows:
        if f and f > 0: f_c += 1
        else: break
    for f, t in rows:
        if t and t > 0: t_c += 1
        else: break
    return f_c, t_c

def scan(symbol):
    try:
        df = yf.download(symbol + '.TW', period='90d', auto_adjust=True, progress=False)
        if df is None or len(df) < 30:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        close = df['Close'].values
        ma20 = pd.Series(close).rolling(20).mean().iloc[-1]
        ma60 = pd.Series(close).rolling(60).mean().iloc[-1]
        rsi = get_rsi(close)
        bias = (close[-1] / ma20 - 1) * 100
        f_c, t_c = get_inst(symbol)
        
        def inst_score(d):
            if d >= 11: return 20
            elif d >= 6: return 60
            elif d >= 4: return 50
            elif d == 3: return 40
            elif d == 2: return 15
            elif d == 1: return 10
            return 0
        
        f_s = inst_score(f_c)
        t_s = inst_score(t_c)
        base = max(f_s, t_s)
        if f_c >= 3 and t_c >= 3:
            base += 10
        inst_total = min(70, base)
        
        rsi_score = 15 if 50 <= rsi <= 70 else (10 if 30 <= rsi < 50 else 5)
        bias_score = 15 if -2 <= bias <= 3 else (10 if 3 < bias <= 6 else 0)
        total = inst_total + rsi_score + bias_score
        
        rsi_ok = rsi < 70
        ma_ok = ma20 > ma60
        inst_ok = f_c > 0 or t_c > 0
        
        if total >= 80 and rsi_ok and ma_ok and inst_ok:
            signal = '⭐️ 買進'
        elif total >= 60 and rsi_ok and ma_ok and inst_ok:
            signal = '買進'
        elif total < 40:
            signal = '不進場'
        else:
            signal = '觀望'
        
        date_str = str(df.index[-1])[:10]
        return {
            '代號': symbol,
            '日期': date_str,
            '價格': round(close[-1], 0),
            '總分': total,
            '法人分': inst_total,
            '技術分': rsi_score + bias_score,
            'RSI': round(rsi, 1),
            'Bias': round(bias, 1),
            'F天': f_c,
            'T天': t_c,
            '訊號': signal
        }
    except Exception as e:
        return None

def main():
    print('='*50)
    print(' Nana v1.0 快速掃描')
    print('='*50)
    print()
    
    results = []
    for s in STOCKS:
        r = scan(s)
        if r:
            results.append(r)
            print(f' {s}: {r["總分"]}分 {r["訊號"]}')
        else:
            print(f' {s}: 失敗')
    
    if not results:
        print('無資料')
        return
    
    df = pd.DataFrame(results).sort_values('總分', ascending=False)
    
    print()
    print('='*50)
    print(' Top 10')
    print('='*50)
    print()
    print('%-6s %-8s %-8s %-7s %-7s %-6s %-6s %-5s' % ('代號', '日期', '價格', '總分', '法人', '技術', 'RSI', '訊號'))
    print('-'*50)
    
    for _, r in df.head(10).iterrows():
        print('%-6s %-8s %-8.0f %-7d %-7d %-6d %-6.1f %-5s' % (
            r['代號'], r['日期'], r['價格'], r['總分'], 
            r['法人分'], r['技術分'], r['RSI'], r['訊號']))
    
    print()
    print('='*50)
    
    df.to_json('Tina_Quant_System/teams/nana/scan_result.json', orient='records', force_ascii=False)
    print(' 已儲存: scan_result.json')

if __name__ == '__main__':
    main()