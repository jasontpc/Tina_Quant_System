# -*- coding: utf-8 -*-
"""Quick market snapshot"""
import yfinance as yf
from datetime import datetime

print("=== International Market Snapshot ===", datetime.now().strftime("%Y-%m-%d %H:%M"), "\n")

# Indices
indices = [
    ("^GSPC", "S&P 500"),
    ("^DJI", "Dow Jones"),
    ("^IXIC", "Nasdaq"),
    ("^VIX", "VIX Fear Index"),
    ("^SOX", "Philadelphia Semi"),
]

print("[MAJOR INDICES]")
for sym, name in indices:
    try:
        t = yf.Ticker(sym)
        h = t.history(period="2d")
        if not h.empty:
            prev = h["Close"].iloc[-2] if len(h) > 1 else h["Close"].iloc[-1]
            curr = h["Close"].iloc[-1]
            chg = (curr - prev) / prev * 100
            arrow = "+" if chg > 0 else ""
            print(f"  {name}: {curr:,.2f} ({arrow}{chg:.2f}%)")
    except:
        pass

# Tech giants
print("\n[TECH GIANTS]")
tech = [("AAPL", "Apple"), ("MSFT", "Microsoft"), ("NVDA", "Nvidia"), ("META", "Meta"), ("GOOGL", "Google"), ("AMZN", "Amazon")]
for sym, name in tech:
    try:
        t = yf.Ticker(sym)
        h = t.history(period="2d")
        if not h.empty:
            prev = h["Close"].iloc[-2] if len(h) > 1 else h["Close"].iloc[-1]
            curr = h["Close"].iloc[-1]
            chg = (curr - prev) / prev * 100
            arrow = "+" if chg > 0 else ""
            print(f"  {name}: {curr:.2f} ({arrow}{chg:.2f}%)")
    except:
        pass

# Key commodities
print("\n[COMMODITIES]")
items = [("GC=F", "Gold"), ("CL=F", "Crude Oil"), ("SI=F", "Silver")]
for sym, name in items:
    try:
        t = yf.Ticker(sym)
        h = t.history(period="2d")
        if not h.empty:
            curr = h["Close"].iloc[-1]
            print(f"  {name}: {curr:.2f}")
    except:
        pass

# Crypto
print("\n[CRYPTO]")
coins = [("BTC-USD", "Bitcoin"), ("ETH-USD", "Ethereum")]
for sym, name in coins:
    try:
        t = yf.Ticker(sym)
        h = t.history(period="2d")
        if not h.empty:
            curr = h["Close"].iloc[-1]
            print(f"  {name}: ${curr:,.0f}")
    except:
        pass

print("\n" + "=" * 45)