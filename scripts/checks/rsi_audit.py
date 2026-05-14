# -*- coding: utf-8 -*-
"""
RSI 數值覆核 v3 — 對比 DB RSI 與 yfinance 即時 RSI
找出 DB 計算是否有 systematic error
"""

import sys
import yfinance as yf
import sqlite3
import json
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\yfinance.db")
REPORT_FILE = Path(r"C:\Users\USER\.openclaw\workspace\rsi_audit_report.json")


def calc_rsi_pandas(closes, period=14):
    """PDSERIES RSI — 與 yfinance 一致"""
    delta = closes.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = gain / loss.replace(0, float('inf'))
    return 100.0 - (100.0 / (1.0 + rs))


def verify_symbol(sym):
    """對比 DB RSI vs yfinance 即時 RSI"""
    try:
        # 1. DB stored RSI
        conn = sqlite3.connect(DB_PATH)
        conn.execute('PRAGMA journal_mode=WAL')
        db_row = conn.execute('''
            SELECT date, close, rsi_14 FROM daily_ohlcv
            WHERE symbol=? AND rsi_14 IS NOT NULL
            ORDER BY date DESC LIMIT 1
        ''', (sym,)).fetchone()
        conn.close()

        if not db_row:
            return {'sym': sym, 'status': 'no_data'}

        db_date, db_close, db_rsi = db_row

        # 2. yfinance 即時 RSI
        tk = yf.Ticker(sym)
        hist = tk.history(period='3mo')
        if len(hist) < 15:
            return {'sym': sym, 'status': 'insufficient_yfinance'}

        closes = hist['Close']
        yf_rsi = float(calc_rsi_pandas(closes, 14).iloc[-1])

        diff = abs(db_rsi - yf_rsi)

        # Threshold: diff < 3 is acceptable (normal floating point variation)
        if diff < 3:
            status = 'PASS'
        elif diff < 8:
            status = 'WARN'
        else:
            status = 'FAIL'

        return {
            'sym': sym,
            'db_date': db_date,
            'db_close': round(db_close, 2),
            'db_rsi': round(db_rsi, 2),
            'yf_rsi': round(yf_rsi, 2),
            'diff': round(diff, 2),
            'status': status,
        }
    except Exception as e:
        return {'sym': sym, 'status': 'ERROR', 'error': str(e)[:80]}


def run_audit():
    targets = {
        '台股科技股': ['2330.TW','2454.TW','2317.TW','2382.TW','3665.TW','3034.TW'],
        '台股ETF': ['0050.TW','0056.TW','00646.TW','00662.TW','00713.TW','00757.TW','00927.TW'],
        '美股科技股': ['NVDA','AMD','MSFT','AAPL','TSLA','GOOGL'],
        '槓桿/反向ETF': ['SOXL','SOXS','TQQQ','UPRO','SPXL','SPY','QQQ'],
    }

    report = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'results': {}
    }

    total = passed = warned = failed = 0

    for category, syms in targets.items():
        results = []
        for sym in syms:
            r = verify_symbol(sym)
            results.append(r)
            total += 1
            if r.get('status') == 'PASS':
                passed += 1
            elif r.get('status') == 'WARN':
                warned += 1
            elif r.get('status') == 'FAIL':
                failed += 1

        report['results'][category] = results

    report['summary'] = {
        'total': total, 'passed': passed, 'warned': warned, 'failed': failed,
        'pass_rate': round(passed/total*100, 1) if total > 0 else 0
    }

    # Save JSON
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Print
    print(f"\n[RSI 數值覆核 v3] {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"DB: {DB_PATH.name} | 比對: yfinance 即時 RSI")
    print(f"Result: ✅{passed} ⚠️{warned} ❌{failed} | Total: {total}")
    print("=" * 65)

    for cat, res in report['results'].items():
        print(f"\n{cat}:")
        for r in res:
            if r['status'] == 'PASS':
                print(f"  ✅ {r['sym']:<12} DB={r['db_rsi']:>5}  YF={r['yf_rsi']:>5}  DIFF={r['diff']}")
            elif r['status'] == 'WARN':
                print(f"  ⚠️  {r['sym']:<12} DB={r['db_rsi']:>5}  YF={r['yf_rsi']:>5}  DIFF={r['diff']}  ({r['db_date']})")
            elif r['status'] == 'FAIL':
                print(f"  ❌ {r['sym']:<12} DB={r['db_rsi']:>5}  YF={r['yf_rsi']:>5}  DIFF={r['diff']}  ({r['db_date']})")
            else:
                print(f"  ⏭️  {r['sym']}: {r['status']}")

    print(f"\nReport: {REPORT_FILE}")
    return report


if __name__ == '__main__':
    run_audit()
