# -*- coding: utf-8 -*-
"""
Phase 4 完成：生成 HTML 回測報告
backtest_report_generator.py
"""

import json, sqlite3
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

WORKSPACE     = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
RESULTS_DIR   = WORKSPACE / 'data' / 'backtest_results'
OUTPUT_HTML   = WORKSPACE / 'data' / 'backtest_results.html'

STRATEGIES_CN = {
    'swing':      '波段交易 (Swing)',
    'growth_long':'長期成長 (Growth-Long)',
    'dca':        '定期定額 (DCA)',
    'etf_trend':  'ETF 趨勢追蹤',
}

def load_results():
    results = {}
    for f in RESULTS_DIR.glob('backtest_*.json'):
        strat = f.stem.replace('backtest_', '')
        with open(f, 'r', encoding='utf-8') as fp:
            results[strat] = json.load(fp)
    return results

def build_table(strat, rows):
    rows_sorted = sorted(rows, key=lambda x: x.get('total_return', 0), reverse=True)
    trs = ''
    for r in rows_sorted:
        ret  = r.get('total_return', 0)
        wr   = r.get('win_rate', 0)
        sharpe = r.get('sharpe_ratio', 0)
        dd   = r.get('max_drawdown', 0)
        color = '#2d6a4f' if ret > 0 else '#9b2226'
        trs += f'''
        <tr>
          <td class="symbol">{r.get('symbol','')}</td>
          <td class="num" style="color:{color};font-weight:700">{ret:+.2f}%</td>
          <td class="num">{wr:.1f}%</td>
          <td class="num">{r.get('num_trades',0)}</td>
          <td class="num">{sharpe:.2f}</td>
          <td class="num" style="color:#9b2226">{dd:.2f}%</td>
          <td class="num">{(r.get('avg_win_pct',0)):.1f}%</td>
          <td class="num">{(r.get('avg_loss_pct',0)):.1f}%</td>
        </tr>'''
    return trs

def strategy_summary_table(all_results):
    rows = []
    for strat, data in all_results.items():
        rets  = [r['total_return'] for r in data]
        wins  = [r['win_rate'] for r in data]
        dds   = [r['max_drawdown'] for r in data]
        best_sym  = max(data, key=lambda x: x['total_return'])['symbol']
        best_ret  = max(r['total_return'] for r in data)
        worst_sym = min(data, key=lambda x: x['total_return'])['symbol']
        worst_ret = min(r['total_return'] for r in data)
        rows.append({
            'strategy':   STRATEGIES_CN.get(strat, strat),
            'n':          len(data),
            'avg_ret':    np.mean(rets),
            'med_ret':    np.median(rets),
            'avg_wr':     np.mean(wins),
            'avg_dd':     min(dds),
            'sharpe_avg': np.mean([r['sharpe_ratio'] for r in data]),
            'best':       f'{best_sym} ({best_ret:+.2f}%)',
            'worst':      f'{worst_sym} ({worst_ret:+.2f}%)',
        })
    rows_sorted = sorted(rows, key=lambda x: x['avg_ret'], reverse=True)
    trs = ''
    for r in rows_sorted:
        color = '#2d6a4f' if r['avg_ret'] > 0 else '#9b2226'
        trs += f'''
        <tr class="summary-row">
          <td class="strategy-name">{r['strategy']}</td>
          <td class="num">{r['n']}</td>
          <td class="num" style="color:{color};font-weight:700">{r['avg_ret']:+.2f}%</td>
          <td class="num">{r['med_ret']:+.2f}%</td>
          <td class="num">{r['avg_wr']:.1f}%</td>
          <td class="num">{r['sharpe_avg']:.2f}</td>
          <td class="num" style="color:#9b2226">{r['avg_dd']:.2f}%</td>
          <td class="win-tag">{r['best']}</td>
          <td class="loss-tag">{r['worst']}</td>
        </tr>'''
    return trs

def main():
    all_results = load_results()

    strategy_blocks = ''
    for strat, data in all_results.items():
        cn_name = STRATEGIES_CN.get(strat, strat)
        avg_ret = np.mean([r['total_return'] for r in data])
        avg_wr  = np.mean([r['win_rate'] for r in data])
        avg_dd  = min(r['max_drawdown'] for r in data)
        badge_color = '#2d6a4f' if avg_ret >= 0 else '#9b2226'

        strategy_blocks += f'''
        <div class="strategy-block">
          <div class="strategy-header">
            <h2>{cn_name}</h2>
            <div class="badge" style="background:{badge_color}">{avg_ret:+.2f}% Avg</div>
            <div class="badge" style="background:#1d3557">{avg_wr:.1f}% WinRate</div>
            <div class="badge" style="background:#9b2226">MaxDD {avg_dd:.2f}%</div>
          </div>
          <table>
            <thead>
              <tr>
                <th>Symbol</th><th>Return</th><th>WinRate</th><th>Trades</th>
                <th>Sharpe</th><th>MaxDD</th><th>Avg Win</th><th>Avg Loss</th>
              </tr>
            </thead>
            <tbody>
              {build_table(strat, data)}
            </tbody>
          </table>
        </div>'''

    html = f'''<!DOCTYPE html>
<html lang="zh-TW"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tina Quant System - Backtest Report {datetime.now().strftime('%Y-%m-%d')}</title>
<style>
 *{{margin:0;padding:0;box-sizing:border-box}}
  body{{font-family:'Segoe UI',system-ui,sans-serif;background:#0d1b2a;color:#e0e0e0;padding:24px}}
  .container{{max-width:1400px;margin:0 auto}}
  h1{{color:#a8dadc;font-size:1.8em;margin-bottom:6px}}
  .subtitle{{color:#778da9;font-size:0.85em;margin-bottom:28px}}
  .summary-table{{width:100%;border-collapse:collapse;margin-bottom:32px;background:#1b263b;border-radius:10px;overflow:hidden}}
  .summary-table th{{background:#1d3557;padding:12px 16px;text-align:left;font-size:0.85em;color:#a8dadc;letter-spacing:0.05em}}
  .summary-table td{{padding:11px 16px;font-size:0.9em;border-bottom:1px solid #2a4460}}
  .summary-row:hover{{background:#243554}}
  .strategy-block{{background:#1b263b;border-radius:12px;margin-bottom:24px;overflow:hidden}}
  .strategy-header{{display:flex;align-items:center;gap:14px;padding:18px 22px;background:#243554;border-bottom:2px solid #2a4460}}
  .strategy-header h2{{color:#a8dadc;font-size:1.2em;flex:1}}
  .badge{{color:#fff;font-size:0.78em;font-weight:700;padding:4px 10px;border-radius:20px}}
  table{{width:100%;border-collapse:collapse}}
  thead tr{{background:#1d3557}}
  th{{padding:10px 16px;text-align:left;font-size:0.8em;color:#a8dadc;letter-spacing:0.04em;font-weight:600}}
  td{{padding:9px 16px;font-size:0.88em;border-bottom:1px solid #1e3048;color:#d0d8e4}}
  tr:last-child td{{border-bottom:none}}
  tr:hover{{background:#1e3048}}
  .num{{text-align:right;font-variant-numeric:tabular-nums}}
  .symbol{{font-weight:600;color:#a8dadc}}
  .strategy-name{{font-weight:700;color:#a8dadc}}
  .win-tag{{color:#2d6a4f;font-size:0.82em}}
  .loss-tag{{color:#9b2226;font-size:0.82em}}
  .info-bar{{display:flex;gap:16px;margin-bottom:24px;font-size:0.82em;color:#778da9}}
  .info-bar span{{background:#1b263b;padding:8px 14px;border-radius:6px}}
  .footer{{text-align:center;color:#3a5068;font-size:0.78em;margin-top:32px}}
</style></head><body>
<div class="container">
  <h1>Tina Quant System - 回測報告</h1>
  <div class="subtitle">2024-01-01 至 2026-05-08 | 台股 20 檔 | 4 策略比較 | {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
  <div class="info-bar">
    <span>波段 (Swing) - 7天 / RSI&lt;55 / 2xATR停損</span>
    <span>成長 (Growth-Long) - 18個月 / RSI&lt;50 / 20%停損</span>
    <span>DCA - 月配 / 30天频率 / 無停利</span>
    <span>ETF趨勢 - MA5&gt;MA20進場 / 60天持有</span>
  </div>
  <table class="summary-table">
    <thead><tr>
      <th>策略</th><th>檔數</th><th>平均報酬</th><th>中位數報酬</th>
      <th>平均勝率</th><th>Sharpe</th><th>最大回落</th>
      <th>最佳標的</th><th>最差標的</th>
    </tr></thead>
    <tbody>{strategy_summary_table(all_results)}</tbody>
  </table>
  {strategy_blocks}
  <div class="footer">Tina Quant System | backtest_framework.py v1.0 | yfinance.db本地數據</div>
</div></body></html>'''

    with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'[OK] Report saved: {OUTPUT_HTML}')

if __name__ == '__main__':
    main()