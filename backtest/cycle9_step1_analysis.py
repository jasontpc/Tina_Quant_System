# -*- coding: utf-8 -*-
"""
Cycle 9 Step 1: Failure Analysis - 分析最近失敗交易
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
from datetime import datetime, timedelta

DB = r'C:\Users\USER\.openclaw\workspace\skills\stock-analyzer\scripts\tina_master.db'

# 主系統候選股票池
POOL = ['2330','2454','3034','2379','2303','2344','2382','3231','3717','4938',
        '2317','2353','2357','2345','3017','6230','6269','3044','6213','4935',
        '4952','2401','2340','2385','3481','2409','6176','2412','3045','6239',
        '2327','2492','2356','2471','2497','5203','2881','2882','2884','2885',
        '2891','2801','2812','2834','1301','1326','2002','0050','0056','00891','00713']

BLACKLIST = ['2615','1590','2382','2317','2303','3008','3231','2408','3443','6446','6669','2597','2379']
POOL = [s for s in POOL if s not in BLACKLIST]

def load_inst():
    inst = {}
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('SELECT symbol, date, foreign_net, trust_net FROM MarketData')
    for sym, date, f, t in cur.fetchall():
        if sym not in inst: inst[sym] = {}
        inst[sym][date] = (f or 0, t or 0)
    conn.close()
    return inst

def calc_rsi(closes):
    d = np.diff(closes)
    g = np.where(d > 0, d, 0)
    l = np.where(d > 0, 0, -d)
    ag = np.mean(g[-14:])
    al = np.mean(l[-14:])
    return 100 - (100 / (1 + ag / al)) if al != 0 else 50

def calc_atr(closes, highs, lows, i):
    trs = []
    for j in range(max(1, i-13), i+1):
        tr = max(highs[j]-lows[j], abs(highs[j]-closes[j-1]), abs(lows[j]-closes[j-1]))
        trs.append(tr)
    return np.mean(trs) if trs else 0

def backtest_with_failures(inst_map, days=180, max_hold=5):
    end = '2026-04-23'
    start = (pd.to_datetime(end) - pd.Timedelta(days=days)).strftime('%Y-%m-%d')
    
    all_trades = []
    fail_trades = []
    
    for code in POOL:
        try:
            tk = yf.Ticker(code+'.TW')
            h = tk.history(start=start, end=end, auto_adjust=True)
            if h is None or len(h) < 60: continue
            closes = list(h['Close'])
            highs = list(h['High'])
            lows = list(h['Low'])
            vols = list(h['Volume'])
            dates_idx = list(h.index)
            
            for i in range(30, len(closes)-max_hold-5):
                date_str = str(dates_idx[i])[:10]
                ma20 = np.mean(closes[i-19:i+1])
                ma60 = np.mean(closes[i-59:i+1]) if i >= 60 else ma20
                rsi_v = calc_rsi(closes[:i+1])
                atr = calc_atr(closes, highs, lows, i)
                atr_pct = atr / closes[i] * 100 if closes[i] > 0 else 0
                bias = (closes[i] / ma20 - 1) * 100
                vr = vols[i] / np.mean(vols[i-20:i]) if np.mean(vols[i-20:i]) > 0 else 0
                
                # Entry: v5.2 conditions
                if rsi_v >= 65: continue
                if closes[i] < ma20: continue
                if ma20 <= ma60: continue
                if atr_pct < 0.3: continue
                if bias > 8: continue  # cycle 8 fix
                
                # Inst filter
                f_days = t_days = 0
                if code in inst_map:
                    for dd in range(1, 4):
                        dt = (pd.to_datetime(date_str) - pd.Timedelta(days=dd)).strftime('%Y-%m-%d')
                        if dt in inst_map[code]:
                            if inst_map[code][dt][0] > 0: f_days += 1
                            if inst_map[code][dt][1] > 0: t_days += 1
                    if max(f_days, t_days) < 1: continue
                
                entry_price = h['Open'].iloc[i+1] if i+1 < len(h) else closes[i]
                
                # Simulate holding with exit conditions
                position = {'entry': entry_price, 'days': 0, 'entry_rsi': rsi_v, 'entry_bias': bias}
                exit_reason = None
                exit_price = None
                
                for d in range(1, max_hold+1):
                    if i+d >= len(closes): break
                    curr_rsi = calc_rsi(closes[:i+d+1])
                    curr_ma20 = np.mean(closes[i+d-19:i+d+1])
                    curr_bias = (closes[i+d] / curr_ma20 - 1) * 100 if curr_ma20 > 0 else 0
                    curr_date = str(dates_idx[i+d])[:10]
                    
                    # inst_reversal check (cycle 8 fix)
                    today_f = inst_map.get(code, {}).get(curr_date, (0,0))[0] if code in inst_map else 0
                    entry_f = inst_map.get(code, {}).get(date_str, (0,0))[0] if code in inst_map else 0
                    prev_d = (pd.to_datetime(curr_date) - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
                    prev_f = inst_map.get(code, {}).get(prev_d, (0,0))[0] if code in inst_map else 0
                    
                    if today_f < 0 and entry_f > 0 and prev_f > 0:
                        exit_reason = 'inst_reversal'
                        exit_price = closes[i+d]
                        break
                    
                    if d >= max_hold:
                        exit_reason = 'hold_max'
                        exit_price = closes[i+d]
                    elif curr_rsi >= 80:
                        exit_reason = 'rsi_overbought'
                        exit_price = closes[i+d]
                    elif curr_bias >= 8:
                        exit_reason = 'bias_high'
                        exit_price = closes[i+d]
                    elif np.mean(closes[i+d-19:i+d+1]) <= np.mean(closes[i+d-59:i+d+1]) if i+d >= 60 else False:
                        exit_reason = 'ma_cross'
                        exit_price = closes[i+d]
                    
                    if exit_reason:
                        break
                
                if not exit_reason:
                    exit_reason = 'hold_max'
                    exit_price = closes[min(i+max_hold, len(closes)-1)]
                
                profit = (exit_price / entry_price - 1) * 100 - 0.45
                
                trade = {
                    'code': code, 'date': date_str, 'entry': entry_price, 'exit': exit_price,
                    'profit': profit, 'days': position['days']+1,
                    'rsi_entry': rsi_v, 'bias_entry': bias, 'atr_pct': atr_pct,
                    'vr': vr, 'f_days': f_days, 't_days': t_days,
                    'exit_reason': exit_reason
                }
                all_trades.append(trade)
                if profit < 0:
                    fail_trades.append(trade)
        except Exception as e:
            pass
    return all_trades, fail_trades

print('='*70)
print(' Cycle 9 Step 1: 失敗交易分析')
print('='*70)

inst_map = load_inst()
print(f'\n[載入法人資料: {len(inst_map)} 檔股票]')
print('[執行回測中...]')
all_trades, fail_trades = backtest_with_failures(inst_map)

if not all_trades:
    print(' 無交易資料')
else:
    wins = [t for t in all_trades if t['profit'] > 0]
    losses = [t for t in all_trades if t['profit'] <= 0]
    
    print(f'\n總交易: {len(all_trades)} | 勝利: {len(wins)} ({len(wins)/len(all_trades)*100:.1f}%) | 失敗: {len(losses)} ({len(losses)/len(all_trades)*100:.1f}%)')
    
    print('\n--- 失敗因子分析 ---')
    fail_reasons = {}
    for t in fail_trades:
        r = t['exit_reason']
        if r not in fail_reasons: fail_reasons[r] = {'count': 0, 'total': 0, 'avg': 0}
        fail_reasons[r]['count'] += 1
        fail_reasons[r]['total'] += t['profit']
    
    for r, d in sorted(fail_reasons.items(), key=lambda x: x[1]['count'], reverse=True):
        d['avg'] = d['total'] / d['count']
        print(f'  {r}: {d["count"]}次, avg={d["avg"]:.2f}%, total={d["total"]:.2f}%')
    
    # 最失敗的股票
    by_stock = {}
    for t in fail_trades:
        c = t['code']
        if c not in by_stock: by_stock[c] = {'count': 0, 'total': 0}
        by_stock[c]['count'] += 1
        by_stock[c]['total'] += t['profit']
    
    worst_stocks = sorted(by_stock.items(), key=lambda x: x[1]['total'])[:10]
    print('\n--- 最失敗股票 (總虧損) ---')
    for s, d in worst_stocks:
        print(f'  {s}: {d["count"]}次, 總虧損={d["total"]:.2f}%')
    
    # 勝利因子分析
    print('\n--- 勝利關鍵因子 ---')
    rsi_win = [t for t in wins if t['rsi_entry'] < 50]
    bias_good = [t for t in wins if -3 <= t['bias_entry'] <= 5]
    vr_good = [t for t in wins if t['vr'] >= 1.5]
    inst_good = [t for t in wins if t['f_days'] >= 3 or t['t_days'] >= 3]
    print(f'  RSI<50進場: {len(rsi_win)}次 ({len(rsi_win)/len(wins)*100:.1f}%)')
    print(f'  Bias適中(-3~5%): {len(bias_good)}次 ({len(bias_good)/len(wins)*100:.1f}%)')
    print(f'  VR>=1.5: {len(vr_good)}次 ({len(vr_good)/len(wins)*100:.1f}%)')
    print(f'  法人>=3天: {len(inst_good)}次 ({len(inst_good)/len(wins)*100:.1f}%)')
    
    # 平均勝利/虧損
    avg_win = np.mean([t['profit'] for t in wins]) if wins else 0
    avg_loss = np.mean([t['profit'] for t in losses]) if losses else 0
    print(f'\n平均勝利: +{avg_win:.2f}% | 平均虧損: {avg_loss:.2f}%')
    print(f'勝利/虧損比: {abs(avg_win/avg_loss):.2f}' if avg_loss != 0 else 'N/A')
    
    print('\n--- 關鍵發現 ---')
    # RSI>70 still causing issues?
    rsi_high_losses = [t for t in losses if t['rsi_entry'] >= 60]
    print(f'1. RSI>=60進場失敗: {len(rsi_high_losses)}次 ({len(rsi_high_losses)/len(losses)*100:.1f}% of losses)')
    
    bias_high_losses = [t for t in losses if t['bias_entry'] > 5]
    print(f'2. Bias>5%進場失敗: {len(bias_high_losses)}次 ({len(bias_high_losses)/len(losses)*100:.1f}% of losses)')
    
    low_inst_losses = [t for t in losses if t['f_days'] < 2 and t['t_days'] < 2]
    print(f'3. 法人<2天進場失敗: {len(low_inst_losses)}次 ({len(low_inst_losses)/len(losses)*100:.1f}% of losses)')
    
    print('\n--- 改善建議 ---')
    # Recommend: raise RSI threshold for BULLISH vs OVERBOUGHT
    high_rsi_wins = [t for t in wins if 55 <= t['rsi_entry'] < 65]
    high_rsi_losses = [t for t in losses if 55 <= t['rsi_entry'] < 65]
    if high_rsi_losses:
        wr = len(high_rsi_wins) / (len(high_rsi_wins) + len(high_rsi_losses)) * 100
        print(f'  RSI 55-65 區間勝率: {wr:.1f}% ({"建議" if wr < 55 else "可接受"})')
