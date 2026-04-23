# -*- coding: utf-8 -*-
"""
Nana System v5.0 - 完整波段交易系統
======================================
目標: 
- 台股前100大，科技/AI優先
- 模擬真實交易 (費用/滑點/T+1)
- 回測修正迭代
- 評分: 法人40% + 技術35% + 趨勢25%
- 動態條件，多層分流
- 自主學習修正
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

DB_PATH = 'skills/stock-analyzer/scripts/tina_master.db'
DATA_DIR = 'Tina_Quant_System/data'
TEAM_DIR = 'Tina_Quant_System/teams/nana'

# ==================== 股票池 ====================

TIER1_TECH = [
    '2330','2454','3034','2379','2303','2344',  # 半導體
    '2382','3231','3717','4938',  # AI伺服器
    '2317','2353','2357','2345',  # 電子代工
    '3017','6230','6269',  # 散熱/機殼
    '3044','6213','4935','4952',  # PCB/CCL
    '2401','2340',  # 記憶體
    '2385',  # 高速傳輸
]

TIER2_RELATED = [
    '3481','2409','6176',  # 光電
    '2412','3045',  # 網通
    '6239',  # 封測
    '2327','2492','2356',  # 電子零組件
    '2471','2497','5203',  # 軟體/其他
]

TIER3_BLUE = [
    '2881','2882','2884','2885','2891',  # 金控
    '2801','2812','2834',  # 官股行庫
    '1301','1326','2002',  # 傳產
    '0050','0056','00891','00713',  # ETF
]

ALL_STOCKS = list(set(TIER1_TECH + TIER2_RELATED + TIER3_BLUE))

# ==================== 股票名稱 ====================

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

def name(code):
    return STOCK_NAMES.get(code, code)

# ==================== 市場判斷 ====================

def get_market_status():
    """判斷市場狀態"""
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
            return 'OVERBOUGHT', 5, '過熱'
        elif curr > ma20 and rsi > 55:
            return 'BULLISH', 7, '多頭'
        elif curr < ma20 and rsi < 45:
            return 'BEARISH', 3, '空頭'
        else:
            return 'NEUTRAL', 5, '盤整'
    except:
        return 'NEUTRAL', 5, '未知'

# ==================== 法人評分 ====================

def inst_score(days):
    if days >= 11: return 20
    elif days >= 6: return 60
    elif days >= 4: return 50
    elif days == 3: return 40
    elif days == 2: return 15
    elif days == 1: return 10
    return 0

# ==================== 股票分析 ====================

def analyze(symbol: str) -> Optional[Dict]:
    """完整分析單一股票"""
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
        
        # 評分
        f_s = inst_score(f_days)
        t_s = inst_score(t_days)
        base = max(f_s, t_s)
        if f_days >= 3 and t_days >= 3: base += 10
        inst = min(70, base)
        
        # RSI評分
        if 40 <= rsi <= 75: rsi_s = 20
        elif 30 <= rsi < 40: rsi_s = 12
        elif 75 < rsi <= 80: rsi_s = 10
        elif 80 < rsi <= 85: rsi_s = 5
        else: rsi_s = 3
        
        # Bias
        if -3 <= bias <= 5: bias_s = 15
        elif 5 < bias <= 8: bias_s = 10
        else: bias_s = 5
        
        # ATR
        atr_s = 10 if atr_pct >= 0.5 else (5 if atr_pct >= 0.3 else 0)
        
        tech = rsi_s + bias_s + atr_s
        trend = (15 if ma20 > ma60 else 0) + (10 if bias > 0 else 5)
        total = inst * 0.40 + tech * 0.35 + trend * 0.25
        
        # Tier
        if symbol in TIER1_TECH: tier = 1
        elif symbol in TIER2_RELATED: tier = 2
        else: tier = 3
        
        # 可交易
        can_trade = bool(total >= 35 and rsi < 85 and ma20 > ma60 and atr_pct >= 0.3)
        
        # 今日數據
        curr = close[-1]
        prev = close[-2] if len(close) >= 2 else curr
        today_chg = (curr / prev - 1) * 100
        
        return {
            'symbol': symbol,
            'name': name(symbol),
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
            'today_chg': round(today_chg, 2),
            'can_trade': can_trade,
            'ma20_above': ma20 > ma60
        }
    except:
        return None

# ==================== 回測引擎 ====================

def backtest(symbol: str, max_hold: int = 5) -> List[Dict]:
    """動態波段回測"""
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
            
            rsi_s = 20 if 40 <= r <= 75 else (5 if r >= 80 else 12)
            bias_s = 15 if -3 <= b <= 5 else 10
            atr_s = 10 if a >= 0.5 else (5 if a >= 0.3 else 0)
            tech = rsi_s + bias_s + atr_s
            trend = (15 if m20 > m60 else 0) + (10 if b > 0 else 5)
            total = inst_val * 0.40 + tech * 0.35 + trend * 0.25
            
            if position is None:
                if total >= 35 and r < 85 and m20 > m60 and a >= 0.3:
                    position = {'entry': price, 'days': 0, 'score': total}
            else:
                position['days'] += 1
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

# ==================== 主力系統 ====================

class NanaSystem:
    """Nana 主力系統"""
    
    def __init__(self):
        self.status, self.max_hold, self.status_desc = get_market_status()
        self.results = []
        self.trades = []
        self.top_picks = []
        
    def scan_universe(self):
        """掃描整個股票池"""
        print(f'[{datetime.now().strftime("%H:%M:%S")}] Scanning {len(ALL_STOCKS)} stocks...')
        
        for symbol in ALL_STOCKS:
            r = analyze(symbol)
            if r:
                self.results.append(r)
                if r['can_trade']:
                    self.top_picks.append(r)
        
        # 排序
        self.results.sort(key=lambda x: x['score'], reverse=True)
        self.top_picks.sort(key=lambda x: x['score'], reverse=True)
        
        print(f'  Scanned: {len(self.results)} | Tradeable: {len(self.top_picks)}')
        
    def backtest_all(self):
        """回測所有可交易標的"""
        print(f'[{datetime.now().strftime("%H:%M:%S")}] Backtesting...')
        
        all_trades = []
        
        for r in self.top_picks[:15]:  # Top 15
            symbol = r['symbol']
            trades = backtest(symbol, self.max_hold)
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
    
    def generate_report(self):
        """產生報告"""
        report = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'market': {'status': self.status, 'desc': self.status_desc, 'max_hold': self.max_hold},
            'scan': {
                'total': len(self.results),
                'tradeable': len(self.top_picks)
            },
            'top_picks': self.top_picks[:10],
            'summary': {}
        }
        
        if self.trades:
            df = pd.DataFrame(self.trades)
            report['summary'] = {
                'total_trades': len(df),
                'win_rate': round(len(df[df['profit'] > 0]) / len(df) * 100, 1),
                'avg_return': round(df['profit'].mean(), 2),
                'total_return': round(df['profit'].sum(), 1),
                'max_win': round(df['profit'].max(), 1),
                'max_loss': round(df['profit'].min(), 1)
            }
            
            # Tier分析
            tier_stats = []
            for t in [1, 2, 3]:
                tdf = df[df['tier'] == t]
                if len(tdf) > 0:
                    tier_stats.append({
                        'tier': t,
                        'trades': len(tdf),
                        'wr': round(len(tdf[tdf['profit'] > 0]) / len(tdf) * 100, 1),
                        'avg': round(tdf['profit'].mean(), 2)
                    })
            report['summary']['tier_stats'] = tier_stats
        
        return report
    
    def save_report(self, report):
        """儲存報告"""
        os.makedirs(TEAM_DIR, exist_ok=True)
        
        with open(f'{TEAM_DIR}/nana_v5_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # Top picks CSV
        if self.top_picks:
            df = pd.DataFrame(self.top_picks[:10])
            df.to_csv(f'{TEAM_DIR}/top_picks.csv', index=False, encoding='utf-8-sig')
        
        print(f'  Report saved: {TEAM_DIR}/nana_v5_report.json')
    
    def run(self):
        """執行完整流程"""
        print('='*70)
        print(' NANA SYSTEM v5.0 - 完整波段交易系統')
        print('='*70)
        print()
        print(f'市場狀態: {self.status_desc} | 最大持有: {self.max_hold}天')
        print()
        
        # 1. 掃描
        self.scan_universe()
        print()
        
        # 2. 顯示Top20
        print('-'*70)
        print(f'{'排名':<4} {'代碼':<8} {'名稱':<8} {'Tier':<6} {'評分':<6} {'RSI':<6} {'法人':<6} {'漲跌':<8}')
        print('-'*70)
        
        for i, r in enumerate(self.results[:20], 1):
            tier_icon = {1:'*', 2:'~', 3:'-'}
            icon = tier_icon.get(r['tier'], '?')
            chg_str = f"{r['today_chg']:+.2f}%"
            print(f'{i:<4} {r["symbol"]:<8} {r["name"]:<8} {icon}{r["tier"]:<5} {r["score"]:<6.1f} {r["rsi"]:<6.1f} {r["f_days"]:<6} {chg_str}')
        
        print()
        
        # 3. 可交易標的
        print('-'*70)
        print(' 可交易標的 (Score >= 35, RSI < 85, MA20 > MA60, ATR >= 0.3%)')
        print('-'*70)
        
        if self.top_picks:
            for r in self.top_picks[:10]:
                print(f'  [{r["score"]:.1f}] {r["symbol"]} {r["name"]} - RSI={r["rsi"]}, F={r["f_days"]}天, T={r["t_days"]}天')
        else:
            print('  無符合條件的標的')
        
        print()
        
        # 4. 回測
        wr, avg, total = self.backtest_all()
        print()
        
        # 5. 報告
        report = self.generate_report()
        self.save_report(report)
        
        # 6. 總結
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
            for i, r in enumerate(self.top_picks[:3], 1):
                print(f'    {i}. {r["symbol"]} {r["name"]} (評分: {r["score"]}, WR待驗證)')
        
        print()
        print('='*70)
        
        return report

# ==================== 主程式 ====================

if __name__ == '__main__':
    system = NanaSystem()
    report = system.run()