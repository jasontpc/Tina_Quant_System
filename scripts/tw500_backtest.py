"""
TW500 MA Crossover Backtest Engine
- Reads from tw_stock_registry.db
- Filters top 500 TWSE stocks
- Runs MA20/MA60 crossover strategy with RSI filter
- Stores all trades in JSON, summarizes stats
"""

import sqlite3
import json
import os
import sys
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import locale

import yfinance as yf
import pandas as pd
import numpy as np

# Fix stdout for Windows CP950
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# -- Config ---------------------------------------------------------------------
DB_PATH   = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\tw_stock_registry.db"
OUT_DIR   = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data"
STORES    = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\stores\long_term"

MAX_WORKERS      = 20
TOP_N            = 500
START_DATE       = "2018-01-01"
END_DATE         = "2025-12-31"
RSI_ENTRY_MAX    = 65
RSI_ENTRY_IDEAL  = 50
STOP_LOSS_PCT    = -0.08
TAKE_PROFIT_PCT  = 0.06
MAX_HOLD_DAYS    = 60

MA_SHORT = 20
MA_LONG  = 60

# -- Load Stock List ------------------------------------------------------------
def get_stock_list(limit=500):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT code, name_cn, industry
        FROM stock_registry
        WHERE market = 'twse'
          AND industry NOT LIKE '%ETF%'
          AND industry NOT LIKE '%指數股票%'
        ORDER BY code
    """)
    rows = cur.fetchall()
    conn.close()
    stocks = [{"code": r[0], "name": r[1], "industry": r[2]} for r in rows]
    print(f"[DB] Total TWSE stocks (excl ETF): {len(stocks)}")
    return stocks[:limit]

# -- Download Data -------------------------------------------------------------
def download_data(symbol, start, end, retries=2):
    for attempt in range(retries):
        try:
            ticker = yf.Ticker(f"{symbol}.TW")
            df = ticker.history(start=start, end=end, auto_adjust=True, timeout=10)
            if df is None or df.empty:
                return None
            df = df[['Open','High','Low','Close','Volume']].copy()
            df.columns = ['open','high','low','close','volume']
            df = df[df['volume'] > 0]
            return df
        except Exception:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    return None

# -- Indicators ----------------------------------------------------------------
def compute_indicators(df):
    df = df.copy()
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma60'] = df['close'].rolling(60).mean()
    delta = df['close'].diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, np.nan)
    df['rsi'] = 100 - (100 / (1 + rs))
    return df.dropna()

# -- Backtest Single Stock -----------------------------------------------------
def backtest_stock(stock):
    code = stock['code']
    name = stock['name']
    industry = stock['industry']

    df = download_data(code, START_DATE, END_DATE)
    if df is None or len(df) < 200:
        return None

    df = compute_indicators(df)
    trades = []
    position = None

    for i in range(1, len(df)):
        row    = df.iloc[i]
        prev   = df.iloc[i-1]
        date   = df.index[i]
        close  = row['close']
        ma20   = row['ma20']
        ma60   = row['ma60']
        rsi    = row['rsi']
        prev_ma20 = prev['ma20']
        prev_ma60 = prev['ma60']

        # Entry: MA20 crosses above MA60
        if position is None:
            if prev_ma20 <= prev_ma60 and ma20 > ma60:
                if rsi <= RSI_ENTRY_MAX:
                    position = {
                        'symbol':        code,
                        'name':          name,
                        'industry':      industry,
                        'entry_date':    str(date.date()),
                        'entry_price':   float(close),
                        'entry_rsi':     round(float(rsi), 1),
                        'shares':        1000,
                        'ma20_gt_ma60_at_entry': True,
                    }

        # Exit check
        else:
            entry_price = position['entry_price']
            ret_pct = (close - entry_price) / entry_price
            hold_days = (date - pd.Timestamp(position['entry_date'])).days
            exited = False
            exit_reason = None

            if ret_pct <= STOP_LOSS_PCT:
                exit_reason = 'stop_loss'
                exited = True
            elif ret_pct >= TAKE_PROFIT_PCT:
                exit_reason = 'take_profit'
                exited = True
            elif hold_days >= MAX_HOLD_DAYS:
                exit_reason = 'max_hold_days'
                exited = True
            elif prev_ma20 > prev_ma60 and ma20 <= ma60:
                exit_reason = 'ma_death_cross'
                exited = True

            if exited:
                position['exit_date']    = str(date.date())
                position['exit_price']   = float(close)
                position['exit_rsi']     = round(float(rsi), 1)
                position['return_pct']   = round(ret_pct * 100, 2)
                position['hold_days']    = hold_days
                position['exit_reason']  = exit_reason
                position['pnl']          = round(ret_pct * position['shares'] * entry_price, 0)
                trades.append(position)
                position = None

    # Force close open position at end
    if position is not None:
        last_row  = df.iloc[-1]
        last_date = df.index[-1]
        close_price = float(last_row['close'])
        entry_price = position['entry_price']
        ret_pct  = (close_price - entry_price) / entry_price
        hold_days = (last_date - pd.Timestamp(position['entry_date'])).days
        position['exit_date']    = str(last_date.date())
        position['exit_price']   = close_price
        position['exit_rsi']     = round(float(last_row['rsi']), 1)
        position['return_pct']   = round(ret_pct * 100, 2)
        position['hold_days']    = hold_days
        position['exit_reason']  = 'end_of_data'
        position['pnl']          = round(ret_pct * position['shares'] * entry_price, 0)
        trades.append(position)

    return {'symbol': code, 'name': name, 'industry': industry, 'trades': trades}

# -- Analyze Results -----------------------------------------------------------
def analyze_results(all_results):
    all_trades = []
    for res in all_results:
        if res and res['trades']:
            for t in res['trades']:
                t['industry'] = res['industry']
            all_trades.extend(res['trades'])

    if not all_trades:
        return {'total_trades': 0, 'wins': 0, 'losses': 0, 'win_rate': 0,
                'avg_return': 0, 'avg_hold_days': 0, 'exit_reason_counts': {}}

    df = pd.DataFrame(all_trades)
    wins   = df[df['return_pct'] > 0]
    losses = df[df['return_pct'] <= 0]
    exit_counts = df['exit_reason'].value_counts().to_dict()

    rsi_bins = pd.cut(df['entry_rsi'], bins=[0,30,40,50,60,70,100],
                      labels=['0-30','30-40','40-50','50-60','60-70','70+'])
    rsi_dist = pd.Series(rsi_bins).value_counts().to_dict()

    ind_stats = df.groupby('industry').agg(
        trades=('return_pct','count'),
        avg_return=('return_pct','mean'),
        win_rate=('return_pct', lambda x: (x>0).mean()*100)
    ).sort_values('trades', ascending=False).head(20).to_dict('index')

    success_pats = []
    failure_pats = []

    # Patterns
    tp_wins = df[(df['exit_reason']=='take_profit') & (df['return_pct']>0)]
    if len(tp_wins) > 0:
        success_pats.append({
            'pattern': 'MA golden cross + RSI<entry_max -> take profit',
            'count': int(len(tp_wins)),
            'avg_return': round(float(tp_wins['return_pct'].mean()), 2),
            'win_rate': 100.0,
            'avg_hold_days': round(float(tp_wins['hold_days'].mean()), 1)
        })

    dc_loss = df[(df['exit_reason']=='ma_death_cross') & (df['return_pct']<0)]
    if len(dc_loss) > 0:
        failure_pats.append({
            'pattern': 'MA death cross exit (holding too long)',
            'count': int(len(dc_loss)),
            'avg_return': round(float(dc_loss['return_pct'].mean()), 2),
            'avg_hold_days': round(float(dc_loss['hold_days'].mean()), 1)
        })

    mh_loss = df[(df['exit_reason']=='max_hold_days') & (df['return_pct']<0)]
    if len(mh_loss) > 0:
        failure_pats.append({
            'pattern': 'Max hold 60d forced exit (time decay / trend exhaustion)',
            'count': int(len(mh_loss)),
            'avg_return': round(float(mh_loss['return_pct'].mean()), 2)
        })

    high_rsi = df[(df['entry_rsi'] > 60) & (df['return_pct'] < 0)]
    if len(high_rsi) > 0:
        failure_pats.append({
            'pattern': 'Entry RSI > 60 (overbought entry)',
            'count': int(len(high_rsi)),
            'avg_return': round(float(high_rsi['return_pct'].mean()), 2),
            'avg_entry_rsi': round(float(high_rsi['entry_rsi'].mean()), 1)
        })

    risky = df[(df['hold_days'] > 30) & (df['entry_rsi'] > 50) & (df['return_pct'] < 0)]
    if len(risky) > 0:
        failure_pats.append({
            'pattern': 'Hold >30d + entry RSI >50 (danger zone per Tina rules)',
            'count': int(len(risky)),
            'avg_return': round(float(risky['return_pct'].mean()), 2),
            'avg_hold_days': round(float(risky['hold_days'].mean()), 1),
            'severity': 'HIGH'
        })

    best_industries = []
    for ind, stats in ind_stats.items():
        if stats['trades'] >= 20:
            best_industries.append({
                'industry':   ind,
                'trades':    int(stats['trades']),
                'avg_return': round(float(stats['avg_return']), 2),
                'win_rate':   round(float(stats['win_rate']), 1)
            })
    best_industries.sort(key=lambda x: x['avg_return'], reverse=True)
    best_industries = best_industries[:10]

    best_trade_row = df.loc[df['return_pct'].idxmax()]
    worst_trade_row = df.loc[df['return_pct'].idxmin()]

    summary = {
        'backtest_period':       f"{START_DATE} to {END_DATE}",
        'universe':              f"Top {TOP_N} TWSE stocks (excl ETF)",
        'strategy':              f"MA{MA_SHORT}/MA{MA_LONG} crossover + RSI<={RSI_ENTRY_MAX}",
        'total_stocks':          TOP_N,
        'total_trades':          int(len(df)),
        'wins':                  int(len(wins)),
        'losses':                int(len(losses)),
        'win_rate':              round(float(len(wins)/len(df)*100), 2) if len(df)>0 else 0,
        'avg_return':            round(float(df['return_pct'].mean()), 2),
        'median_return':         round(float(df['return_pct'].median()), 2),
        'std_return':            round(float(df['return_pct'].std()), 2),
        'avg_hold_days':         round(float(df['hold_days'].mean()), 1),
        'median_hold_days':      round(float(df['hold_days'].median()), 1),
        'best_trade': {
            'symbol':      str(best_trade_row['symbol']),
            'name':        str(best_trade_row['name']),
            'return_pct':  round(float(best_trade_row['return_pct']), 2),
            'hold_days':   int(best_trade_row['hold_days']),
            'exit_reason': str(best_trade_row['exit_reason'])
        },
        'worst_trade': {
            'symbol':      str(worst_trade_row['symbol']),
            'name':        str(worst_trade_row['name']),
            'return_pct':  round(float(worst_trade_row['return_pct']), 2),
            'hold_days':   int(worst_trade_row['hold_days']),
            'exit_reason': str(worst_trade_row['exit_reason'])
        },
        'exit_reason_counts': {str(k): int(v) for k, v in exit_counts.items()},
        'rsi_entry_distribution': {str(k): int(v) for k, v in rsi_dist.items()},
        'industry_stats':       ind_stats,
        'best_industries':      best_industries,
        'success_patterns':      success_pats,
        'failure_patterns':      failure_pats,
    }
    return summary

# -- Recommendations -----------------------------------------------------------
def make_recommendations(summary):
    recs = []
    rsi_dist = summary.get('rsi_entry_distribution', {})

    if rsi_dist.get('70+', 0) > 5:
        recs.append({
            'param':     'RSI_ENTRY_MAX',
            'current':  RSI_ENTRY_MAX,
            'suggested': 55,
            'reason':    f"Entries with RSI>70 ({rsi_dist.get('70+',0)} trades) show negative returns. Tighten to 55."
        })

    if summary.get('avg_hold_days', 0) > 40:
        recs.append({
            'param':     'MAX_HOLD_DAYS',
            'current':  MAX_HOLD_DAYS,
            'suggested': 45,
            'reason':    f"Avg hold {summary['avg_hold_days']}d with many forced exits at {MAX_HOLD_DAYS}d. Shortening reduces time-decay losses."
        })

    win_rate = summary.get('win_rate', 0)
    if win_rate < 55:
        recs.append({
            'param':     'TAKE_PROFIT_PCT',
            'current':  TAKE_PROFIT_PCT,
            'suggested': 0.05,
            'reason':    f"Win rate {win_rate}% < 55%. Lowering TP from {TAKE_PROFIT_PCT*100}% to 5% captures smaller gains more reliably."
        })

    if summary.get('avg_return', 0) < 0:
        recs.append({
            'param':     'STOP_LOSS_PCT',
            'current':  STOP_LOSS_PCT,
            'suggested': -0.06,
            'reason':    "Avg return is negative; tighter stop loss (-6%) cuts losses earlier."
        })

    return recs

# -- Update Lessons -------------------------------------------------------------
def update_lessons(summary, recommendations):
    import datetime
    now = datetime.datetime.now().isoformat()

    new_lesson = {
        'date':            now,
        'title':           f'TW500 Backtest: {summary["total_trades"]} trades, {summary["win_rate"]}% WR',
        'severity':        'major',
        'team':            'tina',
        'backtest_period': summary['backtest_period'],
        'strategy':        summary['strategy'],
        'key_metrics': {
            'total_trades': summary['total_trades'],
            'win_rate':     summary['win_rate'],
            'avg_return':   summary['avg_return'],
            'avg_hold_days': summary['avg_hold_days']
        },
        'success_patterns':  summary.get('success_patterns', []),
        'failure_patterns':  summary.get('failure_patterns', []),
        'recommendations':   recommendations
    }

    lessons_path = os.path.join(STORES, 'lessons.json')
    if os.path.exists(lessons_path):
        with open(lessons_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = {'lessons': [], 'metadata': {}}

    data['lessons'].append(new_lesson)
    data['metadata']['last_updated'] = now
    data['metadata']['total'] = len(data['lessons'])
    data['last_updated'] = now

    with open(lessons_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return lessons_path

# -- Main ----------------------------------------------------------------------
def main():
    print(f"TW500 Backtest Starting...")
    print(f"Strategy: MA{MA_SHORT}/MA{MA_LONG} + RSI<={RSI_ENTRY_MAX} | Period: {START_DATE} to {END_DATE}")

    stocks = get_stock_list(limit=TOP_N)
    print(f"[DB] Selected {len(stocks)} stocks for backtest")

    all_results = []
    failed = []

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(backtest_stock, s): s for s in stocks}
        done = 0
        for future in as_completed(futures):
            done += 1
            if done % 50 == 0:
                elapsed = time.time() - t0
                print(f"  ... {done}/{len(stocks)} done ({elapsed:.0f}s elapsed)")
            try:
                result = future.result()
                if result:
                    all_results.append(result)
            except Exception as e:
                s = futures[future]
                failed.append(s['code'])

    elapsed = time.time() - t0
    print(f"[Done] {len(all_results)} stocks processed, {len(failed)} failed in {elapsed:.0f}s")

    all_trades = []
    for res in all_results:
        if res and res['trades']:
            for t in res['trades']:
                t['industry'] = res['industry']
            all_trades.extend(res['trades'])

    print(f"[Trades] Total: {len(all_trades)}")

    # Save trades
    trades_path = os.path.join(OUT_DIR, 'backtest_tw500_results.json')
    with open(trades_path, 'w', encoding='utf-8') as f:
        json.dump({
            'metadata': {
                'strategy':      f'MA{MA_SHORT}/MA{MA_LONG} crossover + RSI<={RSI_ENTRY_MAX}',
                'period':        f'{START_DATE} to {END_DATE}',
                'universe':      f'Top {TOP_N} TWSE stocks',
                'total_trades':  len(all_trades),
                'generated':     datetime.now().isoformat()
            },
            'trades': all_trades
        }, f, ensure_ascii=False, indent=2)
    print(f"[Output] Trades -> {trades_path}")

    # Analyze
    summary = analyze_results(all_results)
    summary['failed_stocks'] = failed
    summary['stocks_processed'] = len(all_results)

    recs = make_recommendations(summary)
    summary['recommendations'] = recs

    summary_path = os.path.join(OUT_DIR, 'backtest_tw500_summary.json')
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"[Output] Summary -> {summary_path}")

    # Update lessons
    lessons_path = update_lessons(summary, recs)
    print(f"[Output] Lessons -> {lessons_path}")

    # Print summary
    print(f"\n{'='*60}")
    print(f"TW500 BACKTEST RESULTS")
    print(f"{'='*60}")
    print(f"  Period:         {summary['backtest_period']}")
    print(f"  Stocks:         {summary['stocks_processed']} / {TOP_N}")
    print(f"  Total Trades:   {summary['total_trades']}")
    print(f"  Win Rate:       {summary['win_rate']}%")
    print(f"  Avg Return:     {summary['avg_return']}%")
    print(f"  Median Return:  {summary['median_return']}%")
    print(f"  Avg Hold Days:  {summary['avg_hold_days']}")
    print(f"  Exit Breakdown: {summary['exit_reason_counts']}")
    print(f"\n-- Recommendations --")
    for r in recs:
        param = r.get('param','?')
        reason = r.get('reason','')[:80]
        print(f"  [{param}] {reason}")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()