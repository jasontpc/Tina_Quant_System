# -*- coding: utf-8 -*-
"""
Tina 每小時心跳監控 v2 — 使用本地 DB，極速
"""

import sys
import sqlite3
import json
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\yfinance.db")
WATCHLIST = ['2330.TW', '2382.TW', '3665.TW', '0050.TW', 'SPY', 'QQQ']


def check_db_health(conn):
    """檢查 DB 健康度"""
    issues = []
    c = conn.cursor()

    # Row count
    cnt = c.execute('SELECT COUNT(*) FROM daily_ohlcv').fetchone()[0]
    if cnt < 1000:
        issues.append(f'row_count_low:{cnt}')

    # Recent data check
    for sym in WATCHLIST:
        row = c.execute('''
            SELECT date, close, rsi_14 FROM daily_ohlcv
            WHERE symbol=? ORDER BY date DESC LIMIT 1
        ''', (sym,)).fetchone()
        if row:
            date, close, rsi = row
            # Check if data is stale (> 5 days old)
            if date and date < '2026-04-25':
                issues.append(f'{sym}_stale:{date}')
        else:
            issues.append(f'{sym}_missing')

    # Indicator coverage
    for col in ['sma_20', 'sma_60', 'rsi_14']:
        null_pct = c.execute(f'''
            SELECT COUNT(*) * 100.0 / (SELECT COUNT(*) FROM daily_ohlcv WHERE close IS NOT NULL)
            FROM daily_ohlcv WHERE {col} IS NULL AND close IS NOT NULL
        ''').fetchone()[0]
        if null_pct > 20:
            issues.append(f'{col}_null:{null_pct:.0f}%')

    return issues


def get_latest_prices(conn):
    """抓取監控名單最新價格"""
    c = conn.cursor()
    results = []
    for sym in WATCHLIST:
        row = c.execute('''
            SELECT date, close, rsi_14 FROM daily_ohlcv
            WHERE symbol=? AND close IS NOT NULL
            ORDER BY date DESC LIMIT 1
        ''', (sym,)).fetchone()
        if row:
            date, close, rsi = row
            results.append({'sym': sym, 'date': date, 'close': close, 'rsi': rsi})
    return results


def run():
    print(f"[Tina 心跳] {datetime.now().strftime('%H:%M')}")

    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA journal_mode=WAL')

    issues = check_db_health(conn)
    prices = get_latest_prices(conn)

    conn.close()

    print(f"DB Health: {'✅ OK' if not issues else '❌ ' + ', '.join(issues)}")
    print("Latest Prices:")
    for p in prices:
        rsi_str = f"{p['rsi']:.1f}" if p['rsi'] else "N/A"
        print(f"  {p['sym']:<12} {p['date']}  ${p['close']:>8.2f}  RSI={rsi_str}")

    if issues:
        print(f"\n⚠️ Issues found: {len(issues)}")
        for iss in issues[:5]:
            print(f"  - {iss}")

    return {'issues': issues, 'prices': prices, 'ok': len(issues) == 0}


if __name__ == '__main__':
    result = run()
    sys.exit(0 if result['ok'] else 1)
