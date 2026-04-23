# -*- coding: utf-8 -*-
"""
Nana System v3.1 - 動態波段系統
==================================
重點更新:
- 動態出场: 1-7天靈活持有
- 市場判斷: 多頭/盤整/空頭
- 獲利了結: 2-5% 可考慮次日出
- ATR 停損: 2x ATR
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np
import yfinance as yf
import sqlite3
import json
from datetime import datetime

DB_PATH = 'skills/stock-analyzer/scripts/tina_master.db'

# ==================== 市場情緒 ====================

class MarketMood:
    @staticmethod
    def get_status():
        try:
            twii = yf.download('^TWII', period='20d', auto_adjust=True, progress=False)
            if twii is None or len(twii) < 20:
                return {'status': 'neutral', 'max_hold': 5, 'desc': '資料不足'}
            
            if isinstance(twii.columns, pd.MultiIndex):
                twii.columns = [c[0] for c in twii.columns]
            
            close = twii['Close'].values
            ma20 = float(pd.Series(close).rolling(20).mean().iloc[-1])
            current = close[-1]
            
            # RSI
            delta = np.diff(close, prepend=close[0])
            gain = np.where(delta > 0, delta, 0)
            loss = np.where(delta > 0, 0, -delta)
            avg_gain = pd.Series(gain).rolling(14).mean().iloc[-1]
            avg_loss = pd.Series(loss).rolling(14).mean().iloc[-1]
            rsi = 100 - (100 / (1 + avg_gain / avg_loss)) if avg_loss > 0 else 50
            
            ret = (current / ma20 - 1) * 100
            
            if rsi > 80 or ret > 8:
                return {'status': 'overbought', 'max_hold': 5, 'desc': '過熱'}
            elif current > ma20 and rsi > 55:
                return {'status': 'bullish', 'max_hold': 7, 'desc': '多頭'}
            elif current < ma20 and rsi < 45:
                return {'status': 'bearish', 'max_hold': 3, 'desc': '空頭'}
            else:
                return {'status': 'neutral', 'max_hold': 5, 'desc': '盤整'}
        except:
            return {'status': 'neutral', 'max_hold': 5, 'desc': '未知'}

# ==================== 動態出场 ====================

class DynamicExit:
    def __init__(self, mood):
        self.max_hold = mood.get('max_hold', 5)
        self.status = mood.get('status', 'neutral')
    
    def should_exit(self, pos, price, rsi=50, bias=0):
        entry = pos['entry']
        days = pos['days']
        high = pos.get('high', entry)
        atr = pos.get('atr', 0)
        profit = (price / entry - 1) * 100
        
        # 1. ATR 停損
        if atr > 0 and price <= entry - atr * 2:
            return True, f'ATR停損({profit:.1f}%)', 'high'
        
        # 2. 持有期滿
        if days >= self.max_hold:
            return True, f'期滿({self.max_hold}天,{profit:.1f}%)', 'medium'
        
        # 3. RSI 過熱
        if rsi >= 85:
            return True, f'RSI過熱({rsi:.0f})', 'medium'
        
        # 4. 獲利了結
        if profit >= 8:
            return True, f'目標達成({profit:.1f}%)', 'low'
        elif profit >= 5 and self.status in ['overbought', 'neutral']:
            return True, f'利潤入袋({profit:.1f}%)', 'low'
        elif profit >= 2 and days >= 2 and self.status == 'bearish':
            return True, f'空頭了結({profit:.1f}%)', 'low'
        
        # 5. 虧損止損
        if profit <= -5 and days >= 2:
            return True, f'認損({profit:.1f}%)', 'high'
        
        return False, f'續抱({profit:.1f}%)', None

# ==================== 評分 ====================

def inst_score(d):
    if d >= 11: return 20
    elif d >= 6: return 60
    elif d >= 4: return 50
    elif d == 3: return 40
    elif d == 2: return 15
    elif d == 1: return 10
    return 0

def score_stock(symbol, mood):
    """完整評分"""
    try:
        df = yf.download(symbol + '.TW', period='90d', auto_adjust=True, progress=False)
        if df is None or len(df) < 60:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        
        close = df['Close'].values
        high = df['High'].values
        low = df['Low'].values
        
        ma20 = float(pd.Series(close).rolling(20).mean().iloc[-1])
        ma60 = float(pd.Series(close).rolling(60).mean().iloc[-1])
        
        # RSI
        delta = np.diff(close, prepend=close[0])
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta > 0, 0, -delta)
        avg_gain = pd.Series(gain).rolling(14).mean().iloc[-1]
        avg_loss = pd.Series(loss).rolling(14).mean().iloc[-1]
        rsi = 100 - (100 / (1 + avg_gain / avg_loss)) if avg_loss > 0 else 50
        
        # ATR
        tr = np.maximum(high - low, np.maximum(np.abs(high - np.roll(close, 1)), np.abs(low - np.roll(close, 1))))
        atr = float(pd.Series(tr).rolling(14).mean().iloc[-1])
        atr_pct = atr / close[-1] * 100
        
        # Bias
        bias = (close[-1] / ma20 - 1) * 100
        
        # 法人
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('SELECT foreign_net, trust_net FROM MarketData WHERE symbol = ? ORDER BY date DESC LIMIT 10', (symbol,))
        rows = cur.fetchall()
        conn.close()
        
        f_d = t_d = 0
        for f, t in rows:
            if f and f > 0: f_d += 1
            else: break
        for f, t in rows:
            if t and t > 0: t_d += 1
            else: break
        
        # ===== 評分 =====
        f_s = inst_score(f_d)
        t_s = inst_score(t_d)
        base = max(f_s, t_s)
        if f_d >= 3 and t_d >= 3: base += 10
        inst = min(70, base)
        
        # RSI 評分 (健康區間擴大)
        if 40 <= rsi <= 75: rsi_s = 20
        elif 30 <= rsi < 40: rsi_s = 12
        elif 75 < rsi <= 80: rsi_s = 10
        elif 80 < rsi <= 85: rsi_s = 5
        else: rsi_s = 3
        
        # Bias
        if -3 <= bias <= 5: bias_s = 15
        elif 5 < bias <= 8: bias_s = 10
        elif -5 <= bias < -3: bias_s = 8
        else: bias_s = 5
        
        # ATR
        atr_s = 10 if atr_pct >= 0.5 else (5 if atr_pct >= 0.3 else 0)
        
        tech = rsi_s + bias_s + atr_s
        trend = (15 if ma20 > ma60 else 0) + (10 if bias > 0 else 5)
        
        total = inst * 0.40 + tech * 0.35 + trend * 0.25
        
        # ===== 進場判斷 =====
        can_buy = bool(total >= 35 and rsi < 85 and ma20 > ma60 and atr_pct >= 0.3)
        
        return {
            'symbol': symbol,
            'score': round(total, 1),
            'inst': round(inst, 1),
            'tech': round(tech, 1),
            'trend': round(trend, 1),
            'rsi': round(rsi, 1),
            'bias': round(bias, 1),
            'atr': round(atr_pct, 2),
            'ma20': round(ma20, 0),
            'ma60': round(ma60, 0),
            'f_days': f_d,
            't_days': t_d,
            'can_buy': can_buy,
            'price': round(close[-1], 0),
            'atr_value': round(atr, 2)
        }
    except Exception as e:
        return None

# ==================== 回測 ====================

def backtest(symbol, params, mood):
    """動態波段回測"""
    df = yf.download(symbol + '.TW', period='180d', auto_adjust=True, progress=False)
    if df is None or len(df) < 60:
        return []
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    
    close = df['Close'].values
    high = df['High'].values
    low = df['Low'].values
    dates = [str(d)[:10] for d in df.index]
    
    # 指標
    ma20 = pd.Series(close).rolling(20).mean().values
    ma60 = pd.Series(close).rolling(60).mean().values
    
    delta = np.diff(close, prepend=close[0])
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta > 0, 0, -delta)
    avg_gain = pd.Series(gain).rolling(14).mean().values
    avg_loss = pd.Series(loss).rolling(14).mean().values
    rs = avg_gain / np.where(avg_loss == 0, np.nan, avg_loss)
    rsi = 100 - (100 / (1 + rs))
    rsi = np.where(np.isnan(rsi), 50, rsi)
    
    tr = np.maximum(high - low, np.maximum(np.abs(high - np.roll(close, 1)), np.abs(low - np.roll(close, 1))))
    atr = pd.Series(tr).rolling(14).mean().values
    atr_pct = atr / close * 100
    
    bias = (close - ma20) / ma20 * 100
    
    # 法人
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT date, foreign_net, trust_net FROM MarketData WHERE symbol = ? ORDER BY date DESC LIMIT 180', (symbol,))
    rows = cur.fetchall()
    conn.close()
    inst_map = {str(r[0])[:10]: {'f': r[1] or 0, 't': r[2] or 0} for r in rows}
    
    exit_mgr = DynamicExit(mood)
    entry_min = params.get('entry_min', 35)
    
    trades = []
    position = None
    
    for i in range(60, len(dates)):
        price = close[i]
        r = rsi[i]
        m20 = ma20[i] if not np.isnan(ma20[i]) else 0
        m60 = ma60[i] if not np.isnan(ma60[i]) else 0
        a = atr_pct[i] if not np.isnan(atr_pct[i]) else 0
        b = bias[i] if not np.isnan(bias[i]) else 0
        date = dates[i]
        
        # 法人
        f_d = t_d = 0
        for j in range(i, max(i - 20, -1), -1):
            if j < 0: break
            inst = inst_map.get(dates[j], {'f': 0})
            if inst['f'] > 0: f_d += 1
            else: break
        for j in range(i, max(i - 20, -1), -1):
            if j < 0: break
            inst = inst_map.get(dates[j], {'t': 0})
            if inst['t'] > 0: t_d += 1
            else: break
        
        # 評分
        f_s = inst_score(f_d)
        t_s = inst_score(t_d)
        base = max(f_s, t_s)
        if f_d >= 3 and t_d >= 3: base += 10
        inst = min(70, base)
        
        rsi_s = 20 if 40 <= r <= 75 else (12 if 30 <= r < 40 else 5)
        bias_s = 15 if -3 <= b <= 5 else (10 if 5 < b <= 8 else 5)
        atr_s = 10 if a >= 0.5 else (5 if a >= 0.3 else 0)
        tech = rsi_s + bias_s + atr_s
        trend = (15 if m20 > m60 else 0) + (10 if b > 0 else 5)
        total = inst * 0.40 + tech * 0.35 + trend * 0.25
        
        # 進場
        if position is None:
            if total >= entry_min and r < 85 and m20 > m60 and a >= 0.3:
                position = {
                    'entry': price,
                    'days': 0,
                    'high': price,
                    'atr': a,
                    'score': total
                }
        else:
            position['days'] += 1
            if high[i] > position['high']:
                position['high'] = high[i]
            
            # 动态出场
            should_exit, reason, urgency = exit_mgr.should_exit(
                {'entry': position['entry'], 'days': position['days'], 'high': position['high'], 'atr': position['atr']},
                price, r, b
            )
            
            if should_exit:
                profit = (price / position['entry'] - 1) * 100
                trades.append({
                    'symbol': symbol,
                    'entry': position['entry'],
                    'exit': price,
                    'profit': profit,
                    'days': position['days'],
                    'reason': reason,
                    'score': position['score']
                })
                position = None
    
    if position:
        profit = (close[-1] / position['entry'] - 1) * 100
        trades.append({
            'symbol': symbol,
            'entry': position['entry'],
            'exit': close[-1],
            'profit': profit,
            'days': position['days'],
            'reason': 'eod',
            'score': position['score']
        })
    
    return trades

# ==================== 主程式 ====================

def main():
    print()
    print('='*60)
    print(' Nana System v3.1 - 動態波段')
    print('='*60)
    
    # 市場情緒
    mood = MarketMood.get_status()
    print(f'市場: {mood["desc"]} | 最大持有: {mood["max_hold"]}天')
    print()
    
    # 股票池
    TIER1 = ['2330','2454','3034','2379','2303','2344','2382','3231','3717','4938',
              '2317','2353','2357','2345','3017','6230','6269','3044','6213',
              '4935','4952','2401','2340','2385']
    
    TIER2 = ['3481','2409','6176','2412','3045','6239','6108','6192',
              '2471','2497','5203','2327','2492','2356','2376','2395','2308']
    
    ALL = list(set(TIER1 + TIER2))[:30]  # 先測試30檔
    
    params = {'entry_min': 35}
    
    print(f'掃描 {len(ALL)} 檔...')
    print()
    
    all_trades = []
    results = []
    
    for symbol in ALL:
        r = score_stock(symbol, mood)
        if r:
            results.append(r)
            if r['can_buy']:
                print(f'  {symbol}: {r["score"]}分 ✅ (RSI={r["rsi"]}, F={r["f_days"]}天)')
    
    print()
    print('='*60)
    print(' 回測結果')
    print('='*60)
    print()
    
    for r in sorted(results, key=lambda x: x['score'], reverse=True)[:10]:
        trades = backtest(symbol, params, mood)
        if trades:
            df = pd.DataFrame(trades)
            wr = len(df[df['profit'] > 0]) / len(df) * 100
            avg = df['profit'].mean()
            print(f'  {r["symbol"]}: {len(df)}筆, WR={wr:.0f}%, Avg={avg:.1f}%, Score={r["score"]}')
            all_trades.extend([{**t, 'symbol': r['symbol']} for t in trades])
    
    if all_trades:
        df = pd.DataFrame(all_trades)
        total_wr = len(df[df['profit'] > 0]) / len(df) * 100
        total_avg = df['profit'].mean()
        
        print()
        print('='*60)
        print(' 總結')
        print('='*60)
        print(f'  總交易: {len(df)} 筆')
        print(f'  勝率: {total_wr:.1f}%')
        print(f'  平均報酬: {total_avg:.2f}%')
        print(f'  總報酬: {df["profit"].sum():.1f}%')
        
        # 出场原因分佈
        print()
        print(' 出場原因:')
        for reason, cnt in df['reason'].value_counts().items():
            print(f'   {reason}: {cnt}次')
    
    # 儲存
    with open('Tina_Quant_System/teams/nana/band_results.json', 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'mood': mood,
            'results': results[:20],
            'total_trades': len(all_trades)
        }, f, ensure_ascii=False, indent=2)
    
    print()
    print('已儲存: band_results.json')

if __name__ == '__main__':
    main()