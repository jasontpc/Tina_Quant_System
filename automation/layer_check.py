import sqlite3
import yfinance as yf
import datetime
from datetime import timedelta

print("=" * 60)
print("TINA AUTONOMOUS DECISION FLOW — Layer 1-5 Full Check")
print("Time: 2026-05-08 15:12 TWN (07:12 UTC)")
print("=" * 60)

# ── Layer 1: Goals ──────────────────────────────────────────
goals = {
    "capital": 2000000,
    "max_position_pct": 0.40,
    "max_loss_per_trade": 0.08,
    "target_monthly_return": 0.03,
    "twii_rsi_overheat_threshold": 85,
    "active_strategies": ["Nana_v6.8", "Leo_v7.1", "Ray_DCA_v6"],
    "tier_settings": {
        "Tier1": {"max_hold": 5, "target_return": 0.05},
        "Tier2": {"max_hold": 7, "target_return": 0.04},
        "Tier3": {"max_hold": 10, "target_return": 0.02},
    }
}
print("\n[Layer 1] GOALS")
for k, v in goals.items():
    print(f"  {k}: {v}")

# ── Layer 2: Risk Boundaries ─────────────────────────────────
risk_rules = {
    "entry_rsi_max": 65,
    "max_loss_per_trade": 0.08,
    "total_position_limit": 0.40,
    "excess_threshold": 3,  # same stock count
    "holding_warning_days": 30,
    "twii_overheat_reduce": 0.50,  # reduce 50% when RSI>85
}
print("\n[Layer 2] RISK BOUNDARIES")
for k, v in risk_rules.items():
    print(f"  {k}: {v}")

# ── Layer 3: Market Sensing ───────────────────────────────────
print("\n[Layer 3] MARKET SENSING")
try:
    twii = yf.Ticker('^TWII')
    hist = twii.history(period='5d')
    close = hist['Close']
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = (100 - (100 / (1 + rs))).iloc[-1]
    recent_close = close.iloc[-1]
    prev_close = close.iloc[-2] if len(close) > 1 else close.iloc[-1]
    change_pct = (recent_close - prev_close) / prev_close * 100

    # Determine regime
    if rsi > 85:
        regime = "OVERBOUGHT"
    elif rsi > 65:
        regime = "BULL"
    elif rsi < 35:
        regime = "OVERSOLD"
    else:
        regime = "NEUTRAL"

    print(f"  TWII: {recent_close:.2f} ({change_pct:+.2f}%)")
    print(f"  RSI(14): {rsi:.1f} → Regime: {regime}")

    market_status = {
        "twii_price": float(recent_close),
        "twii_rsi": float(rsi),
        "twii_change_pct": float(change_pct),
        "regime": regime,
        "overheat_warning": rsi >= 83,  # advance warning at 83+
    }
except Exception as e:
    print(f"  [ERROR] TWII fetch failed: {e}")
    market_status = {"twii_rsi": 83, "regime": "BULL", "overheat_warning": True}

# ── Layer 4: Sandbox Status ───────────────────────────────────
print("\n[Layer 4] SANDBOX STATUS")
conn = sqlite3.connect('C:/Users/USER/.openclaw/workspace/Tina_Quant_System/data/master_backtest.db')
c = conn.cursor()

# Open positions
c.execute('SELECT symbol, quantity, entry_price, entry_date, stop_loss FROM open_positions ORDER BY entry_date')
rows = c.fetchall()

positions = []
total_cost = 0
total_value = 0

for r in rows:
    sym, qty, entry, edate, sl = r
    try:
        ticker = yf.Ticker(sym if '.' in sym else f"{sym}.TW")
        price = ticker.history(period='1d')['Close'].iloc[-1]
        pnl_pct = (price - entry) / entry * 100
        pnl_abs = (price - entry) * qty
    except:
        price = entry
        pnl_pct = 0
        pnl_abs = 0
    cost = entry * qty
    value = price * qty
    total_cost += cost
    total_value += value

    days_held = (datetime.datetime.now() - datetime.datetime.strptime(str(edate), '%Y-%m-%d')).days if edate else 0

    positions.append({
        "symbol": sym, "qty": qty, "entry": entry, "price": price,
        "pnl_pct": pnl_pct, "pnl_abs": pnl_abs, "days": days_held, "stop_loss": sl
    })

conn.close()

print(f"  Open positions: {len(positions)}")
print(f"  Total cost: ${total_cost:,.0f} | Current value: ${total_value:,.0f}")
print(f"  Unrealized PnL: ${total_value - total_cost:,.0f} ({(total_value/total_cost-1)*100:+.2f}%)")
print(f"  Position limit (40%): ${goals['capital'] * 0.40:,.0f}")
print(f"  Usage: {total_cost / (goals['capital'] * 0.40) * 100:.1f}%")

if len(positions) > 0:
    print("\n  Position Details:")
    for p in positions:
        flag = "⚠️" if p['days'] > risk_rules['holding_warning_days'] else ("🔴" if p['pnl_pct'] < -5 else "✅")
        print(f"  {flag} {p['symbol']}: {p['qty']}@{p['entry']} → {p['price']:.2f} ({p['pnl_pct']:+.2f}%, {p['pnl_abs']:+.0f}) | {p['days']}d | stop={p['stop_loss']}")

# Count excess (same stock multiple times)
from collections import Counter
sym_counts = Counter([p['symbol'] for p in positions])
excess = {s: c for s, c in sym_counts.items() if c >= risk_rules['excess_threshold']}
if excess:
    print(f"\n  ⚠️ EXCESS POSITIONS: {excess}")
else:
    print(f"\n  ✅ No excess positions (max {risk_rules['excess_threshold']} per stock)")

# ── Layer 5: Execution Decision ──────────────────────────────
print("\n[Layer 5] EXECUTION DECISION")
print(f"  Regime: {market_status['regime']}")
print(f"  TWII RSI: {market_status['twii_rsi']:.1f}")

# Committee scoring
scores = {"QA": 0, "Dev": 0, "RC": 0}

# QA scoring
if market_status['twii_rsi'] > 85:
    scores['QA'] = -25
elif market_status['twii_rsi'] > 70:
    scores['QA'] = -15
elif market_status['twii_rsi'] < 40:
    scores['QA'] = 20
else:
    scores['QA'] = 5

# Dev scoring
if market_status['twii_rsi'] > 85:
    scores['Dev'] = -20
elif regime == "OVERBOUGHT":
    scores['Dev'] = -10
else:
    scores['Dev'] = 10

# RC scoring
total_pos_pct = total_cost / goals['capital']
if total_pos_pct > 0.35:
    scores['RC'] = -15
if market_status['twii_rsi'] > 85:
    scores['RC'] -= 20

weighted = scores['QA'] * 0.35 + scores['Dev'] * 0.35 + scores['RC'] * 0.30

if weighted >= 30:
    decision = "APPROVE"
elif weighted >= 0:
    decision = "CAUTION"
else:
    decision = "REJECT"

print(f"  Committee scores: QA={scores['QA']}, Dev={scores['Dev']}, RC={scores['RC']}")
print(f"  Weighted total: {weighted:.1f}")
print(f"  Decision: {decision}")

# Recommendations
print("\n  === RECOMMENDATIONS ===")
if market_status['overheat_warning']:
    print(f"  ⚠️ TWII RSI {market_status['twii_rsi']:.1f} approaching 85 — monitor for reduction")

for p in positions:
    if p['days'] > 25:
        print(f"  🔴 {p['symbol']}: {p['days']} days held — approach holding limit")
    elif p['pnl_pct'] > 5:
        print(f"  📤 {p['symbol']}: +{p['pnl_pct']:.1f}% — consider partial harvest")
    elif p['pnl_pct'] < -3:
        print(f"  🛡️ {p['symbol']}: {p['pnl_pct']:.1f}% — watch stop loss")

if total_pos_pct > 0.35:
    print(f"  ⚠️ Position at {total_pos_pct*100:.1f}% — approaching 40% limit")

print("\n" + "=" * 60)
print("Layer 1-5 Check Complete")
print("=" * 60)