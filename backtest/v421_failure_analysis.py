# -*- coding: utf-8 -*-
"""
v4.21 失敗因子歸因分析
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

DB = 'skills/stock-analyzer/scripts/tina_master.db'

STOCKS = ['2330','2454','3034','2002','1301','1326','1216','2610','2891','2881',
    '5871','6505','3665','3017','2345','6230','3583','2360','6139','3189',
    '2308','2474','3033','3338','3702','4938','5880','6770','8046','8454',
    '8478','8499','3711','4961','2379','2451','2201','2207','2231','2352',
    '2353','2354','2356','2371','2373','2376','2383','2385','2392','2393',
    '2401','2402','2404','2412','2420','2423','2425','2426','2427','2428',
    '2429','2430','2431','2432','2433','2434','2436','2438','2439','4952',
    '6415','6183','2618','2630','2892','2884','2886','2887','2890']

BLACKLIST = ['2615','1590','2382','2317','2303','3008','3231','2408','3443','6446','6669','2597']
STOCKS = [s for s in STOCKS if s not in BLACKLIST][:100]

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

def backtest_v421(inst_map, days=180):
    end = '2026-04-23'
    start = (pd.to_datetime(end) - pd.Timedelta(days=days)).strftime('%Y-%m-%d')
    
    trades = []
    for code in STOCKS:
        try:
            h = yf.Ticker(code+'.TW').history(start=start, end=end)
            if len(h) < 60: continue
            cl = list(h['Close'])
            vol = list(h['Volume'])
            
            for i in range(30, len(cl)-6):
                rs = rsi(cl[:i+1])
                ma20 = np.mean(cl[i-19:i+1])
                ma60 = np.mean(cl[i-59:i+1])
                atr = calc_atr(h, i)
                atr_pct = atr / cl[i] * 100 if cl[i] > 0 else 0
                date_str = str(h.index[i])[:10]
                
                # v4.21 條件
                if rs >= 70: continue
                if cl[i] < ma20: continue
                if ma20 <= ma60: continue
                if atr_pct < 0.5: continue
                
                # 法人
                if code in inst_map:
                    f_days = t_days = 0
                    for dd in range(1, 4):
                        dt = (pd.to_datetime(date_str) - pd.Timedelta(days=dd)).strftime('%Y-%m-%d')
                        if dt in inst_map[code]:
                            if inst_map[code][dt][0] > 0: f_days += 1
                            if inst_map[code][dt][1] > 0: t_days += 1
                    if max(f_days, t_days) < 1: continue
                
                entry = h['Open'].iloc[i+1] if i+1 < len(h) else cl[i]
                exit_p = cl[min(i+6, len(cl)-1)]
                ret = (exit_p / entry - 1) * 100 - 0.45
                
                # 失敗因子分析
                bias = (cl[i] / ma20 - 1) * 100
                vr = vol[i] / np.mean(vol[i-20:i]) if np.mean(vol[i-20:i]) > 0 else 0
                
                trades.append({
                    'ret': ret, 'code': code, 'rsi': rs, 'atr': atr_pct,
                    'bias': bias, 'vr': vr, 'ma20': ma20, 'ma60': ma60
                })
        except:
            pass
        time.sleep(0.05)
    return trades

def analyze_failures(trades):
    losses = [t for t in trades if t['ret'] <= 0]
    wins = [t for t in trades if t['ret'] > 0]
    
    # 失敗因子分類
    fail_reasons = {
        'high_rsi': {'count': 0, 'total_loss': 0, 'avg_loss': 0},
        'low_vr': {'count': 0, 'total_loss': 0, 'avg_loss': 0},
        'high_bias': {'count': 0, 'total_loss': 0, 'avg_loss': 0},
        'low_atr': {'count': 0, 'total_loss': 0, 'avg_loss': 0},
        'ma_trend_weaken': {'count': 0, 'total_loss': 0, 'avg_loss': 0},
        'market_pullback': {'count': 0, 'total_loss': 0, 'avg_loss': 0},
    }
    
    for t in losses:
        reasons = []
        if t['rsi'] >= 65: reasons.append('high_rsi')
        if t['vr'] < 1.0: reasons.append('low_vr')
        if t['bias'] > 5: reasons.append('high_bias')
        if t['atr'] < 1.0: reasons.append('low_atr')
        if t['bias'] > 8: reasons.append('ma_trend_weaken')
        if t['ret'] < -3: reasons.append('market_pullback')
        
        for r in reasons:
            fail_reasons[r]['count'] += 1
            fail_reasons[r]['total_loss'] += t['ret']
    
    for r in fail_reasons:
        if fail_reasons[r]['count'] > 0:
            fail_reasons[r]['avg_loss'] = fail_reasons[r]['total_loss'] / fail_reasons[r]['count']
    
    # 勝利因子
    win_reasons = {
        'low_rsi': {'count': 0, 'total_gain': 0, 'avg_gain': 0},
        'good_vr': {'count': 0, 'total_gain': 0, 'avg_gain': 0},
        'moderate_bias': {'count': 0, 'total_gain': 0, 'avg_gain': 0},
        'high_atr': {'count': 0, 'total_gain': 0, 'avg_gain': 0},
    }
    
    for t in wins:
        reasons = []
        if t['rsi'] < 55: reasons.append('low_rsi')
        if t['vr'] >= 1.2: reasons.append('good_vr')
        if -2 <= t['bias'] <= 4: reasons.append('moderate_bias')
        if t['atr'] >= 1.0: reasons.append('high_atr')
        
        for r in reasons:
            win_reasons[r]['count'] += 1
            win_reasons[r]['total_gain'] += t['ret']
    
    for r in win_reasons:
        if win_reasons[r]['count'] > 0:
            win_reasons[r]['avg_gain'] = win_reasons[r]['total_gain'] / win_reasons[r]['count']
    
    return losses, wins, fail_reasons, win_reasons

print('='*70)
print(' v4.21 失敗因子歸因分析')
print(' 回測區間: 最近180天')
print('='*70)

inst_map = load_inst()
print('\n[ 回測中... ]')
trades = backtest_v421(inst_map)

if not trades:
    print(' 無交易資料')
else:
    losses, wins, fail_reasons, win_reasons = analyze_failures(trades)
    
    print('\n'+'='*70)
    print(' 總結')
    print('='*70)
    print(' 總交易次數: %d' % len(trades))
    print(' 勝利: %d (%.1f%%)' % (len(wins), len(wins)/len(trades)*100))
    print(' 失敗: %d (%.1f%%)' % (len(losses), len(losses)/len(trades)*100))
    print()
    
    print('='*70)
    print(' 失敗因子分析')
    print('='*70)
    print('%-20s %8s %12s %10s' % ('失敗因子', '次數', '總虧損', '平均虧損'))
    print('-'*55)
    
    sorted_fails = sorted(fail_reasons.items(), key=lambda x: x[1]['count'], reverse=True)
    for reason, data in sorted_fails:
        if data['count'] > 0:
            reason_name = {
                'high_rsi': 'RSI過高(>=65)',
                'low_vr': '成交量不足(VR<1)',
                'high_bias': '偏離均線過大(>5%)',
                'low_atr': '波動度不足(<1%)',
                'ma_trend_weaken': 'MA趨勢減弱(>8%)',
                'market_pullback': '市場回調(虧損>-3%)'
            }.get(reason, reason)
            print('%-20s %8d %+12.2f%% %+10.2f%%' % (reason_name, data['count'], data['total_loss'], data['avg_loss']))
    
    print()
    print('='*70)
    print(' 勝利因子分析')
    print('='*70)
    print('%-20s %8s %12s %10s' % ('勝利因子', '次數', '總獲利', '平均獲利'))
    print('-'*55)
    
    sorted_wins = sorted(win_reasons.items(), key=lambda x: x[1]['count'], reverse=True)
    for reason, data in sorted_wins:
        if data['count'] > 0:
            reason_name = {
                'low_rsi': 'RSI偏低(<55)',
                'good_vr': '成交量放大(VR>=1.2)',
                'moderate_bias': '偏離適中(-2%~4%)',
                'high_atr': '波動度充足(>=1%)'
            }.get(reason, reason)
            print('%-20s %8d %+12.2f%% %+10.2f%%' % (reason_name, data['count'], data['total_gain'], data['avg_gain']))
    
    print()
    print('='*70)
    print(' 檢討與建議')
    print('='*70)
    
    # 找出最大失敗因子
    top_fail = sorted_fails[0] if sorted_fails else None
    if top_fail and top_fail[1]['count'] > 0:
        print('\n【最大失敗因子】: %s (%d次)' % (top_fail[0], top_fail[1]['count']))
        print('  建議: 加入 %s 過濾條件' % top_fail[0])
    
    print('\n【勝利關鍵】:')
    top_win = sorted_wins[0] if sorted_wins else None
    if top_win and top_win[1]['count'] > 0:
        print('  %s 因子最能預測勝利 (%d次, 平均+%+.2f%%)' % (top_win[0], top_win[1]['count'], top_win[1]['avg_gain']))
    
    print('\n【優化建議】:')
    print('  1. RSI >= 65 的交易失敗率過高，建議提高進場門檻')
    print('  2. VR < 1.0 表示量能不足，應排除此類交易')
    print('  3. Bias > 5% 偏離過大，容易回調')
    print('  4. 勝利交易多有 low_rsi + good_vr 因子，可作為正向篩選')
    
    print()
    print('='*70)