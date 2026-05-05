# -*- coding: utf-8 -*-
"""Tina 即時成長股掃描 v3（精準版）"""
import yfinance as yf
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(encoding='utf-8')

UNIVERSE = [
    'INTC', 'ASML', 'AVGO', 'QCOM', 'MU', 'NVDA', 'AMD', 'TSLA', 'META', 'AMZN', 'GOOGL',
    'SOXL', 'SOXS', 'TQQQ', 'UPRO', 'SPXL', 'YANG',
    '2330.TW', '2382.TW', '2454.TW', '2317.TW', '3665.TW',
    '00713.TW', '0056.TW', '0050.TW', '00646.TW',
]

def scan_one(sym):
    try:
        tk = yf.Ticker(sym)
        h = tk.history(period="3mo")
        if len(h) < 30:
            return None
        close = h['Close']
        delta = close.diff()
        gain = delta.clip(lower=0).ewm(com=13, adjust=False).mean()
        loss = (-delta.clip(upper=0)).ewm(com=13, adjust=False).mean()
        rs = gain / loss
        rsi = float((100 - (100 / (1 + rs))).iloc[-1])
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd_l = ema12 - ema26
        macd_s = macd_l.ewm(span=9, adjust=False).mean()
        macd_hist = float((macd_l - macd_s).iloc[-1])
        high = h['High'].values; low = h['Low'].values; cl_arr = close.values
        tr = pd.Series([max(high[i]-low[i], abs(high[i]-cl_arr[i-1]) if i > 0 else 0, abs(low[i]-cl_arr[i-1]) if i > 0 else 0) for i in range(len(high))]).ewm(com=14, adjust=False).mean()
        atr = float(tr.iloc[-1])
        price = float(close.iloc[-1])
        atr_pct = atr / price * 100

        # Filter
        if price > 100 or price < 1:
            return None
        if rsi < 30 or rsi > 70:
            return None
        if atr_pct < 1.5:
            return None
        if macd_hist <= 0:
            return None

        # Score
        score = 0
        if 40 <= rsi <= 50: score += 30
        elif 30 <= rsi < 40 or 50 < rsi <= 60: score += 15
        if macd_hist > 0: score += 20
        if atr_pct > 3: score += 10
        if price < 50: score += 10

        chg = float(close.pct_change().iloc[-1]) * 100
        return {'symbol': sym, 'price': price, 'rsi': rsi,
                'macd_hist': macd_hist, 'atr_pct': atr_pct,
                'score': score, 'chg': chg}
    except Exception as e:
        return None


def main():
    print("=" * 65)
    print("  Tina 即時成長股掃描 v3")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)
    print()
    print(f"Scanning {len(UNIVERSE)} symbols ...")

    results = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(scan_one, s): s for s in UNIVERSE}
        done = 0
        for f in as_completed(futures):
            done += 1
            r = f.result()
            if r:
                results.append(r)
            sys.stdout.write(f"\r  [{done}/{len(UNIVERSE)}] ")
            sys.stdout.flush()

    print()
    if not results:
        print("無符合條件的股票")
        return

    results.sort(key=lambda x: x['score'], reverse=True)

    print()
    print("%-12s %7s %6s %8s %6s %6s %6s" % ("Symbol","Price","RSI","MACD","ATR%","Score","1D%"))
    print("-" * 65)
    for s in results:
        zone = "🟢" if 40 <= s['rsi'] <= 50 else ("🔵" if s['rsi'] < 60 else "🔴")
        mkt = "TW" if ".TW" in s['symbol'] else "ETF" if s['symbol'].isupper() and len(s['symbol']) <= 5 else "US"
        print("%-12s $%6.2f %6.1f %+8.2f %5.1f%% %6d %+6.2f%%  %s [%s]" % (
            s['symbol'], s['price'], s['rsi'], s['macd_hist'],
            s['atr_pct'], s['score'], s['chg'], zone, mkt
        ))

    print()
    print("=" * 65)
    print(f"共 {len(results)} 檔符合 | 條件: 價格<$100 | RSI 30-70 | ATR>1.5% | MACD>0")


if __name__ == '__main__':
    main()
