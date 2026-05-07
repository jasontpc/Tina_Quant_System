# -*- coding: utf-8 -*-
"""Nana v5.4 - Relaxed thresholds for more trades"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np
import yfinance as yf
import sqlite3
import json
import os
from datetime import datetime

DB_PATH = 'C:/Users/USER/.openclaw/workspace/Tina_Quant_System/data/tina_master.db'
DATA_DIR = 'Tina_Quant_System/data'
TEAM_DIR = 'Tina_Quant_System/teams/nana'

TIER1_TECH = [
    '2330','2454','3034','2379','2303','2344',
    '2382','3231','3717','4938',
    '2317','2353','2357','2345',
    '3017','6230','6269',
    '3044','6213','4935','4952',
    '2401','2340','2385',
]
TIER2_RELATED = [
    '3481','2409','6176','2412','3045','6239',
    '2327','2492','2356','2471','2497','5203',
]
TIER3_BLUE = [
    '2881','2882','2884','2885','2891',
    '2801','2812','2834','1301','1326','2002',
    '0050','0056','00891','00713',
]
ALL_STOCKS = list(set(TIER1_TECH + TIER2_RELATED + TIER3_BLUE))

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
    '0050':'元大台灣50','0056':'元大高股息','00891':'中信金特',
    '00713':'統一台灣高息',
}
def name(code): return STOCK_NAMES.get(code, code)

def last_valid(series, default=np.nan):
    vals = series.dropna()
    return vals.iloc[-1] if len(vals) > 0 else default

def safe_round(val, decimals=2):
    try:
        if val is None or (isinstance(val, float) and np.isnan(val)): return 0.0
        return round(float(val), decimals)
    except: return 0.0

# ============== STEP 1: Verify RSI < 65 in nana_v5.py ==============
# The v5.2 code already has RSI < 65 in entry check (can_trade)
# But let me verify the entry logic: total >= 35 and rsi < 65
# v5.2: if total >= 35 and rsi < 65 and ma20 > ma60 and atr_pct >= 0.3
# This is correct. Step 1 done.

# ============== STEP 5: Run Nana v5.3 backtest ==============
def get_market_status():
    try:
        twii = yf.download('^TWII', period='20d', auto_adjust=True, progress=False)
        if isinstance(twii.columns, pd.MultiIndex): twii.columns = [c[0] for c in twii.columns]
        close = twii['Close'].values
        ma20_s = pd.Series(close).rolling(20).mean()
        ma20 = last_valid(ma20_s, 0)
        rsi = 50
        if len(close) >= 14:
            delta = np.diff(close, prepend=close[0])
            gain = np.where(delta > 0, delta, 0)
            loss = np.where(delta > 0, 0, -delta)
            avg_gain = pd.Series(gain).ewm(alpha=1/14, min_periods=14).mean().iloc[-1]
            avg_loss = pd.Series(loss).ewm(alpha=1/14, min_periods=14).mean().iloc[-1]
            if avg_loss > 0: rsi = 100 - (100 / (1 + avg_gain / avg_loss))
        curr = close[-1]
        ret = (curr / ma20 - 1) * 100 if ma20 > 0 else 0
        if rsi > 80 or ret > 8: return 'OVERBOUGHT', 3, '過熱'
        elif curr > ma20 and rsi > 55: return 'BULLISH', 5, '多頭'  # v5.4: revert to 5 (4 hurt performance)
        elif curr < ma20 and rsi < 45: return 'BEARISH', 2, '空頭'
        else: return 'NEUTRAL', 3, '盤整'
    except: return 'NEUTRAL', 3, '未知'

def inst_score(days):
    if days >= 11: return 20
    elif days >= 8: return 60
    elif days >= 6: return 55
    elif days >= 4: return 50
    elif days == 3: return 40
    elif days == 2: return 20
    elif days == 1: return 15
    return 0

def calc_rsi(close, period=14):
    delta = np.diff(close, prepend=close[0])
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta > 0, 0, -delta)
    avg_gain = pd.Series(gain).ewm(alpha=1/period, min_periods=period).mean().values
    avg_loss = pd.Series(loss).ewm(alpha=1/period, min_periods=period).mean().values
    rs = avg_gain / np.where(avg_loss == 0, np.nan, avg_loss)
    rsi = 100 - (100 / (1 + rs))
    return np.where(np.isnan(rsi), 50, rsi)

def calc_atr(close, high, low, period=14):
    prev_close = np.roll(close, 1)
    prev_close[0] = close[0]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_close), np.abs(low - prev_close)))
    atr = pd.Series(tr).rolling(period).mean().values
    return atr / close * 100

def analyze(symbol):
    try:
        df = yf.download(symbol + '.TW', period='90d', auto_adjust=True, progress=False)
        if df is None or len(df) < 60: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = [c[0] for c in df.columns]
        close = df['Close'].values; high = df['High'].values; low = df['Low'].values
        
        ma20_s = pd.Series(close).rolling(20).mean()
        ma60_s = pd.Series(close).rolling(60).mean()
        ma20 = last_valid(ma20_s, 0)
        ma60 = last_valid(ma60_s, 0)
        
        rsi_vals = calc_rsi(close)
        rsi = rsi_vals[-1]
        atr_pct_arr = calc_atr(close, high, low)
        atr_pct = last_valid(pd.Series(atr_pct_arr), 0)
        bias_arr = (close - ma20_s.values) / ma20_s.values * 100
        bias = last_valid(pd.Series(bias_arr), 0)
        
        # Volume 5-day MA for vol_ratio check (v5.4)
        vol_arr = df['Volume'].values if 'Volume' in df.columns else np.full(len(close), np.nan)
        vol_ma5_arr = pd.Series(vol_arr).rolling(5).mean().values
        last_vol_ma5 = vol_ma5_arr[-1] if len(vol_ma5_arr) > 0 and not np.isnan(vol_ma5_arr[-1]) else (vol_arr[-1] if len(vol_arr) > 0 and not np.isnan(vol_arr[-1]) else 1.0)
        last_vol = vol_arr[-1] if len(vol_arr) > 0 and not np.isnan(vol_arr[-1]) else 1.0
        vol_ratio = round(last_vol / last_vol_ma5, 2) if last_vol_ma5 and last_vol_ma5 > 0 and last_vol else 1.0
        
        today_chg = (close[-1] / close[-2] - 1) * 100 if len(close) >= 2 else 0.0
        
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('SELECT foreign_net, trust_net FROM MarketData WHERE symbol = ? ORDER BY date DESC LIMIT 10', (symbol,))
        rows = cur.fetchall(); conn.close()
        f_days = t_days = 0
        for f, t in rows:
            if f and f > 0: f_days += 1
            else: break
        for f, t in rows:
            if t and t > 0: t_days += 1
            else: break
        
        f_s = inst_score(f_days); t_s = inst_score(t_days)
        base = max(f_s, t_s)
        if f_days >= 3 and t_days >= 3: base += 10
        inst = min(70, base)
        
        if 40 <= rsi <= 70: rsi_s = 20
        elif 30 <= rsi < 40: rsi_s = 12
        elif 70 < rsi <= 75: rsi_s = 10
        elif 75 < rsi <= 80: rsi_s = 5
        else: rsi_s = 3
        
        # v5.3 fix: Bias score adjustment
        bias_s = 15 if -3 <= bias <= 5 else (10 if 5 < bias <= 8 else (5 if 8 < bias <= 10 else 3))
        atr_s = 10 if atr_pct >= 0.5 else (5 if atr_pct >= 0.3 else 0)
        tech = rsi_s + bias_s + atr_s
        trend = (15 if ma20 > ma60 else 0) + (10 if bias > 0 else 5)
        total = inst * 0.40 + tech * 0.35 + trend * 0.25
        
        tier = 1 if symbol in TIER1_TECH else (2 if symbol in TIER2_RELATED else 3)
        
        # v5.4 ENTRY RULES (relaxed for more trades):
        # RSI < 70, Bias < 12%, ATR >= 0.2%, vol_ratio >= 0.5
        # Tier-based score thresholds
        tier_score_min = {1: 35, 2: 32, 3: 30}
        score_min = tier_score_min.get(tier, 35)
        can_trade = bool(total >= score_min and rsi < 70 and ma20 > ma60 and atr_pct >= 0.2 and bias < 12 and vol_ratio >= 0.5)
        
        # Check inst reversal condition
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('SELECT foreign_net FROM MarketData WHERE symbol = ? ORDER BY date DESC LIMIT 5', (symbol,))
        inst_rows = cur.fetchall(); conn.close()
        inst_reversal = False
        if len(inst_rows) >= 2:
            sell_days = 0
            for f, in inst_rows:
                if f and f < 0: sell_days += 1
                else: break
            if sell_days >= 2 and rsi > 65:
                inst_reversal = True
                can_trade = False
        
        return {'symbol': symbol, 'name': name(symbol), 'tier': tier,
            'score': round(total, 1), 'inst': round(inst, 1), 'tech': round(tech, 1), 'trend': round(trend, 1),
            'rsi': round(rsi, 1), 'bias': round(bias, 1), 'atr': round(atr_pct, 2),
            'f_days': f_days, 't_days': t_days,
            'ma20': round(ma20, 0), 'ma60': round(ma60, 0),
            'price': round(close[-1], 0), 'today_chg': round(today_chg, 2),
            'vol_ratio': round(vol_ratio, 2),
            'can_trade': can_trade, 'ma20_above': ma20 > ma60,
            'inst_reversal': inst_reversal}
    except Exception as e:
        print(f"  Error analyzing {symbol}: {e}")
        return None

def backtest(symbol, max_hold=5, tier=1):
    try:
        df = yf.download(symbol + '.TW', period='180d', auto_adjust=True, progress=False)
        if df is None or len(df) < 60: return []
        if isinstance(df.columns, pd.MultiIndex): df.columns = [c[0] for c in df.columns]
        close = df['Close'].values; high = df['High'].values; low = df['Low'].values
        dates = [str(d)[:10] for d in df.index]
        ma20 = pd.Series(close).rolling(20).mean().values
        ma60 = pd.Series(close).rolling(60).mean().values
        rsi = calc_rsi(close)
        atr_pct = calc_atr(close, high, low)
        bias_arr = (close - ma20) / ma20 * 100
        
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('SELECT date, foreign_net, trust_net FROM MarketData WHERE symbol = ? ORDER BY date DESC LIMIT 180', (symbol,))
        rows = cur.fetchall(); conn.close()
        inst_map = {str(r[0])[:10]: {'f': r[1] or 0, 't': r[2] or 0} for r in rows}
        
        trades = []; position = None
        for i in range(60, len(dates)):
            price = close[i]; r = rsi[i]
            m20 = ma20[i] if not np.isnan(ma20[i]) else 0
            m60 = ma60[i] if not np.isnan(ma60[i]) else 0
            a = atr_pct[i] if not np.isnan(atr_pct[i]) else 0
            b = bias_arr[i] if not np.isnan(bias_arr[i]) else 0
            
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
            
            f_s = inst_score(f_d); t_s = inst_score(t_d)
            base = max(f_s, t_s)
            if f_d >= 3 and t_d >= 3: base += 10
            inst_val = min(70, base)
            
            rsi_s = 20 if 40 <= r <= 70 else (12 if 30 <= r < 40 else (10 if 70 < r <= 75 else (5 if 75 < r <= 80 else 3)))
            bias_s = 15 if -3 <= b <= 5 else (10 if 5 < b <= 8 else (5 if 8 < b <= 10 else 3))
            atr_s = 10 if a >= 0.5 else (5 if a >= 0.3 else 0)
            tech = rsi_s + bias_s + atr_s
            trend = (15 if m20 > m60 else 0) + (10 if b > 0 else 5)
            total = inst_val * 0.40 + tech * 0.35 + trend * 0.25
            
            if position is None:
                # v5.4 entry: RSI < 70, Bias < 12%, ATR >= 0.2%
                tier_score_min = {1: 35, 2: 32, 3: 30}
                score_min = tier_score_min.get(tier, 35)
                if total >= score_min and r < 70 and m20 > m60 and a >= 0.2 and b < 12:
                    position = {'entry': price, 'days': 0, 'score': total, 'bias': b}
            else:
                position['days'] += 1
                exit = False; reason = 'time'
                # v5.4 exit: RSI >= 80, bias >= 12%, or MA cross
                if position['days'] >= max_hold:
                    exit = True; reason = 'hold_max'
                elif r >= 80:
                    exit = True; reason = 'rsi_overbought'
                elif b >= 12:
                    exit = True; reason = 'bias_high'
                elif m20 <= m60:
                    exit = True; reason = 'ma_cross'
                if exit:
                    profit = (price / position['entry'] - 1) * 100
                    trades.append({'symbol': symbol, 'entry': position['entry'], 'exit': price,
                        'profit': profit, 'days': position['days'], 'reason': reason, 'score': position['score']})
                    position = None
        if position:
            profit = (close[-1] / position['entry'] - 1) * 100
            trades.append({'symbol': symbol, 'entry': position['entry'], 'exit': close[-1],
                'profit': profit, 'days': position['days'], 'reason': 'eod', 'score': position['score']})
        return trades
    except Exception as e:
        print(f"  Error backtesting {symbol}: {e}")
        return []

class NanaSystem:
    def __init__(self):
        self.status, self.max_hold, self.status_desc = get_market_status()
        self.results = []; self.trades = []; self.top_picks = []
        
    def scan_universe(self):
        print(f'[{datetime.now().strftime("%H:%M:%S")}] Scanning {len(ALL_STOCKS)} stocks...')
        for symbol in ALL_STOCKS:
            r = analyze(symbol)
            if r:
                self.results.append(r)
                if r['can_trade']: self.top_picks.append(r)
        self.results.sort(key=lambda x: x['score'], reverse=True)
        self.top_picks.sort(key=lambda x: x['score'], reverse=True)
        print(f'  Scanned: {len(self.results)} | Tradeable: {len(self.top_picks)}')
        
    def backtest_all(self):
        print(f'[{datetime.now().strftime("%H:%M:%S")}] Backtesting (max_hold={self.max_hold}days)...')
        all_trades = []
        for r in self.top_picks[:20]:
            symbol = r['symbol']
            trades = backtest(symbol, self.max_hold, r['tier'])
            if trades:
                for t in trades:
                    t['name'] = name(symbol); t['tier'] = r['tier']
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
        print(' NANA SYSTEM v5.4 - RSI<70 + BIAS<12% + ATR>=0.2% + TIER_SCORES + VOL>=0.5')
        print('='*70)
        print(f'市場狀態: {self.status_desc} | 最大持有: {self.max_hold}天')
        print()
        self.scan_universe(); print()
        
        print('-'*70)
        print(f'{"排名":<4} {"代碼":<8} {"名稱":<8} {"Tier":<6} {"評分":<6} {"法人":<6} {"RSI":<6} {"Bias":<6} {"ATR%":<6} {"漲跌":<8}')
        print('-'*70)
        for i, r in enumerate(self.results[:20], 1):
            tier_icon = {1:'*', 2:'~', 3:'-'}
            icon = tier_icon.get(r['tier'], '?')
            chg_str = f"{r['today_chg']:+.2f}%"
            trade_tag = '✓' if r['can_trade'] else ' '
            reversal_tag = ' [REV]' if r.get('inst_reversal', False) else ''
            vr_tag = f" VR={r.get('vol_ratio',0):.1f}" if r.get('vol_ratio',0) < 1.0 else ''
            print(f'{i:<4} {r["symbol"]:<8} {r["name"]:<8} {icon}{r["tier"]:<5} {r["score"]:<6.1f} {r["f_days"]:<6} {r["rsi"]:<6.1f} {r["bias"]:<6.1f} {r["atr"]:<6} {chg_str}{reversal_tag}{vr_tag}')
        
        print()
        print('-'*70)
        print(f' 可交易標的 (Score>=30-35 by Tier, RSI<70, MA20>MA60, ATR>=0.2%, Bias<12%)')
        print('-'*70)
        if self.top_picks:
            for r in self.top_picks[:10]:
                tier_icon = {1:'⭐', 2:'~', 3:'-'}
                print(f'  {tier_icon.get(r["tier"],"?")} [{r["score"]:.1f}] {r["symbol"]} {r["name"]} - RSI={r["rsi"]}, F={r["f_days"]}d, T={r["t_days"]}d, bias={r["bias"]:.1f}%')
        else:
            print('  無符合條件的標的（市場過熱或不符合進場條件）')
        print()
        
        wr, avg, total = self.backtest_all()
        
        if self.trades:
            df = pd.DataFrame(self.trades)
            print('\n【Tier 分析】')
            for t in [1, 2, 3]:
                tdf = df[df['tier'] == t]
                if len(tdf) > 0:
                    wr_t = len(tdf[tdf['profit'] > 0]) / len(tdf) * 100
                    print(f'  Tier {t}: {len(tdf)}筆 | WR={wr_t:.1f}% | Avg={tdf["profit"].mean():.2f}%')
            print('\n【Exit 原因】')
            for reason, cnt in df['reason'].value_counts().items():
                rdf = df[df['reason'] == reason]
                wr_r = len(rdf[rdf['profit'] > 0]) / len(rdf) * 100
                print(f'  {reason}: {cnt}筆 | WR={wr_r:.1f}% | Avg={rdf["profit"].mean():.2f}%')
        
        print()
        print('='*70)
        print(f' 勝率: {wr:.1f}% | 平均報酬: {avg:.2f}% | 總交易: {total}筆')
        print('='*70)
        
        report = {
            'version': 'v5.4_relaxed',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'market': self.status_desc, 'max_hold': self.max_hold,
            'scan_total': len(self.results), 'tradeable': len(self.top_picks),
            'wr': float(wr), 'avg_return': float(avg), 'total_trades': int(total),
            'top_picks': [{'symbol': r['symbol'], 'name': r['name'], 'score': r['score'], 'rsi': r['rsi'], 'bias': r['bias']} for r in self.top_picks[:5]],
            'fixes_applied': ['RSI<70_relaxed', 'Bias<12%', 'ATR>=0.2%', 'vol_ratio>=0.5', 'Tier_score_thresholds']
        }
        os.makedirs(TEAM_DIR, exist_ok=True)
        with open(f'{TEAM_DIR}/nana_v5_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f'\n報告已儲存: {TEAM_DIR}/nana_v5_report.json')
        
        return report

if __name__ == '__main__':
    NanaSystem().run()