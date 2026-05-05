# -*- coding: utf-8 -*-
"""
Tina v5.24 - 基於 Boost v1.4 策略 + 擴充股票池
Boost v1.4: WR=57.71%, Avg=3.35%, 603 trades
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

# ============== v5.24 股票池 ==============
ETF_POOL = ['0050','0056','00646','00662','00713','00891','00900','00902']
STOCK_POOL = ['2382','2884','2474','2303','2317','2353','2377','2345','4938','3017']
BLACKLIST = ['2451','2330','1605','6230','2454','2308','3034','3413','2458','2379','8081']
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
    except: pass
    return inst

def rsi(p):
    d = np.diff(p)
    g = np.where(d > 0, d, 0)
    l = np.where(d > 0, 0, -d)
    ag = np.mean(g[-14:])
    al = np.mean(l[-14:])
    return 100 - (100 / (1 + ag / al)) if al != 0 else 50

def calc_atr_pct(h, i):
    high = list(h['High'].iloc[max(0,i-14):i+1])
    low = list(h['Low'].iloc[max(0,i-14):i+1])
    close = list(h['Close'].iloc[max(0,i-14):i+1])
    tr = [max(high[j]-low[j], abs(high[j]-close[j-1]), abs(low[j]-close[j-1])) for j in range(1, len(high))]
    atr = np.mean(tr[-14:]) if len(tr) >= 14 else 30
    return (atr / close[-1]) * 100 if close[-1] > 0 else 0

def ma(p, n):
    return np.mean(p[-n:]) if len(p) >= n else 0

def macd_signal(p):
    ema12 = pd.Series(p).ewm(span=12).mean()
    ema26 = pd.Series(p).ewm(span=26).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9).mean()
    return macd.iloc[-1], signal.iloc[-1]

def backtest_boost_v14(inst_map):
    """Boost v1.4 策略: RSI 40-80, ATR%>=0.3, trend_ma=True, inst_level=1"""
    end_date = '2026-04-23'
    start_date = '2025-01-01'  # 擴充至 450天 以取得足夠資料
    
    all_trades = []
    stock_stats = {}
    
    for code in ALL_CANDIDATES:
        try:
            tk = yf.Ticker(code + '.TW' if code.isdigit() else code)
            h = tk.history(start=start_date, end=end_date)
            if len(h) < 60: continue
            cl = list(h['Close'].values)
            
            stock_stats[code] = {'total': 0, 'wins': 0, 'losses': 0, 'rets': []}
            
            for i in range(60, len(cl)-6):
                rs = rsi(cl[:i+1])
                ma20 = ma(cl, 20)
                ma60 = ma(cl, 60) if i >= 60 else ma20
                atr_pct = calc_atr_pct(h, i)
                macd_val, signal_val = macd_signal(cl[:i+1])
                
                # RSI 40-80
                if not (40 <= rs <= 80): continue
                # ATR >= 0.3%
                if atr_pct < 0.3: continue
                # Trend: MA20 > MA60 * 0.98 (放寬)
                if ma20 <= ma60 * 0.98: continue
                
                # === 法人條件 (inst_level=1: 外资 or 投信連續買超) ===
                date_str = str(h.index[i])[:10]
                if code in inst_map:
                    f_days, t_days = 0, 0
                    for dd in range(1, 4):
                        dt = (pd.to_datetime(date_str) - pd.Timedelta(days=dd)).strftime('%Y-%m-%d')
                        if dt in inst_map[code]:
                            if inst_map[code][dt][0] > 0: f_days += 1
                            if inst_map[code][dt][1] > 0: t_days += 1
                    if f_days < 1 and t_days < 1: continue
                else:
                    if code not in ETF_POOL: continue
                
                entry = h['Open'].iloc[i+1] if i+1 < len(h) else cl[i]
                exit_p = cl[min(i+6, len(cl)-1)]
                if np.isnan(entry) or np.isnan(exit_p): continue
                ret = (exit_p / entry - 1) * 100 - 0.45
                
                all_trades.append({'ret': ret, 'code': code, 'rsi': rs})
                stock_stats[code]['total'] += 1
                stock_stats[code]['rets'].append(ret)
                if ret > 0:
                    stock_stats[code]['wins'] += 1
                else:
                    stock_stats[code]['losses'] += 1
        except: pass
        time.sleep(0.1)
    
    return all_trades, stock_stats

def analyze(trades):
    if not trades: return None
    wins = [t for t in trades if t['ret'] > 0]
    losses = [t for t in trades if t['ret'] <= 0]
    return {
        'total': len(trades), 'wins': len(wins), 'losses': len(losses),
        'wr': len(wins)/len(trades)*100,
        'avg': float(np.mean([t['ret'] for t in trades])) if trades else 0,
        'max_win': float(max([t['ret'] for t in trades])) if trades else 0,
        'max_loss': float(min([t['ret'] for t in trades])) if trades else 0
    }

print('='*70)
print(' Tina v5.24 - Boost v1.4 策略 + 擴充股票池')
print('='*70)

inst_map = load_inst()
print('\n[載入法人資料] %d 檔有資料' % len(inst_map))

print('\n[回測中 (Boost v1.4 策略)... ]')
trades, stats = backtest_boost_v14(inst_map)
result = analyze(trades)

if result:
    print('\n[ v5.24 總結果 ]')
    print('  總交易筆數: %d' % result['total'])
    print('  勝率 (WR): %.1f' % result['wr'])
    print('  平均報酬 (Avg): %.2f' % result['avg'])
    print('  最大獲利: %.2f' % result['max_win'])
    print('  最大虧損: %.2f' % result['max_loss'])
    
    etf_trades = [t for t in trades if t['code'] in ETF_POOL]
    stock_trades = [t for t in trades if t['code'] not in ETF_POOL]
    etf_result = analyze(etf_trades) if etf_trades else None
    stock_result = analyze(stock_trades) if stock_trades else None
    
    print('\n[ ETF vs 股票 ]')
    if etf_result:
        print('  ETF: %d筆 | WR=%.1f | Avg=%.2f' % (etf_result['total'], etf_result['wr'], etf_result['avg']))
    if stock_result:
        print('  股票: %d筆 | WR=%.1f | Avg=%.2f' % (stock_result['total'], stock_result['wr'], stock_result['avg']))
    
    print('\n[ 個別股票/ETF 分析 ]')
    sorted_stats = sorted(stats.items(), key=lambda x: x[1]['total'], reverse=True)
    for code, s in sorted_stats:
        if s['total'] < 5: continue
        wr = s['wins'] / s['total'] * 100 if s['total'] > 0 else 0
        avg = float(np.mean(s['rets'])) if s['rets'] else 0
        tag = 'ETF' if code in ETF_POOL else '股'
        print('  %s(%s): %d筆 | WR=%.1f | Avg=%.2f' % (code, tag, s['total'], wr, avg))
    
    print('\n[ 目標達成 ]')
    print('  交易量 >300: ' + ('Y' if result['total'] >= 300 else 'N') + ' (' + str(result['total']) + '筆)')
    print('  WR >55: ' + ('Y' if result['wr'] >= 55 else 'N') + ' (' + str(round(result['wr'],1)) + ')')
    print('  Avg >3.0: ' + ('Y' if result['avg'] >= 3.0 else 'N') + ' (' + str(round(result['avg'],2)) + ')')
    
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
    print('\n[ JSON Output ]')
    print(json.dumps(output, ensure_ascii=False, indent=2))
else:
    print('[錯誤] 無交易資料')
