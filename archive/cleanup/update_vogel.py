# -*- coding: utf-8 -*-
"""Update Vogel TX indicators with today's data"""
import sys, sqlite3, requests, time
sys.stdout.reconfigure(encoding='utf-8')

DB = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\vogel_indicators.db'
TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSJ9.oCdQO1qNRUCYxHZSVuRQCqlF7X2DbQ77wury5ARCKzM'
BASE = 'https://api.finmindtrade.com/api/v4/data'

print('=== ?´æ–° Vogel TX ?‡æ?è³‡æ?åº?===\n')

# Get today's data from FinMind
params = {
    'dataset': 'TaiwanFuturesDaily',
    'data_id': 'TX',
    'start_date': '2026-04-28',
    'end_date': '2026-04-28',
    'token': TOKEN
}

r = requests.get(BASE, params=params, timeout=10)
if r.status_code == 200:
    d = r.json()
    if d.get('status') == 200 and d['data']['data']:
        row = d['data']['data'][0]
        date = row.get('date')
        close = float(row.get('close', 0))
        open_p = float(row.get('open', 0))
        high = float(row.get('high', 0))
        low = float(row.get('low', 0))
        
        print(f'FinMind TX {date}: close={close}')
        
        # Calculate indicators
        # SMA(20), SMA(60), EMA(12), EMA(26), BB(20,2), RSI(14), ATR(14)
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        
        # Get last 60 records for calculation
        cur.execute('SELECT date, close FROM daily ORDER BY date DESC LIMIT 60')
        rows = cur.fetchall()
        conn.close()
        
        if rows:
            closes = [r[1] for r in reversed(rows)] + [close]
            
            # SMA
            sma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else 0
            sma60 = sum(closes[-60:]) / 60 if len(closes) >= 60 else 0
            
            # EMA
            ema12 = close
            ema26 = close
            if len(closes) >= 12:
                multiplier = 2 / 13
                ema12 = sum([closes[i] * ((1-multiplier) ** (11-i)) for i in range(11, -1, -1)])
            if len(closes) >= 26:
                multiplier = 2 / 27
                ema26 = sum([closes[i] * ((1-multiplier) ** (25-i)) for i in range(25, -1, -1)])
            
            # BB(20,2)
            recent20 = closes[-20:] if len(closes) >= 20 else closes
            sma = sum(recent20) / len(recent20)
            std = (sum([(x - sma)**2 for x in recent20]) / len(recent20)) ** 0.5
            bb_upper = sma + 2 * std
            bb_middle = sma
            bb_lower = sma - 2 * std
            
            # RSI(14)
            gains = []
            losses = []
            for i in range(1, len(closes)):
                diff = closes[i] - closes[i-1]
                if diff > 0:
                    gains.append(diff)
                    losses.append(0)
                else:
                    gains.append(0)
                    losses.append(abs(diff))
            
            if len(gains) >= 14:
                avg_gain = sum(gains[-14:]) / 14
                avg_loss = sum(losses[-14:]) / 14
                rs = avg_gain / avg_loss if avg_loss > 0 else 100
                rsi = 100 - (100 / (1 + rs))
            else:
                rsi = 50
            
            # ATR(14)
            trs = []
            for i in range(1, len(closes)):
                tr = max(closes[i] - closes[i-1], abs(closes[i] - closes[i-1]), abs(closes[i] - closes[i-1]))
                trs.append(tr)
            atr = sum(trs[-14:]) / 14 if len(trs) >= 14 else 100
            
            # Zone
            if close > bb_upper:
                zone = 'BULL_ZONE'
            elif close < bb_lower:
                zone = 'BEAR_ZONE'
            else:
                zone = 'NEUTRAL'
            
            print(f'Calculated: BB_U={bb_upper:.0f} BB_L={bb_lower:.0f} RSI={rsi:.1f} ATR={atr:.0f} Zone={zone}')
            
            # Check if already exists
            conn2 = sqlite3.connect(DB)
            cur2 = conn2.cursor()
            cur2.execute('SELECT date FROM daily WHERE date=?', (date,))
            exists = cur2.fetchone()
            
            if exists:
                print(f'{date} å·²å??¨ï??´æ–°ä¸?..')
                cur2.execute('''UPDATE daily SET open=?, high=?, low=?, close=?, bb_upper=?, bb_middle=?, bb_lower=?, rsi_14=?, atr_14=?, zone=? WHERE date=?''',
                    (open_p, high, low, close, bb_upper, bb_middle, bb_lower, rsi, atr, zone, date))
            else:
                print(f'{date} ä¸å??¨ï?å¯«å…¥ä¸?..')
                cur2.execute('''INSERT INTO daily (date, futures_id, contract_date, open, high, low, close, sma_20, sma_60, ema_12, ema_26, bb_upper, bb_middle, bb_lower, rsi_14, atr_14, zone)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (date, 'TX', '202606', open_p, high, low, close, sma20, sma60, ema12, ema26, bb_upper, bb_middle, bb_lower, rsi, atr, zone))
            
            conn2.commit()
            cur2.execute('SELECT COUNT(*) FROM daily')
            cnt = cur2.fetchone()[0]
            print(f'DB?´æ–°å®Œæ?: {cnt}ç­?)
            conn2.close()
    else:
        print(f'No data: {d}')
else:
    print(f'HTTP {r.status_code}')
