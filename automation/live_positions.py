import yfinance as yf, datetime

positions = [
    ('2376.TW', 332, 301), ('3034.TW', 226, 442),
    ('2379.TW', 183, 544), ('2379.TW', 184, 543),
    ('3034.TW', 223, 448), ('3034.TW', 222, 449),
    ('COHR', 5, 345), ('LITE', 2, 944), ('AMAT', 4, 429),
]

results = []
for sym, qty, entry in positions:
    try:
        price = yf.Ticker(sym).history(period='1d')['Close'].iloc[-1]
    except:
        price = entry
    pnl_pct = (price - entry) / entry * 100
    pnl_abs = (price - entry) * qty
    results.append((sym, qty, entry, price, pnl_pct, pnl_abs))

total_cost = sum(r[1] * r[2] for r in results)
total_value = sum(r[1] * r[3] for r in results)
total_pnl = sum(r[5] for r in results)

print(f"Total cost: {total_cost:,.0f}")
print(f"Total value: {total_value:,.0f}")
print(f"Unrealized PnL: {total_pnl:,.0f} ({total_pnl/total_cost*100:+.2f}%)")
for sym, qty, entry, price, pnl_pct, pnl_abs in sorted(results, key=lambda x: x[5], reverse=True):
    flag = "FAIL" if pnl_pct < -3 else ("HARVEST" if pnl_pct > 4 else "OK")
    print(f"  [{flag}] {sym}: {qty}@{entry} -> {price:.2f} ({pnl_pct:+.2f}%, {pnl_abs:+.0f})")