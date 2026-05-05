# -*- coding: utf-8 -*-
import yfinance as yf
import sys
import json

print("=== Ray 自主學習 — 市場數據更新 ===")
print(f"時間: 2026-04-25 01:17 AM (Asia/Taipei)")
print()

# TWII
twii = yf.Ticker('^TWII').history(period='1mo')
twii_low = twii['Low'].min()
twii_high = twii['High'].max()
twii_current = twii['Close'].iloc[-1]
twii_pos = (twii_current - twii_low) / (twii_high - twii_low) * 100
print(f"TWII 加權: {twii_current:.0f}")
print(f"TWII 1年區間: {twii_low:.0f} ~ {twii_high:.0f}")
print(f"TWII 位置: {twii_pos:.1f}%")
print()

# ETF positions
etfs = [
    ('0050', '0050'),
    ('0056', '0056'),
    ('00878', '00878'),
    ('00919', '00919'),
    ('00927', '00927'),
    ('00713', '00713'),
    ('00646', '00646'),
    ('00891', '00891'),
    ('00917', '00917'),
]

results = []
for name, ticker in etfs:
    try:
        sym = f"{ticker}.TW"
        t = yf.Ticker(sym)
        h = t.history(period='1y')
        cur = h['Close'].iloc[-1]
        low = h['Low'].min()
        high = h['High'].max()
        pos = (cur - low) / (high - low) * 100
        results.append((name, cur, low, high, pos))
        print(f"{name}: {cur:.2f} | 位置 {pos:.1f}%")
    except Exception as e:
        print(f"{name}: Error - {e}")

print()

# Market assessment
overbought = sum(1 for r in results if r[4] > 70)
neutral = sum(1 for r in results if 50 <= r[4] <= 70)
attractive = sum(1 for r in results if r[4] < 50)

print(f"=== 市場狀態 ===")
print(f"過熱 (>70%): {overbought} 檔")
print(f"中性 (50-70%): {neutral} 檔")
print(f"吸引 (<50%): {attractive} 檔")

if overbought == len(results):
    recommendation = "市場過熱，建議暫停DCA，等待回調"
elif attractive > 0:
    recommendation = f"{attractive} 檔ETF處於合理進場位置"
else:
    recommendation = "市場中性，維持正常DCA金額"

print(f"建議: {recommendation}")

# Save market snapshot
snapshot = {
    "timestamp": "2026-04-25T01:17:00+08:00",
    "twii": {"current": twii_current, "low": twii_low, "high": twii_high, "position_pct": twii_pos},
    "etfs": [{"name": r[0], "price": r[1], "low": r[2], "high": r[3], "position_pct": r[4]} for r in results],
    "market_state": "OVERBOUGHT" if overbought == len(results) else "NEUTRAL",
    "recommendation": recommendation
}

with open("teams/shared/market_snapshot.json", "w", encoding="utf-8") as f:
    json.dump(snapshot, f, indent=2, ensure_ascii=False)
print("\n已寫入 teams/shared/market_snapshot.json")