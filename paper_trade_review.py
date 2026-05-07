import json, os, sys, time

sys.stdout.reconfigure(encoding='utf-8')

print('=' * 60)
print('Leo Paper Trade Review — 2026-05-07')
print('=' * 60)

# Load trades
trades_file = 'teams/leadtrades/leos/leos_trades.json'
data = json.load(open(trades_file, encoding='utf-8'))
trades = data.get('trades', [])
open_t = [t for t in trades if t.get('status') == 'open']
closed_t = [t for t in trades if t.get('status') == 'closed']

print(f'\nPositions: {len(open_t)} open, {len(closed_t)} closed')

# Current prices from leos_analysis_v65
analysis_file = 'teams/leadtrades/leos/leos_analysis_v65.json'
if os.path.exists(analysis_file):
    analysis = json.load(open(analysis_file, encoding='utf-8'))
    current_prices = {a['symbol']: a for a in analysis}
    print(f'Analysis data: {len(analysis)} stocks')
else:
    current_prices = {}
    print('No analysis data found')

# Analyze each open position
print('\n=== Open Position Status ===')
overbought = 0
near_target = 0
near_stop = 0
good_profit = 0

for t in open_t:
    sym = t['symbol']
    entry = t['entry_price']
    target = t.get('target_price', entry * 1.15)
    stop = t.get('stop_loss', entry * 0.90)
    shares = t.get('shares', 0)
    entry_rsi = t.get('entry_rsi', 0)

    if sym in current_prices:
        cur = current_prices[sym]['price']
        rsi = current_prices[sym]['rsi']
        pnl_pct = (cur - entry) / entry * 100
        pnl_abs = (cur - entry) * shares
        dist_target = (target - cur) / cur * 100
        dist_stop = (cur - stop) / cur * 100
    else:
        cur = entry
        rsi = entry_rsi
        pnl_pct = 0
        pnl_abs = 0
        dist_target = 100
        dist_stop = 100

    # Categorize
    if rsi > 80: overbought += 1
    if pnl_pct > 10: good_profit += 1
    if dist_target < 5: near_target += 1
    if dist_stop < 3: near_stop += 1

    print(f"\n{cur} {t['name']} ({sym})")
    print(f"  Entry: ${entry} | Current: ${cur} | RSI: {rsi}")
    print(f"  PnL: {pnl_pct:+.1f}% (NT${pnl_abs:+,.0f})")
    print(f"  Target: ${target} ({dist_target:+.1f}%) | Stop: ${stop} ({dist_stop:+.1f}%)")
    print(f"  Entry signals: {t.get('entry_signals', [])}")

    # Check exit conditions
    exits = []
    if cur >= target: exits.append('TARGET HIT')
    if cur <= stop: exits.append('STOP HIT')
    if rsi > 85 and pnl_pct > 5: exits.append('OVERBOUGHT - TAKE PROFIT')
    if pnl_pct > 15: exits.append('BIG GAIN - LOCK IN')
    if exits:
        print(f"  >>> EXIT SIGNAL: {', '.join(exits)}")

print(f'\n=== Summary ===')
print(f'Overbought (RSI>80): {overbought}')
print(f'Good profit (>10%): {good_profit}')
print(f'Near target (<5%): {near_target}')
print(f'Near stop (<3%): {near_stop}')
print(f'Closed: {len(closed_t)}')

# Show stats
print(f'\n=== Closed Trade Stats ===')
if closed_t:
    wins = [t for t in closed_t if t.get('pnl', 0) > 0]
    losses = [t for t in closed_t if t.get('pnl', 0) <= 0]
    wr = len(wins) / len(closed_t) * 100
    total_pnl = sum(t.get('pnl', 0) for t in closed_t)
    print(f'Win Rate: {wr:.0f}% ({len(wins)}/{len(closed_t)})')
    print(f'Total PnL: NT${total_pnl:,.0f}')
else:
    print('No closed trades yet')
    print('No real performance data until positions are closed')

print('\n=== Issues Identified ===')
print('1. 106 positions all open — no exits triggered')
print('2. System paused due to overbought market, but existing positions not managed')
print('3. No daily PnL tracking or stats updates')
print('4. Need automated exit check even when market is overbought')

print('\n=== Recommended Actions ===')
print('A. Run exit check daily regardless of market state')
print('B. Add "lock in profit" rule: if RSI>80 AND profit>5%, auto-exit')
print('C. Build unified paper trade platform for multiple teams')
print('D. Add daily performance report to Telegram')