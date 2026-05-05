# -*- coding: utf-8 -*-
"""
CPO 學習引擎 - 每週自動學習
==========================
CPO 散熱產業專屬回測 + 參數優化
"""
import sqlite3, json, sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
DATA = WORKSPACE / "data"
DB = DATA / "yfinance.db"

CPO_WATCH = ['6230.TW','3324.TWO','3653.TW','3711.TW','3017.TW','4908.TW',
             '6120.TW','6592.TW','6278.TWO','6269.TW','2486.TW',
             '3128.TW','5227.TW','6109.TW','6243.TWO','6236.TW']

STRATEGY = {
    'rsi_min': 30, 'rsi_max': 50,
    'macd_min': 0,
    'filter': 'ma20_above_ma60',
    'stop_loss': 1.5, 'take_profit': 3.5
}


def cpo_backtest(sym, params, days=730):
    conn = sqlite3.connect(str(DB))
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

    wins, total = 0, 0
    gains_list, losses_list = [], []

    for i in range(60, len(prices) - 15):
        rsi_i = float(rsi_s.iloc[i])
        macd_i = float(macd_h.iloc[i])
        if not (params['rsi_min'] <= rsi_i <= params['rsi_max']):
            continue
        if macd_i <= params['macd_min']:
            continue
        if params['filter'] == 'ma20_above_ma60':
            if not (float(sma20.iloc[i]) > float(sma60.iloc[i])):
                continue

        entry = prices[i]
        atr = float(pd.Series([max(highs[j]-lows[j], abs(highs[j]-prices[j-1]) if j > 0 else 0) for j in range(max(0,i-13), i+1)]).ewm(span=14, adjust=False).mean().iloc[-1])
        sl = entry - atr * params['stop_loss']
        tp = entry + atr * params['take_profit']

        for j in range(i+1, min(i+16, len(prices))):
            if prices[j] <= sl:
                total += 1; losses_list.append((sl - entry) / entry * 100); break
            elif prices[j] >= tp:
                wins += 1; total += 1; gains_list.append((tp - entry) / entry * 100); break

    if total == 0:
        return None
    wr = wins / total * 100
    avg_g = sum(gains_list) / len(gains_list) if gains_list else 0
    avg_l = sum(losses_list) / len(losses_list) if losses_list else 0
    pf = avg_g / abs(avg_l) if avg_l != 0 else 0
    return {'trades': total, 'win_rate': round(wr, 1), 'wins': wins,
            'avg_gain': round(avg_g, 2), 'avg_loss': round(avg_l, 2), 'pf': round(pf, 2)}


def main():
    print('='*60)
    print('  CPO 散熱產業學習引擎')
    print('  ' + datetime.now().strftime('%Y-%m-%d %H:%M'))
    print('='*60)

    results = []
    for sym in CPO_WATCH:
        bt = cpo_backtest(sym, STRATEGY)
        if bt:
            bt['symbol'] = sym
            results.append(bt)
            icon = '🟢' if bt['win_rate'] >= 60 else ('🟡' if bt['win_rate'] >= 40 else '🔴')
            print(f"  {icon} {sym}: {bt['win_rate']}% ({bt['trades']}筆) PF={bt['pf']}")

    if results:
        total_trades = sum(r['trades'] for r in results)
        total_wins = sum(r['wins'] for r in results)
        wr_all = total_wins / total_trades * 100 if total_trades > 0 else 0
        print(f"\n  總交易: {total_trades} 筆 | 加權勝率: {wr_all:.1f}%")

        with open(DATA / 'cpo_learning_results.json', 'w', encoding='utf-8') as f:
            json.dump({'date': datetime.now().strftime('%Y-%m-%d'), 'results': results}, f, ensure_ascii=False, indent=2)

        top = sorted(results, key=lambda x: -x['win_rate'])[:3]
        print(f"\n  TOP3: {', '.join(r['symbol'] for r in top)}")


if __name__ == '__main__':
    main()