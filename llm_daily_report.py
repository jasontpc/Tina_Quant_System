# -*- coding: utf-8 -*-
"""Ray LLM 今日運作報告"""
import sys, sqlite3, json, time, subprocess
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB = 'ray_wisdom.db'
conn = sqlite3.connect(DB)
c = conn.cursor()

print("=== Ray LLM 今日運作報告 ===")
print()

# 1. Token 使用
print("1. Token 使用")
c.execute("SELECT model, weekly_used, weekly_total FROM token_history WHERE date >= date('now', '-1 day') GROUP BY model")
rows = c.fetchall()
for r in rows:
    pct = (r[1] / r[2] * 100) if r[2] > 0 else 0
    print(f"   {r[0]}: {r[1]:,} / {r[2]:,} ({pct:.1f}%)")
print()

# 2. backtest_reports
print("2. 回測報告")
c.execute("SELECT COUNT(*), AVG(sharpe_ratio), MAX(sharpe_ratio) FROM backtest_reports WHERE sharpe_ratio > 0")
bt = c.fetchone()
print(f"   總筆數: {bt[0]}")
print(f"   Avg Sharpe: {bt[1]:.2f}")
print(f"   Max Sharpe: {bt[2]:.2f}")
c.execute("SELECT COUNT(*) FROM backtest_reports WHERE sharpe_ratio >= 1.5")
high = c.fetchone()[0]
print(f"   高 Sharpe (>=1.5): {high} 筆")
print()

# 3. wisdom_corrections
print("3. 智慧修正")
c.execute("SELECT COUNT(*) FROM wisdom_corrections")
wc = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM wisdom_corrections WHERE confidence >= 0.8")
high = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM wisdom_corrections WHERE symbol='WEB_SOURCE'")
web = c.fetchone()[0]
print(f"   總修正: {wc} 筆")
print(f"   高信心 (>=0.8): {high} 筆")
print(f"   連網學習: {web} 筆")
print()

# 4. signals_log
print("4. 交易信號")
c.execute("SELECT COUNT(*) FROM signals_log")
sig = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM signals_log WHERE approved=1")
app = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM signals_log WHERE approved=0")
pend = c.fetchone()[0]
print(f"   總信號: {sig} 筆")
print(f"   已核准: {app} 筆")
print(f"   待確認: {pend} 筆")
print()

# 5. daily_performance
print("5. 每日績效")
c.execute("SELECT COUNT(*) FROM daily_performance")
dp = c.fetchone()[0]
print(f"   總記錄: {dp} 筆")
print()

# 6. Ollama 模型狀態
print("6. Ollama 模型")
try:
    result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
    lines = result.stdout.strip().split('\n')
    for line in lines[1:6]:
        if line:
            print(f"   {line}")
except:
    print("   (無法取得狀態)")

print()
print("=== 報告完成 ===")
conn.close()