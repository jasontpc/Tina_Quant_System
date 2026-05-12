# -*- coding: utf-8 -*-
"""回測數據應用檢討"""
import sys, sqlite3, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB = 'ray_wisdom.db'
conn = sqlite3.connect(DB)
c = conn.cursor()

print("=== 回測數據應用檢討 ===")
print()

# 1. 策略勝率分布
print("📊 策略 Sharpe 分布:")
c.execute("SELECT sharpe_ratio >= 1.5, COUNT(*) FROM backtest_reports GROUP BY sharpe_ratio >= 1.5")
for r in c.fetchall():
    label = "高 Sharpe (≥1.5)" if r[0] else "一般 Sharpe"
    print(f"   {label}: {r[1]} 筆")

print()

# 2. 指標表現排名
print("📈 指標表現排名:")
c.execute("SELECT indicator, COUNT(*), AVG(sharpe_ratio), MAX(sharpe_ratio), AVG(max_drawdown) FROM backtest_reports WHERE sharpe_ratio > 0 GROUP BY indicator ORDER BY MAX(sharpe_ratio) DESC")
for r in c.fetchall():
    ind = r[0][:15] if r[0] else "N/A"
    print(f"   {ind:<15} {r[1]:>4}筆 avg:{r[2]:.2f} max:{r[3]:.2f} avgMDD:{r[4]:.1f}%")

print()

# 3. 高Sharpe策略symbol分布
print("🎯 高Sharpe策略標的分布:")
c.execute("SELECT symbol, strategy_name, sharpe_ratio, max_drawdown, win_rate FROM backtest_reports WHERE sharpe_ratio >= 1.5 ORDER BY sharpe_ratio DESC LIMIT 30")
high_strategies = c.fetchall()
print(f"   {'Symbol':<10} {'Strategy':<25} {'Sharpe':>7} {'MDD':>7} {'Win%':>6}")
print(f"   {'-'*10} {'-'*25} {'-'*7} {'-'*7} {'-'*6}")
for r in high_strategies[:20]:
    sym = r[0][:8] if r[0] else "N/A"
    strat = r[1][:23] if r[1] else "N/A"
    print(f"   {sym:<10} {strat:<25} {r[2]:>7.2f} {r[3]:>7.2f} {r[4]:>6.1f}")

print()

# 4. 應用建議
print("💡 回測數據應用建議:")
high_count = len(high_strategies)
total_count = c.execute("SELECT COUNT(*) FROM backtest_reports").fetchone()[0]

# 計算平均 Sharpe
c.execute("SELECT AVG(sharpe_ratio) FROM backtest_reports WHERE sharpe_ratio > 0")
avg_sharpe = c.fetchone()[0]

# 計算平均 MDD
c.execute("SELECT AVG(max_drawdown) FROM backtest_reports WHERE sharpe_ratio > 0")
avg_mdd = c.fetchone()[0]

print(f"   1. 高Sharpe策略: {high_count} 筆 → 建議直接應用於實盤")
print(f"   2. 平均Sharpe: {avg_sharpe:.2f} → 系統性交易可達正期望")
print(f"   3. 平均MDD: {avg_mdd:.2f}% → 風控設計參考")

# 5. 找出最佳入場時機
print()
print("⏰ 最佳入場時機:")
c.execute("SELECT indicator, AVG(win_rate) as avg_win FROM backtest_reports WHERE sharpe_ratio > 0 GROUP BY indicator ORDER BY avg_win DESC LIMIT 5")
for r in c.fetchall():
    ind = r[0][:20] if r[0] else "N/A"
    print(f"   {ind:<20} 勝率: {r[1]:.1f}%")

# 6. 推薦實盤策略
print()
print("🚀 推薦實盤策略 Top 5:")
c.execute("""
SELECT symbol, indicator, sharpe_ratio, max_drawdown, win_rate, num_trades
FROM backtest_reports
WHERE sharpe_ratio >= 1.5 AND max_drawdown <= 20 AND num_trades >= 5
ORDER BY sharpe_ratio DESC
LIMIT 5
""")
for r in c.fetchall():
    sym = r[0][:8] if r[0] else "N/A"
    ind = r[1][:15] if r[1] else "N/A"
    print(f"   {sym:<8} {ind:<15} Sharpe:{r[2]:.2f} MDD:{r[3]:.1f}% Win:{r[4]:.1f}% Trades:{r[5]}")

conn.close()
print()
print("=== 檢討完成 ===")