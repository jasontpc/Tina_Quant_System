import sys, json, os, time, yfinance as yf
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

TRADES_FILE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leadtrades\leos\leos_trades.json'
ANALYSIS_FILE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leadtrades\leos\leos_analysis_v65.json'

# Fixed exit rules
MAX_HOLD_DAYS = 45
MAX_POSITIONS_PER_STOCK = 3
OVERBOUGHT_PROFIT_LOCK_PCT = 5.0
OVERBOUGHT_EXIT_RSI = 80
BIG_GAIN_TAKE_PROFIT_PCT = 15.0

def get_rsi(closes, period=12):
    if len(closes) < period + 1: return 50.0
    d = np.diff(closes)
    g = np.where(d > 0, d, 0)
    l = np.where(d < 0, -d, 0)
    ag = np.mean(g[-period:])
    al = np.mean(l[-period:])
    return 100 - (100 / (1 + ag/al)) if al != 0 else 50

def load_trades():
    if os.path.exists(TRADES_FILE):
        try:
            with open(TRADES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return {'trades': [], 'stats': {'total': 0, 'wins': 0, 'losses': 0, 'total_pnl': 0}}

def save_trades(data):
    with open(TRADES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_current_prices():
    """Get current prices for all monitored stocks"""
    MONITOR = ['2330', '2454', '2317', '2379', '2376', '2382', '3665', '3034']
    prices = {}
    for sym in MONITOR:
        try:
            t = yf.Ticker(f'{sym}.TW')
            h = t.history(period='2d')
            if not h.empty:
                closes = h['Close'].dropna().values
                if len(closes) >= 2:
                    prices[sym] = {
                        'price': float(closes[-1]),
                        'rsi': get_rsi(closes, 12)
                    }
        except: pass
    return prices

def run_daily_review():
    print('=' * 60)
    print('Leo Daily Paper Trade Review')
    print('Time:', time.strftime('%Y-%m-%d %H:%M'))
    print('=' * 60)

    trades_data = load_trades()
    open_t = [t for t in trades_data['trades'] if t.get('status') == 'open']
    closed_t = [t for t in trades_data['trades'] if t.get('status') == 'closed']

    print(f'\nOpen: {len(open_t)} | Closed: {len(closed_t)}')

    # Get current prices
    print('\n[Step 1] Fetching current prices...')
    current = get_current_prices()
    print(f'Got prices for {len(current)} stocks')

    # Analyze each open position
    print('\n[Step 2] Position Analysis:')
    exits_to_run = []
    near_target = []
    near_stop = []
    overbought_profit = []
    big_gains = []

    for t in open_t:
        sym = t['symbol']
        if sym not in current:
            print(f'  {sym}: No price data, skipping')
            continue

        cur = current[sym]['price']
        entry = t['entry_price']
        target = t.get('target_price', entry * 1.15)
        stop = t.get('stop_loss', entry * 0.90)
        rsi = current[sym]['rsi']
        shares = t.get('shares', 0)
        pnl_pct = (cur - entry) / entry * 100
        pnl_abs = (cur - entry) * shares
        dist_target = (target - cur) / cur * 100
        dist_stop = (cur - stop) / cur * 100

        # Entry age check
        try:
            entry_time = time.mktime(time.strptime(t['timestamp'], '%Y-%m-%d %H:%M:%S'))
            days_held = (time.time() - entry_time) / 86400
        except:
            days_held = 0

        reason = None

        # Exit conditions
        if cur >= target:
            reason = 'take_profit_target'
        elif cur <= stop:
            reason = 'stop_loss'
        elif rsi > OVERBOUGHT_EXIT_RSI and pnl_pct > OVERBOUGHT_PROFIT_LOCK_PCT:
            reason = f'overbought_lock_profit_RSI{int(rsi)}_pnl{pnl_pct:.1f}'
        elif pnl_pct > BIG_GAIN_TAKE_PROFIT_PCT:
            reason = f'big_gain_take_profit_{pnl_pct:.1f}'
        elif days_held > MAX_HOLD_DAYS:
            reason = f'max_hold_days_{days_held:.0f}'

        print(f'\n  {sym} {t.get("name","")}')
        print(f'    Entry: ${entry} | Current: ${cur} | RSI: {rsi:.0f}')
        print(f'    PnL: {pnl_pct:+.1f}% (NT${pnl_abs:+,.0f}) | Days held: {days_held:.1f}')
        print(f'    Target: ${target:.0f} ({dist_target:+.1f}%) | Stop: ${stop:.0f} ({dist_stop:+.1f}%)')

        if reason:
            print(f'    >>> EXIT TRIGGER: {reason}')
            exits_to_run.append((t, reason, cur, pnl_pct, pnl_abs))
        elif pnl_pct > 5:
            overbought_profit.append((sym, pnl_pct, rsi, dist_target))
        elif dist_target < 5:
            near_target.append((sym, dist_target, pnl_pct))
        elif dist_stop < 3:
            near_stop.append((sym, dist_stop, pnl_pct))

    # Execute exits
    print(f'\n[Step 3] Executing {len(exits_to_run)} exits...')
    for t, reason, cur, pnl_pct, pnl_abs in exits_to_run:
        t['status'] = 'closed'
        t['exit_price'] = cur
        t['exit_reason'] = reason
        t['exit_time'] = time.strftime('%Y-%m-%d %H:%M:%S')
        t['pnl'] = round(pnl_abs, 0)
        t['pnl_pct'] = round(pnl_pct, 2)
        print(f'  EXITED {t["symbol"]}: {reason} -> ${cur} ({pnl_pct:+.1f}%)')

    # Count positions per stock
    from collections import Counter
    sym_counts = Counter(t['symbol'] for t in open_t if t.get('status') == 'open')
    excess_stocks = {s: c for s, c in sym_counts.items() if c > MAX_POSITIONS_PER_STOCK}
    if excess_stocks:
        print(f'\n[Step 4] Excess positions to close:')
        for sym, count in excess_stocks.items():
            # Close oldest positions until under limit
            same_sym = [t for t in open_t if t['symbol'] == sym and t.get('status') == 'open']
            same_sym.sort(key=lambda x: x.get('timestamp', ''))
            excess = count - MAX_POSITIONS_PER_STOCK
            for t in same_sym[:excess]:
                cur = current.get(sym, {}).get('price', t['entry_price'])
                pnl_pct = (cur - t['entry_price']) / t['entry_price'] * 100
                pnl_abs = (cur - t['entry_price']) * t.get('shares', 0)
                t['status'] = 'closed'
                t['exit_price'] = cur
                t['exit_reason'] = 'excess_positions_reduced'
                t['exit_time'] = time.strftime('%Y-%m-%d %H:%M:%S')
                t['pnl'] = round(pnl_abs, 0)
                t['pnl_pct'] = round(pnl_pct, 2)
                print(f'  Closed {sym} (excess): entry ${t["entry_price"]} -> ${cur} ({pnl_pct:+.1f}%)')

    save_trades(trades_data)

    # Final stats
    closed_now = [t for t in trades_data['trades'] if t.get('status') == 'closed']
    open_now = [t for t in trades_data['trades'] if t.get('status') == 'open']
    wins = [t for t in closed_now if t.get('pnl', 0) > 0]
    losses = [t for t in closed_now if t.get('pnl', 0) <= 0]
    total_pnl = sum(t.get('pnl', 0) for t in closed_now)
    wr = len(wins) / len(closed_now) * 100 if closed_now else 0

    print(f'\n=== Final Summary ===')
    print(f'Open: {len(open_now)} | Closed: {len(closed_now)}')
    print(f'Win Rate: {wr:.0f}% ({len(wins)}W/{len(losses)}L)')
    print(f'Total PnL: NT${total_pnl:,.0f}')

    # Show watch list
    if overbought_profit:
        print(f'\n=== Overbought with Profit (Watch) ===')
        for sym, pnl, rsi, dist in overbought_profit[:5]:
            print(f'  {sym}: +{pnl:.1f}% profit, RSI {rsi:.0f}, {dist:+.1f}% to target')

    return trades_data

if __name__ == '__main__':
    run_daily_review()