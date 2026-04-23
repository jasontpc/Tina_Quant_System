# -*- coding: utf-8 -*-
"""
Nana Scanner - Top100 科技/AI 專用掃描器
=========================================
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np
import yfinance as yf
import sqlite3
import json
from datetime import datetime

DB_PATH = 'skills/stock-analyzer/scripts/tina_master.db'

def inst_score(days):
    if days >= 11: return 20
    elif days >= 6: return 60
    elif days >= 4: return 50
    elif days == 3: return 40
    elif days == 2: return 15
    elif days == 1: return 10
    return 0

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

def analyze(symbol):
    """分析單一股票"""
    try:
        df = yf.download(symbol + '.TW', period='90d', auto_adjust=True, progress=False)
        if df is None or len(df) < 30:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        
        close = df['Close'].values
        high = df['High'].values
        low = df['Low'].values
        ma20 = pd.Series(close).rolling(20).mean().iloc[-1]
        ma60 = pd.Series(close).rolling(60).mean().iloc[-1]
        rsi = get_rsi(close)
        bias = (close[-1] / ma20 - 1) * 100
        
        atr = np.mean(np.maximum(high - low, np.abs(high - np.roll(close, 1))))
        atr_pct = atr / close[-1] * 100
        
        f_c, t_c = get_inst(symbol)
        f_s = inst_score(f_c)
        t_s = inst_score(t_c)
        base = max(f_s, t_s)
        if f_c >= 3 and t_c >= 3: base += 10
        inst_total = min(70, base)
        
        rsi_score = 15 if 50 <= rsi <= 70 else (10 if 30 <= rsi < 50 else 5)
        bias_score = 15 if -2 <= bias <= 3 else (10 if 3 < bias <= 6 else 0)
        total = inst_total + rsi_score + bias_score
        
        # 過濾條件
        filters = []
        if rsi >= 75: filters.append('RSI_high')
        if rsi < 40: filters.append('RSI_low')
        if inst_total == 0: filters.append('NoInst')
        if atr_pct < 0.3: filters.append('ATR_low')
        if ma20 <= ma60: filters.append('MA_down')
        
        rsi_ok = 40 <= rsi <= 75
        ma_ok = ma20 > ma60
        atr_ok = atr_pct >= 0.3
        inst_ok = inst_total >= 10
        
        entry_ok = rsi_ok and ma_ok and atr_ok and inst_ok
        
        if total >= 65 and entry_ok:
            signal = 'BUY'
        elif total >= 50 and entry_ok:
            signal = 'buy'
        elif total < 40:
            signal = 'NO'
        else:
            signal = 'WATCH'
        
        return {
            'Code': symbol,
            'Price': round(close[-1], 0),
            'Score': total,
            'InstScore': inst_total,
            'TechScore': rsi_score + bias_score,
            'RSI': round(rsi, 1),
            'Bias': round(bias, 1),
            'ATR': round(atr_pct, 2),
            'MA20': round(ma20, 0),
            'MA60': round(ma60, 0),
            'F': f_c,
            'T': t_c,
            'Signal': signal,
            'Filters': filters if filters else None
        }
    except:
        return None

def scan_universe(stocks):
    """掃描整個股票池"""
    results = []
    print(f'掃描 {len(stocks)} 檔股票...')
    
    for i, s in enumerate(stocks, 1):
        r = analyze(s)
        if r:
            results.append(r)
            if r['Signal'] == 'BUY':
                print(f'  [{i}/{len(stocks)}] {s}: BUY! Score={r["Score"]}')
        
        if i % 20 == 0:
            print(f'  已掃描 {i}/{len(stocks)}...')
    
    return pd.DataFrame(results)

def get_top_picks(df, n=10):
    """取得Top N 候選"""
    if df is None or len(df) == 0:
        return pd.DataFrame()
    
    buys = df[df['Signal'].str.contains('BUY', case=False)]
    return buys.sort_values('Score', ascending=False).head(n)

def main():
    print('='*50)
    print(' Nana Top100 Scanner')
    print('='*50)
    print()
    
    # 載入股票池
    sys.path.insert(0, 'Tina_Quant_System/teams/nana')
    from nana_universe import ALL_STOCKS, get_tier_name, get_stock_count
    
    counts = get_stock_count()
    print(f'股票池: {counts["總計"]} 檔')
    print(f'  科技/AI核心: {counts["科技/AI核心"]} 檔')
    print(f'  科技相關: {counts["科技相關"]} 檔')
    print(f'  大型藍籌: {counts["大型藍籌"]} 檔')
    print()
    
    # 掃描
    df = scan_universe(ALL_STOCKS)
    
    if len(df) == 0:
        print('無資料')
        return
    
    # 分析結果
    print()
    print('='*50)
    print(' 掃描結果')
    print('='*50)
    print()
    
    print(f'總計: {len(df)} 檔')
    print()
    print('訊號分佈:')
    for sig, cnt in df['Signal'].value_counts().items():
        print(f'  {sig}: {cnt} ({cnt/len(df)*100:.0f}%)')
    
    # Top picks
    top = get_top_picks(df, 10)
    if len(top) > 0:
        print()
        print('Top 10 買進候選:')
        print('-'*70)
        print(f'{"代號":<6} {"價格":<8} {"總分":<5} {"法人":<5} {"RSI":<6} {"Bias":<6} {"F天":<4} {"T天":<4}')
        print('-'*70)
        for _, r in top.iterrows():
            print(f'{r["Code"]:<6} {r["Price"]:<8.0f} {r["Score"]:<5} {r["InstScore"]:<5} {r["RSI"]:<6.1f} {r["Bias"]:<6.1f} {r["F"]:<4} {r["T"]:<4}')
    
    # 儲存
    df.to_json('Tina_Quant_System/teams/nana/scan_universe.json', orient='records', force_ascii=False)
    top.to_json('Tina_Quant_System/teams/nana/top_picks.json', orient='records', force_ascii=False)
    print()
    print('已儲存: scan_universe.json, top_picks.json')
    
    return df, top

if __name__ == '__main__':
    main()