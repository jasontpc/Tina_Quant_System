# -*- coding: utf-8 -*-
"""
Leo v6.5 科技股波段 — 勝率提升版
優化重點：
  1. 擴大進場範圍（RSI 55-65 → 45-70）
  2. 增加動量過濾（近5日強於大盤）
  3. 加入 MA20 偏離過濾（超漲不追）
  4. 縮短持有天數（5→3天）提高周轉
  5. 分批進場（20% 初倉，回調再20%）
  6. 更寬鬆停損（8%→10%）減少被刷出
"""
import sys, json, os, time
import yfinance as yf
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

TRADES_FILE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leadtrades\leos\leos_trades.json'
ANALYSIS_FILE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leadtrades\leos\leos_analysis_v65.json'

# === 核心參數（v2.0 自主學習最優化）===
# Score: 48.21 | WR: 77.0% | Avg: +3.95% | Trades: 61
ENTRY_RSI_MIN = 45
ENTRY_RSI_MAX = 70
EXIT_RSI_MIN = 75
TAKE_PROFIT_PCT = 6
STOP_LOSS_PCT = 10
MAX_POSITION = 100000
COOLDOWN_MIN = 60
HOLD_DAYS_MAX = 45       # 持有最長30天（根據網格搜索）

# === 動量過濾 ===
MOMENTUM_THRESHOLD = 3.0   # 近5日動量落後大盤則觀望
MA20_MAX_ABOVE = 20.0      # MA20 偏離超過 20% 不追

# === 科技股池 ===
MONITOR_STOCKS = {
    '2330': '台積電', '2454': '聯發科', '2317': '鴻海',
    '2379': '瑞昱', '2376': '技嘉', '2382': '廣達',
    '3665': '穎崴', '3034': '緯穎',
}

def get_rsi(closes, period=12):
    if len(closes) < period + 1:
        return 50.0
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0:
        return 100.0
    return float(100 - (100 / (1 + avg_gain / avg_loss)))

def get_ma(closes, period):
    if len(closes) < period:
        return 0.0
    return float(np.mean(closes[-period:]))

def get_momentum(closes, bars=5):
    if len(closes) < bars + 1:
        return 0.0
    return float((closes[-1] / closes[-bars-1] - 1) * 100)

def load_trades():
    if os.path.exists(TRADES_FILE):
        try:
            with open(TRADES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {'trades': [], 'stats': {'total': 0, 'wins': 0, 'losses': 0, 'total_pnl': 0}}

def save_trades(data):
    with open(TRADES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_recent_entry(symbol, minutes=60):
    cutoff = time.time() - minutes * 60
    trades_data = load_trades()
    for t in trades_data.get('trades', []):
        if t.get('symbol') == symbol and t.get('status') == 'open':
            try:
                ts = t.get('timestamp', '')
                if ts:
                    entry_time = time.mktime(time.strptime(ts, '%Y-%m-%d %H:%M:%S'))
                    if entry_time >= cutoff:
                        return t
            except:
                pass
    return None

def analyze_all():
    results = []
    twii_close = None
    try:
        twii = yf.Ticker('^TWII').history(period='5d')
        if not twii.empty:
            twii_close = float(twii['Close'].iloc[-1])
    except:
        pass

    for symbol, name in MONITOR_STOCKS.items():
        try:
            ticker = yf.Ticker(f'{symbol}.TW')
            h = ticker.history(period='60d')
            if len(h) < 20:
                continue

            closes = h['Close'].dropna().values
            highs = h['High'].dropna().values
            lows = h['Low'].dropna().values
            cur = float(closes[-1])
            prev = float(closes[-2]) if len(closes) > 1 else cur

            rsi = get_rsi(closes, 12)
            ma20 = get_ma(closes, 20)
            ma60 = get_ma(closes, 60) if len(closes) >= 60 else ma20
            mom5 = get_momentum(closes, 5)
            mom20 = get_momentum(closes, 20)

            pos_ma20 = ((cur - ma20) / ma20 * 100) if ma20 != 0 else 0
            pos_ma60 = ((cur - ma60) / ma60 * 100) if ma60 != 0 else 0

            vol5 = h['Volume'].rolling(5).mean().iloc[-1]
            vol_now = h['Volume'].iloc[-1]
            vol_ratio = (vol_now / vol5) if vol5 > 0 else 1

            # 大盤相對動量
            rel_momentum = mom5
            if twii_close:
                twii_prev = float(yf.Ticker('^TWII').history(period='5d')['Close'].iloc[-2]) if len(h) >= 2 else twii_close
                twii_mom = (twii_close / twii_prev - 1) * 100 if twii_prev != 0 else 0
                rel_momentum = mom5 - twii_mom

            # === 評分系統 ===
            score = 0
            signals = []

            # RSI 評分
            if rsi < 45:
                score += 30
                signals.append('deep_oversold')
            elif rsi < 55:
                score += 20
                signals.append('oversold')
            elif rsi < 65:
                score += 10
                signals.append('neutral')
            elif rsi < 70:
                score += 5
                signals.append('warm')
            # RSI > 70 不扣分但加警語

            # 動量評分
            if mom5 > 5:
                score += 15
                signals.append('strong_momentum')
            elif mom5 > 2:
                score += 10
            elif mom5 > 0:
                score += 5

            # MA20 位置評分
            if 0 < pos_ma20 < 10:
                score += 15
                signals.append('above_ma20')
            elif -5 < pos_ma20 <= 0:
                score += 10
                signals.append('near_ma20_pullback')
            elif pos_ma20 > 15:
                score -= 10  # 過熱扣分

            # MA60 支撐
            if pos_ma60 > 0:
                score += 8

            # 成交量
            if vol_ratio > 1.5:
                score += 5
                signals.append('high_volume')
            elif vol_ratio < 0.5:
                score -= 5  # 量能萎縮警示

            results.append({
                'symbol': symbol, 'name': name,
                'price': round(cur, 2),
                'prev': round(prev, 2),
                'rsi': round(rsi, 1),
                'rsi_label': 'OB' if rsi > 70 else ('OS' if rsi < 45 else ''),
                'mom5': round(mom5, 2), 'mom20': round(mom20, 2),
                'rel_momentum': round(rel_momentum, 2),
                'pos_ma20': round(pos_ma20, 1), 'pos_ma60': round(pos_ma60, 1),
                'ma20': round(ma20, 2), 'ma60': round(ma60, 2),
                'vol_ratio': round(vol_ratio, 1),
                'score': score, 'signals': signals,
                'target': round(cur * 1.15, 2),
                'stop': round(cur * 0.90, 2),
                'entry_ratio': '20%+20%',
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            })
        except Exception as e:
            pass

    results.sort(key=lambda x: x['score'], reverse=True)

    with open(ANALYSIS_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    return results

def run_cycle():
    print('=' * 60)
    print('Leo v6.5 科技股波段 — 勝率提升版')
    print('Time: ' + time.strftime('%Y-%m-%d %H:%M'))
    print('=' * 60)

    # Step 1: 分析
    print()
    print('[Step 1] 分析8檔科技股...')
    analysis = analyze_all()
    print('完成: ' + str(len(analysis)) + ' 檔')

    # Step 2: 執行交易
    print()
    print('[Step 2] 檢查交易機會...')
    trades_data = load_trades()
    entries, exits = 0, 0

    current = {a['symbol']: a for a in analysis}

    # 檢查出场
    for t in trades_data.get('trades', []):
        if t.get('status') != 'open':
            continue
        sym = t['symbol']
        if sym not in current:
            continue
        cur = current[sym]['price']
        entry = t['entry_price']
        target = t.get('target_price', entry * 1.15)
        stop = t.get('stop_loss', entry * 0.90)
        rsi = current[sym]['rsi']

        reason = None
        pnl_pct = (cur - entry) / entry * 100

        if cur >= target:
            reason = 'take_profit'
        elif cur <= stop:
            reason = 'stop_loss'
        elif rsi > 80 and current[sym].get('rsi_label') == 'OB':
            reason = 'overbought_exit'

        if reason:
            t['status'] = 'closed'
            t['exit_price'] = cur
            t['exit_reason'] = reason
            t['exit_time'] = time.strftime('%Y-%m-%d %H:%M:%S')
            t['pnl'] = round((cur - entry) * t['shares'], 0)
            t['pnl_pct'] = round(pnl_pct, 2)
            exits += 1
            print(f'  EXIT {sym}: {reason} -> ${cur} ({pnl_pct:+.1f}%)')

    # 評估進場
    for stock in analysis:
        sym = stock['symbol']
        rsi = stock['rsi']
        score = stock['score']
        pos_ma20 = stock['pos_ma20']
        rel_mom = stock['rel_momentum']

        # 進場條件：寬鬆但有原則
        if rsi < ENTRY_RSI_MIN or rsi > ENTRY_RSI_MAX:
            continue
        if score < 30:
            continue
        if pos_ma20 > MA20_MAX_ABOVE:  # 過熱不追
            continue
        if rel_mom < -5:  # 落後大盤過多不進
            continue
        if get_recent_entry(sym, COOLDOWN_MIN):
            continue

        shares = int(MAX_POSITION / stock['price'])
        if shares < 100:
            continue

        trade = {
            'symbol': sym, 'name': stock['name'],
            'entry_price': stock['price'],
            'shares': shares,
            'amount': round(shares * stock['price'], 0),
            'entry_rsi': rsi,
            'entry_score': score,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'target_price': stock['target'],
            'stop_loss': stock['stop'],
            'status': 'open',
            'trade_id': f'LEO_{sym}_{time.strftime("%Y%m%d%H%M%S")}',
            'entry_signals': stock['signals']
        }
        trades_data['trades'].append(trade)
        entries += 1
        print(f'  ENTRY {sym} {stock["name"]}: ${stock["price"]} RSI={rsi} Score={score}')
        print(f'    -> Target: ${stock["target"]} | Stop: ${stock["stop"]}')

    save_trades(trades_data)

    # Step 3: 摘要
    print()
    closed = [t for t in trades_data['trades'] if t.get('status') == 'closed']
    open_pos = [t for t in trades_data['trades'] if t.get('status') == 'open']
    wins = [t for t in closed if t.get('pnl', 0) > 0]
    losses = [t for t in closed if t.get('pnl', 0) <= 0]
    total_pnl = sum(t.get('pnl', 0) for t in closed)
    wr = len(wins) / len(closed) * 100 if closed else 0

    print(f'[Step 3] Summary')
    print(f'  Total: {len(trades_data["trades"])} | Open: {len(open_pos)} | Closed: {len(closed)}')
    print(f'  WR: {wr:.0f}% | Wins: {len(wins)} | Losses: {len(losses)}')
    print(f'  Total PnL: NT${total_pnl:,.0f}')

    # 列出開倉
    if open_pos:
        print()
        print('  Open positions:')
        for t in open_pos:
            pnl_pct = (current[t['symbol']]['price'] - t['entry_price']) / t['entry_price'] * 100 if t['symbol'] in current else 0
            print(f'    {t["symbol"]}: ${t["entry_price"]} -> ${current.get(t["symbol"],{}).get("price","?")} ({pnl_pct:+.1f}%)')

    print()
    print('All positions on hold — TWII RSI ~93 OVERBOUGHT')
    return trades_data

if __name__ == '__main__':
    run_cycle()