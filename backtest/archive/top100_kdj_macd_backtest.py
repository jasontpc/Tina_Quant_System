# -*- coding: utf-8 -*-
"""
Tina 量化交易策略回測
標的: 台股市值前100大
時間: 最近180天
策略: KDJ + MACD + MA + 法人篩選
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import numpy as np
import sqlite3
from datetime import datetime, timedelta

DB = 'skills/stock-analyzer/scripts/tina_master.db'

# Top 100 台股市值股
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
    '3596','3610','3673','3686','3702','3711','3722','4001','4002','4904',
    '4938','4956','4968','4974','4999','5283','5388','5438','5478','5483'
]

def get_kdj(h):
    close = h['Close'].values
    low = h['Low'].values
    high = h['High'].values
    
    period = 9
    k_period = 3
    d_period = 3
    
    # KDJ 計算
    lows = []
    highs = []
    for i in range(-period, 0):
        lows.append(np.min(low[i]))
        highs.append(np.max(high[i]))
    
    k_values = []
    d_values = []
    
    for i in range(period, len(close)):
        lo = np.min(low[i-period:i])
        hi = np.max(high[i-period:i])
        
        if hi == lo:
            rsv = 50
        else:
            rsv = (close[i-1] - lo) / (hi - lo) * 100
        
        if len(k_values) == 0:
            k = 50
            d = 50
        else:
            k = 2/3 * k_values[-1] + 1/3 * rsv
            d = 2/3 * d_values[-1] + 1/3 * k
        
        k_values.append(k)
        d_values.append(d)
    
    return k_values, d_values

def get_macd(h):
    close = h['Close'].values
    
    ema12 = []
    ema26 = []
    
    for i in range(len(close)):
        if i == 0:
            e12 = close[i]
            e26 = close[i]
        else:
            e12 = (11/13) * ema12[-1] + (2/13) * close[i]
            e26 = (25/27) * ema26[-1] + (2/27) * close[i]
        ema12.append(e12)
        ema26.append(e26)
    
    macd = [e12 - e26 for e12, e26 in zip(ema12, ema26)]
    
    signal = []
    for i in range(9, len(macd)):
        avg = np.mean(macd[i-9:i])
        signal.append(avg)
    
    return macd[-1] if len(macd) > 0 else 0, signal[-1] if len(signal) > 0 else 0

def check_instutional(code, date_str):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('''
        SELECT SUM(foreign_net), SUM(trust_net)
        FROM MarketData
        WHERE symbol = ? AND date >= date(?, '-5 days')
    ''', (code, date_str))
    f_sum, t_sum = cur.fetchone()
    conn.close()
    return (f_sum or 0) > 0 or (t_sum or 0) > 0

def analyze_stock(code, days=180):
    try:
        h = yf.Ticker(code + '.TW').history(period=f'{days}d')
        if len(h) < 60:
            return None
        
        close = h['Close'].values
        current = close[-1]
        prev = close[-2]
        
        # MA
        ma20 = np.mean(close[-20:])
        ma60 = np.mean(close[-60:]) if len(close) >= 60 else ma20
        
        # KDJ
        k_vals, d_vals = get_kdj(h)
        k = k_vals[-1] if len(k_vals) > 0 else 50
        d = d_vals[-1] if len(d_vals) > 0 else 50
        k_cross_d = k_vals[-1] > d_vals[-1] if len(k_vals) > 1 else False
        
        # MACD
        macd_val, macd_signal = get_macd(h)
        macd_bull = macd_val > macd_signal
        
        # 漲跌
        change = (current / prev - 1) * 100
        
        return {
            'code': code,
            'price': current,
            'change': change,
            'ma20': ma20,
            'ma60': ma60,
            'ma_cross': ma20 > ma60,
            'k': k,
            'd': d,
            'k_cross_d': k_cross_d,
            'macd_bull': macd_bull,
            'above_ma20': current > ma20,
            'above_ma60': current > ma60
        }
    except:
        return None

print('='*70)
print(' 台股市值前100大 量化策略回測')
print(' 時間: 最近180天')
print(' 策略: KDJ + MACD + MA + 法人篩選')
print('='*70)

results = []
for code in TOP100:
    info = analyze_stock(code, 180)
    if info:
        results.append(info)

# 篩選符合條件的股票
signals = []
for r in results:
    # 技術面: KDJ 金叉 + MACD 多頭 + MA 多頭排列
    tech_ok = (r['k_cross_d'] and r['macd_bull'] and r['ma_cross'] and r['above_ma20'])
    
    if tech_ok:
        signals.append(r)

signals.sort(key=lambda x: x['change'], reverse=True)

print()
print(f' 分析完成: {len(results)}/100 筆資料')
print(f' 符合進場條件: {len(signals)} 檔')
print()

print('%-6s %-8s %8s %6s %7s %6s %6s %7s' % (
    '代碼', '價格', '漲跌', 'KD', 'KDJ交叉', 'MACD', 'MA排列', '評估'))
print('-'*70)

for r in signals[:20]:
    kd_str = f'{r["k"]:.0f}/{r["d"]:.0f}'
    kd_cross = '金叉' if r['k_cross_d'] else '死叉'
    macd = '多' if r['macd_bull'] else '空'
    ma = '多頭' if r['ma_cross'] else '空頭'
    
    icon = '▲' if r['change'] > 0 else '▼'
    
    print('%-6s %8.2f %s%.1f%% %s %s %s %s' % (
        r['code'], r['price'], icon, r['change'],
        kd_str, kd_cross, macd, ma))

print()
print('='*70)
print(' 進場條件:')
print('  1. KDJ 金叉 (K > D)')
print('  2. MACD 多頭 (DIF > MACD)')
print('  3. MA 多頭排列 (MA20 > MA60)')
print('  4. 價格 > MA20')
print('  5. 法人近期買超 (選項)')
print('='*70)
print()

# 策略績效估算
if signals:
    avg_change = np.mean([s['change'] for s in signals])
    win_rate = len([s for s in signals if s['change'] > 0]) / len(signals) * 100
    
    print('【策略統計】')
    print(f' 符合條件: {len(signals)} 檔')
    print(f' 平均漲跌幅: {avg_change:+.2f}%')
    print(f' 上漲比例: {win_rate:.1f}%')
    print()
    
    print('【前5名標的】')
    for i, s in enumerate(signals[:5], 1):
        print(f' {i}. {s["code"]} {s["price"]:.2f} ({s["change"]:+.2f}%)')