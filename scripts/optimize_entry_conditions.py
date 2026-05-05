# -*- coding: utf-8 -*-
"""
optimize_entry_conditions.py
============================
分析低勝率原因，測試不同進場參數組合
找出最優化進場條件
"""
import sqlite3, json, sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
DATA = WORKSPACE / "data"

RSI_RANGES = [(25, 40), (30, 45), (35, 50), (40, 55), (35, 45)]
EXTRA_FILTERS = [
    ('none', '無過濾'),
    ('ma20_above_ma60', 'MA20>MA60'),
    ('vol_1.5x', '量能>1.5x'),
    ('both', '多頭+量能'),
]


def compute_rsi(prices):
    s = pd.Series(prices)
    delta = s.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def test_entry(sym, rsi_min, rsi_max, extra_filter, days=365):
    conn = sqlite3.connect(str(DATA / 'yfinance.db'))
    c = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    c.execute("SELECT date, close, high, low, volume FROM daily_ohlcv WHERE symbol=? AND date>=? ORDER BY date", (sym, cutoff))
    rows = c.fetchall()
    conn.close()

    if len(rows) < 60:
        return None

    dates = [r[0] for r in rows]
    prices = [r[1] for r in rows]
    highs = [r[2] for r in rows]
    lows = [r[3] for r in rows]
    vols = [r[4] for r in rows]

    rsi_s = compute_rsi(prices)

    s = pd.Series(prices)
    ema12 = s.ewm(span=12, adjust=False).mean()
    ema26 = s.ewm(span=26, adjust=False).mean()
    macd_l = ema12 - ema26
    macd_s = macd_l.ewm(span=9, adjust=False).mean()
    macd_h = macd_l - macd_s

    sma20 = s.ewm(span=20, adjust=False).mean()
    sma60 = s.ewm(span=60, adjust=False).mean()

    tr = pd.Series([max(highs[i]-lows[i], abs(highs[i]-prices[i-1]) if i>0 else 0) for i in range(len(prices))])
    atr = tr.ewm(span=14, adjust=False).mean()
    avg_vol = pd.Series(vols).rolling(20).mean()

    wins, total = 0, 0
    gains_list, losses_list = [], []

    for i in range(60, len(prices) - 10):
        rsi_i = float(rsi_s.iloc[i])
        macd_i = float(macd_h.iloc[i])

        if not (rsi_min <= rsi_i <= rsi_max):
            continue
        if macd_i <= 0:
            continue

        if extra_filter == 'ma20_above_ma60':
            if not (float(sma20.iloc[i]) > float(sma60.iloc[i])):
                continue
        elif extra_filter == 'vol_1.5x':
            if vols[i] <= float(avg_vol.iloc[i]) * 1.5:
                continue
        elif extra_filter == 'both':
            if not (float(sma20.iloc[i]) > float(sma60.iloc[i]) and vols[i] > float(avg_vol.iloc[i]) * 1.5):
                continue

        entry = prices[i]
        sl = entry - float(atr.iloc[i]) * 1.5
        tp = entry + float(atr.iloc[i]) * 3.0

        for j in range(i+1, min(i+11, len(prices))):
            if prices[j] <= sl:
                total += 1
                losses_list.append((sl - entry) / entry * 100)
                break
            elif prices[j] >= tp:
                wins += 1
                total += 1
                gains_list.append((tp - entry) / entry * 100)
                break

    if total == 0:
        return None

    wr = wins / total * 100
    avg_g = sum(gains_list) / len(gains_list) if gains_list else 0
    avg_l = abs(sum(losses_list) / len(losses_list)) if losses_list else 0

    return {
        'trades': total, 'win_rate': round(wr, 1),
        'avg_gain': round(avg_g, 1), 'avg_loss': round(avg_l, 1),
        'pf': round(avg_g / avg_l, 2) if avg_l > 0 else 999,
    }


def main():
    print('='*60)
    print('  Tina Brain - 進場條件優化系統')
    print('  ' + datetime.now().strftime('%Y-%m-%d %H:%M'))
    print('='*60)

    teams = {
        'LEO': ['5269.TW', '4966.TWO', '2359.TW', '2467.TW', '3711.TW'],
        'MAGGY': ['MSFT', 'CRM'],
        'NANA': ['3324.TWO', '1590.TW'],
    }

    all_results = {}

    for team, syms in teams.items():
        print(f'\n[{team}]')
        best = None
        best_wr = 0

        for rsi_min, rsi_max in RSI_RANGES:
            for filter_name, filter_desc in EXTRA_FILTERS:
                team_results = []
                for sym in syms:
                    r = test_entry(sym, rsi_min, rsi_max, filter_name, 365)
                    if r and r['trades'] > 0:
                        team_results.append((sym, r))

                if not team_results:
                    continue

                total_trades = sum(x[1]['trades'] for x in team_results)
                if total_trades < 5:
                    continue

                wins_sum = sum(x[1]['win_rate']/100 * x[1]['trades'] for x in team_results)
                overall_wr = wins_sum / total_trades * 100

                if overall_wr > best_wr:
                    best_wr = overall_wr
                    best = {
                        'rsi_min': rsi_min, 'rsi_max': rsi_max,
                        'filter': filter_name, 'filter_desc': filter_desc,
                        'stocks': dict(team_results),
                        'total_trades': total_trades,
                        'overall_wr': round(overall_wr, 1),
                    }

        if best:
            print(f'  Best: RSI {best["rsi_min"]}-{best["rsi_max"]} + {best["filter_desc"]}')
            print(f'  WR: {best["overall_wr"]}% ({best["total_trades"]}筆)')
            for sym, r in best['stocks'].items():
                print(f'    {sym}: {r["win_rate"]}% ({r["trades"]}筆) PF:{r["pf"]}')
            all_results[team] = best
        else:
            print(f'  No profitable combo')

    # Save suggestions
    suggestions = {team: {k: v for k, v in r.items() if k not in ['stocks']} for team, r in all_results.items()}
    for team, r in all_results.items():
        suggestions[team]['stock_details'] = {sym: {k: v for k, v in data.items() if k != 'trades'} for sym, data in r.get('stocks', {}).items()}

    with open(DATA / 'optimized_entry_rules.json', 'w', encoding='utf-8') as f:
        json.dump(suggestions, f, ensure_ascii=False, indent=2)

    print()
    print(f'Saved to: data/optimized_entry_rules.json')


if __name__ == '__main__':
    main()