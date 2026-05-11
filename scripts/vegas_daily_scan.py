"""
Tina 收盤後 Vega Tunnel 每日摘要
TW: 每日 16:30 (收盤後)
US: 每日 06:30 (开盘前)
"""
import sqlite3
import json
import yfinance as yf
import pandas as pd
from datetime import datetime

DB_PATH = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\tw_stock_registry.db"
OUT_FILE = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\vegas_tunnel_scan.json"
SCAN_LIMIT = 500

def get_stocks(n=500):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT code, name_cn FROM stock_registry
        WHERE market = 'twse'
          AND industry NOT LIKE '%ETF%'
          AND industry NOT LIKE '%指數股票%'
        ORDER BY code
    """)
    rows = cur.fetchall()
    conn.close()
    return [{"code": r[0], "name": r[1]} for r in rows[:n]]

def vegas_tunnel(code, market='TW'):
    import numpy as np
    try:
        sym = code + ".TW" if market == 'TW' else code
        try:
            df2 = yf.Ticker(sym).history(period="2y", interval="1d", auto_adjust=True)
        except Exception:
            df2 = yf.Ticker(sym).history(period="1y", interval="1d", auto_adjust=True)
        if df2 is None or df2.empty or len(df2) < 100:
            return None
        close = df2['Close'].astype(float).dropna()
        price = float(close.iloc[-1])
        prev  = float(close.iloc[-2]) if len(close) >= 2 else price
        chg   = (price - prev) / prev * 100
        for m in [12, 144, 169, 576, 676]:
            df2['EMA' + str(m)] = df2['Close'].ewm(span=m).mean()
        cur   = df2.iloc[-1]
        prev2 = df2.iloc[-2] if len(df2) > 1 else cur
        ema12  = float(cur['EMA12'])
        ema144 = float(cur['EMA144'])
        ema169 = float(cur['EMA169'])
        ema576 = float(cur['EMA576'])
        ema676 = float(cur['EMA676'])
        if any(np.isnan(x) for x in [ema12, ema144, ema169, ema576, ema676]):
            return None
        h1_above_h4 = (ema144 > ema576) and (ema169 > ema676)
        h1_below_h4 = (ema144 < ema576) and (ema169 < ema676)
        bias = 'BULL' if h1_above_h4 else ('BEAR' if h1_below_h4 else 'NEUTRAL')
        price_above   = (price > ema144) and (price > ema169)
        ema12_above   = (ema12 > ema144) and (ema12 > ema169)
        ema12_cross_up = (float(prev2['EMA12']) <= float(prev2['EMA144'])) and (ema12 > ema144)
        ema12_inside   = (min(ema144, ema169) < ema12 < max(ema144, ema169))
        tunnel_w = abs(ema144 - ema169)
        tp1 = round(float(price + tunnel_w * 0.55), 2)
        tp2 = round(float(price + tunnel_w * 0.89), 2)
        tp3 = round(float(price + tunnel_w * 1.44), 2)
        tp4 = round(float(price + tunnel_w * 2.33), 2)
        sl_long = round(float(min(ema144, ema169)), 2)
        sl_pct  = round((price - sl_long) / price * 100, 2)
        if bias == 'NEUTRAL':
            signal, sig_color = 'NEUTRAL', 'gray'
        elif bias == 'BULL' and price_above and ema12_above:
            signal, sig_color = 'BUY', 'green'
        elif bias == 'BULL' and price_above and not ema12_above:
            signal, sig_color = 'PULLBACK', 'blue'
        elif bias == 'BULL' and ema12_inside:
            signal, sig_color = 'INSIDE_TUNNEL', 'orange'
        elif bias == 'BEAR' and not price_above:
            signal, sig_color = 'SELL', 'red'
        elif price_above and not ema12_above:
            signal, sig_color = 'FAKEOUT', 'orange'
        else:
            signal, sig_color = 'NO_SIGNAL', 'gray'
        bias_sc = 2 if bias == 'BULL' else (-2 if bias == 'BEAR' else 0)
        brk_sc  = 3 if (price_above and ema12_above) else (1 if price_above else 0)
        dist_sc = min(5, int((price / min(ema144, ema169) - 1) * 100 / 5))
        score   = int((bias_sc + brk_sc + dist_sc) * 10)
        return dict(
            code=code, price=price, chg=chg, bias=bias, signal=signal,
            score=score, ema12=ema12, ema144=ema144, ema169=ema169,
            ema576=ema576, ema676=ema676,
            price_vs_144=round((price/ema144-1)*100,2),
            price_vs_169=round((price/ema169-1)*100,2),
            tunnel_w=round(float(tunnel_w),2), sl_long=sl_long, sl_pct=sl_pct,
            tp1=tp1, tp2=tp2, tp3=tp3, tp4=tp4,
            price_above=price_above, ema12_above=ema12_above,
            ema12_cross_up=ema12_cross_up, ema12_inside=ema12_inside,
            h1_above_h4=h1_above_h4,
        )
    except Exception:
        return None

def main():
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import time

    t0 = time.time()
    print("=== Vegas Daily Scan ===")
    stocks = get_stocks(SCAN_LIMIT)
    results = []

    with ThreadPoolExecutor(max_workers=15) as ex:
        futures = {ex.submit(vegas_tunnel, s['code'], 'TW'): s for s in stocks}
        done = 0
        for f in as_completed(futures):
            done += 1
            if done % 50 == 0:
                print(f"  {done}/{len(stocks)} done")
            try:
                r = f.result()
                if r:
                    results.append(r)
            except Exception:
                pass

    # Sort
    signal_order = {'BUY': 0, 'PULLBACK': 1, 'INSIDE_TUNNEL': 2,
                    'FAKEOUT': 3, 'NO_SIGNAL': 4, 'SELL': 5, 'NEUTRAL': 6}
    results.sort(key=lambda x: (signal_order.get(x['signal'], 9), -x['score']))

    buys = [r for r in results if r['signal'] == 'BUY']
    pulls = [r for r in results if r['signal'] == 'PULLBACK']
    fakes = [r for r in results if r['signal'] == 'FAKEOUT']

    print(f"\nScan complete: {len(results)} stocks in {time.time()-t0:.0f}s")
    print(f"BUY={len(buys)} | PULLBACK={len(pulls)} | FAKEOUT={len(fakes)}")

    output = {
        'scan_time': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'total': len(results),
        'buys': len(buys), 'pullbacks': len(pulls), 'fakeouts': len(fakes),
        'top10_buy': buys[:10],
        'watch_list': pulls[:10],
    }

    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # Build Telegram summary
    msg = (
        f"[VEGAS DAILY] {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"═══════════════════\n"
        f"BUY signals: {len(buys)}\n"
    )
    if buys[:5]:
        for r in buys[:5]:
            msg += f"  {r['code']} {r['name']} | ${r['price']} | {r['bias']} | S={r['score']}\n"

    msg += f"\nPULLBACK watch: {len(pulls)}\n"
    if pulls[:3]:
        for r in pulls[:3]:
            msg += f"  {r['code']} ${r['price']} | ema12={r['ema12']:.0f} | inside tunnel\n"

    msg += f"\nFAKEOUT caution: {len(fakes)}\n"
    if fakes[:3]:
        for r in fakes[:3]:
            msg += f"  {r['code']} ${r['price']} | EMA12 not confirmed\n"

    print(msg)
    return msg

if __name__ == '__main__':
    main()