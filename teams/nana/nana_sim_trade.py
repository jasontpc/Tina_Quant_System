# -*- coding: utf-8 -*-
"""
Nana v7.0 — 模擬交易追蹤系統
讀取 nana_v64.py 當日掃描候選，模擬進場/停利/停損，
追蹤持倉（JSON），計算勝率、P&L，每筆交易記錄。
"""

import sys, os, json, time, glob
from datetime import datetime, timedelta
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

# ===== 路徑 =====
NANA_DIR    = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\nana'
CACHE_FILE  = os.path.join(NANA_DIR, 'scan_cache_v64.json')
PORTFOLIO_FILE = os.path.join(NANA_DIR, 'reports', 'nana_sim_portfolio.json')
TRADES_FILE   = os.path.join(NANA_DIR, 'reports', 'nana_sim_trades.json')
REPORTS_DIR    = os.path.join(NANA_DIR, 'reports')
os.makedirs(REPORTS_DIR, exist_ok=True)

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
    if rsi < 30:      score += 30
    elif rsi < 40:    score += 25
    elif rsi < 45:    score += 20
    if mom > 5:       score += 15
    elif mom > 3:     score += 10
    elif mom > 0:     score += 5
    if price > ma20:  score += 10
    if price > ma60:  score += 10
    if ma60 > ma120:  score += 8
    if slope20 > 1.5: score += 10
    elif slope20 > 0.5: score += 5
    if adx >= 25:     score += 10
    elif adx >= ADX_MIN: score += 5
    return score

# ===== 分析個股（完整版本，讀取 nana_v64 掃描格式）=====
def analyze_stock(symbol, days=30):
    try:
        ticker = yf.Ticker(f'{symbol}.TW')
        h = ticker.history(period=f'{days}d', interval='1d')
        if h.empty or len(h) < 20:
            return None

        closes = h['Close'].values
        highs  = h['High'].values
        lows   = h['Low'].values
        price  = float(closes[-1])

        rsi   = get_rsi(closes, RSI_PERIOD)
        ma20  = get_ma(closes, 20)
        ma60  = get_ma(closes, 60)
        ma120 = get_ma(closes, 120) if len(closes) >= 120 else ma60
        mom5  = get_momentum(closes, 5)
        adx   = get_adx(highs, lows, closes)
        atr   = get_atr(highs, lows, closes)

        # slope20
        if len(closes) >= 25:
            past_ma = get_ma(closes[:-5], 20)
            slope20 = ((ma20 - past_ma) / past_ma * 100) if past_ma != 0 else 0
        else:
            slope20 = 0

        rsi_ok   = RSI_ENTRY_MIN <= rsi <= RSI_ENTRY_MAX
        mom_ok   = mom5 > MOMENTUM_MIN or mom5 < -2
        adx_ok   = adx >= ADX_MIN
        score    = calc_score(rsi, mom5, price, ma20, ma60, ma120, adx, slope20)
        ma20_ok  = price > ma20

        if score < SCORE_MIN or not rsi_ok:
            return None

        return {
            'symbol':   symbol,
            'name':     STOCK_NAMES.get(symbol, symbol),
            'price':    round(price, 2),
            'rsi':      round(rsi, 1),
            'mom':      round(mom5, 2),
            'adx':      round(adx, 1),
            'score':    score,
            'atr':      round(atr, 2),
            'ma20':     round(ma20, 2),
            'ma60':     round(ma60, 2),
            'ma20_ok':  ma20_ok,
            'target':   round(price + atr * ATR_TP_MULT, 2),
            'stop':     round(price - atr * ATR_SL_MULT, 2),
            'ma20_broken_stop': round(ma20, 2),
        }
    except:
        return None

# ===== 從 cache 讀取候選（nana_v64 格式）=====
def load_candidates():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            results = data.get('results', {}) if isinstance(data, dict) else data
            if results:
                return list(results.values())
        except:
            pass
    return None

# ===== 掃描候選（當日）=====
def scan_candidates():
    print('掃描候選個股...')
    candidates = []
    for i, sym in enumerate(STOCK_POOL):
        r = analyze_stock(sym)
        if r:
            candidates.append(r)
        if (i + 1) % 20 == 0:
            print(f'  {i+1}/{len(STOCK_POOL)}...')
    candidates.sort(key=lambda x: x['score'], reverse=True)
    return candidates

# ===== 持倉管理 =====
def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {'positions': [], 'cash': 0, 'last_updated': ''}

def save_portfolio(portfolio):
    portfolio['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(PORTFOLIO_FILE, 'w', encoding='utf-8') as f:
        json.dump(portfolio, f, ensure_ascii=False, indent=2)

def load_trades():
    if os.path.exists(TRADES_FILE):
        try:
            with open(TRADES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return []

def save_trades(trades):
    with open(TRADES_FILE, 'w', encoding='utf-8') as f:
        json.dump(trades, f, ensure_ascii=False, indent=2)

# ===== 更新持倉（檢查停利/停損/MA20跌破）=====
def update_positions(portfolio, trades):
    if not portfolio.get('positions'):
        return portfolio, []

    updated_positions = []
    closed_trades = []

    for pos in portfolio['positions']:
        sym   = pos['symbol']
        entry = pos['entry_price']
        target = pos['target']
        stop   = pos['stop']
        ma20_s = pos['ma20_stop']
        hold_days = pos.get('hold_days', HOLD_DAYS)
        entry_date_str = pos.get('entry_date', '')
        day_count = pos.get('day_count', 0)

        try:
            ticker = yf.Ticker(f'{sym}.TW')
            h = ticker.history(period='5d', interval='1d')
            if h.empty:
                updated_positions.append({**pos, 'day_count': day_count + 1})
                continue

            closes = h['Close'].values
            highs  = h['High'].values
            lows   = h['Low'].values

            cur_price  = float(closes[-1])
            cur_high   = float(np.max(highs))
            prev_close = float(closes[-2]) if len(closes) > 1 else cur_price

            # 更新日數
            day_count += 1

            exit_reason = None
            exit_price  = None

            # 停利：价格达到目标价 OR MA20 跌破（收盘价 < MA20）
            ma20_current = get_ma(closes, 20)
            ma20_broken = cur_price < ma20_current

            if cur_high >= target:
                exit_reason = 'take_profit'; exit_price = target
            elif ma20_broken:
                exit_reason = 'ma20_broken'; exit_price = cur_price
            elif cur_price <= stop:
                exit_reason = 'stop_loss'; exit_price = stop
            elif day_count >= hold_days:
                exit_reason = 'hold_expired'; exit_price = cur_price

            if exit_reason:
                ret_pct = (exit_price - entry) / entry * 100
                closed_trades.append({
                    'symbol':       sym,
                    'entry_date':   entry_date_str,
                    'exit_date':    datetime.now().strftime('%Y-%m-%d'),
                    'entry_price':  entry,
                    'exit_price':   round(exit_price, 2),
                    'target':       target,
                    'stop':         stop,
                    'ma20_stop':    ma20_s,
                    'return_pct':   round(ret_pct, 3),
                    'exit_reason':  exit_reason,
                    'hold_days':    day_count,
                    'score':        pos.get('score', 0),
                    'rsi':          pos.get('rsi', 0),
                })
            else:
                # 仍未出局，記錄浮動損益
                pos['current_price'] = round(cur_price, 2)
                pos['unrealized_pct'] = round((cur_price - entry) / entry * 100, 3)
                pos['day_count'] = day_count
                updated_positions.append(pos)
        except Exception as e:
            pos['day_count'] = day_count + 1
            updated_positions.append(pos)

    portfolio['positions'] = updated_positions

    if closed_trades:
        trades.extend(closed_trades)
        save_trades(trades)

    save_portfolio(portfolio)
    return portfolio, closed_trades

# ===== 進場（從候選选股）=====
def enter_positions(candidates, portfolio, trades, max_positions=5, capital=1000000):
    current_positions = len(portfolio.get('positions', []))
    available = max_positions - current_positions

    if available <= 0:
        print('已達最大持倉數限制')
        return portfolio, trades

    # 每次最多進場 1 檔（控制風險）
    if available > 1:
        available = 1

    # 根據 score 排序，過濾已在持倉的
    held = {p['symbol'] for p in portfolio.get('positions', [])}
    eligible = [c for c in candidates if c['symbol'] not in held][:available]

    entry_price = capital / available  if available > 0 else capital

    for cand in eligible:
        pos = {
            'symbol':       cand['symbol'],
            'name':         cand['name'],
            'entry_price':  cand['price'],
            'entry_date':   datetime.now().strftime('%Y-%m-%d'),
            'target':       cand['target'],
            'stop':         cand['stop'],
            'ma20_stop':    cand['ma20'],
            'hold_days':    HOLD_DAYS,
            'score':        cand['score'],
            'rsi':          cand['rsi'],
            'mom':          cand['mom'],
            'atr':          cand['atr'],
            'day_count':    0,
            'current_price': cand['price'],
            'unrealized_pct': 0.0,
        }
        portfolio['positions'].append(pos)
        trades.append({
            'action':      'enter',
            'symbol':      cand['symbol'],
            'name':        cand['name'],
            'entry_price': cand['price'],
            'entry_date':  datetime.now().strftime('%Y-%m-%d'),
            'target':      cand['target'],
            'stop':        cand['stop'],
            'score':       cand['score'],
        })

    save_portfolio(portfolio)
    save_trades(trades)
    return portfolio, trades

# ===== 統計分析 =====
def calc_stats(trades):
    closed = [t for t in trades if t.get('return_pct') is not None and t.get('exit_reason')]
    if not closed:
        return None
    rets   = [t['return_pct'] for t in closed]
    wins   = [r for r in rets if r > 0]
    losses = [r for r in rets if r <= 0]
    n      = len(rets)

    total = sum(rets)
    wr    = len(wins) / n * 100 if n else 0
    avg   = total / n if n else 0
    avg_w = sum(wins) / len(wins) if wins else 0
    avg_l = sum(losses) / len(losses) if losses else 0
    pl    = abs(avg_w / avg_l) if avg_l != 0 else 0

    if n > 1:
        rf    = 0.01 / 252
        exc   = [r/100 - rf for r in rets]
        sharpe = np.mean(exc) / np.std(exc) * np.sqrt(252) if np.std(exc) > 0 else 0
    else:
        sharpe = 0

    cum   = np.cumsum(rets)
    peak  = np.maximum.accumulate(cum)
    dd    = peak - cum
    max_dd = float(np.max(dd)) if len(dd) > 0 else 0

    tp_c  = sum(1 for t in closed if t['exit_reason'] == 'take_profit')
    sl_c  = sum(1 for t in closed if t['exit_reason'] == 'stop_loss')
    ma20_c= sum(1 for t in closed if t['exit_reason'] == 'ma20_broken')
    hold_c= sum(1 for t in closed if t['exit_reason'] == 'hold_expired')

    return {
        'total_trades': n,
        'wr':       round(wr, 2),
        'avg_return': round(avg, 3),
        'total_return': round(total, 2),
        'avg_win':  round(avg_w, 2),
        'avg_loss': round(avg_l, 2),
        'pl_ratio': round(pl, 3),
        'sharpe':   round(sharpe, 3),
        'max_dd':   round(max_dd, 2),
        'max_gain': round(max(rets), 2) if rets else 0,
        'max_loss': round(min(rets), 2) if rets else 0,
        'tp_count': tp_c,
        'sl_count': sl_c,
        'ma20_count': ma20_c,
        'hold_count': hold_c,
    }

# ===== 主程式 =====
def run_sim_trade(mode='full'):
    print('=' * 65)
    print('  Nana v7.0 — 模擬交易追蹤系統')
    print('  時間：' + datetime.now().strftime('%Y-%m-%d %H:%M'))
    print('=' * 65)

    # 嘗試讀取 nana_v64 cache
    cached = load_candidates()

    if cached:
        print(f'已讀取 nana_v64 scan_cache，共 {len(cached)} 檔')
        candidates = sorted(cached, key=lambda x: x.get('score', 0), reverse=True)
        print(f'  取前 {min(10, len(candidates))} 檔候選：')
        for c in candidates[:10]:
            print(f"  {c.get('symbol','')}  score={c.get('score',0)}  "
                  f"RSI={c.get('rsi','')}  price={c.get('price','')}")
    else:
        print('Cache 不存在或無效，執行當日掃描...')
        candidates = scan_candidates()
        print(f'掃描完成，共 {len(candidates)} 檔合格')

    # 載入持倉與交易記錄
    portfolio = load_portfolio()
    trades    = load_trades()

    print(f'\n目前持倉：{len(portfolio.get("positions", []))} 檔')
    print(f'歷史交易：{len(trades)} 筆')

    # 更新持倉（檢查停利/停損）
    print('\n更新持倉中...')
    portfolio, closed = update_positions(portfolio, trades)
    if closed:
        print(f'  本次關閉 {len(closed)} 筆：')
        for t in closed:
            print(f"  {t['symbol']} {t['exit_reason']} 報酬率={t['return_pct']:.2f}%")

    # 進場
    print('\n進場評估...')
    portfolio, trades = enter_positions(candidates, portfolio, trades)

    # 顯示持倉
    pos_list = portfolio.get('positions', [])
    print(f'\n目前持倉（{len(pos_list)} 檔）：')
    print(f'{"CODE":<6} {"名稱":<8} {"進場价":<9} {"現价":<8} {"停利":<8} {"停損":<8} {"MA20停":<8} {"浮盈%":<7} {"天數":<5}')
    print('  ' + '-' * 73)
    for p in pos_list:
        print(f"  {p['symbol']:<6} {p.get('name',''):<8} "
              f"{p['entry_price']:<9.2f} {p.get('current_price', p['entry_price']):<8.2f} "
              f"{p['target']:<8.2f} {p['stop']:<8.2f} {p.get('ma20_stop',0):<8.2f} "
              f"{p.get('unrealized_pct',0):<7.2f} {p.get('day_count',0):<5}")

    # 統計
    stats = calc_stats(trades)
    if stats:
        print('\n' + '=' * 65)
        print('  模擬交易統計（已關閉倉位）')
        print('=' * 65)
        print(f'  總交易次數：{stats["total_trades"]}')
        print(f'  勝率（WR）：{stats["wr"]}%')
        print(f'  平均報酬率：{stats["avg_return"]}%')
        print(f'  總報酬率：{stats["total_return"]}%')
        print(f'  平均獲利：{stats["avg_win"]}%')
        print(f'  平均虧損：{stats["avg_loss"]}%')
        print(f'  盈虧比：{stats["pl_ratio"]}')
        print(f'  Sharpe：{stats["sharpe"]}')
        print(f'  最大Drawdown：{stats["max_dd"]}%')
        print(f'  停利：{stats["tp_count"]} 次')
        print(f'  停損：{stats["sl_count"]} 次')
        print(f'  MA20跌破：{stats["ma20_count"]} 次')
        print(f'  持有期滿：{stats["hold_count"]} 次')

    print(f'\n  持倉檔案：{PORTFOLIO_FILE}')
    print(f'  交易記錄：{TRADES_FILE}')

    return portfolio, trades, stats

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', default='full', choices=['full', 'update', 'scan'])
    args = parser.parse_args()
    run_sim_trade(args.mode)