# -*- coding: utf-8 -*-
"""
步驟5: 股票池擴充 - 加入 VIF>=1.5 過濾
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import numpy as np
import json
import time

# 擴充候選池 (量能前200檔 + 主要ETF)
CANDIDATES = [
    # Tier1 (法人熱門)
    '2330','2454','3034','2379','3717','4938','2345','3017','6230','2451',
    '3665','4961','6477','3406','2385','5521','6153','2458','2377','6515',
    '6533','6531','2492','2474','3532','2308','2344','2401','2404','3033',
    '3686','3702','4935','4952','5215','5469','6139','6183','6257','6415',
    '6770','8046','8081','9917','2481','3545','3593','4722','4968','6239',
    # Tier2 (技術面熱門)
    '8261','9955','2327','2356','2471','2497','5203','3543','2498','8464',
    '1536','6605','2707','9945','2882','2884','2885','2886','2887','2890',
    '2892','2801','2812','2834','5871','1301','1326','2002','1216','1215',
    '2610','2603','2609','2630','3035','3044','3413','3481','2409','4904',
    '2412','6505','9914','9921','3583','2376','6282','6116','2456','2313',
    '2354','2201','2023','1723','2615','1609','2108','2501','2352','2317',
    # ETF
    '0050','0056','00646','00662','00891','00713','00751','00752','00878',
    '00900','00929','00937','00631L','00830','00757','00738U','00941',
    '00945B','00946','00768R','00633L'
]

def get_rsi(closes):
    d = np.diff(closes)
    g = np.where(d > 0, d, 0)
    l = np.where(d > 0, 0, -d)
    ag = np.mean(g[-14:])
    al = np.mean(l[-14:])
    return 100 - (100 / (1 + ag / al)) if al != 0 else 50

def calc_vif(closes, window=20):
    """計算VIF (波動性過濾指標) = ATR/MA20"""
    if len(closes) < window + 14:
        return 0
    trs = [max(closes[i]-closes[i-1], 
               closes[i]-min(closes[i-window:i]),
               max(closes[i-window:i])-closes[i]) 
           for i in range(window, len(closes))]
    atr = np.mean(trs[-14:]) if trs else 0
    ma = np.mean(closes[-window:])
    return atr / ma * 100 if ma > 0 else 0

def calc_volume_ratio(vols, window=20):
    """計算量能比 = 近20日均量 / 歷史均量"""
    if len(vols) < 60:
        return 1.0
    recent = np.mean(vols[-window:])
    hist = np.mean(vols[-60:-window])
    return recent / hist if hist > 0 else 1.0

def bt_full(code, holding=5):
    """完整回測 + VIF過濾"""
    try:
        tk = yf.Ticker(code + '.TW')
        h = tk.history(period='250d')
        if len(h) < 120:
            return None
        closes = list(h['Close'].values)
        highs = list(h['High'].values)
        vols = list(h['Volume'].values)
        
        trades = []
        for i in range(60, len(closes) - holding - 15):
            ma20 = np.mean(closes[i-19:i+1])
            ma60 = np.mean(closes[i-59:i+1]) if i >= 60 else ma20
            rsi = get_rsi(closes[:i+1])
            vif = calc_vif(closes[:i+1])
            vol_r = calc_volume_ratio(vols[:i+1])
            
            # 進場條件: RSI<70, MA20向上, VIF>=1.5, 量比>0.8
            if rsi >= 70 or ma20 <= closes[i] or vif < 1.5 or vol_r < 0.8:
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
                    trades.append({'return': (price/entry-1)*100, 'exit': 'SL', 'code': code, 'vif': vif})
                    exited = True
                    break
                
                # RSI > 75 出場
                if day > 1:
                    rsi_cur = get_rsi(closes[:i+day+1])
                    rsi_prev = get_rsi(closes[:i+day])
                    if rsi_prev >= 75 and rsi_cur < 75:
                        trades.append({'return': (price/entry-1)*100, 'exit': 'RSI', 'code': code, 'vif': vif})
                        exited = True
                        break
                
                if day == holding:
                    trades.append({'return': (price/entry-1)*100, 'exit': 'HOLD', 'code': code, 'vif': vif})
                    exited = True
                    break
            
            if not exited:
                trades.append({'return': (closes[i+holding]/entry-1)*100, 'exit': 'MAX', 'code': code, 'vif': vif})
        
        return trades
    except:
        return None

def stats(trades):
    if not trades:
        return {'total': 0, 'wins': 0, 'win_rate': 0, 'avg': 0, 'max_win': 0, 'max_loss': 0}
    rets = [t['return'] for t in trades]
    wins = [r for r in rets if r > 0]
    losses = [r for r in rets if r <= 0]
    return {
        'total': len(rets),
        'wins': len(wins),
        'win_rate': len(wins)/len(rets)*100,
        'avg': np.mean(rets),
        'max_win': max(wins) if wins else 0,
        'max_loss': min(losses) if losses else 0
    }

def avg_vol(code):
    try:
        tk = yf.Ticker(code + '.TW')
        h = tk.history(period='25d')
        if len(h) < 20:
            return 0
        return np.mean(list(h['Volume'].values)[-20:])
    except:
        return 0

print('='*60)
print(' 步驟5: 股票池擴充 (VIF>=1.5 過濾)')
print('='*60)

# 計算量能
print('\n[1/3] 計算量能...')
vol_map = {}
for i, code in enumerate(CANDIDATES):
    av = avg_vol(code)
    vol_map[code] = av
    if (i+1) % 30 == 0:
        print(f'  {i+1}/{len(CANDIDATES)}')

# 取量能 > 1000 的
viable = [c for c, v in vol_map.items() if v > 1000]
viable.sort(key=lambda x: vol_map[x], reverse=True)

# 擴充至200檔 (不足取現有的)
pool_200 = viable[:200] if len(viable) >= 200 else viable + list(set(CANDIDATES) - set(viable))[:200-len(viable)]

print(f'\n量能>1000: {len(viable)} 檔')
print(f'目標池: {len(pool_200)} 檔')

# 回測
print('\n[2/3] 回測 (VIF>=1.5 + vol>0.8)...')
all_trades = []
etf_trades = []
stock_trades = []

for i, code in enumerate(pool_200):
    trades = bt_full(code, 5)
    if trades:
        if code in ['0050','0056','00646','00662','00891','00713','00751','00752','00878',
                    '00900','00929','00937','00631L','00830','00757','00738U','00941',
                    '00945B','00946','00768R','00633L']:
            etf_trades.extend(trades)
        else:
            stock_trades.extend(trades)
        all_trades.extend(trades)
    if (i+1) % 30 == 0:
        print(f'  {i+1}/{len(pool_200)}')

# 統計
print('\n[3/3] 統計...')
s_all = stats(all_trades)
s_etf = stats(etf_trades)
s_stock = stats(stock_trades)

# Tier分組
tier1_codes = ['2330','2454','3034','2379','3717','4938','2345','3017','6230','2451',
               '3665','4961','6477','3406','2385','5521','6153','2458','2377','6515',
               '6533','6531','2492','2474','3532']
t1 = [t for t in all_trades if t['code'] in tier1_codes]
t2 = [t for t in all_trades if t['code'] not in tier1_codes]

print('\n' + '='*60)
print(' 股票池擴充報告')
print('='*60)
print(f'\n擴充結果:')
print(f'  總檔數: {len(pool_200)} (舊:108)')
etf_count = len([c for c in pool_200 if c in ['0050','0056','00646','00662','00891','00713','00751','00752','00878',
                                              '00900','00929','00937','00631L','00830','00757','00738U','00941',
                                              '00945B','00946','00768R','00633L']])
print(f'  ETF數量: {etf_count}')
print(f'  股票數量: {len(pool_200) - etf_count}')

print(f'\n新池回測結果 (5日持有, VIF>=1.5):')
print(f'  勝率: {s_all["win_rate"]:.1f}%')
print(f'  平均報酬: {s_all["avg"]:.2f}%')
print(f'  總信號: {s_all["total"]}筆')
print(f'  最大獲利: {s_all["max_win"]:.2f}%')
print(f'  最大虧損: {s_all["max_loss"]:.2f}%')

print(f'\n  Tier1: {len(t1)}筆, WR={stats(t1)["win_rate"]:.1f}%, avg={stats(t1)["avg"]:.2f}%')
print(f'  Tier2: {len(t2)}筆, WR={stats(t2)["win_rate"]:.1f}%, avg={stats(t2)["avg"]:.2f}%')
print(f'\n  ETF子池: {s_etf["total"]}筆, WR={s_etf["win_rate"]:.1f}%, avg={s_etf["avg"]:.2f}%')
print(f'  股票子池: {s_stock["total"]}筆, WR={s_stock["win_rate"]:.1f}%, avg={s_stock["avg"]:.2f}%')

# 寫入
result = {
    'date': '2026-04-23',
    'old_count': 108,
    'new_count': len(pool_200),
    'etf_count': etf_count,
    'stock_count': len(pool_200) - etf_count,
    'total_signals': s_all['total'],
    'win_rate': round(s_all['win_rate'], 1),
    'avg_return': round(s_all['avg'], 2),
    'max_win': round(s_all['max_win'], 2),
    'max_loss': round(s_all['max_loss'], 2),
    'etf_signals': s_etf['total'],
    'etf_win_rate': round(s_etf['win_rate'], 1),
    'etf_avg': round(s_etf['avg'], 2),
    'stock_signals': s_stock['total'],
    'stock_win_rate': round(s_stock['win_rate'], 1),
    'stock_avg': round(s_stock['avg'], 2),
    'pool': pool_200
}

with open('Tina_Quant_System/reports/step5_pool_expand.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False)

print('\n[完成]')