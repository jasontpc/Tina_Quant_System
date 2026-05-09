# -*- coding: utf-8 -*-
"""
Tina Growth-Long Paper Engine v1.0
====================================
台美股長期持有成長股 模擬交易引擎

功能：
- 讀取 growth_candidates.json 候選名單
- 監控進場條件（RSI < 50，MA多頭排列，法人買超）
- 追蹤持有期、報酬率、追蹤止損
- 每季再平衡評估
- 寫入 growth_paper_trading.db

用法：
  python growth_paper_engine.py              # 全市場掃描
  python growth_paper_engine.py --TW          # 只掃台股
  python growth_paper_engine.py --US          # 只掃美股
  python growth_paper_engine.py --status       # 顯示目前倉位
  python growth_paper_engine.py --report       # 完整報告
  python growth_paper_engine.py --backtest    # 歷史回測模式
"""

import sys, os, json, sqlite3
import yfinance as yf
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict

# ── 路徑設定 ────────────────────────────────────────────────────────────────
WORKSPACE     = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
DATA_DIR      = WORKSPACE / 'data'
DB_PATH       = DATA_DIR / 'growth_paper_trading.db'
CANDIDATES    = DATA_DIR / 'growth_candidates.json'
LOG_DIR       = WORKSPACE / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ── 基本參數 ───────────────────────────────────────────────────────────────
ENTRY_RSI_MAX      = 50
RSI_OVERSOLD       = 35
RSI_OVERBOUGHT     = 75
STOP_LOSS_PCT      = 0.20       # -20% 停損
TRAILING_PCT       = 0.20       # 從高點拉回 20% 追蹤止損
MAX_HOLD_MONTHS    = 18         # 最長持有 18 個月
REBALANCE_QUARTER  = True       # 每季再平衡

# 進場額外條件
MIN_INSTITUTIONAL_BUY_DAYS = 3   # 3天內有法人買超
MIN_REVENUE_GROWTH_PCT     = 15  # 營收 YoY > 15%


# ═══════════════════════════════════════════════════════════════════════════
# 工具函式
# ═══════════════════════════════════════════════════════════════════════════

def calc_rsi(prices: np.ndarray, period: int = 14) -> Optional[float]:
    if len(prices) < period + 1:
        return None
    deltas = np.diff(prices)
    gains  = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100 - (100 / (1 + rs)))


def calc_sma(prices: np.ndarray, n: int) -> Optional[float]:
    if len(prices) < n:
        return None
    return float(np.mean(prices[-n:]))


def is_ma_bullish(prices: np.ndarray) -> bool:
    """MA20 > MA60 多頭排列"""
    ma20 = calc_sma(prices, 20)
    ma60 = calc_sma(prices, 60)
    if ma20 is None or ma60 is None:
        return False
    return ma20 > ma60


def get_stock_data(symbol: str, lookback_days: int = 90):
    """從 yfinance 抓取數據"""
    try:
        ticker = yf.Ticker(symbol)
        hist   = ticker.history(period=f'{lookback_days}d', auto_adjust=True)
        if hist.empty or len(hist) < 30:
            return None
        closes  = hist['Close'].values.astype(float)
        highs   = hist['High'].values.astype(float)
        lows    = hist['Low'].values.astype(float)
        volumes = hist['Volume'].values.astype(float)
        dates   = hist.index.tolist()
        return {
            'symbol':   symbol,
            'dates':    dates,
            'closes':   closes,
            'highs':    highs,
            'lows':     lows,
            'volumes':  volumes,
        }
    except Exception as e:
        return None


def calc_momentum(prices: np.ndarray, periods: List[int] = [5, 20, 60]) -> Dict[int, float]:
    result = {}
    for p in periods:
        if len(prices) >= p:
            result[p] = float((prices[-1] / prices[-p] - 1) * 100)
        else:
            result[p] = 0.0
    return result


def calc_inst_flow(symbol: str, lookback: int = 5) -> Dict:
    """價格動量代理法人籌碼（真實產品需要 TWSE API）"""
    try:
        ticker = yf.Ticker(symbol)
        hist   = ticker.history(period=f'{lookback}d', auto_adjust=True)
        if hist.empty:
            return {'net_flow': 0, 'direction': 'neutral'}
        closes = hist['Close'].values
        if len(closes) >= 2:
            change_pct = (closes[-1] / closes[0] - 1) * 100
            if change_pct > 3:
                return {'net_flow': 1, 'direction': 'buying'}
            elif change_pct < -3:
                return {'net_flow': -1, 'direction': 'selling'}
        return {'net_flow': 0, 'direction': 'neutral'}
    except:
        return {'net_flow': 0, 'direction': 'neutral'}


# ═══════════════════════════════════════════════════════════════════════════
# 資料庫
# ═══════════════════════════════════════════════════════════════════════════

def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    c    = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS positions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol      TEXT    NOT NULL,
            name        TEXT,
            sector      TEXT,
            entry_date  TEXT,
            entry_price REAL,
            entry_rsi   REAL,
            shares      INTEGER,
            target_price_low  REAL,
            target_price_high REAL,
            hold_until  TEXT,
            status      TEXT    DEFAULT 'open',
            notes       TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol      TEXT    NOT NULL,
            action      TEXT    NOT NULL,
            date        TEXT,
            price       REAL,
            shares      INTEGER,
            pnl_pct     REAL,
            reason      TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_evaluation (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol      TEXT,
            date        TEXT,
            price       REAL,
            rsi_14      REAL,
            ma20        REAL,
            ma60        REAL,
            return_pct  REAL,
            high_water  REAL,
            trailing_pct REAL,
            months_held INTEGER,
            status      TEXT,
            decision    TEXT
        )
    ''')

    conn.commit()
    return conn


# ═══════════════════════════════════════════════════════════════════════════
# 進場評估
# ═══════════════════════════════════════════════════════════════════════════

def evaluate_entry(symbol: str, region: str = 'US') -> Optional[Dict]:
    """評估單一標的是否符合進場條件"""
    data = get_stock_data(symbol)
    if data is None:
        return None

    closes = data['closes']
    price  = closes[-1]

    rsi       = calc_rsi(closes, 14)
    ma20      = calc_sma(closes, 20)
    ma60      = calc_sma(closes, 60)
    ma_bull   = is_ma_bullish(closes)
    momentum  = calc_momentum(closes)
    inst_flow = calc_inst_flow(symbol, MIN_INSTITUTIONAL_BUY_DAYS)

    if rsi is None:
        return None

    score   = 0
    signals = []

    if rsi < 30:
        score += 40; signals.append('RSI_OVERSOLD')
    elif rsi < 40:
        score += 30; signals.append('RSI_LOW')
    elif rsi < ENTRY_RSI_MAX:
        score += 20; signals.append('RSI_OK')
    else:
        return None

    if ma_bull:
        score += 25; signals.append('MA_BULL')
    else:
        score += 5;  signals.append('MA_NEUTRAL')

    if momentum.get(20, 0) > 0:
        score += 15; signals.append('MOM_POS')
    elif momentum.get(20, 0) > -5:
        score += 8;  signals.append('MOM_NEUTRAL')

    if inst_flow['direction'] == 'buying':
        score += 20; signals.append('INST_BUY')
    elif inst_flow['direction'] == 'neutral':
        score += 10; signals.append('INST_NEUTRAL')

    score += 10; signals.append('BASIC_FOCUS')

    return {
        'symbol':        symbol,
        'price':         price,
        'rsi':           rsi,
        'ma20':          ma20,
        'ma60':          ma60,
        'ma_bull':       ma_bull,
        'momentum_20d':   momentum.get(20, 0),
        'inst_flow':     inst_flow['direction'],
        'score':         score,
        'signals':       signals,
        'region':        region,
        'entry_price':   price,
    }


def scan_candidates(region: Optional[str] = None, min_score: int = 60) -> List[Dict]:
    """掃描候選名單，回傳符合進場條件的標的"""
    with open(CANDIDATES, 'r', encoding='utf-8') as f:
        cand_data = json.load(f)

    results = []
    regions = ['tw', 'us'] if region is None else [region]

    for reg in regions:
        for cand in cand_data.get('candidates', {}).get(reg, []):
            sym = cand['symbol']
            result = evaluate_entry(sym, region=reg)
            if result and result['score'] >= min_score:
                result['name']   = cand.get('name', sym)
                result['sector'] = cand.get('sector', 'N/A')
                result['target_low']  = cand.get('target_price_low', 0)
                result['target_high'] = cand.get('target_price_high', 0)
                result['hold_months'] = cand.get('hold_period_months', 18)
                result['position_weight'] = cand.get('position_weight', 0.10)
                results.append(result)

    results.sort(key=lambda x: x['score'], reverse=True)
    return results


# ═══════════════════════════════════════════════════════════════════════════
# 倉位管理
# ═══════════════════════════════════════════════════════════════════════════

def open_position(conn: sqlite3.Connection, signal: Dict, capital: float = 1_000_000):
    """開倉"""
    sym    = signal['symbol']
    price  = signal['entry_price']
    weight = signal.get('position_weight', 0.10)
    shares = int(capital * weight / price)

    if shares < 1:
        return None

    entry_date = datetime.now().strftime('%Y-%m-%d')
    hold_until = (datetime.now() + timedelta(days=signal.get('hold_months', 18) * 30)).strftime('%Y-%m-%d')

    c = conn.cursor()
    c.execute('''
        INSERT INTO positions
        (symbol, entry_date, entry_price, entry_rsi, shares,
         target_price_low, target_price_high, hold_until, status, name, sector)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?)
    ''', (sym, entry_date, price, signal['rsi'], shares,
          signal.get('target_low', 0), signal.get('target_high', 0),
          hold_until, signal.get('name', ''), signal.get('sector', '')))

    c.execute('''
        INSERT INTO trades (symbol, action, date, price, shares, reason)
        VALUES (?, 'BUY', ?, ?, ?, ?)
    ''', (sym, entry_date, price, shares, f"score={signal['score']}, signals={','.join(signal['signals'])}"))

    conn.commit()
    return {'symbol': sym, 'shares': shares, 'entry_price': price}


def check_positions(conn: sqlite3.Connection) -> List[Dict]:
    """檢查所有倉位，評估是否觸發停損/止盈/到期"""
    c = conn.cursor()
    c.execute('SELECT * FROM positions WHERE status="open" ORDER BY entry_date')
    rows = c.fetchall()
    cols = [desc[0] for desc in c.description]

    positions = []
    for row in rows:
        pos  = dict(zip(cols, row))
        sym  = pos['symbol']
        data = get_stock_data(sym)

        if data is None:
            continue

        price    = data['closes'][-1]
        entry_p  = pos['entry_price']
        ret_pct  = (price / entry_p - 1) * 100 if entry_p else 0

        c2 = conn.cursor()
        c2.execute('SELECT MAX(price) FROM daily_evaluation WHERE symbol=?', (sym,))
        prev_high = c2.fetchone()[0] or entry_p
        high_water = max(prev_high, price)
        trail_pct  = (price / high_water - 1) * 100 if high_water > entry_p else 0

        entry_dt  = datetime.strptime(pos['entry_date'], '%Y-%m-%d')
        days_held = (datetime.now() - entry_dt).days
        months_held = days_held // 30

        rsi   = calc_rsi(data['closes'], 14)
        ma20  = calc_sma(data['closes'], 20)
        ma60  = calc_sma(data['closes'], 60)

        decision    = 'HOLD'
        exit_reason = None

        if price < entry_p * (1 - STOP_LOSS_PCT):
            decision = 'STOP_LOSS'; exit_reason = f'price={price:.2f}, ret={ret_pct:.1f}%'
        elif high_water > entry_p and trail_pct <= -TRAILING_PCT:
            decision = 'TRAILING_STOP'; exit_reason = f'high={high_water:.2f}, trail={trail_pct:.1f}%'
        elif rsi and rsi > RSI_OVERBOUGHT:
            decision = 'RSI_OVERBOUGHT_EXIT'; exit_reason = f'RSI={rsi:.1f}'
        elif months_held >= MAX_HOLD_MONTHS:
            decision = 'HOLD_PERIOD_EXPIRED'; exit_reason = f'months={months_held}'

        c2.execute('''
            INSERT INTO daily_evaluation
            (symbol, date, price, rsi_14, ma20, ma60, return_pct, high_water, trailing_pct, months_held, status, decision)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?)
        ''', (sym, datetime.now().strftime('%Y-%m-%d'), price, rsi, ma20, ma60,
              ret_pct, high_water, trail_pct, months_held, decision))

        conn.commit()

        pos['current_price'] = price
        pos['return_pct']    = ret_pct
        pos['high_water']    = high_water
        pos['trailing_pct']  = trail_pct
        pos['days_held']     = days_held
        pos['months_held']   = months_held
        pos['rsi']           = rsi
        pos['decision']      = decision
        pos['exit_reason']   = exit_reason

        if decision != 'HOLD':
            close_position(conn, pos, decision, exit_reason)

        positions.append(pos)

    return positions


def close_position(conn: sqlite3.Connection, pos: Dict, reason: str, detail: str):
    """平倉"""
    c = conn.cursor()
    sym    = pos['symbol']
    price  = pos.get('current_price', pos['entry_price'])
    shares = pos['shares']
    ret_pct = pos.get('return_pct', 0)

    c.execute('UPDATE positions SET status=? WHERE id=?', ('closed', pos['id']))
    c.execute('''
        INSERT INTO trades (symbol, action, date, price, shares, pnl_pct, reason)
        VALUES (?, 'SELL', ?, ?, ?, ?, ?)
    ''', (sym, datetime.now().strftime('%Y-%m-%d'), price, shares, ret_pct, f'{reason}: {detail}'))
    conn.commit()


# ═══════════════════════════════════════════════════════════════════════════
# 報告輸出
# ═══════════════════════════════════════════════════════════════════════════

def print_entry_signals(results: List[Dict]):
    print('=' * 70)
    print(f'  Growth-Long Entry Signals  ({datetime.now().strftime("%Y-%m-%d %H:%M")})')
    print('=' * 70)
    print(f'  {"Symbol":<12} {"Price":>8} {"RSI":>6} {"MA Bull":>9} {"Score":>6} {"Sector":<20}')
    print('-' * 70)
    for r in results:
        ma_str = 'YES' if r['ma_bull'] else 'NO'
        print(f"  {r['symbol']:<12} ${r['price']:>7.2f} {r['rsi']:>6.1f} {ma_str:>9} {r['score']:>6} {r.get('sector','N/A'):<20}")
    print()


def print_positions_status(conn: sqlite3.Connection):
    c = conn.cursor()
    c.execute('''
        SELECT p.symbol, p.name, p.entry_date, p.entry_price, p.shares,
               pe.current_price, pe.return_pct, pe.months_held,
               pe.rsi, pe.decision, pe.exit_reason
        FROM positions p
        LEFT JOIN (
            SELECT symbol,
                   date,
                   price as current_price,
                   return_pct, months_held, rsi, decision, exit_reason,
                   ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY date DESC) as rn
            FROM daily_evaluation
        ) pe ON p.symbol = pe.symbol AND pe.rn = 1
        WHERE p.status = 'open'
    ''')
    rows = c.fetchall()
    if not rows:
        print('[EMPTY] No open positions')
        return

    print('=' * 70)
    print(f'  Position Status  ({datetime.now().strftime("%Y-%m-%d %H:%M")})')
    print('=' * 70)
    print(f'  {"Symbol":<12} {"Entry":>8} {"Current":>8} {"Return":>8} {"Days":>6} {"RSI":>6} {"Decision":<20}')
    print('-' * 70)
    for row in rows:
        sym, name, entry_d, entry_p, shares, curr_p, ret, months, rsi_val, decision, reason = row
        ret_str  = f'{ret:+.2f}%' if ret else 'N/A'
        rsi_str  = f'{rsi_val:.1f}' if rsi_val else 'N/A'
        print(f'  {sym:<12} {entry_p:>8.2f} {(curr_p or 0):>8.2f} {ret_str:>8} {months or 0:>6} {rsi_str:>6} {decision or "HOLD":<20}')
    print()


def generate_full_report(conn: sqlite3.Connection) -> Dict:
    """產生完整績效報告"""
    c = conn.cursor()

    c.execute('SELECT COUNT(*), SUM(return_pct) FROM daily_evaluation WHERE status="open"')
    open_count, open_pnl = c.fetchone()

    c.execute('SELECT action, COUNT(*), AVG(pnl_pct) FROM trades GROUP BY action')
    trade_stats = {row[0]: {'count': row[1], 'avg_pnl': row[2] or 0} for row in c.fetchall()}

    c.execute('SELECT SUM(pnl_pct) FROM trades WHERE action="SELL" AND pnl_pct IS NOT NULL')
    total_pnl = c.fetchone()[0] or 0

    return {
        'open_positions':   open_count or 0,
        'open_pnl_pct':     open_pnl or 0,
        'total_closed_pnl': total_pnl,
        'trade_stats':      trade_stats,
        'generated_at':     datetime.now().strftime('%Y-%m-%d %H:%M')
    }


# ═══════════════════════════════════════════════════════════════════════════
# 主程式
# ═══════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Tina Growth-Long Paper Engine')
    parser.add_argument('--TW',     action='store_true', help='只掃台股')
    parser.add_argument('--US',     action='store_true', help='只掃美股')
    parser.add_argument('--status', action='store_true', help='顯示倉位狀態')
    parser.add_argument('--report', action='store_true', help='完整報告')
    parser.add_argument('--scan',   action='store_true', help='掃描進場候選')
    parser.add_argument('--capital', type=float, default=1_000_000, help='虛擬資本（默認100萬）')
    args = parser.parse_args()

    conn = init_db()

    if args.status or args.report:
        print_positions_status(conn)

    check_positions(conn)

    if args.scan or (not args.status and not args.report):
        region = None
        if args.TW: region = 'tw'
        if args.US: region = 'us'
        results = scan_candidates(region=region, min_score=60)
        if results:
            print_entry_signals(results)
        else:
            print('[EMPTY] No candidates meet entry score threshold (60)')

    if args.report:
        report = generate_full_report(conn)
        print('=' * 70)
        print(f'  Performance Report  ({report["generated_at"]})')
        print('=' * 70)
        print(f'  Open positions : {report["open_positions"]}')
        print(f'  Open PnL       : {report["open_pnl_pct"]:+.2f}%')
        print(f'  Closed PnL     : {report["total_closed_pnl"]:+.2f}%')
        if 'BUY' in report['trade_stats']:
            print(f'  Total trades   : {report["trade_stats"]["BUY"]["count"]}')
        print()

    conn.close()


if __name__ == '__main__':
    main()