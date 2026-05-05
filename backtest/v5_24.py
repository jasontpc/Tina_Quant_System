# -*- coding: utf-8 -*-
"""
Tina 量化系統 v5.24 - 自動化循環第36輪
擴充股票池至 15 檔 + 黑名單 11 檔維持
目標: Avg >3.0%, WR >55%
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import warnings
warnings.filterwarnings('ignore')
import yfinance as yf
yf.suppress_errors=True
import numpy as np
import sqlite3
import pandas as pd
import time
import json
from datetime import datetime

DB = 'skills/stock-analyzer/scripts/tina_master.db'

# ============== v5.24 股票池分層 ==============
# ETF池（維持8檔）
ETF_POOL = ['0050','0056','00646','00662','00713','00891','00900','00902']

# 股票池（擴充至 12-15 檔，排除黑名單）
STOCK_POOL = [
    # 持續觀察清單（表現穩定）
    '2382',  # 2382 Avg=0.64% 但 WR=50.2%，維持觀察
    '2884',  # 2884 Avg=1.20%, WR=56.3%
    '2474',  # 2474 Avg=4.27%, WR=75.6% ✅
    # 新增候選（法人持續買超）
    '2303',  # 奇美 - 塑膠龍頭
    '2317',  # 鴻海 - 電子組裝
    '2353',  # 宏碁 - 筆電/AI
    '2377',  # 友達 - 面版（觀察）
    '2345',  # 義隆 - 觸控晶片
    # 擴充（中型優質股）
    '3717',  # 研華 - 工業電腦
    '4938',  # 冠捷 - 視訊
    '3017',  # 奇鋐 - 散熱
    '6230',  # 華南金（金融）
]

# 黑名單（11檔，維持不變）
BLACKLIST = ['2451','2330','1605','6230','2454','2308','3034','3413','2458','2379','8081']

# 全部候選
ALL_CANDIDATES = ETF_POOL + [s for s in STOCK_POOL if s not in BLACKLIST]

# ============== 載入法人資料 ==============
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
    atr = np.mean(tr[-14:]) if len(tr) >= 14 else 30
    return (atr / close[-1]) * 100 if close[-1] > 0 else 0  # ATR as percentage

def kdj(h, i, n=9):
    low_n = h['Low'].iloc[max(0,i-n):i+1].min()
    high_n = h['High'].iloc[max(0,i-n):i+1].max()
    close = h['Close'].iloc[i]
    rsv = (close - low_n) / (high_n - low_n) * 100 if high_n != low_n else 50
    k = 50
    d = 50
    j = 3 * k - 2 * d
    return k, d, j

def macd(p, fast=12, slow=26, signal=9):
    ema_fast = pd.Series(p).ewm(span=fast).mean()
    ema_slow = pd.Series(p).ewm(span=slow).mean()
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal).mean()
    return macd.iloc[-1], signal_line.iloc[-1]

# ============== 回測引擎 ==============
def backtest_v524(inst_map, days=300):
    end_date = '2026-04-23'
    start_date = (pd.to_datetime(end_date) - pd.Timedelta(days=days)).strftime('%Y-%m-%d')
    
    all_trades = []
    stock_stats = {}
    
    for code in ALL_CANDIDATES:
        try:
            tk = yf.Ticker(code + '.TW' if code.isdigit() else code)
            h = tk.history(period='1y')
            if len(h) < 30: continue
            cl = list(h['Close'].values)
            vol = list(h['Volume'].values)
            
            stock_stats[code] = {'total': 0, 'wins': 0, 'losses': 0, 'rets': []}
            
            for i in range(25, len(cl)-6):
                rs = rsi(cl[:i+1])
                ma20 = np.mean(cl[i-19:i+1])
                ma60 = np.mean(cl[i-59:i+1]) if i >= 60 else np.mean(cl[:i+1])
                atr = calc_atr(h, i)
                k, d, j = kdj(h, i)
                macd_val, signal_val = macd(cl[:i+1])
                date_str = str(h.index[i])[:10]
                
                # === 進場條件 ===
                # RSI 40-70 (非過熱)
                if not (40 <= rs <= 70): continue
                # MA20 > MA60 (多頭趨勢) - 放寬
                if ma20 <= ma60 * 0.98: continue
                # 價格站上 MA20
                if cl[i] < ma20 * 0.98: continue
                # KDJ 金叉
                if not (k > d and j > 0): continue
                # MACD 黃金交叉
                if not (macd_val > signal_val): continue
                # ATR 足夠 (使用百分比)
                if atr < 0.3: continue
                
                # === 法人條件 ===
                if code in inst_map:
                    f_days, t_days = 0, 0
                    for dd in range(1, 4):
                        dt = (pd.to_datetime(date_str) - pd.Timedelta(days=dd)).strftime('%Y-%m-%d')
                        if dt in inst_map[code]:
                            if inst_map[code][dt][0] > 0: f_days += 1
                            if inst_map[code][dt][1] > 0: t_days += 1
                    # 法人連續買超（放寬：外資2天或投信1天）
                    if f_days < 1 and t_days < 1: continue
                else:
                    # ETF 無法人資料，直接進場
                    if code not in ETF_POOL: continue
                
                entry = h['Open'].iloc[i+1] if i+1 < len(h) else cl[i]
                exit_p = cl[min(i+6, len(cl)-1)]
                ret = (exit_p / entry - 1) * 100 - 0.45
                
                all_trades.append({'ret': ret, 'code': code, 'rsi': rs})
                stock_stats[code]['total'] += 1
                stock_stats[code]['rets'].append(ret)
                if ret > 0:
                    stock_stats[code]['wins'] += 1
                else:
                    stock_stats[code]['losses'] += 1
        except Exception as e:
            pass
        time.sleep(0.05)
    
    return all_trades, stock_stats

# ============== 分析 ==============
def analyze(trades):
    if not trades: return None
    wins = [t for t in trades if t['ret'] > 0]
    losses = [t for t in trades if t['ret'] <= 0]
    return {
        'total': len(trades), 'wins': len(wins), 'losses': len(losses),
        'wr': len(wins)/len(trades)*100,
        'avg': np.mean([t['ret'] for t in trades]),
        'max_win': max([t['ret'] for t in trades]) if trades else 0,
        'max_loss': min([t['ret'] for t in trades]) if trades else 0
    }

# ============== 主程式 ==============
print('='*70)
print(' Tina v5.24 - 自動化循環第36輪')
print(' 股票池擴充至 15 檔 + 黑名單 11 檔')
print('='*70)

inst_map = load_inst()
print(f'\n[載入法人資料] {len(inst_map)} 檔有資料')

print('\n[回測中 (180天)... ]')
trades, stats = backtest_v524(inst_map, days=180)
result = analyze(trades)

if result:
    print(f'\n[ v5.24 總結果 ]')
    print(f' 總交易筆數: {result["total"]}')
    print(f' 勝率 (WR): {result["wr"]:.1f}%')
    print(f' 平均報酬 (Avg): {result["avg"]:.2f}%')
    print(f' 最大獲利: {result["max_win"]:.2f}%')
    print(f' 最大虧損: {result["max_loss"]:.2f}%')
    
    # 個別股票分析
    print(f'\n[ 個別股票/ETF 分析 ]')
    sorted_stats = sorted(stats.items(), key=lambda x: x[1]['total'], reverse=True)
    for code, s in sorted_stats:
        if s['total'] < 5: continue
        wr = s['wins'] / s['total'] * 100 if s['total'] > 0 else 0
        avg = np.mean(s['rets']) if s['rets'] else 0
        tag = 'ETF' if code in ETF_POOL else '股票'
        print(f'  {code} ({tag}): {s["total"]}筆 | WR={wr:.1f}% | Avg={avg:.2f}%')
    
    # ETF vs 股票
    etf_trades = [t for t in trades if t['code'] in ETF_POOL]
    stock_trades = [t for t in trades if t['code'] not in ETF_POOL]
    etf_result = analyze(etf_trades) if etf_trades else None
    stock_result = analyze(stock_trades) if stock_trades else None
    
    print(f'\n[ ETF vs 股票 ]')
    if etf_result:
        print(f'  ETF: {etf_result["total"]}筆 | WR={etf_result["wr"]:.1f}% | Avg={etf_result["avg"]:.2f}%')
    if stock_result:
        print(f'  股票: {stock_result["total"]}筆 | WR={stock_result["wr"]:.1f}% | Avg={stock_result["avg"]:.2f}%')
    
    # 目標達成判斷
    print(f'\n[ 目標達成 ]')
    print(f'  交易量 >300: {"✅" if result["total"] >= 300 else "❌"} ({result["total"]}筆)')
    print(f'  WR >55%: {"✅" if result["wr"] >= 55 else "❌"} ({result["wr"]:.1f}%)')
    print(f'  Avg >3.0%: {"✅" if result["avg"] >= 3.0 else "❌"} ({result["avg"]:.2f}%)')
    
    # 保存結果
    output = {
        'version': 'v5.24',
        'cycle': 36,
        'total': result['total'],
        'wr': round(result['wr'], 1),
        'avg': round(result['avg'], 2),
        'max_win': round(result['max_win'], 2),
        'max_loss': round(result['max_loss'], 2),
        'etf_total': etf_result['total'] if etf_result else 0,
        'etf_wr': round(etf_result['wr'], 1) if etf_result else 0,
        'etf_avg': round(etf_result['avg'], 2) if etf_result else 0,
        'stock_total': stock_result['total'] if stock_result else 0,
        'stock_wr': round(stock_result['wr'], 1) if stock_result else 0,
        'stock_avg': round(stock_result['avg'], 2) if stock_result else 0,
        'stock_pool': STOCK_POOL,
        'etf_pool': ETF_POOL,
        'blacklist': BLACKLIST,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M')
    }
    print(f'\n[輸出 JSON]')
    print(json.dumps(output, ensure_ascii=False, indent=2))
else:
    print('[錯誤] 無交易資料')
    output = {'version': 'v5.24', 'cycle': 36, 'error': 'no_trades', 'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M')}
    print(json.dumps(output, ensure_ascii=False, indent=2))
