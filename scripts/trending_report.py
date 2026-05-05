# -*- coding: utf-8 -*-
"""Generate trending stocks report"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import sqlite3
from datetime import datetime

DB = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\stock_trends.db'

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("SELECT symbol, price, rsi_14, bias20, momentum_20d, trend_zone FROM trending_signals ORDER BY rsi_14 DESC")
rows = cur.fetchall()
conn.close()

print("=" * 65)
print("TRENDING STOCKS RSI REPORT")
print(f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("=" * 65)

# Group by zone
overbought = [r for r in rows if r[5] == 'OVERBOUGHT']
oversold = [r for r in rows if r[5] == 'OVERSOLD']
neutral = [r for r in rows if r[5] == 'NEUTRAL']

print(f"\n{'Symbol':<10} {'Price':>9} {'RSI':>5} {'BIAS20':>7} {'20D Mom':>8} Zone")
print("-" * 65)

for r in rows:
    sym, price, rsi, bias, mom, zone = r
    z = '[OVERBOUGHT]' if zone == 'OVERBOUGHT' else '[OVERSOLD]' if zone == 'OVERSOLD' else '[NEUTRAL]'
    print(f"{sym:<10} ${price:>8.2f} {rsi:>5.1f} {bias:>+6.1f}% {mom:>+7.1f}% {z}")

print()
print("=" * 65)
print("SUMMARY")
print("=" * 65)
print(f"Total: {len(rows)} stocks")
print(f"OVERBOUGHT (RSI>70): {len(overbought)}")
print(f"OVERSOLD (RSI<35): {len(oversold)}")
print(f"NEUTRAL: {len(neutral)}")

print()
print("🔴 OVERBOUGHT STOCKS:")
for r in overbought[:10]:
    print(f"  {r[0]}: RSI={r[2]:.1f}, BIAS20={r[3]:+.1f}%, 20D={r[4]:+.1f}%")

print()
print("🟢 BUY CANDIDATES (RSI < 45):")
candidates = [r for r in rows if r[2] < 45]
for r in sorted(candidates, key=lambda x: x[2])[:10]:
    print(f"  {r[0]}: RSI={r[2]:.1f}, BIAS20={r[3]:+.1f}%, 20D={r[4]:+.1f}%")

print()
print("=" * 65)