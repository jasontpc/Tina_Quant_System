# -*- coding: utf-8 -*-
"""
步驟5: 股票池擴充 - 從108檔擴充至200檔
加入量能過濾 (avg volume > 1000 lots/20d)
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import numpy as np
import json
import time
from datetime import datetime, timedelta

STOCKS_OLD = ['2330','2454','2317','3034','2451','2881','2891','3008','3189','6415','8046','2385',
              '2345','2308','2360','6139','3443','3523','3665','3717','4938','2382','6271','6230',
              '3017','2474','3532','2492','3533','6533','2458','2377','6515','6514','5469','6415',
              '3045','2409','3481','6213','6214','6225','6239','2481','5264','4935','4952','5215',
              '6183','6257','6770','8081','9917','3545','3593','4722','4968','8261','9955','2327',
              '2356','2471','2497','5203','2401','2340','3543','2498','8464','1536','6605','2707',
              '9945','2882','2884','2885','2886','2887','2890','2892','2801','2812','2834','5871',
              '1301','1326','2002','1216','1215','2610','2603','2609','2630','3035','3044','3413',
              '4904','2412','6505','9914','9921','3583','2376','6282','6116','2456','2313','2354',
              '0050','0056','00646','00662','00891','00713','00751','00752','00878','00900','00929','00937']

# ETF清單
ETFS = ['0050','0056','00646','00662','00891','00713','00751','00752','00878','00900','00929','00937',
        '00631L','00830','00757','00738U','00941','00945B','00946','00768R','00633L']

def get_rsi(closes):
    d = np.diff(closes)
    g = np.where(d > 0, d, 0)
    l = np.where(d > 0, 0, -d)
    ag = np.mean(g[-14:])
    al = np.mean(l[-14:])
    return 100 - (100 / (1 + ag / al)) if al != 0 else 50

def avg_volume_20d(code):
    """計算近20日平均成交量 ( lots)"""
    try:
        tk = yf.Ticker(code + '.TW')
        h = tk.history(period='25d')
        if len(h) < 20:
            return 0
        vols = list(h['Volume'].values)[-20:]
        return np.mean(vols)
    except:
        return 0

def bt_single(code, holding=5):
    """單一股票回測"""
    try:
        tk = yf.Ticker(code + '.TW')
        h = tk.history(period='180d')
        if len(h) < 100:
            return None
        closes = list(h['Close'].values)
        highs = list(h['High'].values)
        
        trades = []
        for i in range(50, len(closes) - holding - 15):
            ma20 = np.mean(closes[i-19:i+1])
            rsi = get_rsi(closes[:i+1])
            
            # 進場過濾: RSI < 70 且站上MA20
            if rsi >= 70 or ma20 <= closes[i]:
                continue
            
            entry = closes[i]
            peak = entry
            atr = np.mean([max(highs[i+j]-closes[i+j], closes[i+j]-list(h['Low'].values)[i+j]) 
                          for j in range(14)]) if i >= 14 else (entry * 0.02)
            
            exited = False
            for day in range(1, holding + 1):
                price = closes[i+day]
                high_h = max(highs[i:i+day+1])
                if high_h > peak:
                    peak = high_h
                
                # ATR 2x 停損
                if (price / entry - 1) * 100 < -2 * atr / entry * 100:
                    trades.append({'return': (price/entry-1)*100, 'exit': 'ATR', 'code': code})
                    exited = True
                    break
                
                # RSI > 75 出場
                if day > 1:
                    rsi_cur = get_rsi(closes[:i+day+1])
                    rsi_prev = get_rsi(closes[:i+day])
                    if rsi_prev >= 75 and rsi_cur < 75:
                        trades.append({'return': (price/entry-1)*100, 'exit': 'RSI', 'code': code})
                        exited = True
                        break
                
                if day == holding:
                    trades.append({'return': (price/entry-1)*100, 'exit': 'HOLD', 'code': code})
                    exited = True
                    break
            
            if not exited:
                trades.append({'return': (closes[i+holding]/entry-1)*100, 'exit': 'MAX', 'code': code})
        
        return trades
    except:
        return None

print('='*60)
print(' 步驟5: 股票池擴充 (108 -> 200)')
print('='*60)

# Step 1: 計算所有股票量能
print('\n[1/3] 計算量能...')
all_candidates = list(set(STOCKS_OLD + ETFS))
vol_map = {}
for i, code in enumerate(all_candidates):
    av = avg_volume_20d(code)
    vol_map[code] = av
    if (i+1) % 20 == 0:
        print(f'  已處理 {i+1}/{len(all_candidates)}')

# 排序取量能前200檔
sorted_codes = sorted(vol_map.items(), key=lambda x: x[1], reverse=True)
top200 = [c for c, v in sorted_codes if v > 1000][:200]  # 成交量 > 1000 lots

# 分離ETF與股票
etf_in_pool = [c for c in top200 if c in ETFS]
stock_in_pool = [c for c in top200 if c not in ETFS]

print(f'\n量能前200檔: {len(top200)} 檔')
print(f'  ETF: {len(etf_in_pool)} 檔')
print(f'  股票: {len(stock_in_pool)} 檔')

# Step 2: 回測新池
print('\n[2/3] 回測新池...')
new_trades = []
etf_trades = []
stock_trades = []

for i, code in enumerate(top200):
    trades = bt_single(code, 5)
    if trades:
        if code in ETFS:
            etf_trades.extend(trades)
        else:
            stock_trades.extend(trades)
        new_trades.extend(trades)
    if (i+1) % 50 == 0:
        print(f'  已回測 {i+1}/{len(top200)}')

# Step 3: 統計
print('\n[3/3] 統計分析...')

def stats(trades):
    if not trades:
        return {'total': 0, 'wins': 0, 'win_rate': 0, 'avg': 0}
    rets = [t['return'] for t in trades]
    wins = [r for r in rets if r > 0]
    return {
        'total': len(rets),
        'wins': len(wins),
        'win_rate': len(wins)/len(rets)*100,
        'avg': np.mean(rets)
    }

s_all = stats(new_trades)
s_etf = stats(etf_trades)
s_stock = stats(stock_trades)

print('\n' + '='*60)
print(' 股票池擴充報告')
print('='*60)
print(f'\n擴充結果:')
print(f'  總檔數: {len(top200)} (舊:108)')
print(f'  ETF數量: {len(etf_in_pool)}')
print(f'  股票數量: {len(stock_in_pool)}')

print(f'\n新池回測結果 (5日持有):')
print(f'  總信號: {s_all["total"]} 筆')
print(f'  勝率: {s_all["win_rate"]:.1f}%')
print(f'  平均報酬: {s_all["avg"]:.2f}%')

print(f'\n  ETF子池: {s_etf["total"]} 筆, WR={s_etf["win_rate"]:.1f}%, avg={s_etf["avg"]:.2f}%')
print(f'  股票子池: {s_stock["total"]} 筆, WR={s_stock["win_rate"]:.1f}%, avg={s_stock["avg"]:.2f}%')

# 寫入結果
result = {
    'date': '2026-04-23',
    'old_count': 108,
    'new_count': len(top200),
    'etf_count': len(etf_in_pool),
    'stock_count': len(stock_in_pool),
    'total_signals': s_all['total'],
    'win_rate': s_all['win_rate'],
    'avg_return': s_all['avg'],
    'etf_signals': s_etf['total'],
    'etf_win_rate': s_etf['win_rate'],
    'etf_avg': s_etf['avg'],
    'stock_signals': s_stock['total'],
    'stock_win_rate': s_stock['win_rate'],
    'stock_avg': s_stock['avg'],
    'pool': top200
}

with open('Tina_Quant_System/reports/step5_pool_expand.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False)

print('\n[完成] 結果已寫入 reports/step5_pool_expand.json')