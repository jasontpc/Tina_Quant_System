# -*- coding: utf-8 -*-
"""
Nana System v3.0 - Quick Version
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

TIER1 = ['2330','2454','3034','2379','2303','2344','2382','3231','3717','4938',
         '2317','2353','2357','2345','3017','6230','6269','3044','6213',
         '4935','4952','2401','2340','2385']

TIER2 = ['3481','2409','6176','2412','3045','6239','6108','6192',
         '2471','2497','5203','2327','2492','2356','2376','2395','2308']

TIER3 = ['2881','2882','2884','2885','2891','2890','2801','2812','2834',
         '1301','1326','2002','2105','2201','1216','1702',
         '0050','0056','00662','00713','00891']

ALL = list(set(TIER1 + TIER2 + TIER3))

def get_rsi(closes):
    d = np.diff(closes)
    g = np.where(d > 0, d, 0)
    l = np.where(d > 0, 0, -d)
    ag = pd.Series(g).rolling(14).mean().iloc[-1]
    al = pd.Series(l).rolling(14).mean().iloc[-1]
    if al == 0: return 50
    return 100 - (100 / (1 + ag / al))

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
        if df is None or len(df) < 60:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        
        close = df['Close'].values
        high = df['High'].values
        low = df['Low'].values
        
        ma20 = float(pd.Series(close).rolling(20).mean().iloc[-1])
        ma60 = float(pd.Series(close).rolling(60).mean().iloc[-1])
        rsi = get_rsi(close)
        
        atr = float(pd.Series(np.maximum(high - low, np.abs(high - np.roll(close, 1)))).rolling(14).mean().iloc[-1])
        atr_pct = atr / close[-1] * 100
        
        bias = (close[-1] / ma20 - 1) * 100
        
        # 法人
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('SELECT foreign_net, trust_net FROM MarketData WHERE symbol = ? ORDER BY date DESC LIMIT 10', (symbol,))
        rows = cur.fetchall()
        conn.close()
        
        f_d = t_d = 0
        for f, t in rows:
            if f and f > 0: f_d += 1
            else: break
        for f, t in rows:
            if t and t > 0: t_d += 1
            else: break
        
        # 分數
        f_s = inst_score(f_d)
        t_s = inst_score(t_d)
        base = max(f_s, t_s)
        if f_d >= 3 and t_d >= 3: base += 10
        inst = min(70, base)
        
        rsi_s = 15 if 50 <= rsi <= 70 else (10 if 30 <= rsi < 50 else 5)
        bias_s = 15 if -2 <= bias <= 3 else (10 if 3 < bias <= 6 else 0)
        atr_s = 10 if atr_pct >= 0.5 else (5 if atr_pct >= 0.3 else 0)
        tech = rsi_s + bias_s + atr_s
        
        ma_s = 15 if ma20 > ma60 else 0
        trend = ma_s + 10
        
        total = inst * 0.40 + tech * 0.35 + trend * 0.25
        
        tier = 1 if symbol in TIER1 else (2 if symbol in TIER2 else 3)
        
        # 可交易判斷
        can_trade = total >= 50 and rsi < 85 and ma20 > ma60
        
        return {
            'symbol': symbol,
            'tier': tier,
            'score': round(total, 1),
            'inst': inst,
            'tech': tech,
            'trend': trend,
            'rsi': round(rsi, 1),
            'bias': round(bias, 1),
            'atr': round(atr_pct, 2),
            'f_days': f_d,
            't_days': t_d,
            'can_trade': can_trade,
            'price': round(close[-1], 0)
        }
    except:
        return None

def main():
    print()
    print('='*60)
    print(' Nana System v3.0')
    print('='*60)
    print()
    
    results = []
    for i, s in enumerate(ALL, 1):
        r = analyze(s)
        if r:
            results.append(r)
            if r['can_trade']:
                print(f'  {s}: {r["score"]}分 {"✅" if r["can_trade"] else "❌"}')
        if i % 20 == 0:
            print(f'  已掃描 {i}/{len(ALL)}...')
    
    results.sort(key=lambda x: x['score'], reverse=True)
    
    print()
    print('='*60)
    print(' Top 20')
    print('='*60)
    print()
    
    tier_icons = {1: '🥇', 2: '🥈', 3: '🥉'}
    
    print(f'{"排名":<4} {"代碼":<6} {"Tier":<4} {"總分":<6} {"法人":<5} {"RSI":<5} {"F天":<4} {"可交易"}')
    print('-'*50)
    
    for i, r in enumerate(results[:20], 1):
        icon = tier_icons.get(r['tier'], '')
        can = '✅' if r['can_trade'] else '❌'
        print(f'{i:<4} {r["symbol"]:<6} {icon}{r["tier"]:<3} {r["score"]:<6.1f} {r["inst"]:<5.1f} {r["rsi"]:<5.1f} {r["f_days"]:<4} {can}')
    
    # 儲存
    with open('Tina_Quant_System/teams/nana/system_v3_results.json', 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'total_scanned': len(results),
            'tradeable': len([r for r in results if r['can_trade']]),
            'results': results[:30]
        }, f, ensure_ascii=False, indent=2)
    
    print()
    print(f'可交易: {len([r for r in results if r["can_trade"]])} 檔')
    print('已儲存: system_v3_results.json')

if __name__ == '__main__':
    main()