# -*- coding: utf-8 -*-
"""
Marcus - Top100 擴充回測系統
目標: 突破法人資料庫限制，擴充到 100 檔以上

策略:
- Tier1 (30檔): 科技/AI 相關 - 不需要法人資料
- Tier2 (30檔): 相關供應鏈 - 法人資料輔助
- Tier3 (40檔): 藍籌股 - 純技術面
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import warnings
warnings.filterwarnings('ignore')
import yfinance as yf
yf.suppress_errors = True
import numpy as np
import sqlite3
import pandas as pd
import time
import json
from datetime import datetime

DB = 'data/tina_master.db'

# ============== 擴充股票池 ==============

# Tier1: 科技/AI 領頭羊 (30檔) - 不需要法人資料
TIER1_AI = [
    '2330',  # 台積電
    '2454',  # 聯發科
    '2317',  # 鴻海
    '2303',  # 聯電
    '3034',  # 聯詠
    '2379',  # 瑞昱
    '3008',  # 大立光
    '2382',  # 廣達
    '3231',  # 緯創
    '3717',  # 緯穎
    '4938',  # 和碩
    '2345',  # 智邦
    '3017',  # 奇鋐
    '6230',  # 尼吉康
    '2451',  # 創意
    '3443',  # 群創
    '3583',  # 辛耘
    '3665',  # 昇陽
    '4961',  # 景碩
    '6477',  # 保瑞
    '3406',  # 玉晶光
    '2385',  # 群電
    '5521',  # 工信
    '6153',  # 嘉澤
    '2458',  # 義隆
    '2377',  # 瑞昱
    '6515',  # 穎崴
    '6683',  # 雍智
    '6533',  # 晶心科
    '6531',  # 愛普*
]

# Tier2: 相關供應鏈 (30檔) - 法人資料輔助
TIER2_SUPPLY = [
    '1590',  # 亞力
    '2308',  # 台達電
    '2344',  # 華邦電
    '2401',  # 南亞科
    '2404',  # 漢唐
    '2474',  # 可成
    '2481',  # 強茂
    '3033',  # 威健
    '3081',  # 聯亞
    '3317',  # 尼克森
    '3686',  # 達能
    '3702',  # 大聯大
    '4935',  # 竟庭
    '4952',  # 凌華
    '5215',  # 科嘉
    '5274',  # 信驊
    '5469',  # 瀚宇博
    '6104',  # 創惟
    '6139',  # 亞翔
    '6183',  # 遊戲橘子
    '6257',  # 矽格
    '6415',  # 矽創
    '6446',  # 聯策
    '6514',  # 芮特
    '6669',  # 緯穎
    '6770',  # 崇越
    '8046',  # 兆利
    '8081',  # 良維
    '8255',  # 朋程
    '9917',  # 中保科
]

# Tier3: 藍籌/高股息 (40檔) - 純技術面
TIER3_BLUE = [
    # 金控
    '2881',  # 富邦金
    '2882',  # 國泰金
    '2884',  # 玉山金
    '2885',  # 元大金
    '2886',  # 兆豐金
    '2887',  # 台新金
    '2891',  # 中信金
    '2892',  # 第一金
    '2890',  # 永豐金
    # 官股行庫
    '2801',  # 彰銀
    '2812',  # 台中銀
    '2834',  # 臺企銀
    '5871',  # 上海商銀
    # 傳產
    '1301',  # 台塑
    '1326',  # 台化
    '2002',  # 中鋼
    '1216',  # 統一
    '1215',  # 味全
    '1702',  # 茂迪
    '2610',  # 華航
    '2615',  # 長榮航
    '2603',  # 長榮
    '2609',  # 陽明
    '2618',  # 泰山
    '2630',  # 榮運
    '3035',  # 智原
    '3044',  # 崇越
    '3189',  # 景碩
    '3413',  # 京鼎
    '3481',  # 友達
    '2409',  # 友達
    '4904',  # 遠傳
    '2412',  # 中華電
    '3045',  # 台灣大
    '5864',  # 是方
    '6213',  # 聯茂
    '6505',  # 聯詠
    '6666',  # 羅麗芬
    '6706',  # 惠特
    '9914',  # 美利達
    '9921',  # 巨大
    '1536',  # 和大
    '6605',  # 帝寶
]

BLACKLIST = ['2615', '1590', '2382', '2317', '2303', '3008', '3231', '2408', '3443', '6446', '6669', '2597']

# 過濾黑名單
TIER1 = [s for s in TIER1_AI if s not in BLACKLIST][:28]
TIER2 = [s for s in TIER2_SUPPLY if s not in BLACKLIST][:28]
TIER3 = [s for s in TIER3_BLUE if s not in BLACKLIST][:36]

ALL_STOCKS = TIER1 + TIER2 + TIER3
print(f"Tier1 (AI/科技): {len(TIER1)} 檔")
print(f"Tier2 (供應鏈): {len(TIER2)} 檔")
print(f"Tier3 (藍籌): {len(TIER3)} 檔")
print(f"總計: {len(ALL_STOCKS)} 檔")

# ============== 法人資料載入 ==============
def load_inst():
    inst = {}
    try:
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute('SELECT symbol, date, foreign_net, trust_net FROM MarketData')
        for sym, date, f, t in cur.fetchall():
            if sym not in inst: inst[sym] = {}
            inst[sym][date] = (f or 0, t or 0)
        conn.close()
    except:
        pass
    return inst

# ============== 技術指標 ==============
def rsi(p):
    d = np.diff(p)
    g = np.where(d > 0, d, 0)
    l = np.where(d > 0, 0, -d)
    ag = np.mean(g[-14:])
    al = np.mean(l[-14:])
    return 100 - (100 / (1 + ag / al)) if al != 0 else 50

def calc_atr(h, i):
    high = list(h['High'].iloc[max(0,i-14):i+1])
    low = list(h['Low'].iloc[max(0,i-14):i+1])
    close = list(h['Close'].iloc[max(0,i-14):i+1])
    tr = [max(high[j]-low[j], abs(high[j]-close[j-1]), abs(low[j]-close[j-1])) for j in range(1, len(high))]
    return np.mean(tr[-14:]) if len(tr) >= 14 else 30

def macd_signal(p):
    ema12 = pd.Series(p).ewm(span=12).mean()
    ema26 = pd.Series(p).ewm(span=26).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9).mean()
    return macd.iloc[-1], signal.iloc[-1]

# ============== 回測引擎 ==============
def backtest_top100(inst_map, days=180):
    """擴充版回測引擎"""
    end_date = '2026-04-23'
    start_date = (pd.to_datetime(end_date) - pd.Timedelta(days=days)).strftime('%Y-%m-%d')
    
    all_trades = {'tier1': [], 'tier2': [], 'tier3': [], 'all': []}
    
    tier_map = {}
    for s in TIER1: tier_map[s] = 'tier1'
    for s in TIER2: tier_map[s] = 'tier2'
    for s in TIER3: tier_map[s] = 'tier3'
    
    for idx, code in enumerate(ALL_STOCKS):
        try:
            h = yf.Ticker(code+'.TW').history(start=start_date, end=end_date)
            if len(h) < 30: continue
            cl = list(h['Close'])
            vol = list(h['Volume'])
            
            for i in range(25, len(cl)-6):
                rs = rsi(cl[:i+1])
                ma20 = np.mean(cl[i-19:i+1])
                ma60 = np.mean(cl[i-59:i+1]) if i >= 60 else np.mean(cl[:i+1])
                atr = calc_atr(h, i)
                macd_val, signal_val = macd_signal(cl[:i+1])
                date_str = str(h.index[i])[:10]
                vr = vol[i] / np.mean(vol[i-19:i+1]) if np.mean(vol[i-19:i+1]) > 0 else 0
                
                # === 通用技術面條件 ===
                # 1. RSI 非過熱 (40-70)
                if not (40 <= rs <= 70): continue
                # 2. MA20 > MA60 (多頭趨勢)
                if ma20 <= ma60: continue
                # 3. 價格站上 MA20
                if cl[i] < ma20: continue
                # 4. MACD 多頭 (MACD > Signal)
                if not (macd_val > signal_val): continue
                # 5. ATR 足夠
                if atr < 30: continue
                
                # === Tier 分層邏輯 ===
                tier = tier_map.get(code, 'tier3')
                
                if tier == 'tier1':
                    # Tier1: 純技術面，不需法人
                    pass
                elif tier == 'tier2':
                    # Tier2: 法人輔助 (至少1天買超)
                    if code in inst_map:
                        has_inst = False
                        for d in range(1, 4):
                            dt = (pd.to_datetime(date_str) - pd.Timedelta(days=d)).strftime('%Y-%m-%d')
                            if dt in inst_map[code]:
                                f_net, t_net = inst_map[code][dt]
                                if f_net > 0 or t_net > 0:
                                    has_inst = True
                                    break
                        if not has_inst: continue
                    else:
                        # 無法人資料，放寬條件
                        if rs > 60: continue
                else:
                    # Tier3: 藍籌，嚴格技術面
                    if vr < 1.0: continue
                    if rs > 65: continue
                
                # 進場
                entry = h['Open'].iloc[i+1] if i+1 < len(h) else cl[i]
                exit_p = cl[min(i+6, len(cl)-1)]
                ret = (exit_p / entry - 1) * 100 - 0.45
                
                trade = {
                    'ret': ret, 'rsi': rs, 'atr': atr, 'vr': vr,
                    'bias': (cl[i]/ma20-1)*100, 'code': code, 'tier': tier
                }
                
                all_trades[tier].append(trade)
                all_trades['all'].append(trade)
                
        except Exception as e:
            pass
        time.sleep(0.05)
        
        if (idx + 1) % 20 == 0:
            print(f"  已處理 {idx+1}/{len(ALL_STOCKS)} 檔...")
    
    return all_trades

def analyze(trades):
    results = {}
    for key in ['tier1', 'tier2', 'tier3', 'all']:
        t = trades[key]
        if not t: 
            results[key] = None
            continue
        wins = [x for x in t if x['ret'] > 0]
        losses = [x for x in t if x['ret'] <= 0]
        results[key] = {
            'total': len(t), 'wins': len(wins), 'losses': len(losses),
            'wr': len(wins)/len(t)*100,
            'avg': np.mean([x['ret'] for x in t]),
            'max_win': max([x['ret'] for x in t]) if t else 0,
            'max_loss': min([x['ret'] for x in t]) if t else 0
        }
    return results

# ============== 主程式 ==============
print('='*70)
print(' Marcus Top100 擴充回測系統')
print('='*70)

inst_map = load_inst()
print(f"\n法人資料覆蓋: {len(inst_map)} 檔")

print('\n[ 回測中 (180天)... ]')
trades = backtest_top100(inst_map, days=180)
results = analyze(trades)

print('\n' + '='*70)
print(' 回測結果 (180天)')
print('='*70)

for tier in ['tier1', 'tier2', 'tier3', 'all']:
    r = results[tier]
    if r:
        tier_name = {'tier1': 'Tier1 科技/AI', 'tier2': 'Tier2 供應鏈', 'tier3': 'Tier3 藍籌', 'all': '整體'}[tier]
        print(f'\n{tier_name}:')
        print(f'  總交易: {r["total"]} | 勝: {r["wins"]} | 敗: {r["losses"]}')
        print(f'  勝率: {r["wr"]:.1f}%')
        print(f'  平均報酬: {r["avg"]:+.2f}%')
        print(f'  最大獲利: {r["max_win"]:+.2f}%')
        print(f'  最大虧損: {r["max_loss"]:+.2f}%')
    else:
        print(f'\n{tier}: 無交易資料')

print('\n' + '='*70)

# Save results
output = {
    'date': '2026-04-23',
    'stocks_count': len(ALL_STOCKS),
    'inst_coverage': len(inst_map),
    'results': {k: v for k, v in results.items() if v}
}
with open('reports/marcus_top100_results.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print('結果已儲存到 reports/marcus_top100_results.json')
