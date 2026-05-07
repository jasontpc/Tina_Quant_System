# -*- coding: utf-8 -*-
"""Vogel v9.0 - 高頻交易引擎（擴展進場條件）"""
import sys, sqlite3, os, json
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
VOGEL_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\vogel'

def load_db():
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'vogel_indicators.db'))
    cur = conn.cursor()
    cur.execute('SELECT date, open, high, low, close, volume, sma_5, sma_10, sma_20, sma_60, sma_120, ema_12, ema_26, bb_upper, bb_middle, bb_lower, rsi_14, rsi_7, rsi_28, macd_line, macd_signal, macd_hist, atr_14, atr_30, kdj_k, kdj_d, kdj_j, williams_r_14, cci_20, zone FROM daily ORDER BY date ASC')
    rows = cur.fetchall()
    conn.close()
    return [{
        'date': r[0], 'open': r[1], 'high': r[2], 'low': r[3], 'close': r[4], 'volume': r[5],
        'sma_5': r[6], 'sma_10': r[7], 'sma_20': r[8], 'sma_60': r[9], 'sma_120': r[10],
        'ema_12': r[11], 'ema_26': r[12],
        'bb_upper': r[13], 'bb_middle': r[14], 'bb_lower': r[15],
        'rsi_14': r[16], 'rsi_7': r[17], 'rsi_28': r[18],
        'macd_line': r[19], 'macd_signal': r[20], 'macd_hist': r[21],
        'atr_14': r[22], 'atr_30': r[23],
        'kdj_k': r[24], 'kdj_d': r[25], 'kdj_j': r[26],
        'williams_r_14': r[27], 'cci_20': r[28], 'zone': r[29]
    } for r in rows]

def backtest(data, params):
    trades = []
    pos = None

    for i, d in enumerate(data):
        if pos is None:
            ep = d['close']
            atr = d.get('atr_14') or 100
            if atr <= 0: atr = 100

            dir_, reason = None, None

            # A. BB Lower touch (LONG)
            if dir_ is None and d.get('bb_lower') and ep <= d['bb_lower'] and d.get('rsi_14') and d['rsi_14'] < params.get('rsi_long_max', 50):
                dir_, reason = 'LONG', f'BB_L_RSI{d["rsi_14"]:.0f}'

            # B. BB Upper touch (SHORT)
            if dir_ is None and d.get('bb_upper') and ep >= d['bb_upper'] and d.get('rsi_14') and d['rsi_14'] > params.get('rsi_short_min', 40):
                dir_, reason = 'SHORT', f'BB_U_RSI{d["rsi_14"]:.0f}'

            # C. RSI oversold bounce
            if dir_ is None and i > 0 and d.get('rsi_14') and data[i-1].get('rsi_14'):
                prev_rsi = data[i-1]['rsi_14']
                if prev_rsi < 30 <= d['rsi_14'] < params.get('rsi_bounce_max', 45):
                    dir_, reason = 'LONG', f'RSI_bo_{prev_rsi:.0f}_{d["rsi_14"]:.0f}'

            # D. MACD bullish cross
            if dir_ is None and i > 0 and d.get('macd_hist') and data[i-1].get('macd_hist') is not None:
                if data[i-1]['macd_hist'] <= 0 < d['macd_hist'] and d.get('rsi_14') and d['rsi_14'] < params.get('rsi_macd_long', 55):
                    dir_, reason = 'LONG', f'MACD_bull_RSI{d["rsi_14"]:.0f}'

            # E. MACD bearish cross
            if dir_ is None and i > 0 and d.get('macd_hist') and data[i-1].get('macd_hist') is not None:
                if data[i-1]['macd_hist'] >= 0 > d['macd_hist'] and d.get('rsi_14') and d['rsi_14'] > params.get('rsi_macd_short', 45):
                    dir_, reason = 'SHORT', f'MACD_bear_RSI{d["rsi_14"]:.0f}'

            # F. KDJ oversold bounce
            if dir_ is None and i > 0 and d.get('kdj_j') and data[i-1].get('kdj_j') is not None:
                if data[i-1]['kdj_j'] < 20 and d['kdj_j'] > data[i-1]['kdj_j'] and d['kdj_j'] < 40 and d.get('rsi_14') and d['rsi_14'] < 50:
                    dir_, reason = 'LONG', f'KDJ_bo_J{d["kdj_j"]:.0f}'

            # G. CCI oversold
            if dir_ is None and d.get('cci_20') is not None and d['cci_20'] < -100 and d.get('rsi_14') and d['rsi_14'] < 45:
                dir_, reason = 'LONG', f'CCI_ov_{d["cci_20"]:.0f}'

            # H. Williams %R oversold
            if dir_ is None and d.get('williams_r_14') is not None and d['williams_r_14'] < -80 and d.get('rsi_14') and d['rsi_14'] < 45:
                dir_, reason = 'LONG', f'WillR_ov_{d["williams_r_14"]:.0f}'

            # I. SMA 20 golden cross (close crosses above SMA20 from below)
            if dir_ is None and d.get('sma_20') and d.get('close') and data[i-1].get('sma_20') and data[i-1].get('close'):
                if data[i-1]['close'] < data[i-1]['sma_20'] and d['close'] > d['sma_20'] and d.get('rsi_14') and d['rsi_14'] < 50:
                    dir_, reason = 'LONG', f'SMA_gc_RSI{d["rsi_14"]:.0f}'

            # J. SMA death cross (close crosses below SMA20 from above)
            if dir_ is None and d.get('sma_20') and d.get('close') and data[i-1].get('sma_20') and data[i-1].get('close'):
                if data[i-1]['close'] > data[i-1]['sma_20'] and d['close'] < d['sma_20'] and d.get('rsi_14') and d['rsi_14'] > 50:
                    dir_, reason = 'SHORT', f'SMA_dc_RSI{d["rsi_14"]:.0f}'

            if dir_:
                sl_atr = params.get('sl_atr', 2.0)
                tp_atr = params.get('tp_atr', 3.0)
                mh = params.get('max_hold_long' if dir_ == 'LONG' else 'max_hold_short', 7)
                pos = {
                    'entry_date': d['date'], 'dir': dir_, 'ep': ep, 'atr': atr,
                    'sl': ep - sl_atr * atr if dir_ == 'LONG' else ep + sl_atr * atr,
                    'tp': ep + tp_atr * atr if dir_ == 'LONG' else ep - tp_atr * atr,
                    'max_hold': mh, 'reason': reason
                }
        else:
            held = (datetime.strptime(d['date'], '%Y-%m-%d') - datetime.strptime(pos['entry_date'], '%Y-%m-%d')).days

            if held >= pos['max_hold']:
                xp = d['close']
                pnl = (xp - pos['ep']) / pos['ep'] * 100 if pos['dir'] == 'LONG' else (pos['ep'] - xp) / pos['ep'] * 100
                trades.append({'entry_date': pos['entry_date'], 'exit_date': d['date'], 'direction': pos['dir'],
                               'entry_price': pos['ep'], 'exit_price': xp, 'pnl_pct': pnl,
                               'result': 'MAX_HOLD', 'held_days': held, 'reason': pos['reason']})
                pos = None; continue

            sl_hit = (pos['dir'] == 'LONG' and d['close'] <= pos['sl']) or (pos['dir'] == 'SHORT' and d['close'] >= pos['sl'])
            if sl_hit:
                xp = pos['sl']
                pnl = (xp - pos['ep']) / pos['ep'] * 100 if pos['dir'] == 'LONG' else (pos['ep'] - xp) / pos['ep'] * 100
                trades.append({'entry_date': pos['entry_date'], 'exit_date': d['date'], 'direction': pos['dir'],
                               'entry_price': pos['ep'], 'exit_price': xp, 'pnl_pct': pnl,
                               'result': 'STOP_LOSS', 'held_days': held, 'reason': pos['reason']})
                pos = None; continue

            tp_hit = (pos['dir'] == 'LONG' and d['close'] >= pos['tp']) or (pos['dir'] == 'SHORT' and d['close'] <= pos['tp'])
            if tp_hit:
                xp = pos['tp']
                pnl = (xp - pos['ep']) / pos['ep'] * 100 if pos['dir'] == 'LONG' else (pos['ep'] - xp) / pos['ep'] * 100
                trades.append({'entry_date': pos['entry_date'], 'exit_date': d['date'], 'direction': pos['dir'],
                               'entry_price': pos['ep'], 'exit_price': xp, 'pnl_pct': pnl,
                               'result': 'TAKE_PROFIT', 'held_days': held, 'reason': pos['reason']})
                pos = None; continue

    return trades

def score(trades):
    if not trades: return None
    wins = [t for t in trades if t['pnl_pct'] > 0]
    losses = [t for t in trades if t['pnl_pct'] <= 0]
    if not wins or not losses: return None
    wr = len(wins) / len(trades) * 100
    avg_win = sum(t['pnl_pct'] for t in wins) / len(wins)
    avg_loss = abs(sum(t['pnl_pct'] for t in losses) / len(losses))
    rr = avg_win / avg_loss if avg_loss > 0 else 0
    total = sum(t['pnl_pct'] for t in trades)
    score_val = total * (rr ** 0.5) * min(len(trades) / 10, 3)
    return {
        'trades': len(trades), 'win_rate': round(wr, 1),
        'avg_win': round(avg_win, 2), 'avg_loss': round(avg_loss, 2),
        'rr': round(rr, 2), 'total': round(total, 1), 'score': round(score_val, 1),
        'tp': len([t for t in trades if t['result'] == 'TAKE_PROFIT']),
        'sl': len([t for t in trades if t['result'] == 'STOP_LOSS']),
        'mh': len([t for t in trades if t['result'] == 'MAX_HOLD']),
    }

def run():
    print('=== Vogel v9.0 - 高頻交易引擎 ===\n')
    data = load_db()
    print(f'Loaded {len(data)} days: {data[0]["date"]} to {data[-1]["date"]}')

    base_params = {
        'sl_atr': 2.0, 'tp_atr': 3.0,
        'rsi_long_max': 50, 'rsi_short_min': 40,
        'rsi_bounce_max': 45, 'rsi_macd_long': 55, 'rsi_macd_short': 45,
        'max_hold_long': 7, 'max_hold_short': 5,
    }

    configs = [
        {'tp_atr': 3.0, 'sl_atr': 2.0, 'max_hold_long': 7, 'max_hold_short': 5},
        {'tp_atr': 2.0, 'sl_atr': 1.5, 'max_hold_long': 5, 'max_hold_short': 3},
        {'tp_atr': 2.5, 'sl_atr': 1.5, 'max_hold_long': 5, 'max_hold_short': 4},
        {'tp_atr': 2.0, 'sl_atr': 1.0, 'max_hold_long': 5, 'max_hold_short': 3},
        {'tp_atr': 1.5, 'sl_atr': 1.5, 'max_hold_long': 7, 'max_hold_short': 5},
        {'tp_atr': 3.0, 'sl_atr': 1.5, 'max_hold_long': 5, 'max_hold_short': 4},
        {'tp_atr': 2.0, 'sl_atr': 2.0, 'max_hold_long': 10, 'max_hold_short': 7},
        {'tp_atr': 1.5, 'sl_atr': 1.0, 'max_hold_long': 3, 'max_hold_short': 2},
    ]

    results = []
    for cfg in configs:
        p = {**base_params, **cfg}
        trades = backtest(data, p)
        s = score(trades)
        if s:
            s.update(cfg)
            results.append(s)

    results.sort(key=lambda x: x['score'], reverse=True)

    print(f'\n{"Config":<30} {"Trades":<7} {"WR%":<6} {"AvgWin":<7} {"R:R":<5} {"Total%":<7} {"TP":<4} {"SL":<4} {"MH":<4} {"Score":<6}')
    print('-' * 85)
    for i, r in enumerate(results[:10]):
        cfg_str = f"TP={r['tp_atr']} SL={r['sl_atr']} L={r['max_hold_long']} S={r['max_hold_short']}"
        print(f'{cfg_str:<30} {r["trades"]:<7} {r["win_rate"]:<6.1f} {r["avg_win"]:<7.2f} {r["rr"]:<5.2f} {r["total"]:<7.1f} {r["tp"]:<4} {r["sl"]:<4} {r["mh"]:<4} {r["score"]:<6.1f}')

    if not results:
        print('No valid results'); return

    best = results[0]
    print(f'\n=== Best: TP={best["tp_atr"]}x SL={best["sl_atr"]}x L={best["max_hold_long"]}S={best["max_hold_short"]} ===')
    print(f'Trades: {best["trades"]} | WR: {best["win_rate"]:.1f}% | R:R: {best["rr"]} | Total: {best["total"]:+.1f}%')

    p = {**base_params, 'tp_atr': best['tp_atr'], 'sl_atr': best['sl_atr'],
         'max_hold_long': best['max_hold_long'], 'max_hold_short': best['max_hold_short']}
    trades = backtest(data, p)

    print(f'\n=== All Trades ({len(trades)}) ===')
    print(f'{"#":<3} {"Date":<12} {"Dir":<5} {"Entry":>8} {"Exit":>8} {"P&L%":>7} {"Result":<10} {"Days":<5} Reason')
    print('-' * 80)
    for i, t in enumerate(sorted(trades, key=lambda x: x['entry_date']), 1):
        print(f'{i:<3} {t["entry_date"]:<12} {t["direction"]:<5} {t["entry_price"]:>8.0f} {t["exit_price"]:>8.0f} {t["pnl_pct"]:>+7.2f}% {t["result"]:<10} {t["held_days"]:<5} {t["reason"]}')

    # Stats by direction
    short_trades = [t for t in trades if t['direction'] == 'SHORT']
    long_trades = [t for t in trades if t['direction'] == 'LONG']
    print(f'\n=== Direction Breakdown ===')
    print(f'SHORT: {len(short_trades)} trades, WR={len([t for t in short_trades if t["pnl_pct"]>0])/len(short_trades)*100:.1f}%' if short_trades else 'SHORT: none')
    print(f'LONG:  {len(long_trades)} trades, WR={len([t for t in long_trades if t["pnl_pct"]>0])/len(long_trades)*100:.1f}%' if long_trades else 'LONG: none')

    # Stats by reason
    reasons = {}
    for t in trades:
        r = t['reason']
        if r not in reasons: reasons[r] = []
        reasons[r].append(t)
    print(f'\n=== Entry Reason Breakdown ===')
    for r, ts in sorted(reasons.items(), key=lambda x: -len(x[1])):
        ws = len([t for t in ts if t['pnl_pct'] > 0])
        print(f'  {r}: {len(ts)} trades, WR={ws/len(ts)*100:.0f}%, avg={sum(t["pnl_pct"] for t in ts)/len(ts):.2f}%')

    out = os.path.join(VOGEL_DIR, 'v9_high_freq_results.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump({'best': best, 'all_results': results, 'trades': trades}, f, ensure_ascii=False, indent=2)
    print(f'\nSaved: {out}')
    print(f'\n=== Vogel v9.0 Done ===')

if __name__ == '__main__':
    run()