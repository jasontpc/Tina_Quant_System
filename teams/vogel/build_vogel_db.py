# -*- coding: utf-8 -*-
"""Vogel ?æ?è¨ç?æ¨¡ç? - å®æ´?è¡æ?æ¨æ¸?åº« v3"""
import sys, sqlite3, os, requests
from datetime import datetime
import math
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjF9.ivums9mfJUrM2MYazJiOEg49RiYLOJMZtejqX79YWS8'
BASE = 'https://api.finmindtrade.com/api/v4/data'

class TI:
    @staticmethod
    def sma(data, period):
        if len(data) < period: return None
        return sum(data[-period:]) / period
    @staticmethod
    def ema(data, period):
        if len(data) < period: return None
        e = sum(data[:period]) / period
        m = 2 / (period + 1)
        for p in data[period:]: e = (p - e) * m + e
        return e
    @staticmethod
    def bb(closes, period=20):
        if len(closes) < period: return None, None, None
        w = closes[-period:]
        ma = sum(w) / period
        v = sum((x - ma) ** 2 for x in w) / period
        std = math.sqrt(v)
        return ma + 2*std, ma, ma - 2*std
    @staticmethod
    def rsi(prices, period=14):
        if len(prices) < period + 1: return None
        g, l = [], []
        for i in range(len(prices)-period, len(prices)):
            d = prices[i] - prices[i-1]
            (g if d > 0 else l).append(abs(d))
        ag = sum(g) / period if g else 0
        al = sum(l) / period if l else 0
        rs = ag / al if al else 100
        return round(100 - (100 / (1 + rs)), 2)
    @staticmethod
    def atr(h, l, c, period=14):
        if len(h) < period: return None
        trs = []
        for i in range(len(h)-period, len(h)):
            prev_c = c[i-1] if i > 0 else c[i]
            tr = max(h[i]-l[i], abs(h[i]-prev_c), abs(l[i]-prev_c))
            trs.append(tr)
        return round(sum(trs) / period, 2)
    @staticmethod
    def macd(closes, f=12, s=26, sig=9):
        if len(closes) < s: return None, None, None
        ef = TI.ema(closes, f)
        es = TI.ema(closes, s)
        if ef is None or es is None: return None, None, None
        m = ef - es
        mv = []
        for i in range(s, len(closes)):
            ef2 = TI.ema(closes[:i+1], f)
            es2 = TI.ema(closes[:i+1], s)
            if ef2 and es2: mv.append(ef2 - es2)
        if len(mv) >= sig:
            sg = sum(mv[-sig:]) / sig
            return round(m, 2), round(sg, 2), round(m - sg, 2)
        return round(m, 2), None, None
    @staticmethod
    def kdj(h, l, c, n=9):
        if len(c) < n: return None, None, None
        rsvs = []
        for i in range(len(c)-n, len(c)):
            hh = max(h[i-n+1:i+1])
            ll = min(l[i-n+1:i+1])
            rsv = (c[i]-ll)/(hh-ll)*100 if hh!=ll else 50
            rsvs.append(rsv)
        k = sum(rsvs[-3:])/3
        d = sum([k]*3)/3
        j = 3*k - 2*d
        return round(k,2), round(d,2), round(j,2)
    @staticmethod
    def willr(h, l, c, period=14):
        if len(c) < period: return None
        hh = max(h[-period:])
        ll = min(l[-period:])
        if hh==ll: return None
        return round((hh-c[-1])/(hh-ll)*-100, 2)
    @staticmethod
    def cci(tp, period=20):
        if len(tp) < period: return None
        sma = sum(tp[-period:])/period
        md = sum(abs(t-sma) for t in tp[-period:])/period
        if md==0: return None
        return round((tp[-1]-sma)/(0.015*md), 2)

def build():
    print('=== Vogel Indicators DB v3 ===\n')
    db_path = os.path.join(DATA_DIR, 'vogel_indicators.db')
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute('''CREATE TABLE IF NOT EXISTS daily (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT UNIQUE, futures_id TEXT, contract_date TEXT,
        open REAL, high REAL, low REAL, close REAL,
        volume INTEGER, open_interest INTEGER, spread REAL, spread_per REAL,
        sma_5 REAL, sma_10 REAL, sma_20 REAL, sma_60 REAL, sma_120 REAL,
        ema_12 REAL, ema_26 REAL,
        bb_upper REAL, bb_middle REAL, bb_lower REAL,
        rsi_14 REAL, rsi_7 REAL, rsi_28 REAL,
        macd_line REAL, macd_signal REAL, macd_hist REAL,
        atr_14 REAL, atr_30 REAL,
        kdj_k REAL, kdj_d REAL, kdj_j REAL,
        williams_r_14 REAL, cci_20 REAL, adx_14 REAL, zone TEXT
    )''')
    conn.commit()

    print('Fetching TX data from FinMind...')
    r = requests.get(f'{BASE}/data', params={
        'dataset': 'TaiwanFuturesDaily', 'data_id': 'TX',
        'start_date': '2024-01-01',
        'end_date': datetime.now().strftime('%Y-%m-%d')
    }, headers={'Authorization': f'Bearer {TOKEN}'}, timeout=30)
    if r.status_code != 200:
        print(f'API Error: {r.status_code}')
        return

    raw = r.json().get('data', [])
    if not raw:
        print('No data')
        return

    from collections import defaultdict
    by_contract = defaultdict(list)
    for d in raw:
        if '/' not in str(d['contract_date']):
            by_contract[d['contract_date']].append(d)

    # Select contract by most recent date (>= 2025-10-01 with enough records)
    candidates = []
    for cd, items in by_contract.items():
        latest = max(x['date'] for x in items)
        if latest >= '2025-10-01' and len(items) >= 30:
            candidates.append((cd, latest, len(items)))
    
    if candidates:
        # Sort by latest date desc, then by count desc
        candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
        main_cd = candidates[0][0]
        print(f'Contract candidates: {candidates[:5]}')
        print(f'Selected: {main_cd}')
    else:
        # Fallback: most records
        main_cd = max(by_contract, key=lambda cd: len(by_contract[cd]))
        print(f'No recent candidates, fallback to: {main_cd}')

    data = sorted([d for d in by_contract[main_cd] if d['date'] >= '2024-01-01'], key=lambda x: x['date'])
    print(f'Using contract {main_cd}: {len(data)} records ({data[0]["date"]} to {data[-1]["date"]})')

    closes = [d['close'] for d in data]
    highs = [d.get('max', 0) or 0 for d in data]
    lows = [d.get('min', 0) or 0 for d in data]

    inserted = 0
    for i, d in enumerate(data):
        c = d['close']
        bb_u, bb_m, bb_l = TI.bb(closes, 20)
        rsi14 = TI.rsi(closes, 14) if i>=14 else None
        rsi7 = TI.rsi(closes, 7) if i>=7 else None
        rsi28 = TI.rsi(closes, 28) if i>=28 else None
        macd_l, macd_s, macd_h = TI.macd(closes, 12, 26, 9) if i>=26 else (None, None, None)
        atr14 = TI.atr(highs, lows, closes, 14) if i>=14 else None
        atr30 = TI.atr(highs, lows, closes, 30) if i>=30 else None
        kk, kd, kj = TI.kdj(highs, lows, closes, 9) if i>=9 else (None, None, None)
        wr = TI.willr(highs, lows, closes, 14) if i>=14 else None
        tp = [(highs[j]+lows[j]+closes[j])/3 for j in range(max(0,i-19), i+1)]
        cci20 = TI.cci(tp, 20) if len(tp)>=20 else None

        if bb_l and c < bb_l: zone = 'BB_LOWER'
        elif bb_u and c > bb_u: zone = 'BB_UPPER'
        elif bb_m and c > bb_m: zone = 'BULL_ZONE'
        elif bb_m: zone = 'BEAR_ZONE'
        else: zone = 'NEUTRAL'

        sma5 = TI.sma(closes[max(0,i-4):i+1], 5) if i>=4 else None
        sma10 = TI.sma(closes[max(0,i-9):i+1], 10) if i>=9 else None
        sma20 = TI.sma(closes[max(0,i-19):i+1], 20) if i>=19 else None
        sma60 = TI.sma(closes[max(0,i-59):i+1], 60) if i>=59 else None
        sma120 = TI.sma(closes[max(0,i-119):i+1], 120) if i>=119 else None
        ema12 = TI.ema(closes[:i+1], 12) if i>=11 else None
        ema26 = TI.ema(closes[:i+1], 26) if i>=25 else None

        cur.execute('INSERT OR REPLACE INTO daily (date, futures_id, contract_date, open, high, low, close, volume, open_interest, spread, spread_per, sma_5, sma_10, sma_20, sma_60, sma_120, ema_12, ema_26, bb_upper, bb_middle, bb_lower, rsi_14, rsi_7, rsi_28, macd_line, macd_signal, macd_hist, atr_14, atr_30, kdj_k, kdj_d, kdj_j, williams_r_14, cci_20, adx_14, zone) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (d['date'], 'TX', main_cd, d.get('open'), d.get('max'), d.get('min'), c,
             d.get('volume'), d.get('open_interest'), d.get('spread'), d.get('spread_per'),
             sma5, sma10, sma20, sma60, sma120, ema12, ema26,
             bb_u, bb_m, bb_l,
             rsi14, rsi7, rsi28,
             macd_l, macd_s, macd_h,
             atr14, atr30,
             kk, kd, kj,
             wr, cci20, None, zone))
        inserted += 1

    conn.commit()
    sz = os.path.getsize(db_path)/1024
    cur.execute('SELECT COUNT(*) FROM daily')
    cnt = cur.fetchone()[0]
    cur.execute('SELECT MIN(date), MAX(date) FROM daily')
    mn, mx = cur.fetchone()
    print(f'\nDB: {sz:.1f}KB, {cnt} records ({mn} to {mx})')

    print('\n=== Latest 5 ===')
    cur.execute('SELECT date, close, sma_20, bb_upper, bb_middle, bb_lower, rsi_14, atr_14, macd_hist, kdj_k, zone FROM daily ORDER BY date DESC LIMIT 5')
    print(f'{"date":<12} {"close":>8} {"sma20":>8} {"bb_u":>8} {"bb_m":>8} {"bb_l":>8} {"rsi":>6} {"atr":>7} {"macd":>8} {"kdj":>6} {"zone":<12}')
    for r in cur.fetchall():
        print(f'{r[0]:<12} {r[1]:>8.0f} {(r[2] or 0):>8.0f} {(r[3] or 0):>8.0f} {(r[4] or 0):>8.0f} {(r[5] or 0):>8.0f} {(r[6] or 0):>6.1f} {(r[7] or 0):>7.0f} {(r[8] or 0):>8.2f} {(r[9] or 0):>6.1f} {r[10]:<12}')

    print('\n=== Indicators DB Ready ===')
    conn.close()

if __name__ == '__main__':
    build()

