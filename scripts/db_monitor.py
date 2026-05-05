# -*- coding: utf-8 -*-
"""
db_monitor.py - Tina 量化系統資料庫監控套件
整合所有 db_status*.py 功能於單一入口
用法:
  python db_monitor.py              # 完整監控
  python db_monitor.py --basic      # 基本狀態（db_status, db_status2）
  python db_monitor.py --full       # 完整監控（含 vogel/fugle）
  python db_monitor.py --live       # 即時報價 + 槓桿ETF
"""

import sqlite3
import os
import sys
import json
import yfinance as yf
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')
BASE = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System"
DATA = os.path.join(BASE, "data")
os.chdir(BASE)

def monitor_basic():
    """基本監控（整合 db_status.py + db_status2.py）"""
    print("=== DB Monitor - Basic ===\n")
    dbs = [
        ('tw_history.db', '台股歷史'),
        ('us_history.db', '美股歷史'),
        ('maggy_ai_tech.db', 'Maggy AI/科技'),
        ('sherry_etf.db', 'Sherry ETF'),
        ('us_sim_trades.db', '美股模擬交易'),
        ('master_backtest.db', '主回測資料庫'),
        ('vogel_indicators.db', 'Vogel 台指'),
    ]
    total_size = 0
    for db, desc in dbs:
        p = os.path.join(DATA, db)
        if os.path.exists(p):
            sz = os.path.getsize(p) / 1024
            total_size += sz
            conn = sqlite3.connect(p)
            cur = conn.cursor()
            try:
                tables = [t[0] for t in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
                total = 0
                for t in tables:
                    try:
                        total += cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
                    except: pass
                print(f'{desc:<18} {sz:>7.0f}KB  {total:>10,}筆記錄')
            except: print(f'{desc:<18} {sz:>7.0f}KB  ERROR')
            conn.close()
        else:
            print(f'{desc:<18}  NOT FOUND')
    print()
    print(f'總大小: {total_size:.0f} KB ({total_size/1024:.1f} MB)')

def monitor_full():
    """完整監控（整合 db_status_full.py）"""
    print("=== DB Monitor - Full ===\n")

    # Vogel TX indicators DB
    db_vogel = os.path.join(DATA, 'vogel_indicators.db')
    if os.path.exists(db_vogel):
        conn = sqlite3.connect(db_vogel)
        cur = conn.cursor()
        cur.execute('SELECT MAX(date), COUNT(*) FROM daily')
        row = cur.fetchone()
        print(f'Vogel TX Indicators: {row[1]}筆, 最新 {row[0]}')
        # Latest TX state
        cur.execute('SELECT date, close, zone, rsi_14 FROM daily ORDER BY date DESC LIMIT 1')
        r = cur.fetchone()
        if r:
            print(f'  TX: {r[0]} close={r[1]:.0f} zone={r[2]} RSI={r[3]:.1f}')
        conn.close()
    else:
        print('Vogel TX DB: NOT FOUND')

    # Fugle quotes DB
    db_fugle = os.path.join(DATA, 'fugle.db')
    if os.path.exists(db_fugle):
        conn = sqlite3.connect(db_fugle)
        cur = conn.cursor()
        cur.execute('SELECT MAX(updated_at), COUNT(*) FROM quote_latest')
        row = cur.fetchone()
        print(f'Fugle 即時報價: {row[1]}筆, 更新 {row[0]}')
        conn.close()
    else:
        print('Fugle DB: NOT FOUND')

    # TW history DB
    db_tw = os.path.join(DATA, 'tw_history.db')
    if os.path.exists(db_tw):
        conn = sqlite3.connect(db_tw)
        cur = conn.cursor()
        cur.execute('SELECT MAX(date), COUNT(*) FROM daily_ohlcv')
        row = cur.fetchone()
        print(f'TW 歷史日K: {row[1]}筆, 最新 {row[0]}')
        conn.close()
    else:
        print('TW History DB: NOT FOUND')

    # Trade logs
    print()
    logs = {
        'Nana Sim Trades': ('teams/nana/nana_sim_trades.json', 'trades'),
        'Nana Auto Trades': ('teams/nana/autonomous_trades.json', 'trades'),
        'Vogel v8 Trade Log': ('teams/vogel/vogel_trade_log_v8.json', None),
    }
    for name, (path, key) in logs.items():
        full_path = os.path.join(BASE, path)
        if os.path.exists(full_path):
            with open(full_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                print(f'{name}: {len(data)}筆')
            elif isinstance(data, dict):
                trades = data.get('trades', [])
                stats = data.get('stats', {})
                wr = stats.get('win_rate', 0)
                avg = stats.get('avg_return', 0)
                print(f'{name}: {len(trades)}筆交易, WR={wr*100:.0f}%, 報酬={avg*100:.1f}%')
                print(f'  Last updated: {data.get("last_updated", stats.get("last_updated", "unknown"))}')

    print()
    print('=== 今日更新完成 ===')

def monitor_live():
    """即時報價監控（整合 db_status.py live update）"""
    print("=== Live Update (Key ETFs) ===\n")
    key_etfs = [
        ('SOXL', 'SOXL半導體3x'),
        ('TQQQ', 'Nasdaq3x'),
        ('SQQQ', 'Nasdaq-3x'),
        ('SPXL', 'S&P500 3x'),
        ('UPRO', 'S&P500 3x'),
    ]
    for ticker, name in key_etfs:
        try:
            t = yf.Ticker(ticker)
            h = t.history(period='5d')
            if len(h) >= 2:
                curr = float(h['Close'].iloc[-1])
                prev = float(h['Close'].iloc[-2])
                chg = (curr - prev) / prev * 100
                info = t.info
                rsi = info.get('rsi', 50) or 50
                print(f'{ticker} ({name}): {curr:.2f} ({chg:+.2f}%) | RSI: {rsi:.0f}')
        except Exception as e:
            print(f'{ticker}: error - {e}')

    # Also check leverage ETF DB
    db_lev = os.path.join(DATA, 'leverage_etf.db')
    if os.path.exists(db_lev):
        conn = sqlite3.connect(db_lev)
        cur = conn.cursor()
        cur.execute('SELECT name FROM sqlite_master WHERE type="table"')
        tables = [r[0] for r in cur.fetchall()]
        print(f'\nLeverage ETF DB Tables: {tables}')
        for t in tables:
            try:
                cur.execute(f'SELECT COUNT(*) FROM {t}')
                print(f'  {t}: {cur.fetchone()[0]} rows')
            except: pass
        conn.close()

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Tina DB Monitor')
    parser.add_argument('--basic', action='store_true', help='Basic status check')
    parser.add_argument('--full', action='store_true', help='Full monitoring')
    parser.add_argument('--live', action='store_true', help='Live quotes + leverage ETF')
    args = parser.parse_args()

    if not (args.basic or args.full or args.live):
        # Default: run basic + full
        monitor_basic()
        print()
        monitor_full()
        print()
        monitor_live()
        return

    if args.basic:
        monitor_basic()
    if args.full:
        monitor_full()
    if args.live:
        monitor_live()

if __name__ == '__main__':
    main()