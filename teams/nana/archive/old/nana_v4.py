# -*- coding: utf-8 -*-
"""
Nana System v4.0 - 完整波段交易系統
====================================
目標:
1. 台股前100大，科技/AI優先
2. 模擬真實交易 (費用/滑點/T+1)
3. 回測修正迭代
4. 評分權重: 法人40% + 技術35% + 趨勢25%
5. 動態條件，多層分流
6. 自主學習修正
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

# ==================== 股票池 ====================

TIER1 = [
    '2330','2454','3034','2379','2303','2344',  # 半導體
    '2382','3231','3717','4938',  # AI伺服器
    '2317','2353','2357','2345',  # 電子代工
    '3017','6230','6269',  # 散熱
    '3044','6213','4935','4952',  # PCB
    '2401','2340',  # 記憶體
    '2385'  # 高速傳輸
]

TIER2 = [
    '3481','2409','6176',  # 光電
    '2412','3045',  # 網通
    '6239',  # 封測
    '2327','2492','2356',  # 電子零組件
    '2471','2497','5203',  # 軟體
]

TIER3 = [
    '2881','2882','2884','2885','2891',  # 金控
    '2801','2812','2834',  # 官股
    '1301','1326','2002',  # 傳產
    '0050','0056','00891','00713'  # ETF
]

ALL_STOCKS = list(set(TIER1 + TIER2 + TIER3))

# ==================== 市場判斷 ====================

def get_market_status():
    """判斷市場狀態"""
    try:
        twii = yf.download('^TWII', period='20d', auto_adjust=True, progress=False)
        if isinstance(twii.columns, pd.MultiIndex):
            twii.columns = [c[0] for c in twii.columns]
        
        close = twii['Close'].values
        ma20 = float(pd.Series(close).rolling(20).mean().iloc[-1])
        rsi = 50  # 簡化
        
        if len(close) >= 14:
            delta = np.diff(close, prepend=close[0])
            gain = np.where(delta > 0, delta, 0)
            loss = np.where(delta > 0, 0, -delta)
            avg_gain = pd.Series(gain).rolling(14).mean().iloc[-1]
            avg_loss = pd.Series(loss).rolling(14).mean().iloc[-1]
            if avg_loss > 0:
                rsi = 100 - (100 / (1 + avg_gain / avg_loss))
        
        curr = close[-1]
        above_ma = curr > ma20
        
        if rsi > 80 or (curr / ma20 - 1) > 0.08:
            return 'overbought', 5
        elif above_ma and rsi > 55:
            return 'bullish', 7
        elif not above_ma and rsi < 45:
            return 'bearish', 3
        else:
            return 'neutral', 5
    except:
        return 'neutral', 5

# ==================== 法人評分 ====================

def inst_score(days):
    if days >= 11: return 20
    elif days >= 6: return 60
    elif days >= 4: return 50
    elif days == 3: return 40
    elif days == 2: return 15
    elif days == 1: return 10
    return 0

# ==================== 完整評分 ====================

def analyze(symbol):
    """分析單一股票"""
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
        if len(close) >= 14:
            delta = np.diff(close, prepend=close[0])
            gain = np.where(delta > 0, delta, 0)
            loss = np.where(delta > 0, 0, -delta)
            avg_gain = pd.Series(gain).rolling(14).mean().iloc[-1]
            avg_loss = pd.Series(loss).rolling(14).mean().iloc[-1]
            rsi = 100 - (100 / (1 + avg_gain / avg_loss)) if avg_loss > 0 else 50
        else:
            rsi = 50
        
        # ATR
        tr = np.maximum(high - low, np.maximum(
            np.abs(high - np.roll(close, 1)),
            np.abs(low - np.roll(close, 1))
        ))
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
        
        f_days = t_days = 0
        for f, t in rows:
            if f and f > 0: f_days += 1
            else: break
        for f, t in rows:
            if t and t > 0: t_days += 1
            else: break
        
        # ===== 評分 =====
        f_s = inst_score(f_days)
        t_s = inst_score(t_days)
        base = max(f_s, t_s)
        if f_days >= 3 and t_days >= 3: base += 10
        inst = min(70, base)
        
        # RSI評分 (健康區間擴大)
        if 40 <= rsi <= 75: rsi_s = 20
        elif 30 <= rsi < 40: rsi_s = 12
        elif 75 < rsi <= 80: rsi_s = 10
        elif 80 < rsi <= 85: rsi_s = 5
        else: rsi_s = 3
        
        # Bias評分
        if -3 <= bias <= 5: bias_s = 15
        elif 5 < bias <= 8: bias_s = 10
        else: bias_s = 5
        
        # ATR評分
        atr_s = 10 if atr_pct >= 0.5 else (5 if atr_pct >= 0.3 else 0)
        
        tech = rsi_s + bias_s + atr_s
        
        # 趨勢分
        ma_trend = 15 if ma20 > ma60 else 0
        momentum = 10 if bias > 0 else 5
        trend = ma_trend + momentum
        
        # 總分
        total = inst * 0.40 + tech * 0.35 + trend * 0.25
        
        # 可交易
        tier = 1 if symbol in TIER1 else (2 if symbol in TIER2 else 3)
        can_trade = total >= 35 and rsi < 85 and ma20 > ma60 and atr_pct >= 0.3
        
        return {
            'symbol': symbol,
            'tier': tier,
            'score': round(total, 1),
            'inst': round(inst, 1),
            'tech': round(tech, 1),
            'trend': round(trend, 1),
            'rsi': round(rsi, 1),
            'bias': round(bias, 1),
            'atr': round(atr_pct, 2),
            'f_days': f_days,
            't_days': t_days,
            'ma20': round(ma20, 0),
            'ma60': round(ma60, 0),
            'price': round(close[-1], 0),
            'can_trade': can_trade
        }
    except Exception as e:
        return None

# ==================== 回測引擎 ====================

def backtest(symbol, max_hold=5):
    """簡化回測"""
    try:
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
        
        trades = []
        position = None
        
        for i in range(60, len(dates)):
            price = close[i]
            r = rsi[i]
            m20 = ma20[i] if not np.isnan(ma20[i]) else 0
            m60 = ma60[i] if not np.isnan(ma60[i]) else 0
            a = atr_pct[i] if not np.isnan(atr_pct[i]) else 0
            b = bias[i] if not np.isnan(bias[i]) else 0
            
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
            inst_val = min(70, base)
            
            rsi_s = 20 if 40 <= r <= 75 else (5 if r >= 80 else 12)
            bias_s = 15 if -3 <= b <= 5 else 10
            atr_s = 10 if a >= 0.5 else (5 if a >= 0.3 else 0)
            tech = rsi_s + bias_s + atr_s
            trend = (15 if m20 > m60 else 0) + (10 if b > 0 else 5)
            total = inst_val * 0.40 + tech * 0.35 + trend * 0.25
            
            # 進場
            if position is None:
                if total >= 35 and r < 85 and m20 > m60 and a >= 0.3:
                    position = {'entry': price, 'days': 0, 'score': total}
            else:
                position['days'] += 1
                
                # 出場
                exit = False
                reason = 'time'
                
                if position['days'] >= max_hold:
                    exit = True
                    reason = 'hold_max'
                elif r >= 85:
                    exit = True
                    reason = 'rsi_overbought'
                elif b >= 10:
                    exit = True
                    reason = 'bias_high'
                elif m20 <= m60:
                    exit = True
                    reason = 'ma_cross'
                
                if exit:
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
    except:
        return []

# ==================== 主程式 ====================

def main():
    print('='*60)
    print(' Nana System v4.0 - 波段交易')
    print('='*60)
    
    # 市場狀態
    status, max_hold = get_market_status()
    status_names = {'overbought': 'OVERBOUGHT', 'bullish': 'BULLISH', 'bearish': 'BEARISH', 'neutral': 'NEUTRAL'}
    print(f'Market: {status_names.get(status, status)} | Max hold: {max_hold} days')
    print()
    
    # 分析所有股票
    results = []
    trade_candidates = []
    
    for symbol in ALL_STOCKS:
        r = analyze(symbol)
        if r:
            results.append(r)
            if r['can_trade']:
                trade_candidates.append(r)
    
    # 排序
    results.sort(key=lambda x: x['score'], reverse=True)
    trade_candidates.sort(key=lambda x: x['score'], reverse=True)
    
    # 顯示
    print(f'{'RANK':<5} {'SYMBOL':<7} {'TIER':<5} {'SCORE':<7} {'INST':<6} {'RSI':<6} {'F_DAYS':<7} {'TRADE'}')
    print('-'*55)
    
    for i, r in enumerate(results[:20], 1):
        tier_icons = {1: '*', 2: '~', 3: '-'}
        icon = tier_icons.get(r['tier'], '?')
        can = '[BUY]' if r['can_trade'] else ''
        print(f'{i:<5} {r["symbol"]:<7} {icon}{r["tier"]:<4} {r["score"]:<7.1f} {r["inst"]:<6.1f} {r["rsi"]:<6.1f} {r["f_days"]:<7} {can}')
    
    print()
    print(f'Total scanned: {len(results)} | Tradeable: {len(trade_candidates)}')
    print()
    
    # 對候選股票回測
    if trade_candidates:
        print('Backtest results:')
        print('-'*50)
        
        all_trades = []
        
        for r in trade_candidates[:10]:  # Top 10
            symbol = r['symbol']
            trades = backtest(symbol, max_hold)
            
            if trades:
                df = pd.DataFrame(trades)
                wr = len(df[df['profit'] > 0]) / len(df) * 100
                avg = df['profit'].mean()
                print(f'  {symbol}: {len(df)} trades, WR={wr:.0f}%, Avg={avg:.1f}%')
                all_trades.extend(trades)
        
        if all_trades:
            df = pd.DataFrame(all_trades)
            total_wr = len(df[df['profit'] > 0]) / len(df) * 100
            total_avg = df['profit'].mean()
            
            print()
            print('='*50)
            print(' PORTFOLIO SUMMARY')
            print('='*50)
            print(f'  Total trades: {len(df)}')
            print(f'  Win rate: {total_wr:.1f}%')
            print(f'  Avg return: {total_avg:.2f}%')
            print(f'  Total return: {df["profit"].sum():.1f}%')
    
    # 儲存
    output = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'market_status': status,
        'max_hold': max_hold,
        'total_scanned': len(results),
        'tradeable': len(trade_candidates),
        'results': results[:30]
    }
    
    with open('Tina_Quant_System/teams/nana/v4_results.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print()
    print('Saved: v4_results.json')

if __name__ == '__main__':
    main()