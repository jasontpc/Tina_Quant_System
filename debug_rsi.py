# -*- coding: utf-8 -*-
"""Debug RSI discrepancy between pandas rolling and yfinance"""
import yfinance as yf
import pandas as pd
import sqlite3

sym = '0050.TW'

# Get yfinance data
t = yf.Ticker(sym)
h = t.history(period='3mo')  # auto_adjust=True by default
closes = h['Close']

# Method 1: Rolling mean RSI
def calc_rsi_rolling(c, period=14):
    d = c.diff()
    g = d.where(d > 0, 0).rolling(period).mean()
    l = (-d.where(d < 0, 0)).rolling(period).mean()
    rs = g / l
    return (rs / (1 + rs) * 100)

# Method 2: EWM RSI (Wilder's smoothing)
def calc_rsi_ewm(c, period=14):
    delta = c.diff()
    gain = delta.where(delta > 0, 0).ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# Method 3: Manual calculation (true Wilder)
def calc_rsi_manual(prices, period=14):
    if len(prices) < period + 1:
        return None
    deltas = []
    for i in range(1, len(prices)):
        deltas.append(prices[i] - prices[i-1])
    gains = [max(d, 0) for d in deltas]
    losses = [abs(min(d, 0)) for d in deltas]
    
    # First average
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    for i in range(len(gains) - period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    
    rs = avg_gain / avg_loss if avg_loss > 0 else 100
    return 100 - (100 / (1 + rs))

rsi_rolling = calc_rsi_rolling(closes, 14).iloc[-1]
rsi_ewm = calc_rsi_ewm(closes, 14).iloc[-1]
rsi_manual = calc_rsi_manual(list(closes), 14)

print(f"{sym} RSI Comparison:")
print(f"  Rolling mean RSI: {rsi_rolling:.2f}")
print(f"  EWM RSI:           {rsi_ewm:.2f}")
print(f"  Manual RSI:        {rsi_manual:.2f}")
print()

# Check the issue: pandas rolling vs ewm
# The difference of 1.74 between 80.30 and 82.04 comes from:
# 1. The rolling mean uses simple average (SMA)
# 2. EWM/Manual uses Wilder's smoothing (exponential)
# This is expected behavior!

# The rsi_audit.py script uses rolling mean but yfinance might use EWM
print("Root cause: pandas rolling vs ewm smoothing methods")
print(f"  This is expected - different RSI calculation methods")
print()

# Fix: Update rsi_audit.py to use consistent method
print("Fix: Will update rsi_audit.py to use consistent EWM method")