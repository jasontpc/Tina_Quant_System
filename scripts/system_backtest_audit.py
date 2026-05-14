# -*- coding: utf-8 -*-
"""
system_backtest_audit.py — 全系統回測數據普查
"""

import json, os, sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')

reports = [
    # (path, team, description)
    ('stores/backtest_report.json', 'Tina V3 Alpha', '美股/ETF 主資料庫'),
    ('teams/leo/reports/leo_backtest_report_v2.json', 'Leo 台股波段', '290筆模擬交易'),
    ('teams/nana/reports/nana_backtest_report.json', 'Nana 波段', '台股百大'),
    ('teams/ray/reports/backtest_report.json', 'Ray 美股', '美股報告'),
    ('teams/maggy/reports/full_backtest.json', 'Maggy 美股', '完整回測'),
    ('data/backtest_results.json', 'Tina data', '主DB'),
    ('data/full_backtest_results.json', 'Tina data', '完整結果'),
    ('data/full_team_backtest_results.json', 'Tina data', '團隊結果'),
    ('data/nana_backtest_results.json', 'Nana data', 'Nana結果'),
    ('data/quick_backtest.json', 'Tina quick', '快速回測'),
    ('teams/nana/archive_json/expanded_backtest.json', 'Nana archive', '擴展回測'),
    ('teams/nana/archive_json/backtest_final.json', 'Nana archive', '最終回測'),
    ('automation/backtest_results/full_backtest_optimization.json', 'Automation', '自動化優化'),
]

print('=== 全系統回測數據普查 ===\n')
results = []

for rel_path, team, desc in reports:
    full = BASE / rel_path
    if not full.exists():
        print(f'[MISSING]  {team} - {desc}: 檔案不存在')
        results.append({'team': team, 'desc': desc, 'status': 'MISSING', 'total': 0, 'wr': 0, 'avg': 0})
        continue

    size = full.stat().st_size
    if size == 0:
        print(f'[EMPTY]   {team} - {desc}: 0 bytes')
        results.append({'team': team, 'desc': desc, 'status': 'EMPTY', 'total': 0, 'wr': 0, 'avg': 0})
        continue

    try:
        with open(full, 'r', encoding='utf-8') as f:
            raw = f.read()
        data = json.loads(raw)

        # Determine type and extract stats
        if isinstance(data, list):
            # Array of trade results
            trades = data
            total = len(trades)
            wins = len([t for t in trades if (isinstance(t, dict) and t.get('pnl_pct', 0) > 0) or (isinstance(t, (int, float)) and t > 0)])
            wr = wins / total * 100 if total > 0 else 0
            if isinstance(trades[0], dict) if trades else False:
                pnl_vals = [t.get('pnl_pct', 0) for t in trades if isinstance(t, dict)]
            else:
                pnl_vals = [t for t in trades if isinstance(t, (int, float))]
            avg = sum(pnl_vals) / len(pnl_vals) if pnl_vals else 0
            # Get period if available
            period = None
            tickers = set()
            if trades and isinstance(trades[0], dict):
                for t in trades:
                    if 'date' in t: period = 'has_dates'
                    if 'symbol' in t: tickers.add(t.get('symbol', ''))
                period = period or 'N/A'
        elif isinstance(data, dict):
            # Report format with performance dict
            perf = data.get('performance', data)
            total = perf.get('total_trades', 0) or len(data.get('trades', []))
            wr = perf.get('win_rate', 0)
            if isinstance(wr, float) and wr > 100: wr = wr / 100
            avg = perf.get('avg_return', 0)
            period = data.get('backtest_period', data.get('period', 'N/A'))
            tickers = set()
            for k in ['by_stock', 'stocks', 'tickers']:
                if k in data and isinstance(data[k], list):
                    tickers = set(t.get('ticker', t.get('symbol', '')) for t in data[k])
                    break
            if not tickers and 'trades' in data:
                tickers = set(t.get('symbol', t.get('ticker', '')) for t in data['trades'][:50])
            if 'ticker' in data: tickers.add(data['ticker'])
        else:
            total = 0; wr = 0; avg = 0; period = 'N/A'; tickers = set()

        status = 'OK'
        if total == 0: status = 'ZERO'
        elif wr < 45: status = 'LOW'
        elif wr >= 60: status = 'GOOD'

        print(f'[{status:<6}] {team}')
        print(f'         {desc} | {total} trades | WR {wr:.1f}% | Avg {avg:+.3f}%')
        if period: print(f'         Period: {period}')
        if tickers: print(f'         Tickers: {sorted(tickers)[:8]}')

        results.append({
            'team': team, 'desc': desc, 'status': status,
            'total': total, 'wr': round(wr, 1), 'avg': round(avg, 3),
            'path': rel_path, 'period': period, 'tickers': sorted(tickers)[:8]
        })

    except Exception as e:
        print(f'[ERROR]   {team} - {desc}: {e}')
        results.append({'team': team, 'desc': desc, 'status': 'ERROR', 'total': 0, 'wr': 0, 'avg': 0, 'error': str(e)})

    print()

# Summary
print('=== Summary ===')
ok = [r for r in results if r['status'] == 'OK']
good = [r for r in results if r['status'] == 'GOOD']
low = [r for r in results if r['status'] == 'LOW']
empty = [r for r in results if r['status'] in ('EMPTY', 'ZERO', 'MISSING')]

total_trades = sum(r['total'] for r in results if r['status'] not in ('EMPTY', 'MISSING', 'ERROR'))
valid_reports = [r for r in results if r['total'] > 0]

print(f'Total reports: {len(results)}')
print(f'Valid (with data): {len(valid_reports)}')
print(f'Good (WR>=60%): {len(good)}')
print(f'Low (WR<45%): {len(low)}')
print(f'Empty/Missing: {len(empty)}')
print(f'Total trades across all systems: {total_trades}')

# Save consolidated report
summary_path = BASE / 'stores' / 'system_backtest_summary.json'
with open(summary_path, 'w', encoding='utf-8') as f:
    json.dump({
        'date': '2026-05-14',
        'summary': {
            'total_reports': len(results),
            'valid_reports': len(valid_reports),
            'good_reports': len(good),
            'low_reports': len(low),
            'empty_missing': len(empty),
            'total_trades': total_trades
        },
        'reports': results
    }, f, ensure_ascii=False, indent=2)
print(f'\nSaved: {summary_path}')