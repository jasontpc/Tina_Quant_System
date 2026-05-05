# -*- coding: utf-8 -*-
"""Quick test of nana_v5 Veto integration - scan Tier3 stocks"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'C:/Users/USER/.openclaw/workspace/Tina_Quant_System')

import sqlite3
import yfinance as yf
import numpy as np
from teams.nana.nana_v5 import analyze, name, calc_rsi, calc_atr, inst_score, last_valid

DB = 'C:/Users/USER/.openclaw/workspace/Tina_Quant_System/data/tina_master.db'

# Test key stocks from Cycle 24
test_symbols = ['2379', '2454', '2317', '2474', '2884', '2451', '6230']

print("=" * 70)
print("Cycle 25 - nana_v5 Veto 信號測試")
print("=" * 70)
print()
print(f"{'代碼':<8} {'名稱':<10} {'RSI':>6} {'Bias':>7} {'ATR%':>6} {'法人':>4} {'評分':>6} {'信號':<12} {'Veto':<8}")
print("-" * 70)

for symbol in test_symbols:
    result = analyze(symbol)
    if result:
        print(f"{result['symbol']:<8} {result['name']:<10} {result['rsi']:>6.1f} {result['bias']:>7.1f} {result['atr']:>6.2f} {result['f_days']:>4} {result['score']:>6.1f} {result.get('signal','N/A'):<12} {'✅' if result.get('veto') else '—':<8}")
    else:
        print(f"{symbol:<8} {'N/A':<10} {'N/A':>6}")

print()
print("說明：信號欄若為 '不進場'/'觀望' = Veto 降級後的信號")
print("      nana_v5 v5.5 已整合 Veto 降級")
