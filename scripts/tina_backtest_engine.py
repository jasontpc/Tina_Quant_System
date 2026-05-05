"""Tina Backtest Engine v2 - 本地 DB 回測引擎
==========================================
使用 yfinance.db 本地資料庫回測波段策略

策略邏輯：
  進場：RSI < 35 且 MA60 多頭排列，且動量為正
  停損：-8% 或 ATR 1.5x
  停利：+5% ~ +20%（分批）
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta

WORKSPACE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System'
DB_PATH = os.path.join(WORKSPACE, 'data', 'yfinance.db')
OUTPUT_PATH = os.path.join(WORKSPACE, 'data', 'backtest_results.json')
LOG_DIR = os.path.join(WORKSPACE, 'logs')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def get_symbols():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT DISTINCT symbol FROM daily_ohlcv ORDER BY symbol')
    syms = [r[0] for r in c.fetchall()]
    conn.close()
    return syms


def load_ohlcv(conn, symbol, start_date=None, end_date=None):
    """從本地 DB 載入 K 線資料"""
    c = conn.cursor()
    query = 'SELECT date, open, high, low, close, volume, change_pct, sma_20, sma_60, sma_120, rsi_14, atr_14, macd_hist FROM daily_ohlcv WHERE symbol=?'
    params = [symbol]
    if start_date:
        query += ' AND date >= ?'
        params.append(start_date)
    if end_date:
        query += ' AND date <= ?'
        params.append(end_date)
    query += ' ORDER BY date'

    c.execute(query, params)
    rows = c.fetchall()
    if not rows:
        return []

    data = []
    for row in rows:
        data.append({
            'date': row[0],
            'open': row[1], 'high': row[2], 'low': row[3],
            'close': row[4], 'volume': row[5],
            'change_pct': row[6],
            'sma_20': row[7], 'sma_60': row[8], 'sma_120': row[9],
            'rsi_14': row[10], 'atr_14': row[11], 'macd_hist': row[12],
        })
    return data


def run_backtest(data, symbol):
    """執行波段回測"""
    trades = []
    in_position = False
    entry_price = 0
    entry_date = ''
    atr_at_entry = 0

    for i, bar in enumerate(data):
        if in_position:
            # 停損檢查
            trigger_sl = bar['low'] <= entry_price * (1 - 0.08)
            trigger_sl_atr = bar['low'] <= entry_price - (atr_at_entry * 1.5)

            # 停利檢查
            profit_pct = (bar['close'] - entry_price) / entry_price * 100

            tp1 = entry_price * 1.03   # +3%
            tp2 = entry_price * 1.05   # +5%
            tp3 = entry_price * 1.10   # +10%
            tp4 = entry_price * 1.15   # +15%
            tp5 = entry_price * 1.20   # +20%

            exit_reason = None
            exit_price = bar['close']

            if trigger_sl or trigger_sl_atr:
                exit_reason = 'STOP_LOSS'
                exit_price = entry_price * 0.92
            elif profit_pct >= 20:
                exit_reason = 'TAKE_PROFIT_20'
            elif profit_pct >= 15:
                exit_reason = 'TAKE_PROFIT_15'
            elif profit_pct >= 10:
                exit_reason = 'TAKE_PROFIT_10'
            elif profit_pct >= 5:
                exit_reason = 'TAKE_PROFIT_5'
            elif profit_pct >= 3:
                exit_reason = 'TAKE_PROFIT_3'

            # 持倉超過 30 天強制出场
            entry_dt = datetime.strptime(entry_date, '%Y-%m-%d')
            exit_dt = datetime.strptime(bar['date'], '%Y-%m-%d')
            hold_days = (exit_dt - entry_dt).days
            if hold_days > 30 and profit_pct > 0:
                exit_reason = 'TIME_FORCE_EXIT'
            elif hold_days > 45:
                exit_reason = 'MAX_HOLD'

            if exit_reason:
                pnl_pct = (exit_price - entry_price) / entry_price * 100
                trades.append({
                    'symbol': symbol,
                    'entry_date': entry_date,
                    'entry_price': entry_price,
                    'exit_date': bar['date'],
                    'exit_price': exit_price,
                    'exit_reason': exit_reason,
                    'hold_days': hold_days,
                    'pnl_pct': round(pnl_pct, 2),
                    'rsi_entry': trades[-1]['rsi_entry'] if trades else 50,
                    'atr_at_entry': atr_at_entry,
                    'momentum': trades[-1]['momentum'] if trades else 0,
                })
                in_position = False

            if in_position:
                # 移動停損（保本）
                if profit_pct > 5 and bar['close'] < entry_price * 1.01:
                    trades.append({
                        'symbol': symbol, 'entry_date': entry_date,
                        'entry_price': entry_price, 'exit_date': bar['date'],
                        'exit_price': bar['close'], 'exit_reason': 'TRAILING_BREAKEVEN',
                        'hold_days': hold_days, 'pnl_pct': round((bar['close'] - entry_price) / entry_price * 100, 2),
                        'rsi_entry': trades[-1]['rsi_entry'], 'atr_at_entry': atr_at_entry,
                        'momentum': trades[-1]['momentum'],
                    })
                    in_position = False

        if not in_position:
            # 進場訊號
            rsi = bar.get('rsi_14', 50)
            sma20 = bar.get('sma_20', 0)
            sma60 = bar.get('sma_60', 0)
            close = bar['close']
            macd = bar.get('macd_hist', 0)
            change = bar.get('change_pct', 0)

            if rsi and sma20 and sma60:
                ma多头 = close > sma60 > sma20
                rsi_ok = rsi < 35
                momentum_positive = macd > 0 and change > 0

                # Entry: RSI < 35, MA60 > MA20 (bullish alignment), positive momentum
                ma_bullish = sma60 > sma20
                rsi_ok = rsi < 35
                momentum_positive = macd > 0 and change > 0

                # RSI 30-40 zone tag
                rsi_zone = 'LOW' if rsi < 30 else ('MID' if rsi < 35 else ('BELOW50' if rsi < 50 else 'HIGH'))

                if rsi_ok and ma_bullish and momentum_positive:
                    in_position = True
                    entry_price = close
                    entry_date = bar['date']
                    atr_at_entry = bar.get('atr_14', close * 0.02)

                    # 記錄進場時的市場狀態
                    if i >= 20:
                        prev_20 = data[i-20:i]
                        avg_change = sum(d.get('change_pct', 0) for d in prev_20) / 20
                        momentum = avg_change
                    else:
                        momentum = 0

                    # 標記即將建立的最後一筆交易（待filled）
                    trades.append({
                        'symbol': symbol,
                        'entry_date': entry_date,
                        'entry_price': entry_price,
                        'exit_date': '',
                        'exit_price': 0,
                        'exit_reason': 'PENDING',
                        'hold_days': 0,
                        'pnl_pct': 0,
                        'rsi_entry': rsi,
                        'atr_at_entry': atr_at_entry,
                        'momentum': momentum,
                        'rsi_zone': rsi_zone,
                        'ma_alignment': 'BULL' if close > sma60 > sma20 else 'NEUTRAL',
                    })

    # 移除未完成的交易
    trades = [t for t in trades if t['exit_reason'] != 'PENDING']
    return trades


def analyze_trades(trades):
    """分析交易結果"""
    if not trades:
        return None

    wins = [t for t in trades if t['pnl_pct'] > 0]
    losses = [t for t in trades if t['pnl_pct'] <= 0]

    win_rate = len(wins) / len(trades) * 100 if trades else 0
    avg_win = sum(t['pnl_pct'] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t['pnl_pct'] for t in losses) / len(losses) if losses else 0
    avg_return = sum(t['pnl_pct'] for t in trades) / len(trades)

    # RSI 區間分析
    rsi_zones = {'<30': [], '30-35': [], '35-40': [], '40-50': [], '>50': []}
    for t in trades:
        rsi = t.get('rsi_entry', 50)
        if rsi < 30:
            rsi_zones['<30'].append(t)
        elif rsi < 35:
            rsi_zones['30-35'].append(t)
        elif rsi < 40:
            rsi_zones['35-40'].append(t)
        elif rsi < 50:
            rsi_zones['40-50'].append(t)
        else:
            rsi_zones['>50'].append(t)

    rsi_analysis = {}
    for zone, ts in rsi_zones.items():
        if ts:
            wins_z = [t for t in ts if t['pnl_pct'] > 0]
            wr = len(wins_z) / len(ts) * 100
            avg = sum(t['pnl_pct'] for t in ts) / len(ts)
            rsi_analysis[zone] = {
                'count': len(ts), 'win_rate': round(wr, 1),
                'avg_return': round(avg, 2), 'wins': len(wins_z), 'losses': len(ts) - len(wins_z)
            }

    # 持倉天數分析
    hold_days = [t['hold_days'] for t in trades]
    avg_hold = sum(hold_days) / len(hold_days) if hold_days else 0

    return {
        'total_trades': len(trades),
        'wins': len(wins),
        'losses': len(losses),
        'win_rate': round(win_rate, 1),
        'avg_return': round(avg_return, 2),
        'avg_win': round(avg_win, 2),
        'avg_loss': round(avg_loss, 2),
        'avg_hold_days': round(avg_hold, 1),
        'rsi_analysis': rsi_analysis,
        'best_trade': max(trades, key=lambda t: t['pnl_pct']) if trades else None,
        'worst_trade': min(trades, key=lambda t: t['pnl_pct']) if trades else None,
    }


def run():
    print('[Tina Backtest Engine v2] - Local DB Backtest')
    print('=' * 60)

    conn = get_db()
    syms = get_symbols()
    print(f'\n[*] Total symbols in DB: {len(syms)}')

    all_results = {}

    for sym in syms:
        print(f'\n[*] {sym}...', end=' ', flush=True)
        data = load_ohlcv(conn, sym)
        if len(data) < 250:
            print(f'skip (only {len(data)} rows)')
            continue

        trades = run_backtest(data, sym)
        if trades:
            analysis = analyze_trades(trades)
            all_results[sym] = {
                'trades': trades,
                'analysis': analysis,
                'data_points': len(data),
            }
            print(f'{len(trades)} trades, WR={analysis["win_rate"]}%, avg={analysis["avg_return"]}%')
        else:
            print('no signals')

    conn.close()

    # 跨標的分析
    print('\n' + '=' * 60)
    print('[CROSS-SYMBOL ANALYSIS]')

    all_trades = []
    for sym, res in all_results.items():
        all_trades.extend(res['trades'])

    print(f'\nTotal trades: {len(all_trades)}')
    wins = [t for t in all_trades if t['pnl_pct'] > 0]
    losses = [t for t in all_trades if t['pnl_pct'] <= 0]
    print(f'Wins: {len(wins)}, Losses: {len(losses)}')
    print(f'Overall Win Rate: {len(wins) / len(all_trades) * 100:.1f}%')
    print(f'Overall Avg Return: {sum(t["pnl_pct"] for t in all_trades) / len(all_trades):.2f}%')

    # RSI Zone summary
    print('\n[RSI Entry Zone Performance]')
    for zone in ['<30', '30-35', '35-40', '40-50', '>50']:
        zone_trades = [t for t in all_trades if
            (zone == '<30' and t.get('rsi_entry', 50) < 30) or
            (zone == '30-35' and 30 <= t.get('rsi_entry', 50) < 35) or
            (zone == '35-40' and 35 <= t.get('rsi_entry', 50) < 40) or
            (zone == '40-50' and 40 <= t.get('rsi_entry', 50) < 50) or
            (zone == '>50' and t.get('rsi_entry', 50) >= 50)]
        if zone_trades:
            wz = [t for t in zone_trades if t['pnl_pct'] > 0]
            wr = len(wz) / len(zone_trades) * 100
            avg = sum(t['pnl_pct'] for t in zone_trades) / len(zone_trades)
            print(f'  RSI {zone}: {len(zone_trades)} trades, WR={wr:.1f}%, avg={avg:.2f}%')

    # Save results
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f'\n[OK] Results saved: {OUTPUT_PATH}')

    # Per-symbol top performers
    print('\n[Best Symbols by Win Rate]')
    symbol_stats = [(sym, res['analysis']['win_rate'], res['analysis']['avg_return'], res['analysis']['total_trades'])
                    for sym, res in all_results.items() if res['analysis']['total_trades'] >= 5]
    symbol_stats.sort(key=lambda x: x[1], reverse=True)
    for sym, wr, avg, n in symbol_stats[:10]:
        print(f'  {sym}: WR={wr}%, avg={avg}%, n={n}')

    print('\n[DONE]')
    return all_results


if __name__ == '__main__':
    run()
