# -*- coding: utf-8 -*-
"""
Nana v7.0 — Walk-Forward Analysis (WFA)
用 WFA 驗證 nana_v64.py 的參數稳定性。
訓練期：2024-01-01 ~ 2025-06-30
驗證期：2025-07-01 ~ 2026-04-26
輸出：最佳 RSI Period、Threshold、Hold Days
"""

import sys, os, json, itertools, time
from datetime import datetime, timedelta
import yfinance as yf
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

# ===== 股票池（59檔，排除2888已下市）=====
STOCK_POOL = [
    '2330','2317','2454','2303','2382','2881','2882','2883','2884','2885',
    '2886','2887','2889','2890','2891','2892','3008','3037','3231',
    '3443','3711','4532','4770','4938','4952','5203','5215','5388','5471',
    '5538','5876','5880','6116','6139','6176','6183','6230','6257','6285',
    '6405','6409','6415','6446','6550','6579','6770','6789','8016',
    '8028','8046','8081','8131','8150','8261','8454','8464','9914','9921',
    '2880','2897','5882'
]

STOCK_NAMES = {
    '2330':'台積電','2317':'鴻海','2454':'聯發科','2303':'聯電','2382':'廣達',
    '2881':'國泰金','2882':'兆豐金','2883':'開發金','2884':'玉山金','2885':'元大金',
    '2886':'第一金','2887':'富邦金','2889':'永豐金','2890':'中信金',
    '2891':'統一','2892':'遠傳','3008':'大立光','3037':'欣興','3231':'創意',
    '3443':'中碳','3711':'日月光','4532':'華擎','4770':'熱映','4938':'和碩',
    '4952':'凌華','5203':'互盛電','5215':'科嘉-KY','5388':'環球晶','5471':'松翰',
    '5538':'融程電','5876':'上海商銀','5880':'合庫金','6116':'彩晶','6139':'太陽能',
    '6176':'環球晶','6183':'撼訊','6230':'麗臺','6257':'迎廣','6285':'綠能',
    '6405':'景岳','6409':'光菱','6415':'崇越','6446':'秧訊','6550':'長科',
    '6579':'全景軟','6770':'力旺','6789':'安格','8016':'昇技','8028':'敦泰',
    '8046':'力成','8081':'致茂','8131':'立端','8150':'合新','8261':'富鼎',
    '8454':'M31','8464':'億光','9914':'美利肯','9921':'巨大',
    '2880':'華南金','2897':'王道銀','5882':'上海商銀',
}

# ===== WFA 參數格點 =====
RSI_PERIODS = [10, 12, 14]
RSI_ENTRY_MINS = [25, 30, 35]
RSI_ENTRY_MAXS = [40, 45, 50]
HOLD_DAYS_LIST = [5, 7, 10]

# ===== 固定參數（來自 nana_v64.py）=====
MOMENTUM_MIN = 3.0
ADX_MIN = 18
SCORE_MIN = 32
ATR_TP_MULT = 3.0
ATR_SL_MULT = 1.5

# ===== 時間軸 =====
TRAIN_END   = '2025-06-30'
VAL_END     = '2026-04-26'
FETCH_DAYS  = 900  # 約 3 年歷史

OUTPUT_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\nana\reports'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ===== Technical Indicators =====
def get_rsi(closes, period=12):
    if len(closes) < period + 1:
        return 50.0
    deltas = np.diff(closes)
    gains  = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = float(np.mean(gains[-period:]))
    avg_loss = float(np.mean(losses[-period:]))
    if avg_loss == 0:
        return 100.0
    return float(100 - (100 / (1 + avg_gain / avg_loss)))

def get_ma(closes, period):
    if len(closes) < period:
        return 0.0
    return float(np.mean(closes[-period:]))

def get_atr(highs, lows, closes, period=14):
    if len(closes) < period + 1:
        return 5.0
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1]))
        trs.append(tr)
    return float(np.mean(trs[-period:])) if trs else 5.0

def get_adx(highs, lows, closes, period=14):
    if len(closes) < period + 5:
        return 15.0
    ma_now  = get_ma(closes, period)
    ma_prev = float(np.mean(closes[-(period+5):-5]))
    slope   = abs((ma_now - ma_prev) / ma_prev * 100) if ma_prev != 0 else 0
    return min(80, max(10, slope * 5))

def get_momentum(closes, bars=5):
    if len(closes) < bars + 1:
        return 0.0
    return float((closes[-1] / closes[-bars-1] - 1) * 100)

def get_score(rsi, momentum, price, ma20, ma60, ma120, adx, slope20, rsi_ok, momentum_ok, adx_ok):
    score = 0
    zone  = ''
    if rsi < 30:
        score += 30; zone = 'deep_oversold'
    elif rsi < 40:
        score += 25; zone = 'oversold'
    elif rsi < 45:
        score += 20; zone = 'soft_oversold'
    if momentum > 5:
        score += 15
    elif momentum > 3:
        score += 10
    elif momentum > 0:
        score += 5
    if price > ma20:
        score += 10
    if price > ma60:
        score += 10
    if ma60 > ma120:
        score += 8
    if slope20 > 1.5:
        score += 10
    elif slope20 > 0.5:
        score += 5
    if adx >= 25:
        score += 10
    elif adx >= ADX_MIN:
        score += 5
    return score, zone

# ===== 歷史數據取得 =====
def fetch_history(symbol):
    try:
        t = yf.Ticker(f'{symbol}.TW')
        h = t.history(period=f'{FETCH_DAYS}d')
        if h.empty or len(h) < 250:
            return None
        return {
            'close': h['Close'].values,
            'high':  h['High'].values,
            'low':   h['Low'].values,
            'dates': [d.strftime('%Y-%m-%d') for d in h.index],
        }
    except:
        return None

# ===== 評估單筆交易 =====
def simulate_trade(entry_idx, data, hold_days, tp_mult, sl_mult):
    closes = data['close']
    if entry_idx + hold_days >= len(closes):
        return None
    entry_price = float(closes[entry_idx])
    atr_val     = get_atr(data['high'][:entry_idx+1], data['low'][:entry_idx+1],
                          closes[:entry_idx+1], 14)
    target = entry_price + atr_val * tp_mult
    stop   = entry_price - atr_val * sl_mult

    exit_reason = 'hold_expired'
    exit_price  = float(closes[entry_idx + hold_days])
    highest     = entry_price

    for day in range(hold_days):
        if entry_idx + day >= len(closes):
            break
        cur = float(closes[entry_idx + day])
        highest = max(highest, cur)
        if cur >= target:
            exit_reason = 'take_profit'; exit_price = cur; break
        if cur <= stop:
            exit_reason = 'stop_loss';  exit_price = cur; break

    net_pct = (exit_price - entry_price) / entry_price * 100
    return {'return_pct': net_pct, 'exit_reason': exit_reason, 'hold_days': hold_days}

# ===== 完整回測（單檔單參數）=====
def backtest_stock(symbol, data, rsi_period, rsi_min, rsi_max, hold_days):
    closes = data['close']
    dates  = data['dates']
    trades = []

    for i in range(rsi_period + 10, len(closes) - hold_days - 5, 2):
        if i >= len(closes) - hold_days:
            break

        chunk = closes[:i+1]
        c_high = data['high'][:i+1]
        c_low  = data['low'][:i+1]

        rsi     = get_rsi(chunk, rsi_period)
        mom5    = get_momentum(chunk, 5)
        ma20    = get_ma(chunk, 20)
        ma60    = get_ma(chunk, 60)
        ma120   = get_ma(chunk, 120) if len(chunk) >= 120 else ma60
        price   = float(closes[i])
        adx     = get_adx(c_high, c_low, chunk)
        slope20 = ((ma20 - get_ma(closes[max(0,i-20):i], 20)) /
                   get_ma(closes[max(0,i-20):i], 20) * 100) if i >= 20 else 0
        trend_up = ma60 > ma120

        rsi_ok      = rsi_min <= rsi <= rsi_max
        momentum_ok  = mom5 > MOMENTUM_MIN or mom5 < -2
        adx_ok      = adx >= ADX_MIN
        score, zone = get_score(rsi, mom5, price, ma20, ma60, ma120, adx,
                                 slope20, rsi_ok, momentum_ok, adx_ok)

        if not rsi_ok or score < SCORE_MIN:
            continue
        if not adx_ok:
            continue

        trade = simulate_trade(i, data, hold_days, ATR_TP_MULT, ATR_SL_MULT)
        if trade is None:
            continue
        trade['date']  = dates[i] if i < len(dates) else ''
        trade['rsi']   = round(rsi, 1)
        trade['mom']   = round(mom5, 2)
        trade['score']  = score
        trade['adx']   = round(adx, 1)
        trade['price']  = round(price, 2)
        trades.append(trade)

    return trades

# ===== 指標計算 =====
def calc_metrics(trades):
    if not trades:
        return None
    rets = [t['return_pct'] for t in trades]
    wins = [r for r in rets if r > 0]
    losses = [r for r in rets if r <= 0]
    n = len(rets)

    total = sum(rets)
    wr    = len(wins) / n * 100 if n else 0
    avg_r = total / n if n else 0
    avg_w = sum(wins) / len(wins) if wins else 0
    avg_l = sum(losses) / len(losses) if losses else 0
    pl    = abs(avg_w / avg_l) if avg_l != 0 else 0

    if n > 1:
        rf   = 0.01 / 252
        exc  = [r/100 - rf for r in rets]
        sharpe = np.mean(exc) / np.std(exc) * np.sqrt(252) if np.std(exc) > 0 else 0
    else:
        sharpe = 0

    cum  = np.cumsum(rets)
    peak = np.maximum.accumulate(cum)
    dd   = peak - cum
    max_dd = float(np.max(dd)) if len(dd) > 0 else 0

    return {
        'n': n, 'wr': round(wr, 2), 'avg_return': round(avg_r, 3),
        'total_return': round(total, 2), 'avg_win': round(avg_w, 2),
        'avg_loss': round(avg_l, 2), 'pl_ratio': round(pl, 3),
        'sharpe': round(sharpe, 3), 'max_dd': round(max_dd, 2),
        'max_gain': round(max(rets), 2) if rets else 0,
        'max_loss': round(min(rets), 2) if rets else 0,
    }

def split_trades_by_period(trades, train_end, val_end):
    train, val = [], []
    for t in trades:
        d = t.get('date', '')
        if d and d <= train_end:
            train.append(t)
        elif d and d <= val_end:
            val.append(t)
    return train, val

# ===== WFA 主程式 =====
def run_wfa():
    print('=' * 65)
    print('  Nana v7.0 — Walk-Forward Analysis (WFA)')
    print('  訓練期：2024-01-01 ~ 2025-06-30')
    print('  驗證期：2025-07-01 ~ 2026-04-26')
    print('=' * 65)

    # 預先抓取所有股票歷史
    print('\n抓取歷史數據中...')
    stock_data = {}
    for i, sym in enumerate(STOCK_POOL):
        d = fetch_history(sym)
        if d:
            stock_data[sym] = d
        if (i + 1) % 20 == 0:
            print(f'  已處理 {i+1}/{len(STOCK_POOL)} 檔...')
    print(f'  成功取得 {len(stock_data)} 檔歷史數據')

    # 參數格點
    configs = list(itertools.product(
        RSI_PERIODS, RSI_ENTRY_MINS, RSI_ENTRY_MAXS, HOLD_DAYS_LIST
    ))
    print(f'\n共 {len(configs)} 組參數 x {len(stock_data)} 檔 = '
          f'{len(configs) * len(stock_data)} 組合')

    all_results = []
    total = len(configs) * len(stock_data)
    count = 0

    for rsi_p, rsi_min, rsi_max, hold in configs:
        for sym, data in stock_data.items():
            trades = backtest_stock(sym, data, rsi_p, rsi_min, rsi_max, hold)
            if not trades:
                continue
            train_t, val_t = split_trades_by_period(trades, TRAIN_END, VAL_END)
            m_train = calc_metrics(train_t)
            m_val   = calc_metrics(val_t)

            if m_train is None or m_val is None:
                continue
            if m_train['n'] < 8 or m_val['n'] < 3:
                continue

            wr_diff  = abs(m_train['wr'] - m_val['wr'])
            ret_diff = abs(m_train['avg_return'] - m_val['avg_return'])

            # 穩健性評分：驗證期 Sharpe 為主，加權避免過度擬合
            score = (
                min(m_train['sharpe'], m_val['sharpe']) * 12 +
                min(m_train['pl_ratio'], m_val['pl_ratio']) * 6 +
                min(m_train['wr'], m_val['wr']) * 0.6 -
                wr_diff  * 4 -
                ret_diff * 15
            )

            all_results.append({
                'rsi_period':    rsi_p,
                'rsi_entry_min': rsi_min,
                'rsi_entry_max': rsi_max,
                'hold_days':     hold,
                'train_n':       m_train['n'],
                'train_wr':      m_train['wr'],
                'train_avg':     m_train['avg_return'],
                'train_sharpe':  m_train['sharpe'],
                'train_pl':      m_train['pl_ratio'],
                'train_max_dd':  m_train['max_dd'],
                'val_n':         m_val['n'],
                'val_wr':        m_val['wr'],
                'val_avg':       m_val['avg_return'],
                'val_sharpe':    m_val['sharpe'],
                'val_pl':        m_val['pl_ratio'],
                'val_max_dd':    m_val['max_dd'],
                'wr_diff':       round(wr_diff, 2),
                'ret_diff':      round(ret_diff, 3),
                'score':         round(score, 3),
            })
            count += 1

        if count % 100 == 0:
            print(f'  已完成 {count}/{total}...')

    if not all_results:
        print('WFA 無有效結果！')
        return []

    # 排序
    all_results.sort(key=lambda x: x['score'], reverse=True)

    # Top 10 顯示
    print('\n' + '=' * 65)
    print('  Top 10 WFA 參數組合')
    print('=' * 65)
    hdr = f"{'RSI_P':<6} {'Min':<5} {'Max':<5} {'Hold':<5} " \
          f"{'Trn_WR%':<9} {'Val_WR%':<9} {'Trn_Shp':<9} {'Val_Shp':<9} " \
          f"{'Trn_PL':<8} {'Val_PL':<8} {'Score':<8}"
    print(hdr)
    print('-' * 85)
    for r in all_results[:10]:
        print(f"{r['rsi_period']:<6} {r['rsi_entry_min']:<5} {r['rsi_entry_max']:<5} "
              f"{r['hold_days']:<5} "
              f"{r['train_wr']:<9.1f} {r['val_wr']:<9.1f} "
              f"{r['train_sharpe']:<9.2f} {r['val_sharpe']:<9.2f} "
              f"{r['train_pl']:<8.2f} {r['val_pl']:<8.2f} "
              f"{r['score']:<8.2f}")

    # 參數 plateau 分析（找出最穩健的 RSI Period / Hold Days 組合）
    print('\n' + '=' * 65)
    print('  參數區間穩健性分析（Top 50 結果分群）')
    print('=' * 65)

    plateau = {}
    for r in all_results[:50]:
        key = (r['rsi_period'], r['rsi_entry_min'], r['rsi_entry_max'], r['hold_days'])
        if key not in plateau:
            plateau[key] = []
        plateau[key].append(r)

    for key, items in sorted(plateau.items(), key=lambda x: -len(x[1]))[:8]:
        avg_score = sum(i['score'] for i in items) / len(items)
        avg_wr     = np.mean([i['val_wr'] for i in items])
        avg_sharpe = np.mean([i['val_sharpe'] for i in items])
        print(f'  RSI_P={key[0]} Min={key[1]} Max={key[2]} Hold={key[3]}d  '
              f'→ {len(items)}檔 | Avg Score={avg_score:.2f} | '
              f'Val WR={avg_wr:.1f}% | Val Sharpe={avg_sharpe:.2f}')

    # 寫入 JSON 報告
    report = {
        'timestamp':     datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'source':        'nana_wfa.py',
        'train_period':  f'2024-01-01 ~ {TRAIN_END}',
        'val_period':    f'2025-07-01 ~ {VAL_END}',
        'total_runs':    count,
        'n_results':     len(all_results),
        'top_config': {
            'rsi_period':    all_results[0]['rsi_period'],
            'rsi_entry_min': all_results[0]['rsi_entry_min'],
            'rsi_entry_max': all_results[0]['rsi_entry_max'],
            'hold_days':     all_results[0]['hold_days'],
        },
        'train_metrics': {
            'wr':        all_results[0]['train_wr'],
            'avg_return':all_results[0]['train_avg'],
            'sharpe':    all_results[0]['train_sharpe'],
            'pl_ratio':  all_results[0]['train_pl'],
            'max_dd':    all_results[0]['train_max_dd'],
            'n_trades':  all_results[0]['train_n'],
        },
        'val_metrics': {
            'wr':        all_results[0]['val_wr'],
            'avg_return':all_results[0]['val_avg'],
            'sharpe':    all_results[0]['val_sharpe'],
            'pl_ratio':  all_results[0]['val_pl'],
            'max_dd':    all_results[0]['val_max_dd'],
            'n_trades':  all_results[0]['val_n'],
        },
        'wr_diff':  all_results[0]['wr_diff'],
        'ret_diff': all_results[0]['ret_diff'],
        'score':    all_results[0]['score'],
        'all_results': all_results[:20],
    }

    out_file = os.path.join(OUTPUT_DIR, 'nana_wfa_report.json')
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print('\n' + '=' * 65)
    print('  WFA 完成')
    print('=' * 65)
    best = all_results[0]
    print(f'  最佳參數：RSI_P={best["rsi_period"]}  Min={best["rsi_entry_min"]}  '
          f'Max={best["rsi_entry_max"]}  Hold={best["hold_days"]}天')
    print(f'  訓練 WR={best["train_wr"]:.1f}%  Sharpe={best["train_sharpe"]:.2f}')
    print(f'  驗證 WR={best["val_wr"]:.1f}%   Sharpe={best["val_sharpe"]:.2f}')
    print(f'  穩健性評分：{best["score"]:.2f}')
    print(f'  報告已寫入：{out_file}')

    return all_results

if __name__ == '__main__':
    run_wfa()