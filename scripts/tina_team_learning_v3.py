# -*- coding: utf-8 -*-
"""
Tina Brain - 全團隊學習與回測系統 v3.0
======================================
使用優化後的進場參數
"""
import sqlite3, json, sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
DATA = WORKSPACE / "data"

# ========== 已優化參數 ==========
TEAMS = {
    'NANA': {
        'name': 'NANA 波段操作團隊',
        'strategy': 'RSI 35-50 + MA20>MA60 多頭排列（優化版）',
        'rsi_min': 35, 'rsi_max': 50,
        'macd_min': 0,
        'filter': 'ma20_above_ma60',
        'watch': ['2464.TW','3324.TWO','3037.TW','1590.TW'],
    },
    'LEO': {
        'name': 'LEO AI科技波段團隊',
        'strategy': 'RSI 25-40 + 量能>1.5x + MACD多頭（優化版）',
        'rsi_min': 25, 'rsi_max': 40,
        'macd_min': 0,
        'filter': 'vol_1.5x',
        'watch': ['3711.TW','8299.TW','2467.TW','5269.TW','2359.TW','4966.TWO'],
    },
    'MAGGY': {
        'name': 'MAGGY 美股AI團隊',
        'strategy': 'RSI 25-40 + MACD多頭（優化版）',
        'rsi_min': 25, 'rsi_max': 40,
        'macd_min': 0,
        'filter': 'none',
        'watch': ['MSFT','CRM'],
    },
    'SHERKY': {
        'name': 'SHERKY ETF/能源團隊',
        'strategy': 'RSI<45 + 電力基建',
        'rsi_min': 0, 'rsi_max': 45,
        'macd_min': 0,
        'filter': 'none',
        'watch': ['1519.TW'],
    },
}


def backtest_optimized(sym, rsi_min, rsi_max, macd_min, filter_name, days=365):
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

    s = pd.Series(prices)
    delta = s.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi_s = 100 - (100 / (1 + rs))

    ema12 = s.ewm(span=12, adjust=False).mean()
    ema26 = s.ewm(span=26, adjust=False).mean()
    macd_l = ema12 - ema26
    macd_sig = macd_l.ewm(span=9, adjust=False).mean()
    macd_h = macd_l - macd_sig

    sma20 = s.ewm(span=20, adjust=False).mean()
    sma60 = s.ewm(span=60, adjust=False).mean()
    avg_vol = pd.Series(vols).rolling(20).mean()

    tr = pd.Series([max(highs[i]-lows[i], abs(highs[i]-prices[i-1]) if i>0 else 0) for i in range(len(prices))])
    atr = tr.ewm(span=14, adjust=False).mean()

    wins, total, entry_count = 0, 0, 0
    gains_list, losses_list = [], []

    for i in range(60, len(prices) - 10):
        rsi_i = float(rsi_s.iloc[i])
        macd_i = float(macd_h.iloc[i])

        if not (rsi_min <= rsi_i <= rsi_max):
            continue
        if macd_i <= macd_min:
            continue

        if filter_name == 'ma20_above_ma60':
            if not (float(sma20.iloc[i]) > float(sma60.iloc[i])):
                continue
        elif filter_name == 'vol_1.5x':
            if vols[i] <= float(avg_vol.iloc[i]) * 1.5:
                continue

        entry_count += 1
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
        return {'entries': entry_count, 'trades': 0, 'win_rate': 0.0, 'avg_gain': 0, 'avg_loss': 0, 'pf': 0}

    wr = wins / total * 100
    avg_g = sum(gains_list) / len(gains_list) if gains_list else 0
    avg_l = abs(sum(losses_list) / len(losses_list)) if losses_list else 0
    pf = round(avg_g / avg_l, 2) if avg_l > 0 else 999

    return {'entries': entry_count, 'trades': total, 'win_rate': round(wr, 1), 'avg_gain': round(avg_g, 1), 'avg_loss': round(avg_l, 1), 'pf': pf}


def main():
    print('='*70)
    print('  Tina Brain - 全團隊學習與回測系統 v3.0（優化版）')
    print('  ' + datetime.now().strftime('%Y-%m-%d %H:%M'))
    print('='*70)
    print()

    all_results = {}
    total_trades = 0

    for team_name, cfg in TEAMS.items():
        print(f'[{team_name}] {cfg["name"]}')
        print(f'  Strategy: {cfg["strategy"]}')
        print(f'  Entry: RSI {cfg["rsi_min"]}-{cfg["rsi_max"]} + filter={cfg["filter"]}')

        results = []
        for sym in cfg['watch']:
            bt = backtest_optimized(sym, cfg['rsi_min'], cfg['rsi_max'], cfg['macd_min'], cfg['filter'], 365)
            if bt:
                print(f'    {sym}: WR {bt["win_rate"]}% ({bt["trades"]}筆) PF:{bt["pf"]} | entries:{bt["entries"]}')
                results.append({'symbol': sym, 'backtest': bt})
            else:
                print(f'    {sym}: no data')

        team_trades = sum(r['backtest']['trades'] for r in results if r.get('backtest'))
        total_trades += team_trades

        bts = [r['backtest'] for r in results if r.get('backtest') and r['backtest']['trades'] > 0]
        if bts:
            wins_sum = sum(b['win_rate']/100 * b['trades'] for b in bts)
            overall_wr = round(wins_sum / team_trades * 100, 1) if team_trades > 0 else 0
            print(f'  Team WR: {overall_wr}% ({team_trades}筆)')
        else:
            print(f'  Team WR: N/A (0 trades)')

        all_results[team_name] = {'stocks': results, 'strategy': cfg['strategy']}
        print()

    print('='*70)
    print(f'  Total trades: {total_trades}')
    print('='*70)

    with open(DATA / 'team_learning_results.json', 'w', encoding='utf-8') as f:
        json.dump({'date': datetime.now().strftime('%Y-%m-%d %H:%M'), 'teams': all_results, 'total_trades': total_trades}, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()