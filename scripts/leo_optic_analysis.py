# -*- coding: utf-8 -*-
"""Leo 光通訊產業深度分析（FinMind版）
======================================
涵蓋：磊晶/晶片、光收發模組、光連接器、矽光子/CPO
"""
import requests
import pandas as pd
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSJ9.oCdQO1qNRUCYxHZSVuRQCqlF7X2DbQ77wury5ARCKzM'
BASE = 'https://api.finmindtrade.com/api/v4/data'

# 光通訊產業鏈
CHAIN = [
    # 上游：磊晶與晶片製作
    ('3081', '聯亞', '磊晶/晶片'),
    ('2455', '全新', '磊晶/晶片'),
    ('4971', 'IET-KY', '磊晶/晶片'),
    # 光收發模組與封裝
    ('6442', '光聖', '光收發模組'),
    ('4979', '華星光', '光收發模組'),
    ('4977', '眾達-KY', '光收發模組'),
    ('4908', '前鼎', '光收發模組'),
    # 光連接器與被動元件
    ('3363', '上詮', '光連接器'),
    ('3163', '波若威', '光連接器'),
    ('3234', '光環', '光連接器'),
    # 矽光子/CPO
    ('6223', '旺矽', '測試介面'),
    ('6451', '訊芯-KY', '封測'),
    ('3450', '聯鈞', 'CPO'),
]


def fetch_finmind(sid, days=60):
    params = {
        'dataset': 'TaiwanStockPrice',
        'data_id': sid,
        'start_date': (pd.Timestamp.today() - pd.Timedelta(days=days)).strftime('%Y-%m-%d'),
        'end_date': pd.Timestamp.today().strftime('%Y-%m-%d'),
        'token': TOKEN,
    }
    r = requests.get(BASE, params=params, timeout=10)
    d = r.json()
    if d.get('status') == 200:
        return pd.DataFrame(d['data'])
    return None


def calc_indicators(df):
    close = df['close'].astype(float)
    openp = df['open'].astype(float)
    high = df['max'].astype(float)
    low = df['min'].astype(float)

    # RSI
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(com=13, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(com=13, adjust=False).mean()
    rsi = 100 - (100 / (1 + gain / loss))

    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_l = ema12 - ema26
    macd_s = macd_l.ewm(span=9, adjust=False).mean()
    macd_hist = macd_l - macd_s

    # ATR
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = tr1.combine(tr2, max).combine(tr3, max)
    atr = tr.ewm(com=14, adjust=False).mean()

    return close, rsi, macd_hist, atr


def score_it(rsi, macd, atr, price, rsi_low=30, rsi_high=50):
    score = 0
    if rsi_low <= rsi <= rsi_high:
        score += 30
    elif rsi < rsi_low:
        score += 15
    if macd > 0:
        score += 20
    if atr / price * 100 > 3:
        score += 10
    if price < 50:
        score += 10
    return score


def main():
    print("=" * 65)
    print("  Leo 光通訊產業深度分析（第一版）")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 65)
    print()

    # Group by chain
    from collections import defaultdict
    groups = defaultdict(list)
    for sid, name, cat in CHAIN:
        groups[cat].append((sid, name))

    results = []
    for cat, items in groups.items():
        print(f"[{cat}]")
        for sid, name in items:
            df = fetch_finmind(sid, 60)
            if df is None or len(df) < 20:
                print(f"  {sid} {name}: NO DATA")
                continue

            close, rsi, macd_hist, atr = calc_indicators(df)
            price = float(close.iloc[-1])
            rsi_v = float(rsi.iloc[-1])
            macd_v = float(macd_hist.iloc[-1])
            atr_v = float(atr.iloc[-1])
            atr_pct = atr_v / price * 100
            chg = float(close.pct_change().iloc[-1]) * 100
            sc = score_it(rsi_v, macd_v, atr_v, price)

            zone = "🟢" if 30 <= rsi_v <= 50 else ("🔵" if rsi_v < 60 else "🔴")
            print(f"  {sid} {name:8s} ${price:7.2f} RSI={rsi_v:5.1f} MACD={macd_v:+6.2f} ATR={atr_pct:4.1f}% 1D={chg:+5.1f}% Score={sc:3d} {zone}")

            results.append({
                'symbol': f"{sid}.TW", 'name': name, 'category': cat,
                'price': price, 'rsi': rsi_v, 'macd_hist': macd_v,
                'atr_pct': atr_pct, 'chg': chg, 'score': sc
            })

            # Recent table for top candidates
            if sc >= 50:
                print(f"       近5日:")
                for i in range(-5, 0):
                    print(f"         {df['date'].iloc[i]} ${float(close.iloc[i]):.2f} RSI={float(rsi.iloc[i]):.1f} MACD={float(macd_hist.iloc[i]):+.2f}")
        print()

    if not results:
        print("無資料")
        return

    # Sort and show ranking
    results.sort(key=lambda x: x['score'], reverse=True)
    print("=" * 65)
    print("  📊 Leo 光通訊 Score 排名")
    print("=" * 65)
    print("%-12s %-10s %7s %6s %8s %6s %6s" % ("Symbol", "Name", "Price", "RSI", "MACD", "ATR%", "Score"))
    print("-" * 65)
    for r in results:
        zone = "🟢" if 30 <= r['rsi'] <= 50 else ("🔵" if r['rsi'] < 60 else "🔴")
        print(f"  {r['symbol']:<10} {r['name']:<8s} ${r['price']:7.2f} {r['rsi']:6.1f} {r['macd_hist']:+8.2f} {r['atr_pct']:5.1f}% {r['score']:3d} {zone}")

    print()
    top = [r for r in results if r['score'] >= 50]
    if top:
        print("  🏆 Leo 進場候選（Score >= 50）")
        for r in top:
            print(f"    {r['symbol']} {r['name']} Score={r['score']} RSI={r['rsi']:.1f} MACD={r['macd_hist']:+.2f}")
    print()
    print("=" * 65)


if __name__ == '__main__':
    main()
