# -*- coding: utf-8 -*-
"""US Active ETF Screener"""

import sqlite3, yfinance as yf, pandas as pd, sys
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
DB = f'{DATA_DIR}\\us_active_etf.db'

ETFS = [
    'ARKK', 'ARKG', 'ARKQ', 'ARKF', 'ARKW',
    'QQQJ', 'MOO', 'SOXQ', 'BOTZ',
    'UTES', 'PAVE',
    'LALT', 'CONX',
    'VNLA',
    'ESGA', 'ACES',
    'SFYF', 'MOAT',
    'FINX', 'DIV', 'SPHD', 'SPYD',
    'SMH', 'SOXX',
    'ITA', 'XAR',
    'PBS', 'VAC', 'PEJ',
    'CRC',
    'ARKQ', 'ARKW',
]

def rsi(p, n=14):
    d = pd.Series(p).diff()
    g = d.where(d > 0, 0).ewm(alpha=1/n, min_periods=n, adjust=False).mean()
    l = (-d.where(d < 0, 0)).ewm(alpha=1/n, min_periods=n, adjust=False).mean()
    rs_val = (g / l).replace([float('inf'), -float('inf')], float('nan')).fillna(0)
    return float((100 - (100 / (1 + rs_val))).iloc[-1])

def analyze(sym):
    try:
        t = yf.Ticker(sym)
        h = t.history(period='6mo')
        if h is None or h.empty or len(h) < 30:
            return None
        price = float(h['Close'].iloc[-1])
        vol = int(h['Volume'].iloc[-1])
        v20 = int(h['Volume'].rolling(20).mean().iloc[-1]) if len(h) >= 20 else vol
        if price >= 100:
            return None
        c = h['Close'].reset_index(drop=True)
        info = {}
        try:
            info = t.info or {}
        except:
            pass
        mcap = info.get('marketCap', 0)
        nav = info.get('netAssetValue', 0)
        pe = info.get('trailingPE', None)
        rev = info.get('totalRevenue', 0)
        rg = info.get('revenueGrowth', 0) or 0
        dy = info.get('dividendYield', 0) or 0
        beta = info.get('beta', 1) or 1
        er = info.get('expenseRatio', 0) or 0
        name = info.get('longName', '') or info.get('quoteTypeName', '')
        rs = rsi(c.values)
        ma20 = float(c.rolling(20).mean().iloc[-1])
        ma50 = float(c.rolling(50).mean().iloc[-1]) if len(c) >= 50 else ma20
        ma200 = float(c.rolling(200).mean().iloc[-1]) if len(c) >= 200 else ma50
        b20 = (price / ma20 - 1) * 100 if ma20 > 0 else 0
        b50 = (price / ma50 - 1) * 100 if ma50 > 0 else 0
        b200 = (price / ma200 - 1) * 100 if ma200 > 0 else 0
        std20 = float(c.rolling(20).std().iloc[-1])
        bb_u = ma20 + 2 * std20
        bb_l = ma20 - 2 * std20
        bb_p = (price - bb_l) / (bb_u - bb_l) * 100 if bb_u > bb_l else 50
        m1 = float((c.iloc[-1] / c.iloc[-22] - 1) * 100) if len(c) >= 22 else 0
        m3 = float((c.iloc[-1] / c.iloc[-63] - 1) * 100) if len(c) >= 63 else 0
        m6 = float((c.iloc[-1] / c.iloc[-126] - 1) * 100) if len(c) >= 126 else 0
        hi52 = float(c.iloc[-252:].max()) if len(c) >= 252 else float(c.max())
        lo52 = float(c.iloc[-252:].min()) if len(c) >= 252 else float(c.min())
        p52 = (price - lo52) / (hi52 - lo52) * 100 if hi52 > lo52 else 50
        vr = vol / v20 if v20 > 0 else 0
        bp = price < 100 and vol >= 50000 and mcap >= 20000000
        fp = pe and 0 < pe <= 35 and dy >= 0
        tp = rs and 30 <= rs <= 70 and b20 < 15 and vr >= 0.3
        fs = (20 if pe and pe <= 20 else 15 if pe and pe <= 30 else 10 if pe and pe <= 35 else 0) + \
             (15 if dy > 0.03 else 10 if dy > 0.015 else 5 if dy > 0 else 0) + \
             (10 if er and er < 0.005 else 5 if er and er < 0.01 else 0)
        ts = (20 if rs and 35 <= rs <= 60 else 10 if rs and 30 <= rs < 35 else 0) + \
             (15 if -5 < b20 < 5 else 10 if -10 < b20 < 10 else 0) + \
             (20 if price > ma50 > ma200 else 10 if price > ma50 else 0) + \
             (15 if bb_p < 30 else 10 if bb_p < 50 else 0)
        ms = (15 if m1 > 5 else 8 if m1 > 0 else 0) + \
             (15 if m3 > 10 else 10 if m3 > 5 else 5 if m3 > 0 else 0) + \
             (10 if m6 > 15 else 5 if m6 > 10 else 0)
        tot = fs + ts + ms
        sig = 'STRONG_BUY' if tot >= 80 and bp and fp and tp else 'BUY' if tot >= 60 and bp and fp else 'HOLD' if tot >= 40 and bp else 'WAIT'
        return {
            'sym': sym, 'name': name, 'price': price,
            'rs': rs, 'b20': b20, 'm1': m1, 'm3': m3, 'm6': m6,
            'ma50': ma50, 'ma200': ma200, 'bb_p': bb_p, 'dy': dy, 'pe': pe,
            'tot': tot, 'sig': sig, 'bp': bp, 'fp': fp, 'tp': tp,
            'fs': fs, 'ts': ts, 'ms': ms, 'vol': vol, 'v20': v20, 'vr': vr
        }
    except:
        return None

def main():
    print('=' * 70)
    print('US ACTIVE ETF SCREENER')
    print(f'Time: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS etfs (symbol TEXT PRIMARY KEY, name TEXT, price REAL, rs REAL, b20 REAL, m1 REAL, m3 REAL, m6 REAL, ma50 REAL, ma200 REAL, bb_p REAL, dy REAL, pe REAL, tot REAL, sig TEXT, bp INTEGER, fp INTEGER, tp INTEGER, fs REAL, ts REAL, ms REAL, vol INTEGER, v20 INTEGER, vr REAL, updated_at TEXT)')
    cur.execute('DELETE FROM etfs')
    conn.commit()
    res = []
    for s in ETFS:
        r = analyze(s)
        if r:
            res.append(r)
            if r['tot'] >= 60:
                print(f"  {r['sym']}: ${r['price']:.2f} | Score={r['tot']} | {r['sig']}")
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    for r in res:
        cur.execute('INSERT INTO etfs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (r['sym'], r['name'], r['price'], r['rs'], r['b20'], r['m1'], r['m3'], r['m6'],
             r['ma50'], r['ma200'], r['bb_p'], r['dy'], r['pe'], r['tot'], r['sig'],
             r['bp'], r['fp'], r['tp'], r['fs'], r['ts'], r['ms'], r['vol'], r['v20'], r['vr'], now))
    conn.commit()
    print(f'  Analyzed: {len(res)}/{len(ETFS)} | Saved: {len(res)}')
    cur.execute('SELECT symbol, price, rs, b20, m1, m3, tot, sig FROM etfs ORDER BY tot DESC')
    print()
    print(f'{"Rank":<5} {"Symbol":<8} {"Price":>7} {"RSI":>5} {"BIAS20":>7} {"1M":>7} {"3M":>7} {"Score":>6} {"Signal"}')
    print('-' * 75)
    for i, row in enumerate(cur.fetchall(), 1):
        sym, price, rs, b20, m1, m3, tot, sig = row
        print(f'{i:<5} {sym:<8} {price:>7.2f} {(rs or 0):>5.1f} {b20:>+7.1f}% {m1:>+7.1f}% {m3:>+7.1f}% {tot:>6.0f} {sig}')
    conn.close()
    print('=' * 70)
    print('DONE')

if __name__ == '__main__':
    main()