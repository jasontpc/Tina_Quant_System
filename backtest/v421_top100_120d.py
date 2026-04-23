# -*- coding: utf-8 -*-
"""
Tina v4.21 完整回測
市值前100大 | 120天 | KDJ+MACD+MA+法人
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import numpy as np
import sqlite3

DB = 'skills/stock-analyzer/scripts/tina_master.db'

# Top 100
TOP100 = [
    '2330','2454','2317','2382','3034','2379','2451','2308','2345','2353',
    '2395','2401','2421','2449','2474','2492','2610','2880','2881','2882',
    '2883','2884','2885','2886','2887','2888','2891','2892','3008','3033',
    '3044','3189','3229','3231','3443','3481','3665','3717','4938','4958',
    '4961','5871','5880','6409','6415','6505','6669','6770','8016','8046',
    '8105','8233','8261','8341','8464','8478','8926','8996','9945','1234',
    '2312','2327','2337','2344','2385','2390','2515','2527','2603','2609',
    '2707','2823','2834','2855','2912','2939','3029','3045','3088','3105',
    '3234','3257','3294','3305','3380','3416','3443','3533','3557','3593',
    '3596','3610','3673','3686','3702','3711','3722','4001','4002','4904'
]

def get_rsi(closes):
    d = np.diff(closes)
    g = np.where(d > 0, d, 0)
    l = np.where(d > 0, 0, -d)
    ag = np.mean(g[-14:])
    al = np.mean(l[-14:])
    return 100 - (100 / (1 + ag / al)) if al != 0 else 50

def get_kdj(h, i):
    period = 9
    k_period = 3
    d_period = 3
    
    if i < period:
        return 50, 50, False
    
    lows = [float(h['Low'].iloc[j]) for j in range(i-period, i)]
    highs = [float(h['High'].iloc[j]) for j in range(i-period, i)]
    
    lo = min(lows)
    hi = max(highs)
    close = float(h['Close'].iloc[i-1])
    
    if hi == lo:
        rsv = 50
    else:
        rsv = (close - lo) / (hi - lo) * 100
    
    # 簡化: 用目前的 K, D
    k_vals = []
    d_vals = []
    for j in range(period, i):
        lj = min([float(h['Low'].iloc[t]) for t in range(j-period, j)])
        hj = max([float(h['High'].iloc[t]) for t in range(j-period, j)])
        cj = float(h['Close'].iloc[j-1])
        if hj == lj:
            rsvj = 50
        else:
            rsvj = (cj - lj) / (hj - lj) * 100
        
        if len(k_vals) == 0:
            k = 50
            d = 50
        else:
            k = 2/3 * k_vals[-1] + 1/3 * rsvj
            d = 2/3 * d_vals[-1] + 1/3 * k
        k_vals.append(k)
        d_vals.append(d)
    
    k = k_vals[-1] if k_vals else 50
    d = d_vals[-1] if d_vals else 50
    k_cross_d = k_vals[-1] > d_vals[-1] if len(k_vals) > 1 else False
    
    return k, d, k_cross_d

def get_macd(closes):
    if len(closes) < 26:
        return 0, 0, False
    
    ema12 = []
    ema26 = []
    for i in range(len(closes)):
        if i == 0:
            e12 = closes[i]
            e26 = closes[i]
        else:
            e12 = (11/13) * ema12[-1] + (2/13) * closes[i]
            e26 = (25/27) * ema26[-1] + (2/27) * closes[i]
        ema12.append(e12)
        ema26.append(e26)
    
    macd = [e12 - e26 for e12, e26 in zip(ema12, ema26)]
    
    if len(macd) < 9:
        return 0, 0, False
    
    macd_val = macd[-1]
    macd_signal = np.mean(macd[-9:])
    macd_bull = macd_val > macd_signal
    
    return macd_val, macd_signal, macd_bull

def get_atr(h, i):
    trs = []
    for j in range(i-14, i):
        if j < 0:
            continue
        hi = float(h['High'].iloc[j])
        lo = float(h['Low'].iloc[j])
        cl = float(h['Close'].iloc[j-1]) if j-1 >= 0 else float(h['Close'].iloc[j])
        trs.append(max(hi-lo, abs(hi-cl), abs(lo-cl)))
    return np.mean(trs) if trs else 0

def check_inst(code, date):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('''
        SELECT COUNT(*) FROM MarketData
        WHERE symbol = ? AND date <= ? AND date >= date(?, '-3 days')
        AND (foreign_net > 0 OR trust_net > 0)
    ''', (code, date, date))
    count = cur.fetchone()[0]
    conn.close()
    return count >= 1

def backtest_v421(holding_days=5):
    trades = []
    signals = []
    
    for code in TOP100:
        try:
            h = yf.Ticker(code + '.TW').history(period='160d')
            if len(h) < 120:
                continue
            
            closes = list(h['Close'].values)
            
            for i in range(60, len(closes) - holding_days):
                close = closes[i]
                date = h.index[i].strftime('%Y-%m-%d')
                
                # MA
                ma20 = np.mean(closes[i-19:i+1])
                ma60 = np.mean(closes[i-59:i+1]) if i >= 60 else ma20
                
                # RSI
                rsi = get_rsi(closes[:i+1])
                
                # ATR
                atr = get_atr(h, i)
                atr_pct = atr / close * 100
                
                # KDJ
                k, d, k_cross_d = get_kdj(h, i)
                
                # MACD
                macd_val, macd_signal, macd_bull = get_macd(closes[:i+1])
                
                # 法人
                inst = check_inst(code, date)
                
                # v4.21 條件
                cond_rsi = rsi < 70
                cond_atr = atr_pct >= 0.5
                cond_ma = ma20 > ma60
                cond_inst = inst
                
                # KDJ + MACD 條件 (額外加分)
                cond_kdj = k_cross_d
                cond_macd = macd_bull
                
                # 全部滿足 = 核心版本
                ok_v421 = cond_rsi and cond_atr and cond_ma and cond_inst
                
                # v421 + KDJ + MACD = 增強版
                ok_enhanced = ok_v421 and cond_kdj and cond_macd
                
                if ok_v421:
                    future_return = (closes[i+holding_days] / close - 1) * 100
                    signals.append({
                        'code': code,
                        'date': date,
                        'price': close,
                        'return': future_return,
                        'rsi': rsi,
                        'atr': atr_pct,
                        'k': k,
                        'd': d,
                        'k_cross': k_cross_d,
                        'macd_bull': macd_bull
                    })
                    
                    # 計算報酬
                    trades.append({
                        'code': code,
                        'date': date,
                        'return': future_return,
                        'enhanced': ok_enhanced
                    })
        except:
            continue
    
    return trades, signals

print('='*65)
print(' v4.21 量化策略回測')
print(' 選股池: 台股市值前100大')
print(' 回測區間: 120天')
print(' 持有天數: 5天')
print('='*65)

print()
print(' 正在回測...')

trades, signals = backtest_v421(5)

total = len(trades)
if total == 0:
    print(' 無交易資料')
else:
    wins = [t for t in trades if t['return'] > 0]
    losses = [t for t in trades if t['return'] <= 0]
    
    win_rate = len(wins) / total * 100
    avg_return = np.mean([t['return'] for t in trades])
    avg_win = np.mean([t['return'] for t in wins]) if wins else 0
    avg_loss = np.mean([t['return'] for t in losses]) if losses else 0
    
    total_win = sum([t['return'] for t in wins])
    total_loss = abs(sum([t['return'] for t in losses]))
    pf = total_win / total_loss if total_loss > 0 else 0
    
    print()
    print('='*65)
    print(' 回測結果')
    print('='*65)
    print()
    print(' 總交易次數: ' + str(total))
    print(' 勝率: ' + str(round(win_rate,1)) + '%')
    print(' 平均報酬: ' + str(round(avg_return,2)) + '%')
    print(' 平均獲利: ' + str(round(avg_win,2)) + '%')
    print(' 平均虧損: ' + str(round(avg_loss,2)) + '%')
    print(' 獲利因子: ' + str(round(pf,2)))
    print()
    
    # 增強版分析
    enhanced = [t for t in trades if t['enhanced']]
    if enhanced:
        e_wins = [t for t in enhanced if t['return'] > 0]
        e_rate = len(e_wins) / len(enhanced) * 100
        e_avg = np.mean([t['return'] for t in enhanced])
        print('【增強版 (v421 + KDJ + MACD)】')
        print(' 交易次數: ' + str(len(enhanced)) + ' (' + str(round(len(enhanced)/total*100,1)) + '%)')
        print(' 勝率: ' + str(round(e_rate,1)) + '%')
        print(' 平均報酬: ' + str(round(e_avg,2)) + '%')
    
    print()
    print('='*65)
    print(' 信號明細')
    print('='*65)
    print()
    
    # 排序
    signals.sort(key=lambda x: x['return'], reverse=True)
    
    print('%-6s %-10s %-8s %-7s %-6s %-6s %-6s %-6s' % (
        '代碼', '日期', '價格', '報酬', 'RSI', 'ATR%', 'KD', 'MACD'))
    print('-'*65)
    
    for s in signals[:20]:
        icon = '▲' if s['return'] > 0 else '▼'
        kd = str(round(s['k'],0)) + '/' + str(round(s['d'],0))
        macd = '多' if s['macd_bull'] else '空'
        print('%-6s %-10s %-8.0f %s%.1f%% %-6.0f %-6.2f %-6s %-6s' % (
            s['code'], s['date'], s['price'], icon, abs(s['return']),
            s['rsi'], s['atr'], kd, macd))
    
    print()
    print('='*65)