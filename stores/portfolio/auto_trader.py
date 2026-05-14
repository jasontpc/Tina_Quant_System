"""
Tina 模擬倉自動交易引擎 v1.0
stores/portfolio/auto_trader.py

功能：
- 每小時自動抓取最新股價
- 運行 exit_engine 評分
- 根據門檻自動調整倉位（模拟仓）
- 記錄所有交易動作到 trades.log
- 每筆決策寫入 exit_decisions.json（用於學習）

用法：
  python auto_trader.py --mode update    # 只更新+評分，輸出建議
  python auto_trader.py --mode execute   # 更新+評分+自動執行
  python auto_trader.py --mode status    # 顯示當前狀態
"""

import yfinance as yf
import pandas as pd
import json
import os
import sys
from datetime import datetime

# === 路徑設定 ===
BASE_DIR = os.path.dirname(__file__)
POSITIONS_PATH = os.path.join(BASE_DIR, 'positions.json')
TRADES_LOG = os.path.join(BASE_DIR, 'trades.log')
EXIT_DECISIONS = os.path.join(BASE_DIR, 'exit_decisions.json')
SETTINGS_PATH = os.path.join(BASE_DIR, 'auto_trader_settings.json')

# === 評分門檻 ===
EXIT_NOW_THRESHOLD = 70    # 立即出场（分數）
EXIT_HALF_THRESHOLD = 50   # 卖出一半
WATCH_THRESHOLD = 30        # 密切關注

# === 自動執行開關 ===
AUTO_EXECUTE = False  # 預設建議模式，True 時自動執行

# ============================================================
# 技術指標計算
# ============================================================
def get_tech(symbol):
    try:
        df = yf.download(symbol, period='60d', interval='1d', auto_adjust=True, progress=False, timeout=10)
        if df.empty or len(df) < 30:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        close = df['Close']
        high = df['High']
        low = df['Low']

        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = float((100 - (100/(1+rs))).iloc[-1])

        ema_fast = close.ewm(span=12).mean()
        ema_slow = close.ewm(span=26).mean()
        macd_s = ema_fast - ema_slow
        sig = macd_s.ewm(span=9).mean()
        macd_hist = float((macd_s - sig).iloc[-1])
        macd_hist_prev = float((macd_s - sig).iloc[-2])

        low_min = low.rolling(9).min()
        high_max = high.rolling(9).max()
        rsv = (close - low_min) / (high_max - low_min) * 100
        K = rsv.ewm(alpha=1/3).mean()
        D = K.ewm(alpha=1/3).mean()
        J = 3*K - 2*D
        k_val = float(K.iloc[-1])
        d_val = float(D.iloc[-1])
        j_val = float(J.iloc[-1])

        return {
            'price': float(close.iloc[-1]),
            'rsi': rsi,
            'macd_hist': macd_hist,
            'macd_hist_prev': macd_hist_prev,
            'kdj_K': k_val,
            'kdj_D': d_val,
            'kdj_J': j_val,
            'ma5': float(close.iloc[-5]),
            'ma20': float(close.iloc[-20]),
            'ma60': float(close.iloc[-60]) if len(close) >= 60 else None,
        }
    except Exception as e:
        print(f"  ERROR fetching {symbol}: {e}")
        return None

# ============================================================
# 評分系統（整合 exit_engine）
# ============================================================
def score_position(pos, twii_rsi=None):
    """計算單一持倉的出场分數（0-100）"""
    lc = pos.get('last_check', {})
    rsi = lc.get('rsi', 50)
    macd_hist = lc.get('macd_hist', 0)
    price = lc.get('price', 0)
    ma5 = lc.get('ma5', 0)
    ma20 = lc.get('ma20', 0)
    pnl = lc.get('pnl_pct', 0)
    j_val = lc.get('kdj_J', 50)
    k_val = lc.get('kdj_K', 50)
    d_val = lc.get('kdj_D', 50)
    twii = twii_rsi or 50

    score = 0
    signals = []

    # RSI
    if rsi > 75: score += 25; signals.append(f'RSI>{rsi:.0f}')
    elif rsi > 70: score += 15; signals.append(f'RSI>{rsi:.0f}')
    elif rsi > 65: score += 5; signals.append(f'RSI>{rsi:.0f}')

    # KDJ
    if j_val > 90: score += 10; signals.append(f'J>{j_val:.0f}')
    if k_val < d_val: score += 5; signals.append('K<D死叉')

    # MACD
    if macd_hist < 0: score += 15; signals.append(f'MACD<0')

    # 價格
    if price < ma5: score += 10; signals.append('belowMA5')
    if price < ma20: score += 10; signals.append('belowMA20')

    # 市場
    if twii > 82: score += 15; signals.append(f'TWII_RSI>{twii:.0f}')
    elif twii > 78: score += 8; signals.append(f'TWII_RSI>{twii:.0f}')

    # PnL
    if pnl >= 8: score += 10; signals.append(f'PnL+{pnl:.1f}%>=8%')
    elif pnl <= -8: score += 10; signals.append(f'StopLoss')
    elif pnl <= -5: score += 5; signals.append(f'PnLWarn')

    # 信號
    if score >= EXIT_NOW_THRESHOLD: signal = 'EXIT_NOW'
    elif score >= EXIT_HALF_THRESHOLD: signal = 'EXIT_HALF'
    elif score >= WATCH_THRESHOLD: signal = 'WATCH'
    else: signal = 'HOLD'

    return {'score': score, 'signal': signal, 'signals': signals}

# ============================================================
# 更新持倉數據
# ============================================================
def update_positions():
    with open(POSITIONS_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"[{datetime.now().strftime('%H:%M')}] 更新持倉資料...")
    twii_tech = get_tech('^TWII')
    twii_rsi = twii_tech['rsi'] if twii_tech else None

    for pos in data['positions']:
        sym = pos['symbol']
        tech = get_tech(sym)
        if not tech:
            print(f"  {sym}: 抓取失敗，跳過")
            continue

        price = tech['price']
        pnl = (price - pos['cost']) / pos['cost'] * 100
        now = datetime.now().strftime('%Y-%m-%d %H:%M')

        pos['last_check']['date'] = now
        pos['last_check']['price'] = round(price, 1)
        pos['last_check']['rsi'] = round(tech['rsi'], 1)
        pos['last_check']['macd_hist'] = round(tech['macd_hist'], 2)
        pos['last_check']['kdj_K'] = round(tech['kdj_K'], 1)
        pos['last_check']['kdj_D'] = round(tech['kdj_D'], 1)
        pos['last_check']['kdj_J'] = round(tech['kdj_J'], 1)
        pos['last_check']['ma5'] = round(tech['ma5'], 1)
        pos['last_check']['ma20'] = round(tech['ma20'], 1)
        pos['last_check']['ma60'] = round(tech['ma60'], 1) if tech['ma60'] else None
        pos['last_check']['pnl_pct'] = round(pnl, 1)

        # 評分
        result = score_position(pos, twii_rsi)
        pos['auto_score'] = result['score']
        pos['auto_signal'] = result['signal']
        pos['auto_signals'] = result['signals']

        print(f"  {sym}: {price:.1f} | RSI={tech['rsi']:.0f} J={tech['kdj_J']:.0f} | PnL={pnl:+.1f}% | Score={result['score']} {result['signal']}")

    with open(POSITIONS_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  TWII RSI: {twii_rsi:.1f}")
    return data, twii_rsi

# ============================================================
# 交易記錄
# ============================================================
def log_trade(symbol, action, qty, price, reason):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M')
    line = f"[{ts}] {symbol} | ACTION: {action} | QTY: {qty} | PRICE: {price} | REASON: {reason}\n"
    with open(TRADES_LOG, 'a', encoding='utf-8') as f:
        f.write(line)

def log_decision(pos, signal, score, auto=False):
    path = EXIT_DECISIONS
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = {'decisions': []}

    entry = {
        'timestamp': datetime.now().isoformat(),
        'symbol': pos['symbol'],
        'price': pos['last_check']['price'],
        'cost': pos['cost'],
        'pnl_pct': pos['last_check']['pnl_pct'],
        'rsi': pos['last_check']['rsi'],
        'kdj_J': pos['last_check']['kdj_J'],
        'macd_hist': pos['last_check']['macd_hist'],
        'score': score,
        'signal': signal,
        'auto': auto,
        'actual_result': None  # 事後填入
    }
    data['decisions'].append(entry)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ============================================================
# 自動執行
# ============================================================
def execute_actions(data, dry_run=True):
    """根據評分結果自動執行（或dry-run）"""
    executed = []

    for pos in data['positions']:
        signal = pos.get('auto_signal', 'HOLD')
        score = pos.get('auto_score', 0)
        sym = pos['symbol']
        price = pos['last_check']['price']
        shares = pos['shares']

        if signal == 'EXIT_NOW':
            action_qty = shares
            action_name = 'EXIT_FULL'
        elif signal == 'EXIT_HALF':
            action_qty = shares // 2
            action_name = 'EXIT_HALF'
        else:
            continue

        reason = f"score={score} signal={signal} triggers={','.join(pos.get('auto_signals', []))}"

        if not dry_run:
            log_trade(sym, action_name, action_qty, price, reason)
            log_decision(pos, signal, score, auto=True)
            # 更新持仓（减少股数）
            pos['shares'] -= action_qty
            pos['status'] = action_name
            if pos['shares'] <= 0:
                pos['status'] = 'CLOSED'
                data['positions'] = [p for p in data['positions'] if p['shares'] > 0]
        else:
            print(f"  [DRY-RUN] {sym}: would {action_name} {action_qty}股 @ {price}")

        executed.append(f"{sym} {action_name} {action_qty}股")

    if not dry_run:
        with open(POSITIONS_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    return executed

# ============================================================
# 主程序
# ============================================================
def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'status'
    if '--mode' in sys.argv:
        mode = sys.argv[sys.argv.index('--mode') + 1]

    print(f"\n{'='*55}")
    print(f"  Tina 自動交易引擎 -- {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  模式: {mode}")
    print(f"{'='*55}")

    if mode == 'status':
        with open(POSITIONS_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"\n持倉狀態:")
        for pos in data['positions']:
            lc = pos['last_check']
            print(f"  {pos['symbol']}: {lc.get('price','?')} | RSI {lc.get('rsi','?')} | J {lc.get('kdj_J','?')} | PnL {lc.get('pnl_pct','?')}% | score {pos.get('auto_score','?')} {pos.get('auto_signal','?')}")
        return

    # update 或 execute
    data, twii_rsi = update_positions()

    print(f"\n{'─'*55}")
    print("  評分結果:")
    for pos in data['positions']:
        score = pos.get('auto_score', 0)
        signal = pos.get('auto_signal', 'HOLD')
        print(f"  {pos['symbol']}: {score}分 = {signal}")

    if mode == 'execute':
        print(f"\n{'─'*55}")
        print("  自動執行:")
        execs = execute_actions(data, dry_run=False)
        for e in execs:
            print(f"  ✅ {e}")
        print(f"\n  已寫入 trades.log 和 exit_decisions.json")
    else:
        print(f"\n{'─'*55}")
        print("  建議模式（dry-run），如需自動執行請用 --mode execute")

if __name__ == '__main__':
    main()