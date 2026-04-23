# -*- coding: utf-8 -*-
"""
Nana v1.1 - Optimized after stress test
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np
import yfinance as yf
import sqlite3

DB_PATH = 'skills/stock-analyzer/scripts/tina_master.db'

PARAMS = {
    'rsi_max': 75,
    'atr_min': 0.003,
    'inst_min': 10,
    'total_min': 50,
    'entry_min': 65,
}

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

def inst_score(days):
    if days >= 11: return 20
    elif days >= 6: return 60
    elif days >= 4: return 50
    elif days == 3: return 40
    elif days == 2: return 15
    elif days == 1: return 10
    return 0

def analyze(symbol):
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
        
        high = df['High'].values
        low = df['Low'].values
        atr = np.mean(np.maximum(high - low, np.abs(high - np.roll(close, 1))))[-1]
        atr_pct = atr / close[-1]
        
        f_c, t_c = get_inst(symbol)
        f_s = inst_score(f_c)
        t_s = inst_score(t_c)
        base = max(f_s, t_s)
        if f_c >= 3 and t_c >= 3:
            base += 10
        inst_total = min(70, base)
        
        rsi_score = 15 if 50 <= rsi <= 70 else (10 if 30 <= rsi < 50 else 5)
        bias_score = 15 if -2 <= bias <= 3 else (10 if 3 < bias <= 6 else 0)
        total = inst_total + rsi_score + bias_score
        
        filters = []
        if rsi >= 75: filters.append('RSI_high')
        if inst_total == 0: filters.append('NoInst')
        if atr_pct < 0.003: filters.append('ATR_low')
        if ma20 <= ma60: filters.append('MA_down')
        
        rsi_ok = rsi < 75
        ma_ok = ma20 > ma60
        inst_ok = inst_total >= PARAMS['inst_min']
        atr_ok = atr_pct >= PARAMS['atr_min']
        
        entry_ok = rsi_ok and ma_ok and inst_ok and atr_ok
        
        if total >= PARAMS['entry_min'] and entry_ok:
            signal = 'BUY'
        elif total >= PARAMS['total_min'] and entry_ok:
            signal = 'buy'
        elif total < 40:
            signal = 'NO'
        else:
            signal = 'WATCH'
        
        return {
            'Code': symbol,
            'Date': str(df.index[-1])[:10],
            'Price': round(close[-1], 0),
            'Score': total,
            'InstScore': inst_total,
            'TechScore': rsi_score + bias_score,
            'RSI': round(rsi, 1),
            'Bias': round(bias, 1),
            'ATR%': round(atr_pct * 100, 2),
            'F': f_c,
            'T': t_c,
            'Signal': signal,
            'Filters': filters if filters else None
        }
    except Exception as e:
        return None

def main():
    print('='*50)
    print(' Nana v1.1 - Stress Test Optimized')
    print('='*50)
    print()
    
    stocks = ['2330', '2454', '2317', '2382', '3034', '2379', '2451', '2308', '2345', '2353']
    results = []
    
    for s in stocks:
        print(f' Analyzing {s}...', end=' ')
        r = analyze(s)
        if r:
            results.append(r)
            print(f'Score={r["Score"]} Signal={r["Signal"]}')
            if r['Filters']:
                print(f'  Filters: {r["Filters"]}')
    
    if not results:
        return
    
    df = pd.DataFrame(results)
    
    print()
    print('='*50)
    print(' Results')
    print('='*50)
    print()
    
    print('Signal Distribution:')
    for sig, cnt in df['Signal'].value_counts().items():
        print(f'  {sig}: {cnt} ({cnt/len(df)*100:.0f}%)')
    
    print()
    buys = df[df['Signal'].str.contains('BUY', case=False)]
    if len(buys) > 0:
        print('Entry Candidates:')
        for _, r in buys.iterrows():
            print(f'  {r["Code"]} | Price={r["Price"]} | Score={r["Score"]} | RSI={r["RSI"]}')
    
    df.to_json('Tina_Quant_System/teams/nana/scan_v11.json', orient='records', force_ascii=False)
    print()
    print('Saved: scan_v11.json')

if __name__ == '__main__':
    main()