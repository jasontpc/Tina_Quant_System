# -*- coding: utf-8 -*-
"""
Nana v5.4 - 交易量擴充版
目標: 提高交易數量，降低門檻，增加候選池
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np
import yfinance as yf
import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional

DB_PATH = 'data/tina_master.db'

# ==================== 擴充股票池 (100檔) ====================

TIER1_TECH = [
    '2330','2454','3034','2379','2303','2344',
    '2382','3231','3717','4938',
    '2317','2353','2357','2345',
    '3017','6230','6269',
    '3044','6213','4935','4952',
    '2401','2340',
    '2385','3583','6475',
    '2376','2352','2395',
    '3665','6669',
    '2451','2449','2484',
    '2308','2474','3033',
    '6183','6415',
    '2458','2311','3037',
]

TIER2_RELATED = [
    '3481','2409','6176',
    '2412','3045',
    '6239',
    '2327','2492','2356',
    '2471','2497','5203',
    '3515','4989',
    '3293','6285',
    '6123','3653',
    '6128','6130',
    '2423','2436',
    '4532','4958',
    '2371','2383',
    '3010','3036',
    '3443','3529',
]

TIER3_BLUE = [
    '2881','2882','2884','2885','2891',
    '2801','2812','2834',
    '1301','1326','2002',
    '0050','0056','00891','00713',
    '2603','2609','2608',
    '2615','2618',
    '2630','2892',
    '2886','2887','2888',
    '2890','5880',
    '6505','5871',
    '2610','2809',
    '2816','2820',
]

# 擴充股票池：180檔
EXTENDED_POOL = TIER1_TECH + TIER2_RELATED + TIER3_BLUE + [
    '2498','3060','6116','2495','3532',
    '1605','1909','2314','2347',
    '2399','2431','2441','2509',
    '2515','2524','2606','2707',
    '2833','2855','2903','2915',
    '3008','3042','3228','3257',
    '3294','3406','3437','3450',
    '3504','3519','3533','3545',
    '3550','3593','3615','3661',
    '3702','3712','4128','4137',
    '4164','4528','4538','4722',
    '4743','4904','4930','4937',
    '4944','4951','4966','4974',
    '5009','5064','5103','5151',
    '5234','5264','5283','5388',
    '5426','5438','5608','5872',
    '5888','5904','6005','6016',
    '6024','6031','6044','6056',
    '6071','6108','6120','6153',
    '6165','6172','6188','6193',
    '6206','6214','6216','6222',
    '6223','6225','6231','6235',
    '6243','6257','6270','6271',
    '6279','6281','6284','6288',
    '6301','6315','6340','6351',
    '6354','6356','6358','6361',
    '6412','6425','6445','6456',
    '6474','6504','6515','6525',
    '6531','6535','6552','6561',
    '6573','6579','6581','6589',
    '6592','6603','6606','6613',
    '6629','6641','6649','6670',
    '6671','6672','6702','6712',
    '6739','6741','6756','6761',
    '6770','6772','6776',
]

ALL_STOCKS = list(set(EXTENDED_POOL))[:150]  # 限制150檔

STOCK_NAMES = {
    '2330':'台積電','2454':'聯發科','3034':'聯詠','2379':'瑞昱',
    '2303':'聯電','2344':'華邦電','2382':'廣達','3231':'緯創',
    '3717':'緯穎','4938':'和碩','2317':'鴻海','2353':'宏碁',
    '2357':'華碩','2345':'智邦','3017':'奇鋐','6230':'尼吉康',
    '6269':'台郡','3044':'崇越','6213':'聯茂','4935':'竟庭',
    '4952':'凌華','2401':'南亞科','2340':'旺宏','2385':'群電',
    '3481':'友達','2409':'瑞儀','6176':'GIS-KY','2412':'中華電',
    '3045':'遠傳','6239':'力成','2327':'國巨','2492':'華新科',
    '2356':'英業達','2471':'健鼎','2497':'宜特','5203':'凌陽',
    '2881':'富邦金','2882':'國泰金','2884':'玉山金','2885':'元大金',
    '2891':'中信金','2801':'彰銀','2812':'台中銀','2834':'臺企銀',
    '1301':'台塑','1326':'台化','2002':'中鋼',
    '0050':'元大台灣50','0056':'元大高股息','00891':'中信特',
    '00713':'統一台灣高息',
}

def name(code):
    return STOCK_NAMES.get(code, code)

# ==================== 市場判斷 ====================

def get_market_status():
    try:
        twii = yf.download('^TWII', period='20d', auto_adjust=True, progress=False)
        if isinstance(twii.columns, pd.MultiIndex):
            twii.columns = [c[0] for c in twii.columns]
        close = twii['Close'].values
        ma20 = float(pd.Series(close).rolling(20).mean().iloc[-1])
        rsi = 50
        if len(close) >= 14:
            delta = np.diff(close, prepend=close[0])
            gain = np.where(delta > 0, delta, 0)
            loss = np.where(delta > 0, 0, -delta)
            avg_gain = pd.Series(gain).rolling(14).mean().iloc[-1]
            avg_loss = pd.Series(loss).rolling(14).mean().iloc[-1]
            if avg_loss > 0:
                rsi = 100 - (100 / (1 + avg_gain / avg_loss))
        curr = close[-1]
        ret = (curr / ma20 - 1) * 100 if ma20 > 0 else 0
        if rsi > 80 or ret > 8:
            return 'OVERBOUGHT', 4, '過熱'
        elif curr > ma20 and rsi > 55:
            return 'BULLISH', 5, '多頭'
        elif curr < ma20 and rsi < 45:
            return 'BEARISH', 3, '空頭'
        else:
            return 'NEUTRAL', 4, '盤整'
    except:
        return 'NEUTRAL', 4, '未知'

# ==================== 動態門檻調整 ====================

def get_dynamic_thresholds(status):
    """根據市場狀態調整進場門檻 - OVERBOUGHT時降低門檻以提高交易量"""
    if status == 'OVERBOUGHT':
        return {'score': 30, 'rsi': 68, 'bias': 10, 'atr': 0.3}
    elif status == 'BULLISH':
        return {'score': 32, 'rsi': 65, 'bias': 8, 'atr': 0.3}
    elif status == 'NEUTRAL':
        return {'score': 28, 'rsi': 70, 'bias': 10, 'atr': 0.25}
    else:  # BEARISH
        return {'score': 25, 'rsi': 72, 'bias': 12, 'atr': 0.2}

# ==================== 法人評分 ====================

def inst_score(days):
    if days >= 11: return 20
    elif days >= 8: return 60
    elif days >= 6: return 55
    elif days >= 4: return 50
    elif days == 3: return 40
    elif days == 2: return 20
    elif days == 1: return 15
    return 0

# ==================== 股票分析 ====================

def analyze(symbol: str, thresholds: dict, status: str = 'BULLISH') -> Optional[Dict]:
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
        avg_gain = pd.Series(gain).ewm(alpha=1/14, min_periods=14).mean().iloc[-1]
        avg_loss = pd.Series(loss).ewm(alpha=1/14, min_periods=14).mean().iloc[-1]
        rsi = 100 - (100 / (1 + avg_gain / avg_loss)) if avg_loss > 0 else 50
        
        # ATR
        tr = np.maximum(high - low, np.maximum(
            np.abs(high - np.roll(close, 1)),
            np.abs(low - np.roll(close, 1))
        ))
        atr = float(pd.Series(tr).rolling(14).mean().iloc[-1])
        atr_pct = atr / close[-1] * 100
        
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
        
        f_s = inst_score(f_days)
        t_s = inst_score(t_days)
        base = max(f_s, t_s)
        if f_days >= 3 and t_days >= 3: base += 10
        inst = min(70, base)
        
        # RSI評分
        if thresholds['rsi'] - 10 <= rsi <= thresholds['rsi']: rsi_s = 20
        elif thresholds['rsi'] - 20 <= rsi < thresholds['rsi'] - 10: rsi_s = 12
        elif thresholds['rsi'] < rsi <= thresholds['rsi'] + 5: rsi_s = 10
        else: rsi_s = 5
        
        # Bias
        if -3 <= bias <= thresholds['bias'] * 0.6: bias_s = 15
        elif thresholds['bias'] * 0.6 < bias <= thresholds['bias']: bias_s = 10
        else: bias_s = 5
        
        # ATR
        atr_s = 10 if atr_pct >= thresholds['atr'] else (5 if atr_pct >= thresholds['atr'] * 0.7 else 0)
        
        tech = rsi_s + bias_s + atr_s
        trend = (15 if ma20 > ma60 else 0) + (10 if bias > 0 else 5)
        total = inst * 0.40 + tech * 0.35 + trend * 0.25
        
        if symbol in TIER1_TECH: tier = 1
        elif symbol in TIER2_RELATED: tier = 2
        else: tier = 3
        
        # 動態門檻 - OVERBOUGHT時大幅放寬以提高交易量
        tier_score = {1: thresholds['score'], 2: thresholds['score'] - 3, 3: thresholds['score'] - 5}
        score_threshold = tier_score.get(tier, thresholds['score'])
        
        # OVERBOUGHT額外放寬: RSI可到70, Bias可到12%
        rsi_limit = thresholds['rsi'] + 5 if status == 'OVERBOUGHT' else thresholds['rsi']
        bias_limit = thresholds['bias'] + 2 if status == 'OVERBOUGHT' else thresholds['bias']
        
        can_trade = bool(
            total >= score_threshold and 
            rsi < rsi_limit and 
            ma20 > ma60 and 
            atr_pct >= thresholds['atr'] * 0.5 and 
            bias <= bias_limit
        )
        
        curr = close[-1]
        prev = close[-2] if len(close) >= 2 else curr
        today_chg = (curr / prev - 1) * 100
        
        return {
            'symbol': symbol, 'name': name(symbol), 'tier': tier,
            'score': round(total, 1), 'inst': round(inst, 1), 'tech': round(tech, 1), 'trend': round(trend, 1),
            'rsi': round(rsi, 1), 'bias': round(bias, 1), 'atr': round(atr_pct, 2),
            'f_days': f_days, 't_days': t_days,
            'ma20': round(ma20, 0), 'ma60': round(ma60, 0),
            'price': round(close[-1], 0), 'today_chg': round(today_chg, 2),
            'can_trade': can_trade, 'ma20_above': ma20 > ma60,
            'threshold_used': score_threshold
        }
    except Exception as e:
        return None

# ==================== 回測引擎 ====================

def backtest(symbol: str, max_hold: int = 5, thresholds: dict = None, status: str = 'BULLISH') -> List[Dict]:
    if thresholds is None:
        thresholds = {'score': 32, 'rsi': 65, 'bias': 8, 'atr': 0.3}
    
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
        
        ma20 = pd.Series(close).rolling(20).mean().values
        ma60 = pd.Series(close).rolling(60).mean().values
        
        # RSI
        delta = np.diff(close, prepend=close[0])
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta > 0, 0, -delta)
        avg_gain_s = pd.Series(gain).ewm(alpha=1/14, min_periods=14).mean().values
        avg_loss_s = pd.Series(loss).ewm(alpha=1/14, min_periods=14).mean().values
        rs = avg_gain_s / np.where(avg_loss_s == 0, np.nan, avg_loss_s)
        rsi = 100 - (100 / (1 + rs))
        rsi = np.where(np.isnan(rsi), 50, rsi)
        
        # ATR
        prev_close = np.roll(close, 1)
        prev_close[0] = close[0]
        tr = np.maximum(high - low, np.maximum(np.abs(high - prev_close), np.abs(low - prev_close)))
        atr = pd.Series(tr).rolling(14).mean().values
        atr_pct = atr / close * 100
        
        bias_arr = (close - ma20) / ma20 * 100
        
        # 法人
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('SELECT date, foreign_net, trust_net FROM MarketData WHERE symbol = ? ORDER BY date DESC LIMIT 180', (symbol,))
        rows = cur.fetchall()
        conn.close()
        inst_map = {str(r[0])[:10]: {'f': r[1] or 0, 't': r[2] or 0} for r in rows}
        
        trades = []
        position = None
        
        tier = 1 if symbol in TIER1_TECH else (2 if symbol in TIER2_RELATED else 3)
        score_threshold = thresholds['score'] - (tier - 1) * 3
        # OVERBOUGHT額外放寬
        rsi_limit = thresholds['rsi'] + 5 if status == 'OVERBOUGHT' else thresholds['rsi']
        bias_limit = thresholds['bias'] + 2 if status == 'OVERBOUGHT' else thresholds['bias']
        atr_th = thresholds['atr'] * 0.5
        
        for i in range(60, len(dates)):
            price = close[i]
            r = rsi[i]
            m20 = ma20[i] if not np.isnan(ma20[i]) else 0
            m60 = ma60[i] if not np.isnan(ma60[i]) else 0
            a = atr_pct[i] if not np.isnan(atr_pct[i]) else 0
            b = bias_arr[i] if not np.isnan(bias_arr[i]) else 0
            
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
            
            f_s = inst_score(f_d)
            t_s = inst_score(t_d)
            base = max(f_s, t_s)
            if f_d >= 3 and t_d >= 3: base += 10
            inst_val = min(70, base)
            
            # 評分
            rsi_s = 20 if thresholds['rsi'] - 10 <= r <= thresholds['rsi'] else (12 if thresholds['rsi'] - 20 <= r < thresholds['rsi'] - 10 else 5)
            bias_s = 15 if -3 <= b <= thresholds['bias'] * 0.6 else (10 if thresholds['bias'] * 0.6 < b <= thresholds['bias'] else 5)
            atr_s = 10 if a >= thresholds['atr'] else (5 if a >= thresholds['atr'] * 0.7 else 0)
            tech = rsi_s + bias_s + atr_s
            trend = (15 if m20 > m60 else 0) + (10 if b > 0 else 5)
            total = inst_val * 0.40 + tech * 0.35 + trend * 0.25
            
            if position is None:
                if total >= score_threshold and r < thresholds['rsi'] and m20 > m60 and a >= thresholds['atr'] * 0.7 and b <= thresholds['bias']:
                    position = {'entry': price, 'days': 0, 'score': total}
            else:
                position['days'] += 1
                exit = False
                reason = 'time'
                
                if position['days'] >= max_hold:
                    exit = True
                    reason = 'hold_max'
                elif r >= 80:
                    exit = True
                    reason = 'rsi_overbought'
                elif b >= thresholds['bias']:
                    exit = True
                    reason = 'bias_high'
                elif m20 <= m60:
                    exit = True
                    reason = 'ma_cross'
                
                if exit:
                    profit = (price / position['entry'] - 1) * 100
                    trades.append({
                        'symbol': symbol, 'entry': position['entry'], 'exit': price,
                        'profit': profit, 'days': position['days'], 'reason': reason,
                        'score': position['score']
                    })
                    position = None
        
        if position:
            profit = (close[-1] / position['entry'] - 1) * 100
            trades.append({
                'symbol': symbol, 'entry': position['entry'], 'exit': close[-1],
                'profit': profit, 'days': position['days'], 'reason': 'eod',
                'score': position['score']
            })
        
        return trades
    except:
        return []

# ==================== 主系統 ====================

class NanaSystemV54:
    def __init__(self):
        self.status, self.max_hold, self.status_desc = get_market_status()
        self.thresholds = get_dynamic_thresholds(self.status)
        self.results = []
        self.trades = []
        self.top_picks = []
        
    def scan_universe(self):
        print(f'[{datetime.now().strftime("%H:%M:%S")}] Scanning {len(ALL_STOCKS)} stocks...')
        for symbol in ALL_STOCKS:
            r = analyze(symbol, self.thresholds, self.status)
            if r:
                self.results.append(r)
                if r['can_trade']:
                    self.top_picks.append(r)
        self.results.sort(key=lambda x: x['score'], reverse=True)
        self.top_picks.sort(key=lambda x: x['score'], reverse=True)
        print(f'  Scanned: {len(self.results)} | Tradeable: {len(self.top_picks)}')
        print(f'  Thresholds: score>={self.thresholds["score"]}, RSI<{self.thresholds["rsi"]}, Bias<={self.thresholds["bias"]}%, ATR>={self.thresholds["atr"]}%')
        
    def backtest_all(self):
        print(f'[{datetime.now().strftime("%H:%M:%S")}] Backtesting...')
        all_trades = []
        for r in self.top_picks[:30]:
            symbol = r['symbol']
            trades = backtest(symbol, self.max_hold, self.thresholds, self.status)
            if trades:
                for t in trades:
                    t['name'] = name(symbol)
                    t['tier'] = r['tier']
                all_trades.extend(trades)
        self.trades = all_trades
        if all_trades:
            df = pd.DataFrame(all_trades)
            wr = len(df[df['profit'] > 0]) / len(df) * 100
            avg = df['profit'].mean()
            print(f'  Total trades: {len(df)} | WR: {wr:.1f}% | Avg: {avg:.2f}%')
            return wr, avg, len(df)
        return 0, 0, 0
    
    def run(self):
        print('='*70)
        print(' NANA SYSTEM v5.4 - 交易量擴充版')
        print('='*70)
        print()
        print(f'市場狀態: {self.status_desc} | 最大持有: {self.max_hold}天')
        print(f'門檻設定: Score>={self.thresholds["score"]}, RSI<{self.thresholds["rsi"]}')
        print()
        
        self.scan_universe()
        print()
        
        # Top 30
        print('-'*70)
        print(f'{"排名":<4} {"代碼":<8} {"名稱":<8} {"Tier":<6} {"評分":<6} {"門檻":<6} {"RSI":<6} {"法人":<6}')
        print('-'*70)
        for i, r in enumerate(self.results[:30], 1):
            tier_icon = {1:'*', 2:'~', 3:'-'}
            icon = tier_icon.get(r['tier'], '?')
            print(f'{i:<4} {r["symbol"]:<8} {r["name"]:<8} {icon}{r["tier"]:<5} {r["score"]:<6.1f} {r["threshold_used"]:<6.0f} {r["rsi"]:<6.1f} {r["f_days"]:<6}')
        
        print()
        print('-'*70)
        print(f' 可交易標的 (動態門檻)')
        print('-'*70)
        if self.top_picks:
            for r in self.top_picks:
                chg_str = f"{r['today_chg']:+.2f}%"
                print(f'  [{r["score"]:.1f}] {r["symbol"]} {r["name"]} - RSI={r["rsi"]}, F={r["f_days"]}天, T={r["t_days"]}天, {chg_str}')
        else:
            print('  無符合條件的標的')
        print()
        
        wr, avg, total = self.backtest_all()
        
        # 詳細分析
        print()
        print('='*70)
        print(' 詳細分析')
        print('='*70)
        if self.trades:
            df = pd.DataFrame(self.trades)
            
            # Tier 分析
            print('\n【Tier 分析】')
            for t in [1, 2, 3]:
                tdf = df[df['tier'] == t]
                if len(tdf) > 0:
                    wr_t = len(tdf[tdf['profit'] > 0]) / len(tdf) * 100
                    avg_t = tdf['profit'].mean()
                    print(f'  Tier {t}: {len(tdf)}筆 | WR={wr_t:.1f}% | Avg={avg_t:.2f}%')
            
            # 持有期分析
            print('\n【持有期分析 (1-7天)】')
            for d in range(1, 8):
                ddf = df[df['days'] == d]
                if len(ddf) > 0:
                    wr_d = len(ddf[ddf['profit'] > 0]) / len(ddf) * 100
                    avg_d = ddf['profit'].mean()
                    print(f'  {d}天: {len(ddf)}筆 | WR={wr_d:.1f}% | Avg={avg_d:.2f}%')
            
            # Exit reason
            print('\n【Exit 原因】')
            for reason, cnt in df['reason'].value_counts().items():
                rdf = df[df['reason'] == reason]
                wr_r = len(rdf[rdf['profit'] > 0]) / len(rdf) * 100
                avg_r = rdf['profit'].mean()
                print(f'  {reason}: {cnt}筆 | WR={wr_r:.1f}% | Avg={avg_r:.2f}%')
        
        # 倉位配置建議
        print('\n【Position Sizing 建議】')
        tier1_count = len([r for r in self.top_picks if r['tier'] == 1])
        tier2_count = len([r for r in self.top_picks if r['tier'] == 2])
        tier3_count = len([r for r in self.top_picks if r['tier'] == 3])
        total_count = len(self.top_picks)
        if total_count > 0:
            print(f'  Tier1: {tier1_count}檔 → 建議每檔 20-25% 資金')
            print(f'  Tier2: {tier2_count}檔 → 建議每檔 10-15% 資金')
            print(f'  Tier3: {tier3_count}檔 → 建議每檔 5-10% 資金')
            print(f'  總持有: {total_count}檔 → 建議最大 60-70% 倉位')
        
        print()
        print('='*70)
        print(' 系統總結')
        print('='*70)
        print(f'  市場狀態: {self.status_desc}')
        print(f'  掃描股票: {len(self.results)} 檔')
        print(f'  可交易: {len(self.top_picks)} 檔')
        print(f'  總交易: {total} 筆')
        print(f'  勝率: {wr:.1f}%')
        print(f'  平均報酬: {avg:.2f}%')
        print()
        if self.top_picks:
            print('  建議標的:')
            for i, r in enumerate(self.top_picks[:5], 1):
                print(f'    {i}. {r["symbol"]} {r["name"]} (評分: {r["score"]})')
        print()
        print('='*70)
        
        return {
            'market': self.status_desc,
            'results': len(self.results),
            'tradeable': len(self.top_picks),
            'wr': wr, 'avg': avg, 'total_trades': total,
            'thresholds': self.thresholds
        }

if __name__ == '__main__':
    system = NanaSystemV54()
    result = system.run()
    
    # 保存結果
    with open('nana_v54_result.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)