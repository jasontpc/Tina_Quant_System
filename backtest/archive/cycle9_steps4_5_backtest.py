# -*- coding: utf-8 -*-
"""
Cycle 9 Steps 4-5: 評分系統分析 + 擴充股票池回測
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
import time

DB = r'C:\Users\USER\.openclaw\workspace\skills\stock-analyzer\scripts\tina_master.db'

# 擴充股票池（49檔完整覆蓋 + 部分覆蓋 Tier1/Tier2）
FULL_POOL = ['2330','2454','3034','2379','2303','2344','2382','3231','4938',
    '2317','2353','2357','2345','3017','6230','4952','2401','2385',
    '2881','2882','2884','2885','2891','1301','1326','2002','0050','0056',
    '2610','2352','1216','2201','2207','2231','2376','2412','6505',
    '3583','4961','5871','6139','6415','6770','8046','3665','4977',
    '2615','2108','2501','2354','2618','2314','2392','2474','3702']

BLACKLIST = ['2379']  # cycle 8 黑名單
FULL_POOL = [s for s in FULL_POOL if s not in BLACKLIST]

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

def inst_score_v5(days):
    if days >= 11: return 70
    elif days >= 8: return 60
    elif days >= 6: return 55
    elif days >= 4: return 50
    elif days == 3: return 40
    elif days == 2: return 20
    elif days == 1: return 15
    return 0

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

def backtest_pool(pool, max_hold=5, days=180):
    end = '2026-04-23'
    start = (pd.to_datetime(end) - pd.Timedelta(days=days)).strftime('%Y-%m-%d')
    
    all_trades = []
    
    for code in pool:
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
                
                # Entry conditions (v5.2 with cycle 8 fixes)
                if rsi_v >= 65: continue
                if closes[i] < ma20: continue
                if ma20 <= ma60: continue
                if atr_pct < 0.3: continue
                if bias > 8: continue
                
                f_days = t_days = 0
                if code in inst_map:
                    for dd in range(1, 4):
                        dt = (pd.to_datetime(date_str) - pd.Timedelta(days=dd)).strftime('%Y-%m-%d')
                        if dt in inst_map[code]:
                            if inst_map[code][dt][0] > 0: f_days += 1
                            if inst_map[code][dt][1] > 0: t_days += 1
                    if max(f_days, t_days) < 1: continue
                
                # Scoring
                f_s = inst_score_v5(f_days); t_s = inst_score_v5(t_days)
                base = max(f_s, t_s)
                if f_days >= 3 and t_days >= 3: base += 10
                inst_v = min(70, base)
                rsi_s = 20 if 40 <= rsi_v <= 70 else (12 if 30 <= rsi_v < 40 else (10 if 70 < rsi_v <= 75 else 5))
                bias_s = 15 if -3 <= bias <= 5 else (10 if 5 < bias <= 8 else 5)
                atr_s = 10 if atr_pct >= 0.5 else (5 if atr_pct >= 0.3 else 0)
                tech = rsi_s + bias_s + atr_s
                trend = (15 if ma20 > ma60 else 0) + (10 if bias > 0 else 5)
                total = inst_v * 0.40 + tech * 0.35 + trend * 0.25
                
                entry_price = h['Open'].iloc[i+1] if i+1 < len(h) else closes[i]
                
                # inst_reversal exit
                position = {'entry': entry_price, 'days': 0}
                exit_reason = None
                exit_price = None
                
                for d in range(1, max_hold+1):
                    if i+d >= len(closes): break
                    curr_date = str(dates_idx[i+d])[:10]
                    curr_rsi = calc_rsi(closes[:i+d+1])
                    curr_ma20 = np.mean(closes[i+d-19:i+d+1])
                    curr_bias = (closes[i+d] / curr_ma20 - 1) * 100 if curr_ma20 > 0 else 0
                    
                    today_f = inst_map.get(code, {}).get(curr_date, (0,0))[0] if code in inst_map else 0
                    entry_f = inst_map.get(code, {}).get(date_str, (0,0))[0] if code in inst_map else 0
                    prev_d = (pd.to_datetime(curr_date) - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
                    prev_f = inst_map.get(code, {}).get(prev_d, (0,0))[0] if code in inst_map else 0
                    
                    if today_f < 0 and entry_f > 0 and prev_f > 0:
                        exit_reason = 'inst_reversal'; exit_price = closes[i+d]; break
                    
                    if d >= max_hold:
                        exit_reason = 'hold_max'; exit_price = closes[i+d]
                    elif curr_rsi >= 80:
                        exit_reason = 'rsi_overbought'; exit_price = closes[i+d]
                    elif curr_bias >= 8:
                        exit_reason = 'bias_high'; exit_price = closes[i+d]
                    elif np.mean(closes[i+d-19:i+d+1]) <= np.mean(closes[i+d-59:i+d+1]) if i+d >= 60 else False:
                        exit_reason = 'ma_cross'; exit_price = closes[i+d]
                    if exit_reason: break
                
                if not exit_reason:
                    exit_reason = 'hold_max'
                    exit_price = closes[min(i+max_hold, len(closes)-1)]
                
                profit = (exit_price / entry_price - 1) * 100 - 0.45
                
                all_trades.append({
                    'code': code, 'date': date_str, 'entry': entry_price, 'exit': exit_price,
                    'profit': profit, 'days': d, 'score': total,
                    'rsi_entry': rsi_v, 'bias_entry': bias, 'atr_pct': atr_pct,
                    'f_days': f_days, 't_days': t_days,
                    'exit_reason': exit_reason
                })
        except Exception as e:
            pass
        time.sleep(0.03)
    
    return all_trades

def tier_classify(code):
    tier1 = ['2330','2454','3034','2345','3017','6230','2385','2401','2382','3231','3717','4938']
    tier2 = ['3481','2409','6176','2412','2327','2492','2356','2471','2497','3665','6239']
    tier3 = ['2881','2882','2884','2885','2891','1301','1326','2002','0050','0056']
    if code in tier1: return 1
    if code in tier2: return 2
    return 3

def holding_test(pool, inst_map, hold_range=[3,4,5,6]):
    """測試不同持有期"""
    end = '2026-04-23'
    start = (pd.to_datetime(end) - pd.Timedelta(days=180)).strftime('%Y-%m-%d')
    
    results = {}
    for h in hold_range:
        results[h] = {'wins': 0, 'total': 0, 'total_profit': 0}
    
    for code in pool[:30]:  # Quick test on 30 stocks
        try:
            tk = yf.Ticker(code+'.TW')
            hist = tk.history(start=start, end=end, auto_adjust=True)
            if hist is None or len(hist) < 60: continue
            closes = list(hist['Close'])
            highs = list(hist['High'])
            lows = list(hist['Low'])
            dates_idx = list(hist.index)
            
            for i in range(30, len(closes)-7):
                date_str = str(dates_idx[i])[:10]
                ma20 = np.mean(closes[i-19:i+1])
                ma60 = np.mean(closes[i-59:i+1]) if i >= 60 else ma20
                rsi_v = calc_rsi(closes[:i+1])
                atr = calc_atr(closes, highs, lows, i)
                atr_pct = atr / closes[i] * 100 if closes[i] > 0 else 0
                bias = (closes[i] / ma20 - 1) * 100
                
                if rsi_v >= 65 or closes[i] < ma20 or ma20 <= ma60 or atr_pct < 0.3 or bias > 8: continue
                
                f_days = t_days = 0
                if code in inst_map:
                    for dd in range(1, 4):
                        dt = (pd.to_datetime(date_str) - pd.Timedelta(days=dd)).strftime('%Y-%m-%d')
                        if dt in inst_map[code]:
                            if inst_map[code][dt][0] > 0: f_days += 1
                            if inst_map[code][dt][1] > 0: t_days += 1
                    if max(f_days, t_days) < 1: continue
                
                entry_price = hist['Open'].iloc[i+1] if i+1 < len(hist) else closes[i]
                
                for h in hold_range:
                    exit_price = closes[min(i+h, len(closes)-1)]
                    profit = (exit_price / entry_price - 1) * 100 - 0.45
                    results[h]['total'] += 1
                    results[h]['total_profit'] += profit
                    if profit > 0: results[h]['wins'] += 1
        except:
            pass
        time.sleep(0.03)
    
    return results

print('='*60)
print(' Cycle 9 Steps 4-5: 評分系統分析 + 股票池回測')
print('='*60)

inst_map = load_inst()
print(f'[載入法人: {len(inst_map)} 檔股票]')
print(f'[股票池: {len(FULL_POOL)} 檔]')
print()

# Run backtest
print('[執行回測中...]')
all_trades = backtest_pool(FULL_POOL, max_hold=5)

if all_trades:
    wins = [t for t in all_trades if t['profit'] > 0]
    losses = [t for t in all_trades if t['profit'] <= 0]
    wr = len(wins)/len(all_trades)*100
    avg = np.mean([t['profit'] for t in all_trades])
    avg_win = np.mean([t['profit'] for t in wins]) if wins else 0
    avg_loss = np.mean([t['profit'] for t in losses]) if losses else 0
    
    print(f'\n=== 整體表現 ===')
    print(f'總交易: {len(all_trades)} | 勝利: {len(wins)} ({wr:.1f}%) | 失敗: {len(losses)}')
    print(f'平均報酬: {avg:.2f}% | 平均勝利: +{avg_win:.2f}% | 平均虧損: {avg_loss:.2f}%')
    
    # By exit reason
    print(f'\n=== Exit Reason 分析 ===')
    by_exit = {}
    for t in all_trades:
        r = t['exit_reason']
        if r not in by_exit: by_exit[r] = {'wins': 0, 'total_cnt': 0, 'total_profit': 0}
        by_exit[r]['total_cnt'] += 1
        by_exit[r]['total_profit'] += t['profit']
        if t['profit'] > 0: by_exit[r]['wins'] += 1
    
    for r, d in sorted(by_exit.items(), key=lambda x: x[1]['total_cnt'], reverse=True):
        wr_r = d['wins']/d['total_cnt']*100
        avg_r = d['total_profit']/d['total_cnt']
        print(f'  {r}: {d["total_cnt"]}次, WR={wr_r:.1f}%, avg={avg_r:.2f}%')
    
    # Top performers
    by_stock = {}
    for t in all_trades:
        c = t['code']
        if c not in by_stock: by_stock[c] = {'wins': 0, 'total': 0, 'total_p': 0}
        by_stock[c]['total'] += 1
        by_stock[c]['total_p'] += t['profit']
        if t['profit'] > 0: by_stock[c]['wins'] += 1
    
    for c in by_stock:
        by_stock[c]['wr'] = by_stock[c]['wins']/by_stock[c]['total']*100
        by_stock[c]['avg'] = by_stock[c]['total_p']/by_stock[c]['total']
    
    top_perf = sorted(by_stock.items(), key=lambda x: x[1]['avg'], reverse=True)[:10]
    print(f'\n=== Top 10 表現股票 ===')
    for s, d in top_perf:
        print(f'  {s}: WR={d["wr"]:.1f}%, avg={d["avg"]:.2f}%, n={d["total"]}')
    
    # Tier analysis
    print(f'\n=== Tier 分級分析 ===')
    tier_data = {1: [], 2: [], 3: []}
    for t in all_trades:
        tier = tier_classify(t['code'])
        tier_data[tier].append(t)
    
    for tier, trades in tier_data.items():
        if trades:
            w = [x for x in trades if x['profit'] > 0]
            wr_t = len(w)/len(trades)*100
            avg_t = np.mean([x['profit'] for x in trades])
            print(f'  Tier{tier}: {len(trades)} trades, WR={wr_t:.1f}%, avg={avg_t:.2f}%')
    
    # Score buckets
    print(f'\n=== Score 分桶分析 ===')
    score_buckets = {'<40': [], '40-50': [], '50-60': [], '>=60': []}
    for t in all_trades:
        if t['score'] < 40: score_buckets['<40'].append(t)
        elif t['score'] < 50: score_buckets['40-50'].append(t)
        elif t['score'] < 60: score_buckets['50-60'].append(t)
        else: score_buckets['>=60'].append(t)
    
    for b, trades in score_buckets.items():
        if trades:
            w = [x for x in trades if x['profit'] > 0]
            wr_b = len(w)/len(trades)*100
            avg_b = np.mean([x['profit'] for x in trades])
            print(f'  Score {b}: {len(trades)} trades, WR={wr_b:.1f}%, avg={avg_b:.2f}%')
    
    # hold_max breakdown
    hold_max_trades = [t for t in all_trades if t['exit_reason'] == 'hold_max']
    other_trades = [t for t in all_trades if t['exit_reason'] != 'hold_max']
    print(f'\n=== hold_max vs 其他出场 ===')
    if hold_max_trades:
        w_hm = [t for t in hold_max_trades if t['profit'] > 0]
        print(f'  hold_max: {len(hold_max_trades)}次, WR={len(w_hm)/len(hold_max_trades)*100:.1f}%, avg={np.mean([t["profit"] for t in hold_max_trades]):.2f}%')
    if other_trades:
        w_o = [t for t in other_trades if t['profit'] > 0]
        print(f'  其他: {len(other_trades)}次, WR={len(w_o)/len(other_trades)*100:.1f}%, avg={np.mean([t["profit"] for t in other_trades]):.2f}%')
    
    # Holding period test
    print(f'\n=== 持有期測試 ===')
    hold_results = holding_test(FULL_POOL, inst_map)
    for h, d in sorted(hold_results.items()):
        if d['total'] > 0:
            wr_h = d['wins']/d['total']*100
            avg_h = d['total_profit']/d['total']
            print(f'  {h}天: {d["total"]}次, WR={wr_h:.1f}%, avg={avg_h:.2f}%')

else:
    print(' 無交易資料')
