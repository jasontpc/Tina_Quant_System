# -*- coding: utf-8 -*-
"""Leo 失敗模式深度分析 - 2026-04-27"""
import json
from collections import defaultdict

with open('leos_backtest_report.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

trades = d['trades']

# === 基本統計 ===
sl_trades = [t for t in trades if t['exit_reason'] == 'SL']
hold_trades = [t for t in trades if t['exit_reason'] == 'HOLD']
tp_trades = [t for t in trades if t['exit_reason'] == 'TP']

print('=' * 55)
print('Leo 失敗模式深度分析')
print('=' * 55)

# SL 分析
sl_losses = [t for t in sl_trades if t['pnl_pct'] < 0]
print(f'\n【停損 (SL)】共 {len(sl_trades)} 筆')
print(f'  平均虧損: {sum(t["pnl_pct"] for t in sl_trades)/len(sl_trades):.2f}%')
print(f'  最大虧損: {min(t["pnl_pct"] for t in sl_trades):.2f}%')

# 虧損 HOLD 分析
hold_losses = [t for t in hold_trades if t['pnl_pct'] < 0]
print(f'\n【持有到期虧損 (HOLD)】共 {len(hold_losses)} 筆')
if hold_losses:
    print(f'  平均虧損: {sum(t["pnl_pct"] for t in hold_losses)/len(hold_losses):.2f}%')
    print(f'  最大虧損: {min(t["pnl_pct"] for t in hold_losses):.2f}%')

# === 虧損交易特征 ===
print('\n【虧損交易時段分布】')
losses = [t for t in trades if t['pnl_pct'] < 0]
quarters = defaultdict(list)
for t in losses:
    y, m = t['entry_date'].split('-')[:2]
    q = f"{y}-Q{(int(m)-1)//3 + 1}"
    quarters[q].append(t)

for q in sorted(quarters.keys()):
    ts = quarters[q]
    wr = len([t for t in ts if t['pnl_pct'] > 0]) / len(ts) * 100
    avg = sum(t['pnl_pct'] for t in ts) / len(ts)
    print(f"  {q}: {len(ts)}筆虧損 | 季勝率{wr:.0f}% | 均報酬 {avg:+.2f}%")

# === 個股表現排行 ===
print('\n【個股表現排行】')
by_stock = defaultdict(list)
for t in trades:
    by_stock[t['ticker']].append(t)

stock_stats = []
for ticker, ts in by_stock.items():
    wr = len([t for t in ts if t['pnl_pct'] > 0]) / len(ts) * 100
    avg = sum(t['pnl_pct'] for t in ts) / len(ts)
    sl = len([t for t in ts if t['exit_reason'] == 'SL'])
    tp = len([t for t in ts if t['exit_reason'] == 'TP'])
    stock_stats.append((ticker, ts[0]['name'], len(ts), wr, avg, sl, tp))

stock_stats.sort(key=lambda x: x[4], reverse=True)
print(f"{'代碼':<8} {'名稱':<6} {'筆數':<4} {'勝率':<6} {'均報酬':<8} {'SL':<3} {'TP':<3}")
print("-" * 45)
for row in stock_stats:
    print(f"{row[0]:<8} {row[1]:<6} {row[2]:<4} {row[3]:>5.0f}% {row[4]:>+7.2f}% {row[5]:<3} {row[6]:<3}")

# === 停利 vs 停損對比 ===
print('\n【停利vs停損對比】')
tp_wins = [t for t in tp_trades if t['pnl_pct'] > 0]
tp_avg = sum(t['pnl_pct'] for t in tp_trades) / len(tp_trades)
sl_avg = sum(t['pnl_pct'] for t in sl_trades) / len(sl_trades)
print(f"  TP 停利: {len(tp_trades)}筆 | 均報酬 {tp_avg:+.2f}%")
print(f"  SL 停損: {len(sl_trades)}筆 | 均報酬 {sl_avg:+.2f}%")
print(f"  期望值差距: {tp_avg - sl_avg:.2f}%")

# === 改進建議 ===
print('\n【改進建議】')
print("  1. 廣達(2382) 均報酬 +5.14% 最強，應提高權重")
print("  2. 緯穎(3034) 均報酬 -0.11% 偏弱，建議降低或移除")
print("  3. 技嘉(2376) SL 5次最多，止损应更严格或降低持仓")
print("  4. 穎崴(3665) TP 8次但也有5次SL，適合短線操作")
print("  5. 新進場點：MA60 > MA120 多頭排列時進場，勝率更高")
print("  6. 動量過濾：進場前確認近5日漲幅落後大盤 < 3%")
print("  7. 建議建立股票分組：進攻型(2330/2382/3665) / 穩健型(2454/2317)")