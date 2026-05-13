# -*- coding: utf-8 -*-
"""
策略檢討分析 — 增加交易信號
分析 high-quality 策略，評估可以增加信號的機會
"""
import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB = 'ray_wisdom.db'
conn = sqlite3.connect(DB)
c = conn.cursor()

print("=== 策略檢討分析 — 增加交易信號 ===")
print()

# 找高 Sharpe + 高交易次數的策略
c.execute('''
SELECT strategy_name, symbol, indicator, sharpe_ratio, max_drawdown, win_rate,
       total_return, num_trades, AVG(total_return * 1.0 / NULLIF(num_trades, 0)) as avg_per_trade
FROM backtest_reports
WHERE sharpe_ratio > 0 AND num_trades > 5
GROUP BY strategy_name, symbol
ORDER BY sharpe_ratio DESC
LIMIT 15
''')
high_quality = c.fetchall()

print("🔍 高潛力策略（可增加信號）:")
print(f"   {'策略':<20} {'標的':<10} {'Sharpe':>7} {'MDD':>7} {'Win%':>6} {'筆數':>5} {'Avg/筆':>8}")
print(f"   {'-'*20} {'-'*10} {'-'*7} {'-'*7} {'-'*6} {'-'*5} {'-'*8}")
for row in high_quality:
    strat = row[0][:18] if row[0] else "N/A"
    sym = row[1][:8] if row[1] else "N/A"
    avg_ret = row[8] if row[8] else 0
    print(f"   {strat:<20} {sym:<10} {row[3]:>7.2f} {row[4]:>7.2f} {row[5]:>6.1f} {row[6]:>5} {avg_ret:>8.2f}")

print()

# 分析 RSI2 策略（實際有交易的）
c.execute('''
SELECT symbol, indicator, sharpe_ratio, win_rate, num_trades, total_return
FROM backtest_reports
WHERE indicator LIKE '%RSI2%' AND sharpe_ratio > 0
ORDER BY sharpe_ratio DESC
LIMIT 10
''')
rsi2_strategies = c.fetchall()

print("📈 RSI2 相關策略（Connors 延伸）:")
for row in rsi2_strategies:
    print(f"   {row[0]:<10} {row[1]:<15} Sharpe:{row[2]:.2f} Win:{row[3]*100:.0f}% Trades:{row[4]} Ret:{row[5]:.2f}%")

print()

# 找低交易次數但高 Sharpe 的（未被充分利用）
c.execute('''
SELECT strategy_name, symbol, indicator, sharpe_ratio, num_trades, total_return
FROM backtest_reports
WHERE sharpe_ratio >= 1.0 AND num_trades BETWEEN 3 AND 15
ORDER BY sharpe_ratio DESC
LIMIT 10
''')
underutilized = c.fetchall()

print("⚠️ 低交易次數高Sharpe策略（未充分利用）:")
for row in underutilized:
    strat = row[0][:18] if row[0] else "N/A"
    sym = row[1][:8] if row[1] else "N/A"
    print(f"   {strat:<18} {sym:<8} Sharpe:{row[3]:.2f} Trades:{row[4]} Ret:{row[5]:.2f}%")

print()

# Momentum 策略分析
c.execute('''
SELECT symbol, sharpe_ratio, num_trades, total_return, max_drawdown
FROM backtest_reports
WHERE indicator LIKE '%MOMENTUM%' AND sharpe_ratio > 0.5
ORDER BY sharpe_ratio DESC
LIMIT 10
''')
momentum = c.fetchall()

print("🚀 Momentum 策略（推薦加碼）:")
for row in momentum:
    sym = row[0][:8] if row[0] else "N/A"
    print(f"   {sym:<8} Sharpe:{row[1]:.2f} Trades:{row[2]} Ret:{row[3]:.2f}% MDD:{row[4]:.2f}%")

print()

# 找出可以新增信號的標的（根據現有高 Sharpe 策略）
c.execute('''
SELECT DISTINCT symbol FROM backtest_reports
WHERE sharpe_ratio >= 1.0 AND num_trades >= 5
ORDER BY sharpe_ratio DESC
LIMIT 20
''')
good_symbols = [r[0] for r in c.fetchall()]

print("🎯 建議增加信號的標的 (Sharpe >= 1.0):")
print(f"   {', '.join(good_symbols)}")

# 檢查信號邏輯差異
c.execute('''
SELECT indicator, COUNT(*) as cnt, AVG(sharpe_ratio) as avg_s, MAX(sharpe_ratio) as max_s
FROM backtest_reports
WHERE sharpe_ratio > 0
GROUP BY indicator
HAVING cnt >= 3
ORDER BY max_s DESC
LIMIT 8
''')
indicator_perf = c.fetchall()

print()
print("📊 指標表現排名（按最大 Sharpe）:")
for row in indicator_perf:
    ind = row[0][:20] if row[0] else "N/A"
    print(f"   {ind:<20} {row[1]:>3}筆  avg:{row[2]:.2f}  max:{row[3]:.2f}")

conn.close()
print()
print("=== 分析完成 ===")