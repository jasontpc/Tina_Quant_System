# -*- coding: utf-8 -*-
import json, sys
from pathlib import Path
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
LEO_DIR = BASE_DIR / 'teams' / 'leadtrades' / 'leos'
BASELINE_DATE = '2026-05-07'
MAX_HOLDING_DAYS = 3
PERF_FILE = LEO_DIR / 'leo_performance_since_baseline.json'

def load_leos_trades():
    with open(LEO_DIR / 'leos_trades.json', encoding='utf-8') as f:
        return json.load(f)

def parse_date_str(ts):
    """Return date string YYYY-MM-DD or None"""
    if not ts:
        return None
    # Handle ISO with time: "2026-05-07T10:30:00" -> "2026-05-07"
    return ts[:10] if 'T' in ts else (ts[:10] if '-' in ts else None)

def calc_holding_days(ts_str):
    ds = parse_date_str(ts_str)
    if ds is None:
        return 999
    try:
        entry = datetime.strptime(ds, '%Y-%m-%d')
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return (today - entry).days
    except:
        return 999

def calc_performance():
    data = load_leos_trades()
    trades = data.get('trades', [])
    historical = data.get('stats', {})

    open_or_recent = []
    for t in trades:
        ts = t.get('timestamp', '')
        exit_t = t.get('exit_time', '')

        entry_ds = parse_date_str(ts)
        exit_ds = parse_date_str(exit_t) if exit_t else None

        # Skip: both before baseline
        if entry_ds and entry_ds < BASELINE_DATE and exit_ds and exit_ds < BASELINE_DATE:
            continue

        open_or_recent.append(t)

    still_open = [t for t in open_or_recent
                  if not t.get('exit_time') or t.get('exit_time') == '']

    fresh_positions = []
    aged_positions = []
    for t in still_open:
        days = calc_holding_days(t.get('timestamp', ''))
        if days <= MAX_HOLDING_DAYS:
            fresh_positions.append(t)
        else:
            aged_positions.append(t)

    exited = [t for t in open_or_recent
              if t.get('exit_time') and t.get('exit_time') != '']

    wins = sum(1 for t in exited if t.get('pnl_pct', 0) > 0)
    losses = sum(1 for t in exited if t.get('pnl_pct', 0) < 0)
    win_rate = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0.0
    total_pnl = sum(t.get('pnl', 0) or 0 for t in exited)
    fresh_invested = sum(t.get('amount', 0) for t in fresh_positions)
    total_invested = sum(t.get('amount', 0) for t in still_open)

    return {
        'baseline': BASELINE_DATE,
        'calculated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'since_baseline': {
            'open_count': len(still_open),
            'open_fresh_count': len(fresh_positions),
            'open_aged_count': len(aged_positions),
            'exited_count': len(exited),
            'total_count': len(fresh_positions) + len(exited),
            'wins': wins,
            'losses': losses,
            'win_rate': round(win_rate, 1),
            'total_pnl': round(total_pnl, 0),
            'open_invested': round(fresh_invested, 0),
            'open_invested_all': round(total_invested, 0),
            'max_holding_days': MAX_HOLDING_DAYS,
        },
        'aged_sample': [{'symbol': t['symbol'], 'timestamp': t.get('timestamp'), 'days': calc_holding_days(t.get('timestamp',''))} for t in aged_positions[:5]],
        'historical_reference': {
            'total': historical.get('total', 0),
            'wins': historical.get('wins', 0),
            'losses': historical.get('losses', 0),
            'win_rate': round(historical.get('wins', 0) / historical.get('total', 1) * 100, 1),
            'total_pnl': historical.get('total_pnl', 0),
        },
    }

def save_perf(result):
    with open(PERF_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

def main():
    result = calc_performance()
    save_perf(result)

    sb = result['since_baseline']
    hr = result['historical_reference']

    print(f'=== Leo v6.5 Performance Report ===')
    print(f'Baseline: {BASELINE_DATE} | Max hold: {MAX_HOLDING_DAYS} days')
    print(f'Calculated: {result["calculated_at"]}')
    print()
    print(f'[Since {BASELINE_DATE}]')
    print(f'  Open (fresh <= {MAX_HOLDING_DAYS}d): {sb["open_fresh_count"]}')
    print(f'  Open (aged > {MAX_HOLDING_DAYS}d, excluded): {sb["open_aged_count"]}')
    print(f'  Exited: {sb["exited_count"]}')
    print(f'  Total counted: {sb["total_count"]}')
    if sb['exited_count'] > 0:
        print(f'  Win rate: {sb["wins"]}/{sb["wins"]+sb["losses"]} = {sb["win_rate"]}%')
        print(f'  PnL: {sb["total_pnl"]}')
    print(f'  Fresh invested: {sb["open_invested"]}')
    print(f'  Total invested (all): {sb["open_invested_all"]}')
    print()
    print(f'[Historical Reference]')
    print(f'  Total: {hr["total"]} | WR: {hr["win_rate"]}% | PnL: {hr["total_pnl"]}')
    if result.get('aged_sample'):
        print(f'  Aged samples:')
        for s in result['aged_sample']:
            print(f'    {s["symbol"]} ts={s["timestamp"]} held={s["days"]}d')
    print(f'\n[OK] saved to {PERF_FILE}')

if __name__ == '__main__':
    main()