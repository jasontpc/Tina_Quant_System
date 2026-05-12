# -*- coding: utf-8 -*-
import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB = 'ray_wisdom.db'
conn = sqlite3.connect(DB)
c = conn.cursor()

print("=== 本地 LLM 回測歷史交易報告 ===")
print()

# 回測總覽
c.execute('SELECT COUNT(*), AVG(sharpe_ratio), MAX(sharpe_ratio), MIN(sharpe_ratio) FROM backtest_reports WHERE sharpe_ratio > 0')
total, avg_sharpe, max_sharpe, min_sharpe = c.fetchone()

c.execute('SELECT COUNT(*) FROM backtest_reports WHERE sharpe_ratio >= 1.5 AND max_drawdown <= 15')
quality = c.fetchone()[0]

c.execute('SELECT COUNT(*) FROM backtest_reports WHERE sharpe_ratio < 0')
failed = c.fetchone()[0]

print(f"📊 回測概覽")
print(f"   總回測數: {total} 筆")
print(f"   平均 Sharpe: {avg_sharpe:.2f}")
print(f"   最高 Sharpe: {max_sharpe:.2f}")
print(f"   最低 Sharpe: {min_sharpe:.2f}")
print(f"   高品質 (Sharpe≥1.5, MDD≤15%): {quality} 筆")
print(f"   失敗 (Sharpe<0): {failed} 筆")
print()

# Top 10 策略
c.execute('SELECT strategy_name, symbol, indicator, sharpe_ratio, max_drawdown, win_rate, total_return, num_trades FROM backtest_reports WHERE sharpe_ratio > 0 ORDER BY sharpe_ratio DESC LIMIT 10')
print(f"🏆 Top 10 高 Sharpe 策略:")
print(f"   {'策略名':<30} {'標的':<8} {'Sharpe':>7} {'MDD':>7} {'Win%':>6} {'Return':>8} {'筆數':>5}")
print(f"   {'-'*30} {'-'*8} {'-'*7} {'-'*7} {'-'*6} {'-'*8} {'-'*5}")
for row in c.fetchall():
    strat = row[0][:28] if row[0] else "N/A"
    sym = row[1][:6] if row[1] else "N/A"
    print(f"   {strat:<30} {sym:<8} {row[3]:>7.2f} {row[4]:>7.2f} {row[5]:>6.1f} {row[6]:>8.2f} {row[7]:>5}")
print()

# 指標分佈
c.execute('SELECT indicator, COUNT(*), AVG(sharpe_ratio) FROM backtest_reports WHERE sharpe_ratio > 0 GROUP BY indicator ORDER BY COUNT(*) DESC LIMIT 8')
print(f"📈 指標分佈:")
for row in c.fetchall():
    ind = row[0][:25] if row[0] else "N/A"
    print(f"   {ind:<25} {row[1]:>4} 筆  avg Sharpe: {row[2]:.2f}")
print()

# 標的分佈
c.execute('SELECT symbol, COUNT(*), AVG(sharpe_ratio), MAX(sharpe_ratio) FROM backtest_reports WHERE sharpe_ratio > 0 GROUP BY symbol ORDER BY COUNT(*) DESC LIMIT 10')
print(f"📋 標的分佈:")
for row in c.fetchall():
    sym = row[0][:10] if row[0] else "N/A"
    print(f"   {sym:<10} {row[1]:>4} 筆  avg: {row[2]:.2f}  max: {row[3]:.2f}")
print()

# trades_log
c.execute('SELECT COUNT(*) FROM trades_log')
trade_count = c.fetchone()[0]
if trade_count > 0:
    c.execute('SELECT trade_date, symbol, action, price, shares, amount, strategy, pnl_pct FROM trades_log ORDER BY trade_date DESC LIMIT 10')
    print(f"📝 trades_log 最近 ({trade_count} 筆):")
    for row in c.fetchall():
        print(f"   {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]}股 | {row[5]:,.0f} | {row[6]} | PnL {row[7]:.2f}%")
else:
    print("📝 trades_log: 尚未寫入")

conn.close()
print()
print("=== 報告完成 ===")