# -*- coding: utf-8 -*-
import sqlite3, time, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

conn = sqlite3.connect('ray_wisdom.db')
c = conn.cursor()

print("=== 本地 LLM 開發狀況 ===")
print()

# backtest_reports
c.execute('SELECT COUNT(*), AVG(sharpe_ratio), MAX(sharpe_ratio), COUNT(DISTINCT symbol) FROM backtest_reports WHERE sharpe_ratio > 0')
bt = c.fetchone()
print(f"回測報告: {bt[0]} 筆, Avg Sharpe: {bt[1]:.2f}, Max Sharpe: {bt[2]:.2f}, 獨特標的: {bt[3]}")

# wisdom_corrections
c.execute('SELECT COUNT(*) FROM wisdom_corrections')
wc = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM wisdom_corrections WHERE confidence >= 0.8')
high = c.fetchone()[0]
print(f"智慧修正: {wc} 筆 (高信心 {high} 筆)")

# signals_log
c.execute('SELECT COUNT(*) FROM signals_log')
sig = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM signals_log WHERE approved=1')
approved = c.fetchone()[0]
print(f"交易信號: {sig} 筆 (已核准 {approved} 筆)")

# daily_performance
c.execute('SELECT COUNT(*) FROM daily_performance')
dp = c.fetchone()[0]
print(f"每日績效: {dp} 筆")

# token_history
c.execute('SELECT COUNT(*) FROM token_history')
th = c.fetchone()[0]
print(f"Token追蹤: {th} 筆歷史")

print()

# Modelfile
modelfiles = ['ray-v1.Modelfile', 'ray-deep-v1.Modelfile']
for mf in modelfiles:
    if os.path.exists(mf):
        size = os.path.getsize(mf)
        mtime = os.path.getmtime(mf)
        date = time.strftime('%Y-%m-%d %H:%M', time.localtime(mtime))
        print(f"{mf}: {size} bytes, 更新於 {date}")

print()

# Core scripts
scripts = ['ray_brain.py', 'ray_self_correct.py', 'ray_distiller_auto.py', 'ray_retriever_v2.py', 'ray_integrity_booster.py', 'ray_expert_modules.py', 'ray_data_center.py']
print("核心腳本:")
for s in scripts:
    if os.path.exists(s):
        size = os.path.getsize(s)
        print(f"  [OK] {s} ({size} bytes)")
    else:
        print(f"  [MISSING] {s}")

# Ollama models
print()
print("Ollama Models:")
import subprocess
result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
print(result.stdout[:500] if result.stdout else "No models")

conn.close()
print()
print("=== 狀態報告完成 ===")