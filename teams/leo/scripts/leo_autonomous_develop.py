# -*- coding: utf-8 -*-
"""
Leo 自主學習開發系統 v1.1（修復版）
功能：
  1. 自動學習AI/科技股相關技能與知識
  2. 自動模擬波段交易並學習（虛擬倉位）
  3. 自動回測歷史個股驗證策略
  4. 根據結果自動調整波段參數
  5. 記錄學習成果到 leo_learnings.json
"""

import sys, os, json, yfinance as yf, pandas as pd, numpy as np
from datetime import datetime, date, timedelta
from typing import Dict, List

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leo'
LEO_DIR = os.path.join(BASE_DIR, 'reports')
LEARNINGS_FILE = os.path.join(LEO_DIR, 'leo_learnings.json')
EVOLUTIONS_FILE = os.path.join(LEO_DIR, 'leo_evolutions.json')
SIM_TRADES_FILE = os.path.join(LEO_DIR, 'leo_sim_trades.json')

# AI/科技股觀察名單
AI_STOCKS = {
    '2330': '台積電', '2454': '聯發科', '2379': '瑞昱',
    '2376': '技嘉', '2382': '廣達', '3665': '穎崴',
}

# 波段策略參數
SWING_PARAMS = {
    'entry_rsi_max': 65,
    'exit_rsi_min': 80,
    'take_profit_pct': 20.0,
    'stop_loss_pct': 8.0,
    'max_position': 100000,
    'cooldown_minutes': 30,
    'entry_pos_ma20_max': 15,
}

# ── 共用技術指標計算 ─────────────────────
def calc_rsi(series: pd.Series, period: int = 14) -> float:
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    if loss.iloc[-1] > 0:
        return float(100 - (100 / (1 + gain.iloc[-1] / loss.iloc[-1])))
    elif gain.iloc[-1] > 0:
        return 100.0
    return 50.0

# ── 學習市場知識 ───────────────────────────────
def learn_market_knowledge():
    """自動學習市場知識"""
    print('[Step 1] 學習市場知識...')
    learnings = []

    # 學習大盤狀態
    twii = yf.Ticker('^TWII').history(period='1mo')
    if len(twii) > 0:
        closes = twii['Close'].dropna()
        rsi = calc_rsi(closes)
        ma20 = closes.rolling(20).mean().iloc[-1]
        ma60 = closes.rolling(60).mean().iloc[-1] if len(closes) >= 60 else ma20

        regime = 'BULL' if ma20 > ma60 and rsi > 50 else 'BEAR' if ma20 < ma60 and rsi < 50 else 'NEUTRAL'
        if rsi > 80: regime = 'OVERBOUGHT'
        elif rsi < 40: regime = 'OVERSOLD'

        yr = closes.max() - closes.min()
        position = (closes.iloc[-1] - closes.min()) / yr * 100 if yr > 0 else 50

        learnings.append({
            'type': 'market_state',
            'regime': regime,
            'rsi': round(rsi, 1),
            'position': round(position, 1),
        })
        print(f'  大盤: {regime} (RSI={rsi:.1f}, 位置={position:.0f}%)')

    # 學習個股知識（直接附在learnings，不重fetch）
    for symbol, name in AI_STOCKS.items():
        ticker = yf.Ticker(f'{symbol}.TW')
        try:
            h = ticker.history(period='6mo')
            if len(h) < 50:
                continue
            c = h['Close'].dropna()
            last = c.iloc[-1]
            ma20 = c.rolling(20).mean().iloc[-1]
            rsi = calc_rsi(c)
            pos_ma20 = (last - ma20) / ma20 * 100

            learnings.append({
                'type': 'stock_info',
                'symbol': symbol,
                'name': name,
                'price': round(float(last), 2),
                'rsi': round(rsi, 1),
                'pos_ma20': round(float(pos_ma20), 1),
            })
            print(f'  {symbol} {name}: RSI={rsi:.1f}, 偏離MA20={pos_ma20:+.1f}%')
        except:
            pass

    # 學習BIAS離場規則
    learnings.append({
        'type': 'swing_rule',
        'desc': 'BIAS>5%時離場，歷史勝率97.4%',
        'source': 'Nana v5.39',
    })

    # 學習波段知識
    swing_knowledge = {
        'entry_rsi_max': SWING_PARAMS['entry_rsi_max'],
        'exit_rsi_min': SWING_PARAMS['exit_rsi_min'],
        'take_profit_pct': SWING_PARAMS['take_profit_pct'],
        'stop_loss_pct': SWING_PARAMS['stop_loss_pct'],
        'note': '波段操作1-3個月，目標+20%停損-8%'
    }
    learnings.append({'type': 'swing_knowledge', 'data': swing_knowledge})

    save_learnings(learnings)
    print(f'  完成: {len(learnings)}項知識')
    return learnings

def save_learnings(learnings: List[Dict]):
    existing = []
    if os.path.exists(LEARNINGS_FILE):
        with open(LEARNINGS_FILE, 'r', encoding='utf-8') as f:
            existing = json.load(f)
    existing.extend(learnings)
    with open(LEARNINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(existing[-100:], f, ensure_ascii=False, indent=2)

# ── 分析個股 ───────────────────────────────
def analyze_ai_stocks():
    """分析AI/科技股（不重fetch，直接分析）"""
    print('[Step 2] 分析AI/科技股...')
    results = []

    for symbol, name in AI_STOCKS.items():
        ticker = yf.Ticker(f'{symbol}.TW')
        try:
            h = ticker.history(period='6mo')
            if len(h) < 50:
                continue
            c = h['Close'].dropna()
            last = c.iloc[-1]
            ma20 = c.rolling(20).mean().iloc[-1]
            ma60 = c.rolling(60).mean().iloc[-1] if len(c) >= 60 else ma20
            rsi_val = calc_rsi(c)
            vol_now = h['Volume'].iloc[-1]
            vol_ma5 = h['Volume'].rolling(5).mean().iloc[-1]
            from_high = (last - c.max()) / c.max() * 100
            pos_ma20 = (last - ma20) / ma20 * 100

            results.append({
                'symbol': symbol, 'name': name,
                'price': round(float(last), 2),
                'rsi': round(float(rsi_val), 1),
                'pos_ma20': round(float(pos_ma20), 1),
                'ma20': round(float(ma20), 2),
                'ma60': round(float(ma60), 2),
                'from_high': round(float(from_high), 1),
                'vol_ratio': round(float(vol_now / vol_ma5), 2) if vol_ma5 > 0 else 1.0,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
            })
        except Exception as e:
            pass

    # 保存分析
    with open(os.path.join(LEO_DIR, 'leo_analysis.json'), 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f'  完成: {len(results)}檔')
    return results

# ── 模擬波段交易 ─────────────────────────────
def run_simulated_swing_trading(analysis):
    """模擬波段交易（接收已分析的結果）"""
    print('[Step 3] 模擬波段交易...')

    sim_data = {'trades': [], 'open_positions': [], 'stats': {}}
    if os.path.exists(SIM_TRADES_FILE):
        with open(SIM_TRADES_FILE, 'r', encoding='utf-8') as f:
            sim_data = json.load(f)

    open_pos = sim_data.get('open_positions', [])
    current = {a['symbol']: a for a in analysis}

    # 檢查持倉出场
    for pos in list(open_pos):
        sym = pos['symbol']
        if sym not in current:
            continue

        cur = current[sym]['price']
        entry = pos['entry_price']
        target = entry * (1 + SWING_PARAMS['take_profit_pct'] / 100)
        stop = entry * (1 - SWING_PARAMS['stop_loss_pct'] / 100)
        rsi = current[sym]['rsi']

        reason = None
        if cur >= target:
            reason = 'take_profit'
        elif cur <= stop:
            reason = 'stop_loss'
        elif rsi > 85 and pos.get('entry_rsi', 0) > 75:
            reason = 'overheat_exit'

        if reason:
            ret_pct = (cur - entry) / entry * 100
            sim_data['trades'].append({
                'symbol': sym, 'name': pos['name'],
                'entry_price': entry, 'exit_price': cur,
                'return_pct': round(ret_pct, 2),
                'exit_reason': reason,
                'hold_days': pos.get('hold_days', 0),
                'trade_type': 'sim',
            })
            open_pos.remove(pos)
            print(f'  出場 {sym}: {reason} @ ${cur} ({ret_pct:+.1f}%)')

    # 檢查新進場
    for stock in analysis:
        sym = stock['symbol']
        rsi = stock['rsi']
        pos_ma20 = stock['pos_ma20']

        if rsi >= 40 and rsi <= SWING_PARAMS['entry_rsi_max'] and abs(pos_ma20) < SWING_PARAMS['entry_pos_ma20_max']:
            if not any(p['symbol'] == sym for p in open_pos):
                shares = int(SWING_PARAMS['max_position'] / stock['price'])
                pos = {
                    'symbol': sym, 'name': stock['name'],
                    'entry_price': stock['price'],
                    'shares': shares,
                    'entry_rsi': rsi,
                    'entry_pos_ma20': pos_ma20,
                    'entry_date': str(date.today()),
                    'hold_days': 0,
                }
                open_pos.append(pos)
                print(f'  進場 {sym} {stock["name"]}: ${stock["price"]} (RSI={rsi})')

    sim_data['open_positions'] = open_pos

    # 統計
    closed = [t for t in sim_data['trades'] if t.get('trade_type') == 'sim']
    wins = [t for t in closed if t.get('return_pct', 0) > 0]
    win_rate = len(wins) / len(closed) * 100 if closed else 0
    avg_ret = sum(t.get('return_pct', 0) for t in closed) / len(closed) if closed else 0

    sim_data['stats'] = {
        'total_trades': len(closed),
        'win_rate': round(win_rate, 1),
        'avg_return': round(avg_ret, 2),
        'open_positions': len(open_pos),
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M'),
    }

    with open(SIM_TRADES_FILE, 'w', encoding='utf-8') as f:
        json.dump(sim_data, f, ensure_ascii=False, indent=2)

    print(f'  持倉: {len(open_pos)}檔 | 勝率: {win_rate:.0f}% | 均報酬: {avg_ret:.2f}%')
    return sim_data

# ── 回測歷史 ─────────────────────────────
def backtest_swing_strategy():
    """回測波段策略"""
    print('[Step 4] 回測波段策略...')

    ticker = yf.Ticker('2330.TW').history(period='2y')
    if len(ticker) < 200:
        print('  數據不足')
        return None

    c = ticker['Close'].dropna()
    ma20 = c.rolling(20).mean()
    rsi_series = pd.Series([calc_rsi(c.iloc[:i+1]) for i in range(len(c))], index=c.index)

    trades = []
    position = None
    entry_price = 0
    entry_rsi = 0

    for i in range(60, len(c)):
        r = rsi_series.iloc[i]
        m20 = ma20.iloc[i]
        cur = c.iloc[i]

        if position is None:
            if r < 65 and abs((cur - m20) / m20 * 100) < 15:
                position = {'entry_price': cur, 'entry_rsi': r, 'entry_date': c.index[i]}
        else:
            exit_price = cur
            if entry_price > 0:
                ret = (exit_price - entry_price) / entry_price * 100
            else:
                ret = 0.0

            if r > 80 or ret >= 20 or ret <= -8:
                trades.append({
                    'entry_date': str(position['entry_date'].date()),
                    'exit_date': str(c.index[i].date()),
                    'return_pct': round(ret, 2),
                    'exit_reason': 'rsi_exit' if r > 80 else 'profit' if ret >= 20 else 'stop_loss',
                })
                position = None

    if trades:
        wins = [t for t in trades if t['return_pct'] > 0]
        win_rate = len(wins) / len(trades) * 100 if trades else 0
        avg_ret = sum(t['return_pct'] for t in trades) / len(trades) if trades else 0

        result = {
            'total_trades': len(trades),
            'win_rate': round(win_rate, 1),
            'avg_return': round(avg_ret, 2),
            'max_gain': round(max(t['return_pct'] for t in trades), 2) if trades else 0,
            'max_loss': round(min(t['return_pct'] for t in trades), 2) if trades else 0,
        }
        print(f'  回測: {len(trades)}筆 | 勝率={win_rate:.0f}% | 均報酬={avg_ret:.2f}%')
        return result
    return None

# ── 迭代優化 ─────────────────────────────
def iterate_optimize():
    """迭代優化策略"""
    print('[Step 5] 迭代優化...')

    evolutions = []
    if os.path.exists(EVOLUTIONS_FILE):
        with open(EVOLUTIONS_FILE, 'r', encoding='utf-8') as f:
            evolutions = json.load(f)

    new_evo = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'iteration': len(evolutions) + 1,
        'learnings': [],
        'param_changes': [],
    }

    # 分析表現
    if os.path.exists(SIM_TRADES_FILE):
        with open(SIM_TRADES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            stats = data.get('stats', {})

            wr = stats.get('win_rate', 0)
            if wr < 40:
                new_evo['learnings'].append('勝率過低，收緊進場條件')
                new_evo['param_changes'].append({'param': 'entry_rsi_max', 'from': 65, 'to': 60})
            elif wr >= 60:
                new_evo['learnings'].append('勝率優秀，可適度放寬進場')
                new_evo['param_changes'].append({'param': 'entry_rsi_max', 'from': 65, 'to': 70})

    evolutions.append(new_evo)
    with open(EVOLUTIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(evolutions[-20:], f, ensure_ascii=False, indent=2)

    print(f'  迭代 #{new_evo["iteration"]}: {len(new_evo["learnings"])}項學習')
    return new_evo

# ── 主循環 ───────────────────────────────
def run_autonomous_development():
    print('=' * 60)
    print('  Leo 自主學習開發系統 v1.1')
    print(f'  時間: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('=' * 60)

    # Step 1: 學習
    learnings = learn_market_knowledge()

    # Step 2: 分析
    analysis = analyze_ai_stocks()

    # Step 3: 模擬波段交易（傳入已分析結果，不重fetch）
    sim = run_simulated_swing_trading(analysis)

    # Step 4: 回測
    backtest = backtest_swing_strategy()

    # Step 5: 迭代優化
    evo = iterate_optimize()

    print()
    print('=' * 60)
    print('  學習完成')
    print('=' * 60)
    print(f'  新知識: {len(learnings)}項')
    print(f'  分析: {len(analysis)}檔')
    print(f'  勝率: {sim["stats"]["win_rate"]}%')
    print(f'  回測: {"有效" if backtest and backtest["win_rate"] > 50 else "待觀察"}')
    print(f'  迭代: {evo["iteration"]}次')

    return {'learnings': learnings, 'analysis': analysis, 'sim': sim, 'backtest': backtest, 'evo': evo}

if __name__ == '__main__':
    run_autonomous_development()
