# -*- coding: utf-8 -*-
"""
Nana v7.0 — 獨立歷史回測系統
59 檔市值股完整回測（使用 nana_v64.py 進場邏輯）
回測期間：2022-01-01 ~ 2026-04-26
輸出：CSV + JSON 報告
"""

import sys, os, json, time
from datetime import datetime
import yfinance as yf
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

# ===== 股票池（59檔，排除2888）=====
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

# ===== Nana v6.4 固定參數 =====
RSI_PERIOD    = 12
RSI_ENTRY_MIN = 30
RSI_ENTRY_MAX = 45
MOMENTUM_MIN  = 3.0
ADX_MIN       = 18
SCORE_MIN     = 32
ATR_TP_MULT   = 3.0
ATR_SL_MULT   = 1.5
HOLD_DAYS     = 7

BACKTEST_START = '2022-01-01'
BACKTEST_END   = '2026-04-26'
FETCH_DAYS     = 1700  # 約 4.6 年

OUTPUT_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\nana\reports'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ===== 技術指標 =====
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

def calc_score(rsi, mom, price, ma20, ma60, ma120, adx, slope20):
    score = 0
    if rsi < 30:
        score += 30
    elif rsi < 40:
        score += 25
    elif rsi < 45:
        score += 20
    if mom > 5:
        score += 15
    elif mom > 3:
        score += 10
    elif mom > 0:
        score += 5
    if price > ma20:  score += 10
    if price > ma60:  score += 10
    if ma60 > ma120:  score += 8
    if slope20 > 1.5: score += 10
    elif slope20 > 0.5: score += 5
    if adx >= 25:     score += 10
    elif adx >= ADX_MIN: score += 5
    return score

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

# ===== 單筆交易模擬 =====
def simulate_trade(entry_idx, data, hold_days):
    closes = data['close']
    if entry_idx + hold_days >= len(closes):
        return None

    entry_price = float(closes[entry_idx])
    atr_val = get_atr(data['high'][:entry_idx+1], data['low'][:entry_idx+1],
                      closes[:entry_idx+1], 14)
    target    = entry_price + atr_val * ATR_TP_MULT
    stop      = entry_price - atr_val * ATR_SL_MULT
    exit_reason = 'hold_expired'
    exit_price  = float(closes[entry_idx + hold_days])

    for day in range(hold_days):
        if entry_idx + day >= len(closes):
            break
        cur = float(closes[entry_idx + day])
        if cur >= target:
            exit_reason = 'take_profit'; exit_price = cur; break
        if cur <= stop:
            exit_reason = 'stop_loss';  exit_price = cur; break

    net_pct = (exit_price - entry_price) / entry_price * 100
    return {
        'return_pct': round(net_pct, 3),
        'exit_reason': exit_reason,
    }

# ===== 單檔回測 =====
def backtest_stock(symbol, data):
    closes = data['close']
    dates  = data['dates']
    trades = []

    for i in range(RSI_PERIOD + 10, len(closes) - HOLD_DAYS - 3, 2):
        if i >= len(closes) - HOLD_DAYS:
            break

        date_str = dates[i] if i < len(dates) else ''
        if date_str < BACKTEST_START or date_str > BACKTEST_END:
            continue

        chunk   = closes[:i+1]
        c_high  = data['high'][:i+1]
        c_low   = data['low'][:i+1]

        rsi   = get_rsi(chunk, RSI_PERIOD)
        mom5  = get_momentum(chunk, 5)
        ma20  = get_ma(chunk, 20)
        ma60  = get_ma(chunk, 60)
        ma120 = get_ma(chunk, 120) if len(chunk) >= 120 else ma60
        price = float(closes[i])
        adx   = get_adx(c_high, c_low, chunk)

        # slope20
        if i >= 25:
            past_ma = get_ma(closes[max(0, i-20):i], 20)
            slope20 = ((ma20 - past_ma) / past_ma * 100) if past_ma != 0 else 0
        else:
            slope20 = 0

        # MA20 跌破檢查（停利條件之一）
        ma20_broken = price < ma20

        rsi_ok   = RSI_ENTRY_MIN <= rsi <= RSI_ENTRY_MAX
        mom_ok   = mom5 > MOMENTUM_MIN or mom5 < -2
        adx_ok   = adx >= ADX_MIN
        score    = calc_score(rsi, mom5, price, ma20, ma60, ma120, adx, slope20)

        if not rsi_ok or score < SCORE_MIN or not adx_ok:
            continue

        trade = simulate_trade(i, data, HOLD_DAYS)
        if trade is None:
            continue

        trades.append({
            'symbol':      symbol,
            'date':        date_str,
            'entry_price': round(price, 2),
            'rsi':         round(rsi, 1),
            'mom':         round(mom5, 2),
            'score':       score,
            'adx':         round(adx, 1),
            'atr':         round(get_atr(c_high, c_low, chunk, 14), 2),
            'ma20':        round(ma20, 2),
            'ma20_broken': ma20_broken,
            'return_pct':  trade['return_pct'],
            'exit_reason': trade['exit_reason'],
        })

    return trades

# ===== 指標計算 =====
def calc_metrics(trades):
    if not trades:
        return None
    rets   = [t['return_pct'] for t in trades]
    wins   = [r for r in rets if r > 0]
    losses = [r for r in rets if r <= 0]
    n      = len(rets)
    total  = sum(rets)

    wr   = len(wins) / n * 100 if n else 0
    avg  = total / n if n else 0
    avg_w = sum(wins) / len(wins) if wins else 0
    avg_l = sum(losses) / len(losses) if losses else 0
    pl    = abs(avg_w / avg_l) if avg_l != 0 else 0

    if n > 1:
        rf    = 0.01 / 252
        exc   = [r/100 - rf for r in rets]
        sharpe = np.mean(exc) / np.std(exc) * np.sqrt(252) if np.std(exc) > 0 else 0
    else:
        sharpe = 0

    cum    = np.cumsum(rets)
    peak   = np.maximum.accumulate(cum)
    dd     = peak - cum
    max_dd = float(np.max(dd)) if len(dd) > 0 else 0

    tp_count  = sum(1 for t in trades if t['exit_reason'] == 'take_profit')
    sl_count  = sum(1 for t in trades if t['exit_reason'] == 'stop_loss')
    hold_count= sum(1 for t in trades if t['exit_reason'] == 'hold_expired')

    return {
        'n':           n,
        'wr':          round(wr, 2),
        'avg_return':  round(avg, 3),
        'total_return':round(total, 2),
        'avg_win':     round(avg_w, 2),
        'avg_loss':    round(avg_l, 2),
        'pl_ratio':    round(pl, 3),
        'sharpe':      round(sharpe, 3),
        'max_dd':      round(max_dd, 2),
        'max_gain':    round(max(rets), 2) if rets else 0,
        'max_loss':    round(min(rets), 2) if rets else 0,
        'tp_count':    tp_count,
        'sl_count':    sl_count,
        'hold_count':  hold_count,
    }

# ===== 主程式 =====
def run_backtest():
    t_start = time.time()
    print('=' * 65)
    print('  Nana v7.0 — 歷史回測系統')
    print(f'  回測期間：{BACKTEST_START} ~ {BACKTEST_END}')
    print(f'  股票數：{len(STOCK_POOL)} 檔')
    print('=' * 65)

    # 抓取歷史
    print('\n抓取歷史數據中...')
    stock_data = {}
    for i, sym in enumerate(STOCK_POOL):
        d = fetch_history(sym)
        if d:
            stock_data[sym] = d
        if (i + 1) % 20 == 0:
            print(f'  已處理 {i+1}/{len(STOCK_POOL)} 檔...')
    print(f'  成功取得 {len(stock_data)} 檔')

    # 逐檔回測
    print('\n開始回測...')
    all_trades   = []
    stock_report = {}

    for i, (sym, data) in enumerate(stock_data.items()):
        trades = backtest_stock(sym, data)
        if trades:
            all_trades.extend(trades)
            m = calc_metrics(trades)
            stock_report[sym] = {
                'name':  STOCK_NAMES.get(sym, sym),
                'trades': len(trades),
                'wr':    m['wr'],
                'avg':   m['avg_return'],
                'sharpe':m['sharpe'],
                'max_dd':m['max_dd'],
                'total': m['total_return'],
            }
        if (i + 1) % 10 == 0:
            elapsed = time.time() - t_start
            print(f'  {i+1}/{len(stock_data)} 檔完成 ({elapsed:.1f}s) ...')

    if not all_trades:
        print('無任何交易紀錄！')
        return

    # 總體指標
    overall = calc_metrics(all_trades)

    # ===== CSV 輸出 =====
    csv_file = os.path.join(OUTPUT_DIR, 'nana_backtest_trades.csv')
    cols = ['symbol','name','date','entry_price','rsi','mom','score','adx',
            'atr','ma20','ma20_broken','return_pct','exit_reason']
    with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
        f.write(','.join(cols) + '\n')
        for t in all_trades:
            name = STOCK_NAMES.get(t['symbol'], t['symbol'])
            row  = [t['symbol'], name, t['date'], t['entry_price'],
                    t['rsi'], t['mom'], t['score'], t['adx'],
                    t['atr'], t['ma20'], t['ma20_broken'],
                    t['return_pct'], t['exit_reason']]
            f.write(','.join(str(x) for x in row) + '\n')

    # ===== JSON 報告 =====
    report = {
        'timestamp':      datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'source':         'nana_backtest.py',
        'backtest_period': f'{BACKTEST_START} ~ {BACKTEST_END}',
        'stocks_tested':  len(stock_data),
        'total_trades':   len(all_trades),
        'overall_metrics': overall,
        'stock_report':   stock_report,
        'params': {
            'rsi_period':    RSI_PERIOD,
            'rsi_entry_min': RSI_ENTRY_MIN,
            'rsi_entry_max': RSI_ENTRY_MAX,
            'momentum_min':  MOMENTUM_MIN,
            'adx_min':       ADX_MIN,
            'score_min':     SCORE_MIN,
            'atr_tp_mult':   ATR_TP_MULT,
            'atr_sl_mult':   ATR_SL_MULT,
            'hold_days':     HOLD_DAYS,
        },
        'all_trades': all_trades,
    }

    json_file = os.path.join(OUTPUT_DIR, 'nana_backtest_report.json')
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # ===== 顯示結果 =====
    elapsed = time.time() - t_start
    print('\n' + '=' * 65)
    print('  回測結果摘要')
    print('=' * 65)
    print(f'  回測期間：{BACKTEST_START} ~ {BACKTEST_END}')
    print(f'  總交易次數：{overall["n"]}')
    print(f'  勝率（WR）：{overall["wr"]}%')
    print(f'  平均報酬率：{overall["avg_return"]}%')
    print(f'  總報酬率：{overall["total_return"]}%')
    print(f'  平均獲利：{overall["avg_win"]}%')
    print(f'  平均虧損：{overall["avg_loss"]}%')
    print(f'  盈虧比：{overall["pl_ratio"]}')
    print(f'  Sharpe：{overall["sharpe"]}')
    print(f'  最大Drawdown：{overall["max_dd"]}%')
    print(f'  最大單筆獲利：{overall["max_gain"]}%')
    print(f'  最大單筆虧損：{overall["max_loss"]}%')
    print(f'  停利次數：{overall["tp_count"]} ({overall["tp_count"]/overall["n"]*100:.1f}%)')
    print(f'  停損次數：{overall["sl_count"]} ({overall["sl_count"]/overall["n"]*100:.1f}%)')
    print(f'  持有期滿：{overall["hold_count"]} ({overall["hold_count"]/overall["n"]*100:.1f}%)')
    print(f'  耗時：{elapsed:.1f} 秒')

    # Top 10 最佳股票
    sorted_stocks = sorted(stock_report.items(), key=lambda x: x[1]['total'], reverse=True)
    print('\n  Top 10 股票（總報酬率）：')
    print(f'  {"CODE":<6} {"NAME":<8} {"TRADES":<7} {"WR%":<7} {"AVG%":<7} {"SHARPE":<7} {"MAX_DD":<8} {"TOTAL%":<8}')
    print('  ' + '-' * 62)
    for sym, m in sorted_stocks[:10]:
        print(f"  {sym:<6} {m['name']:<8} {m['trades']:<7} "
              f"{m['wr']:<7.1f} {m['avg']:<7.2f} {m['sharpe']:<7.2f} "
              f"{m['max_dd']:<8.2f} {m['total']:<8.2f}")

    print(f'\n  CSV：{csv_file}')
    print(f'  JSON：{json_file}')

    return report

if __name__ == '__main__':
    run_backtest()