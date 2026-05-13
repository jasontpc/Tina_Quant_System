# -*- coding: utf-8 -*-
"""快速測試 supply_chain_scanner"""
import sys, json, os, time, sqlite3
import yfinance as yf
import numpy as np
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

AGENTS_DIR = r"C:\Users\USER\.openclaw\agents\ray"
RAM_CACHE = os.path.join(AGENTS_DIR, "supply_chain_ram.json")

def get_rsi(c, p=14):
    if len(c) < p + 1:
        return 50.0
    d = np.diff(c)
    g = np.where(d > 0, d, 0)
    l = np.where(d < 0, -d, 0)
    ag = np.mean(g[-p:])
    al = np.mean(l[-p:])
    return 100 - (100 / (1 + ag / al)) if al != 0 else 50.0

def get_top_movers(n=5):
    symbols = ["NVDA", "TSLA", "META", "MSFT", "AAPL"]
    movers = []
    for sym in symbols:
        try:
            h = yf.Ticker(sym).history(period="5d")
            if h is None or h.empty or len(h) < 5:
                continue
            close = h['Close'].values
            rsi = get_rsi(close)
            pct = (close[-1] - close[-2]) / close[-2] * 100 if len(close) >= 2 else 0
            movers.append({"symbol": sym, "rsi": rsi, "day_pct": pct, "price": close[-1]})
        except Exception as e:
            print(f"  {sym}: error {e}")
            continue
    movers.sort(key=lambda x: x["day_pct"], reverse=True)
    return movers[:n]

print("=== Supply Chain Scanner Test ===")
print("Fetching top movers...")
movers = get_top_movers(3)
for m in movers:
    print(f"  {m['symbol']}: {m['day_pct']:+.2f}% RSI={m['rsi']:.0f} price={m['price']:.2f}")

# 測試 RAM cache 讀寫
test_data = {"NVDA": {"upstream": ["TSM", "SK Hynix"], "downstream": ["CSPs"], "price": 135.0}}
with open(RAM_CACHE, 'w', encoding='utf-8') as f:
    json.dump(test_data, f, ensure_ascii=False)
print(f"\nRAM cache written to {RAM_CACHE}")

with open(RAM_CACHE, 'r', encoding='utf-8', errors='replace') as f:
    loaded = json.load(f)
print(f"RAM cache loaded: {list(loaded.keys())}")
print("✅ Test complete")