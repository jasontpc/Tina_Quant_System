# -*- coding: utf-8 -*-
"""
Vogel v13 - ATR 品質過濾 × 乾淨資料
策略：
  - ATR >= 200（過濾低波動日）
  - 價格過濾：entry_price > 0 且 close > 0
  - WillR/CCI 保持中等寬鬆（而非嚴格）
  - RSI/SMA/MACD/KDJ 確認進場時機
  - TP/SL 寬鬆，提高 TP 命中率
"""
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
            atr = d.get('atr_14') or 0

            # ATR filter
            if atr <= 0 or atr < params.get('atr_min', 200): continue
            # Price filter
            if ep <= 0: continue

            dir_, reason = None, None

            # A. BB Lower touch (LONG)
            if dir_ is None and d.get('bb_lower') and ep <= d['bb_lower'] and d.get('rsi_14') and d['rsi_14'] < params.get('rsi_long_max', 50):
                dir_, reason = 'LONG', f'BB_L_R{d["rsi_14"]:.0f}'

            # B. BB Upper touch (SHORT)
            if dir_ is None and d.get('bb_upper') and ep >= d['bb_upper'] and d.get('rsi_14') and d['rsi_14'] > params.get('rsi_short_min', 40):
                dir_, reason = 'SHORT', f'BB_U_R{d["rsi_14"]:.0f}'

            # C. RSI 超賣反轉 (LONG)
            if dir_ is None and i > 0 and d.get('rsi_14') and data[i-1].get('rsi_14'):
                prev = data[i-1]['rsi_14']
                if prev < 35 <= d['rsi_14'] < params.get('rsi_bounce_max', 50):
                    dir_, reason = 'LONG', f'RSI_bo_{prev:.0f}_{d["rsi_14"]:.0f}'

            # D. RSI 超買反轉 (SHORT)
            if dir_ is None and i > 0 and d.get('rsi_14') and data[i-1].get('rsi_14'):
                prev = data[i-1]['rsi_14']
                if prev > 65 >= d['rsi_14'] > params.get('rsi_revers_max', 50):
                    dir_, reason = 'SHORT', f'RSI_ob_{prev:.0f}_{d["rsi_14"]:.0f}'

            # E. MACD 黃金交叉 (LONG)
            if dir_ is None and i > 0 and d.get('macd_hist') and data[i-1].get('macd_hist') is not None:
                if data[i-1]['macd_hist'] <= 0 < d['macd_hist']:
                    dir_, reason = 'LONG', f'MACD_bull'

            # F. MACD 死叉 (SHORT)
            if dir_ is None and i > 0 and d.get('macd_hist') and data[i-1].get('macd_hist') is not None:
                if data[i-1]['macd_hist'] >= 0 > d['macd_hist']:
                    dir_, reason = 'SHORT', f'MACD_bear'

            # G. KDJ 低檔黃金交叉 (LONG)
            if dir_ is None and i > 0 and d.get('kdj_j') and data[i-1].get('kdj_j') is not None:
                if data[i-1]['kdj_j'] < 20 and d['kdj_j'] > data[i-1]['kdj_j'] and d['kdj_j'] < 40:
                    dir_, reason = 'LONG', f'KDJ_bo_J{d["kdj_j"]:.0f}'

            # H. KDJ 高檔死叉 (SHORT)
            if dir_ is None and i > 0 and d.get('kdj_j') and data[i-1].get('kdj_j') is not None:
                if data[i-1]['kdj_j'] > 80 and d['kdj_j'] < data[i-1]['kdj_j']:
                    dir_, reason = 'SHORT', f'KDJ_ob_J{d["kdj_j"]:.0f}'

            # I. CCI 超賣 (LONG) - 中等寬鬆 (-80 以下)
            if dir_ is None and d.get('cci_20') is not None and d['cci_20'] < -80:
                dir_, reason = 'LONG', f'CCI_ov_{d["cci_20"]:.0f}'

            # J. CCI 超買 (SHORT) - 中等寬鬆 (+80 以上)
            if dir_ is None and d.get('cci_20') is not None and d['cci_20'] > 80:
                dir_, reason = 'SHORT', f'CCI_ob_{d["cci_20"]:.0f}'

            # K. WillR 超賣 (LONG) - 中等 (-80 以下)
            if dir_ is None and d.get('williams_r_14') is not None and d['williams_r_14'] < -80:
                dir_, reason = 'LONG', f'WillR_ov_{d["williams_r_14"]:.0f}'

            # L. WillR 超買 (SHORT) - 中等 (-20 以上)
            if dir_ is None and d.get('williams_r_14') is not None and d['williams_r_14'] > -20:
                dir_, reason = 'SHORT', f'WillR_ob_{d["williams_r_14"]:.0f}'

            # M. SMA 20 黃金交叉 (LONG)
            if dir_ is None and d.get('sma_20') and d.get('close') and data[i-1].get('sma_20') and data[i-1].get('close'):
                if data[i-1]['close'] < data[i-1]['sma_20'] and d['close'] > d['sma_20']:
                    dir_, reason = 'LONG', f'SMA_gc'

            # N. SMA 20 死叉 (SHORT)
            if dir_ is None and d.get('sma_20') and d.get('close') and data[i-1].get('sma_20') and data[i-1].get('close'):
                if data[i-1]['close'] > data[i-1]['sma_20'] and d['close'] < d['sma_20']:
                    dir_, reason = 'SHORT', f'SMA_dc'

            if dir_:
                sl_atr = params.get('sl_atr', 2.0)
                tp_atr = params.get('tp_atr', 3.0)
                mh = params.get('max_hold_long' if dir_ == 'LONG' else 'max_hold_short', 5)
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
                pnl = (xp - pos['ep']) / pos['ep'] * 100 if pos['dir'] == 'LONG' and pos['ep'] > 0 else (pos['ep'] - xp) / pos['ep'] * 100 if pos['ep'] > 0 else 0
                trades.append({'entry_date': pos['entry_date'], 'exit_date': d['date'], 'direction': pos['dir'],
                               'entry_price': pos['ep'], 'exit_price': xp, 'pnl_pct': pnl,
                               'result': 'MAX_HOLD', 'held_days': held, 'reason': pos['reason']})
                pos = None; continue

            sl_hit = (pos['dir'] == 'LONG' and d['low'] <= pos['sl']) or (pos['dir'] == 'SHORT' and d['high'] >= pos['sl'])
            if sl_hit:
                xp = pos['sl']
                pnl = (xp - pos['ep']) / pos['ep'] * 100 if pos['dir'] == 'LONG' and pos['ep'] > 0 else (pos['ep'] - xp) / pos['ep'] * 100 if pos['ep'] > 0 else 0
                trades.append({'entry_date': pos['entry_date'], 'exit_date': d['date'], 'direction': pos['dir'],
                               'entry_price': pos['ep'], 'exit_price': xp, 'pnl_pct': pnl,
                               'result': 'STOP_LOSS', 'held_days': held, 'reason': pos['reason']})
                pos = None; continue

            tp_hit = (pos['dir'] == 'LONG' and d['high'] >= pos['tp']) or (pos['dir'] == 'SHORT' and d['low'] <= pos['tp'])
            if tp_hit:
                xp = pos['tp']
                pnl = (xp - pos['ep']) / pos['ep'] * 100 if pos['dir'] == 'LONG' and pos['ep'] > 0 else (pos['ep'] - xp) / pos['ep'] * 100 if pos['ep'] > 0 else 0
                trades.append({'entry_date': pos['entry_date'], 'exit_date': d['date'], 'direction': pos['dir'],
                               'entry_price': pos['ep'], 'exit_price': xp, 'pnl_pct': pnl,
                               'result': 'TAKE_PROFIT', 'held_days': held, 'reason': pos['reason']})
                pos = None; continue

    return trades

def score(trades):
    if len(trades) < 5: return None
    wins = [t for t in trades if t['pnl_pct'] > 0]
    losses = [t for t in trades if t['pnl_pct'] <= 0]
    if not wins or not losses: return None
    wr = len(wins) / len(trades) * 100
    avg_win = sum(t['pnl_pct'] for t in wins) / len(wins)
    avg_loss = abs(sum(t['pnl_pct'] for t in losses) / len(losses))
    rr = avg_win / avg_loss if avg_loss > 0 else 0
    total = sum(t['pnl_pct'] for t in trades)
    wr_factor = 1.0 if wr >= 55 else (wr / 55) ** 2
    score_val = total * (rr ** 0.5) * min(len(trades) / 20, 2.5) * wr_factor
    return {
        'trades': len(trades), 'win_rate': round(wr, 1),
        'avg_win': round(avg_win, 2), 'avg_loss': round(avg_loss, 2),
        'rr': round(rr, 2), 'total': round(total, 1), 'score': round(score_val, 2),
        'tp': len([t for t in trades if t['result'] == 'TAKE_PROFIT']),
        'sl': len([t for t in trades if t['result'] == 'STOP_LOSS']),
        'mh': len([t for t in trades if t['result'] == 'MAX_HOLD']),
    }

def run():
    print('=== Vogel v13 - ATR 品質過濾 ===\n')
    data = load_db()
    print(f'Loaded {len(data)} days: {data[0]["date"]} to {data[-1]["date"]}')

    base = {
        'sl_atr': 2.0, 'tp_atr': 3.0,
        'rsi_long_max': 50, 'rsi_short_min': 40,
        'rsi_bounce_max': 50, 'rsi_revers_max': 50,
        'atr_min': 200,
        'max_hold_long': 7, 'max_hold_short': 5,
    }

    configs = []
    for tp in [2.0, 2.5, 3.0, 3.5]:
        for sl in [1.5, 2.0, 2.5]:
            for mh_l in [5, 7, 10]:
                for mh_s in [3, 5, 7]:
                    for atr_min in [150, 200, 300, 400]:
                        configs.append({
                            'tp_atr': tp, 'sl_atr': sl,
                            'max_hold_long': mh_l, 'max_hold_short': mh_s,
                            'atr_min': atr_min
                        })

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

    print(f'\n{"#":<3} {"TP":<4} {"SL":<4} {"MH_L":<5} {"MH_S":<5} {"ATRmin":<7} {"Trades":<7} {"WR%":<6} {"AvgWin":<7} {"R:R":<5} {"Total%":<7} {"TP":<4} {"SL":<4} {"MH":<4} {"Score":<6}')
    print('-' * 85)
    for i, r in enumerate(results[:20]):
        print(f'{i+1:<3} {r["tp_atr"]:<4} {r["sl_atr"]:<4} {r["max_hold_long"]:<5} {r["max_hold_short"]:<5} {r["atr_min"]:<7} {r["trades"]:<7} {r["win_rate"]:<6.1f} {r["avg_win"]:<7.2f} {r["rr"]:<5.2f} {r["total"]:<7.1f} {r["tp"]:<4} {r["sl"]:<4} {r["mh"]:<4} {r["score"]:<6.1f}')

    if not results: return

    candidates = [r for r in results if r['win_rate'] >= 50 and r['trades'] >= 15]
    if not candidates: candidates = [r for r in results if r['trades'] >= 10]
    if not candidates: candidates = results
    best = max(candidates, key=lambda x: (x['win_rate'], x['trades'], x['score']))

    print(f'\n=== SELECTED: TP={best["tp_atr"]} SL={best["sl_atr"]} L={best["max_hold_long"]} S={best["max_hold_short"]} ATRmin={best["atr_min"]} ===')
    print(f'Trades: {best["trades"]} | WR: {best["win_rate"]:.1f}% | R:R: {best["rr"]} | Total: {best["total"]:+.1f}% | TP: {best["tp"]} SL: {best["sl"]} MH: {best["mh"]}')

    p = {**base, 'tp_atr': best['tp_atr'], 'sl_atr': best['sl_atr'],
         'max_hold_long': best['max_hold_long'], 'max_hold_short': best['max_hold_short'],
         'atr_min': best['atr_min']}
    trades = backtest(data, p)

    print(f'\n=== All Trades ({len(trades)}) ===')
    print(f'{"#":<3} {"Date":<12} {"Dir":<6} {"Entry":>8} {"Exit":>8} {"P&L%":>7} {"Result":<12} {"Days":<4} Reason')
    print('-' * 75)
    for i, t in enumerate(sorted(trades, key=lambda x: x['entry_date']), 1):
        marker = ' ◄◄' if abs(t['pnl_pct']) > 4 else ''
        print(f'{i:<3} {t["entry_date"]:<12} {t["direction"]:<6} {t["entry_price"]:>8.0f} {t["exit_price"]:>8.0f} {t["pnl_pct"]:>+7.2f}% {t["result"]:<12} {t["held_days"]:<4} {t["reason"]}{marker}')

    reasons = {}
    for t in trades:
        r = t['reason']
        if r not in reasons: reasons[r] = {'count': 0, 'wins': 0, 'pnls': []}
        reasons[r]['count'] += 1
        if t['pnl_pct'] > 0: reasons[r]['wins'] += 1
        reasons[r]['pnls'].append(t['pnl_pct'])
    print(f'\n=== Entry Reason Stats (sorted by count) ===')
    for r, s in sorted(reasons.items(), key=lambda x: -x[1]['count']):
        wr = s['wins']/s['count']*100
        avg = sum(s['pnls'])/len(s['pnls'])
        print(f'  {r:<20}: {s["count"]:>2} trades, WR={wr:.0f}%, avg={avg:+.2f}%')

    # Direction stats
    for label, ts in [('SHORT', [t for t in trades if t['direction'] == 'SHORT']), ('LONG', [t for t in trades if t['direction'] == 'LONG'])]:
        if ts:
            ws = len([t for t in ts if t['pnl_pct'] > 0])
            print(f'{label}: {len(ts)} trades, WR={ws/len(ts)*100:.1f}%, avg={sum(t["pnl_pct"] for t in ts)/len(ts):+.2f}%')

    # Equity
    eq = 100000
    print(f'\n=== Equity Curve ===')
    for t in sorted(trades, key=lambda x: x['entry_date']):
        eq *= (1 + t['pnl_pct']/100)
        marker = ' ◄◄' if abs(t['pnl_pct']) > 4 else ''
        print(f'{t["entry_date"]} {t["direction"]:<5} {t["pnl_pct"]:>+7.2f}% → ${eq:,.0f}{marker}')

    out = os.path.join(VOGEL_DIR, 'v13_results.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump({'best': best, 'all_results': results[:50], 'trades': trades}, f, ensure_ascii=False, indent=2)
    print(f'\nSaved: {out}')
    print('\n=== Vogel v13 Done ===')

if __name__ == '__main__':
    run()