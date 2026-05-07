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

# 美股絕對停利/停損（每口$2000）
US_TAKE_PROFIT_AMOUNT = 300
US_STOP_LOSS_AMOUNT = 200

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
    """Get current prices for all monitored stocks (TW + US)"""
    # TW stocks
    TW_STOCKS = {
        '2330': '台積電', '2454': '聯發科', '2303': '聯電',
        '2317': '鴻海', '2382': '廣達', '3034': '緯穎',
        '2376': '技嘉', '2379': '瑞昱', '3665': '穎崴',
        '2456': '奇鋐', '3533': '嘉澤', '3532': '昇達科',
        '2371': '華星光', '3443': '創惟', '6717': '大聯大',
    }
    # US stocks
    US_STOCKS = {
        'NVDA': 'NVIDIA', 'AMD': 'AMD', 'QCOM': 'Qualcomm', 'ARM': 'ARM',
        'MU': 'Micron', 'WDC': 'Western Digital', 'STX': 'Seagate',
        'ANET': 'Arista', 'LITE': 'Lumentum', 'COHR': 'Coherent',
        'AMZN': 'Amazon', 'MSFT': 'Microsoft', 'GOOGL': 'Google', 'META': 'Meta',
        'AMAT': 'Applied Mat', 'LRCX': 'Lam Research', 'KLAC': 'KLA', 'SNPS': 'Synopsys', 'ASML': 'ASML',
        'MRVL': 'Marvell', 'AVGO': 'Broadcom',
    }

    prices = {}

    # TW stocks
    for sym in TW_STOCKS:
        try:
            t = yf.Ticker(f'{sym}.TW')
            h = t.history(period='2d')
            if not h.empty:
                closes = h['Close'].dropna().values
                if len(closes) >= 2:
                    prices[('TW', sym)] = {
                        'price': float(closes[-1]),
                        'rsi': get_rsi(closes, 12)
                    }
        except: pass

    # US stocks
    for sym in US_STOCKS:
        try:
            t = yf.Ticker(sym)
            h = t.history(period='2d')
            if not h.empty:
                closes = h['Close'].dropna().values
                if len(closes) >= 2:
                    prices[('US', sym)] = {
                        'price': float(closes[-1]),
                        'rsi': get_rsi(closes, 12)
                    }
        except: pass

    return prices

def run_daily_review():
    print('=' * 60)
    print('Leo Daily Paper Trade Review — TW + US 雙市場版')
    print('Time:', time.strftime('%Y-%m-%d %H:%M'))
    print('=' * 60)

    trades_data = load_trades()
    open_t = [t for t in trades_data['trades'] if t.get('status') == 'open']
    closed_t = [t for t in trades_data['trades'] if t.get('status') == 'closed']

    print(f'\nOpen: {len(open_t)} | Closed: {len(closed_t)}')

    # Get current prices
    print('\n[Step 1] Fetching current prices (TW + US)...')
    current = get_current_prices()
    print(f'Got prices for {len(current)} market-stock pairs')

    # Analyze each open position
    print('\n[Step 2] Position Analysis:')
    exits_to_run = []
    overbought_profit = []

    for t in open_t:
        sym = t['symbol']
        mkt = t.get('market', 'TW')
        key = (mkt, sym)

        if key not in current:
            print(f'  {mkt}:{sym}: No price data, skipping')
            continue

        cur = current[key]['price']
        entry = t['entry_price']
        target = t.get('target_price', entry * 1.15 if mkt == 'TW' else entry + 15)
        stop = t.get('stop_loss', entry * 0.90 if mkt == 'TW' else entry - 10)
        rsi = current[key]['rsi']
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
        if mkt == 'US':
            # 美股：用絕對金額停利/停損
            if pnl_abs >= US_TAKE_PROFIT_AMOUNT:
                reason = 'take_profit_us'
            elif pnl_abs <= -US_STOP_LOSS_AMOUNT:
                reason = 'stop_loss_us'
            elif rsi > 85 and pnl_pct > 3:
                reason = f'overbought_lock_profit_RSI{int(rsi)}_pnl{pnl_pct:.1f}'
        else:
            # 台股：用百分比停利/停損
            if cur >= target:
                reason = 'take_profit_target'
            elif cur <= stop:
                reason = 'stop_loss'
            elif rsi > OVERBOUGHT_EXIT_RSI and pnl_pct > OVERBOUGHT_PROFIT_LOCK_PCT:
                reason = f'overbought_lock_profit_RSI{int(rsi)}_pnl{pnl_pct:.1f}'

        # 通用條件
        if pnl_pct > BIG_GAIN_TAKE_PROFIT_PCT:
            reason = f'big_gain_take_profit_{pnl_pct:.1f}'
        elif days_held > MAX_HOLD_DAYS:
            reason = f'max_hold_days_{days_held:.0f}'

        print(f'\n  {mkt}:{sym} {t.get("name","")}')
        print(f'    Entry: ${entry:.2f} | Current: ${cur:.2f} | RSI: {rsi:.0f}')
        print(f'    PnL: {pnl_pct:+.1f}% (${pnl_abs:+,.0f}) | Days held: {days_held:.1f}')
        print(f'    Target: ${target:.2f} ({dist_target:+.1f}%) | Stop: ${stop:.2f} ({dist_stop:+.1f}%)')

        if reason:
            print(f'    >>> EXIT TRIGGER: {reason}')
            exits_to_run.append((t, reason, cur, pnl_pct, pnl_abs))
        elif pnl_pct > 5:
            overbought_profit.append((f'{mkt}:{sym}', pnl_pct, rsi, dist_target))

    # Execute exits
    print(f'\n[Step 3] Executing {len(exits_to_run)} exits...')
    for t, reason, cur, pnl_pct, pnl_abs in exits_to_run:
        t['status'] = 'closed'
        t['exit_price'] = cur
        t['exit_reason'] = reason
        t['exit_time'] = time.strftime('%Y-%m-%d %H:%M:%S')
        t['pnl'] = round(pnl_abs, 0)
        t['pnl_pct'] = round(pnl_pct, 2)
        mkt = t.get('market', 'TW')
        print(f'  EXITED {mkt}:{t["symbol"]}: {reason} -> ${cur:.2f} ({pnl_pct:+.1f}%)')

    # Count positions per stock (per market)
    from collections import Counter
    open_now = [t for t in trades_data['trades'] if t.get('status') == 'open']
    sym_counts = Counter((t.get('market', 'TW'), t['symbol']) for t in open_now)

    for (mkt, sym), count in sym_counts.items():
        if count > MAX_POSITIONS_PER_STOCK:
            print(f'\n[Step 4] Excess positions {mkt}:{sym} ({count}口) — reducing to {MAX_POSITIONS_PER_STOCK}口')
            same_sym = [t for t in open_now
                        if t.get('market', 'TW') == mkt and t['symbol'] == sym]
            same_sym.sort(key=lambda x: x.get('timestamp', ''))
            excess = count - MAX_POSITIONS_PER_STOCK
            for t in same_sym[:excess]:
                key = (mkt, t['symbol'])
                cur = current.get(key, {}).get('price', t['entry_price'])
                pnl_pct = (cur - t['entry_price']) / t['entry_price'] * 100
                pnl_abs = (cur - t['entry_price']) * t.get('shares', 0)
                t['status'] = 'closed'
                t['exit_price'] = cur
                t['exit_reason'] = 'excess_positions_reduced'
                t['exit_time'] = time.strftime('%Y-%m-%d %H:%M:%S')
                t['pnl'] = round(pnl_abs, 0)
                t['pnl_pct'] = round(pnl_pct, 2)
                print(f'  Closed {mkt}:{t["symbol"]} (excess): ${t["entry_price"]:.2f} -> ${cur:.2f} ({pnl_pct:+.1f}%)')

    # Recalculate stats from scratch (P0 fix: stats were computed but never saved)
    closed_now = [t for t in trades_data['trades'] if t.get('status') == 'closed']
    open_now = [t for t in trades_data['trades'] if t.get('status') == 'open']
    wins = [t for t in closed_now if t.get('pnl', 0) > 0]
    losses = [t for t in closed_now if t.get('pnl', 0) <= 0]
    total_pnl = sum(t.get('pnl', 0) for t in closed_now)
    wr = len(wins) / len(closed_now) * 100 if closed_now else 0
    trades_data['stats'] = {
        'total': len(closed_now),
        'wins': len(wins),
        'losses': len(losses),
        'total_pnl': round(total_pnl, 0)
    }

    # Update open positions with current_price and pnl_pct (P0 fix: US prices missing)
    for t in open_now:
        sym = t['symbol']
        mkt = t.get('market', 'TW')
        key = (mkt, sym)
        if key in current:
            cur = current[key]['price']
            t['current_price'] = cur
            if t['entry_price'] > 0:
                t['pnl_pct'] = round((cur - t['entry_price']) / t['entry_price'] * 100, 2)
                t['current_rsi'] = current[key]['rsi']

    save_trades(trades_data)

    tw_open = [t for t in open_now if t.get('market', 'TW') == 'TW']
    us_open = [t for t in open_now if t.get('market') == 'US']

    print(f'\n=== Final Summary ===')
    print(f'Open: {len(open_now)} (TW:{len(tw_open)}/US:{len(us_open)}) | Closed: {len(closed_now)}')
    print(f'Win Rate: {wr:.0f}% ({len(wins)}W/{len(losses)}L)')
    print(f'Total PnL: ${total_pnl:+,.0f}')

    if overbought_profit:
        print(f'\n=== Overbought with Profit (Watch) ===')
        for sym, pnl, rsi, dist in overbought_profit[:10]:
            print(f'  {sym}: +{pnl:.1f}% profit, RSI {rsi:.0f}, {dist:+.1f}% to target')

    return trades_data

if __name__ == '__main__':
    run_daily_review()