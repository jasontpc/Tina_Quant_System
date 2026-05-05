# -*- coding: utf-8 -*-
"""Vogel v10 - 擴展進場條件 × ATR/固定混合止盈 """
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

            dir_, reason, tp_mode = None, None, 'atr'

            # A. BB Lower touch (LONG)
            if dir_ is None and d.get('bb_lower') and ep <= d['bb_lower'] and d.get('rsi_14') and d['rsi_14'] < params.get('rsi_long_max', 50):
                dir_, reason = 'LONG', f'BB_L_RSI{d["rsi_14"]:.0f}'

            # B. BB Upper touch (SHORT)
            if dir_ is None and d.get('bb_upper') and ep >= d['bb_upper'] and d.get('rsi_14') and d['rsi_14'] > params.get('rsi_short_min', 40):
                dir_, reason = 'SHORT', f'BB_U_RSI{d["rsi_14"]:.0f}'

            # C. RSI oversold bounce (LONG)
            if dir_ is None and i > 0 and d.get('rsi_14') and data[i-1].get('rsi_14'):
                prev_rsi = data[i-1]['rsi_14']
                if prev_rsi < 30 <= d['rsi_14'] < params.get('rsi_bounce_max', 45):
                    dir_, reason = 'LONG', f'RSI_bo_{prev_rsi:.0f}_{d["rsi_14"]:.0f}'

            # D. MACD bullish cross (LONG)
            if dir_ is None and i > 0 and d.get('macd_hist') and data[i-1].get('macd_hist') is not None:
                if data[i-1]['macd_hist'] <= 0 < d['macd_hist'] and d.get('rsi_14') and d['rsi_14'] < params.get('rsi_macd_long', 55):
                    dir_, reason = 'LONG', f'MACD_bull_RSI{d["rsi_14"]:.0f}'

            # E. MACD bearish cross (SHORT)
            if dir_ is None and i > 0 and d.get('macd_hist') and data[i-1].get('macd_hist') is not None:
                if data[i-1]['macd_hist'] >= 0 > d['macd_hist'] and d.get('rsi_14') and d['rsi_14'] > params.get('rsi_macd_short', 45):
                    dir_, reason = 'SHORT', f'MACD_bear_RSI{d["rsi_14"]:.0f}'

            # F. KDJ oversold bounce (LONG)
            if dir_ is None and i > 0 and d.get('kdj_j') and data[i-1].get('kdj_j') is not None:
                if data[i-1]['kdj_j'] < 20 and d['kdj_j'] > data[i-1]['kdj_j'] and d['kdj_j'] < 40 and d.get('rsi_14') and d['rsi_14'] < 50:
                    dir_, reason = 'LONG', f'KDJ_bo_J{d["kdj_j"]:.0f}'

            # G. CCI oversold (LONG)
            if dir_ is None and d.get('cci_20') is not None and d['cci_20'] < -100 and d.get('rsi_14') and d['rsi_14'] < 45:
                dir_, reason = 'LONG', f'CCI_ov_{d["cci_20"]:.0f}'

            # H. Williams %R oversold (LONG)
            if dir_ is None and d.get('williams_r_14') is not None and d['williams_r_14'] < -80 and d.get('rsi_14') and d['rsi_14'] < 45:
                dir_, reason = 'LONG', f'WillR_ov_{d["williams_r_14"]:.0f}'

            # I. SMA golden cross (LONG)
            if dir_ is None and d.get('sma_20') and d.get('close') and data[i-1].get('sma_20') and data[i-1].get('close'):
                if data[i-1]['close'] < data[i-1]['sma_20'] and d['close'] > d['sma_20'] and d.get('rsi_14') and d['rsi_14'] < 50:
                    dir_, reason = 'LONG', f'SMA_gc_RSI{d["rsi_14"]:.0f}'

            # J. SMA death cross (SHORT)
            if dir_ is None and d.get('sma_20') and d.get('close') and data[i-1].get('sma_20') and data[i-1].get('close'):
                if data[i-1]['close'] > data[i-1]['sma_20'] and d['close'] < d['sma_20'] and d.get('rsi_14') and d['rsi_14'] > 50:
                    dir_, reason = 'SHORT', f'SMA_dc_RSI{d["rsi_14"]:.0f}'

            # K. RSI overbought reversal (SHORT)
            if dir_ is None and i > 0 and d.get('rsi_14') and data[i-1].get('rsi_14'):
                prev_rsi = data[i-1]['rsi_14']
                if prev_rsi > 70 >= d['rsi_14'] > params.get('rsi_ob_max', 55):
                    dir_, reason = 'SHORT', f'RSI_ob_{prev_rsi:.0f}_{d["rsi_14"]:.0f}'

            # L. BB middle bounce SHORT (from BULL_ZONE)
            if dir_ is None and d.get('bb_upper') and d.get('bb_middle') and d.get('zone') == 'BULL_ZONE' and d.get('close') and d.get('rsi_14'):
                if d['close'] >= d['bb_middle'] * (1 - params.get('bb_mid_pct', 0.005)) and d['rsi_14'] > 60:
                    dir_, reason = 'SHORT', f'BB_mid_RSI{d["rsi_14"]:.0f}'
                    tp_mode = 'fixed'
                    tp_points = params.get('tp_fixed', 200)

            if dir_:
                sl_atr = params.get('sl_atr', 2.0)
                tp_atr = params.get('tp_atr', 3.0)
                mh = params.get('max_hold_long' if dir_ == 'LONG' else 'max_hold_short', 7)
                tp = ep + tp_atr * atr if dir_ == 'LONG' else ep - tp_atr * atr
                if tp_mode == 'fixed':
                    tp = ep + tp_points if dir_ == 'LONG' else ep - tp_points
                pos = {
                    'entry_date': d['date'], 'dir': dir_, 'ep': ep, 'atr': atr,
                    'sl': ep - sl_atr * atr if dir_ == 'LONG' else ep + sl_atr * atr,
                    'tp': tp,
                    'max_hold': mh, 'reason': reason, 'tp_mode': tp_mode
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

            sl_hit = (pos['dir'] == 'LONG' and d['low'] <= pos['sl']) or (pos['dir'] == 'SHORT' and d['high'] >= pos['sl'])
            if sl_hit:
                xp = pos['sl']
                pnl = (xp - pos['ep']) / pos['ep'] * 100 if pos['dir'] == 'LONG' else (pos['ep'] - xp) / pos['ep'] * 100
                trades.append({'entry_date': pos['entry_date'], 'exit_date': d['date'], 'direction': pos['dir'],
                               'entry_price': pos['ep'], 'exit_price': xp, 'pnl_pct': pnl,
                               'result': 'STOP_LOSS', 'held_days': held, 'reason': pos['reason']})
                pos = None; continue

            tp_hit = (pos['dir'] == 'LONG' and d['high'] >= pos['tp']) or (pos['dir'] == 'SHORT' and d['low'] <= pos['tp'])
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
    # Score: balance between total return and trade count
    score_val = total * (rr ** 0.3) * min(len(trades) / 15, 2.5)
    return {
        'trades': len(trades), 'win_rate': round(wr, 1),
        'avg_win': round(avg_win, 2), 'avg_loss': round(avg_loss, 2),
        'rr': round(rr, 2), 'total': round(total, 1), 'score': round(score_val, 2),
        'tp': len([t for t in trades if t['result'] == 'TAKE_PROFIT']),
        'sl': len([t for t in trades if t['result'] == 'STOP_LOSS']),
        'mh': len([t for t in trades if t['result'] == 'MAX_HOLD']),
    }

def run():
    print('=== Vogel v10 - 高頻多條件優化 ===\n')
    data = load_db()
    print(f'Loaded {len(data)} days')

    base = {
        'sl_atr': 2.0, 'tp_atr': 3.0,
        'rsi_long_max': 50, 'rsi_short_min': 40,
        'rsi_bounce_max': 45, 'rsi_macd_long': 55, 'rsi_macd_short': 45,
        'rsi_ob_max': 55, 'bb_mid_pct': 0.005, 'tp_fixed': 200,
        'max_hold_long': 7, 'max_hold_short': 5,
    }

    # Grid: tp_atr × sl_atr × max_hold_short × max_hold_long
    configs = []
    for tp in [1.5, 2.0, 2.5, 3.0]:
        for sl in [1.0, 1.5, 2.0]:
            for mh_l in [3, 5, 7]:
                for mh_s in [2, 3, 5]:
                    configs.append({'tp_atr': tp, 'sl_atr': sl, 'max_hold_long': mh_l, 'max_hold_short': mh_s})

    print(f'Testing {len(configs)} configurations...')
    results = []
    for cfg in configs:
        p = {**base, **cfg}
        trades = backtest(data, p)
        s = score(trades)
        if s:
            s.update(cfg)
            results.append(s)

    results.sort(key=lambda x: x['score'], reverse=True)

    print(f'\nTop 15 by Score (Total × R:R^0.3 × min(trades/15, 2.5)):')
    print(f'{"#":<3} {"TP":<4} {"SL":<4} {"MH_L":<5} {"MH_S":<5} {"Trades":<7} {"WR%":<6} {"AvgWin":<7} {"R:R":<5} {"Total%":<7} {"TP_hits":<8} {"Score":<6}')
    print('-' * 80)
    for i, r in enumerate(results[:15]):
        print(f'{i+1:<3} {r["tp_atr"]:<4} {r["sl_atr"]:<4} {r["max_hold_long"]:<5} {r["max_hold_short"]:<5} {r["trades"]:<7} {r["win_rate"]:<6.1f} {r["avg_win"]:<7.2f} {r["rr"]:<5.2f} {r["total"]:<7.1f} {r["tp"]:<8} {r["score"]:<6.1f}')

    if not results: return

    best = results[0]
    print(f'\n=== BEST: TP={best["tp_atr"]}x SL={best["sl_atr"]}x L={best["max_hold_long"]} S={best["max_hold_short"]} ===')
    print(f'Trades: {best["trades"]} | WR: {best["win_rate"]:.1f}% | R:R: {best["rr"]} | Total: {best["total"]:+.1f}% | TP_hits: {best["tp"]}')

    p = {**base, 'tp_atr': best['tp_atr'], 'sl_atr': best['sl_atr'],
         'max_hold_long': best['max_hold_long'], 'max_hold_short': best['max_hold_short']}
    trades = backtest(data, p)

    print(f'\n=== All Trades ({len(trades)}) ===')
    for i, t in enumerate(sorted(trades, key=lambda x: x['entry_date']), 1):
        print(f'{i:<3} {t["entry_date"]:<12} {t["direction"]:<5} {t["entry_price"]:>8.0f} {t["exit_price"]:>8.0f} {t["pnl_pct"]:>+7.2f}% {t["result"]:<12} {t["held_days"]}d {t["reason"]}')

    # Reason breakdown
    reasons = {}
    for t in trades:
        r = t['reason']
        if r not in reasons: reasons[r] = {'count': 0, 'wins': 0, 'pnls': []}
        reasons[r]['count'] += 1
        if t['pnl_pct'] > 0: reasons[r]['wins'] += 1
        reasons[r]['pnls'].append(t['pnl_pct'])
    print(f'\n=== Entry Reason Stats ===')
    for r, s in sorted(reasons.items(), key=lambda x: -x[1]['count']):
        wr = s['wins']/s['count']*100
        avg = sum(s['pnls'])/len(s['pnls'])
        print(f'  {r:<20}: {s["count"]} trades, WR={wr:.0f}%, avg={avg:+.2f}%')

    # Equity curve
    equity = 100000
    print(f'\n=== Equity Curve ===')
    for t in sorted(trades, key=lambda x: x['entry_date']):
        equity *= (1 + t['pnl_pct']/100)
        print(f'{t["entry_date"]} {t["direction"]} {t["pnl_pct"]:>+7.2f}% → ${equity:,.0f}')

    out = os.path.join(VOGEL_DIR, 'v10_results.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump({'best': best, 'all_results': results[:50], 'trades': trades}, f, ensure_ascii=False, indent=2)
    print(f'\nSaved: {out}')
    print('\n=== Vogel v10 Done ===')

if __name__ == '__main__':
    run()