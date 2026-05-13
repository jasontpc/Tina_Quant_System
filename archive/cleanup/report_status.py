# -*- coding: utf-8 -*-
import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB = 'ray_wisdom.db'
conn = sqlite3.connect(DB)
c = conn.cursor()

# Backtest 統計
c.execute('SELECT COUNT(*), AVG(sharpe_ratio), MAX(sharpe_ratio), AVG(max_drawdown) FROM backtest_reports WHERE sharpe_ratio > 0')
bt = c.fetchone()

# High-conf corrections
c.execute('SELECT COUNT(*) FROM wisdom_corrections WHERE confidence >= 0.8')
high = c.fetchone()[0]

# wisdom_logs 總量
c.execute('SELECT COUNT(*) FROM wisdom_logs')
wl = c.fetchone()[0]

# 今日新寫入
c.execute("SELECT COUNT(*) FROM wisdom_corrections WHERE created_at >= date('now', '-1 day')")
new_today = c.fetchone()[0]

from datetime import date
today = date.today().strftime("%Y-%m-%d")

print(f"📊 Ray 大腦今日報告 ({today})")
print()
print(f"🧠 大腦庫存")
print(f"   策略報告: {bt[0]} 筆 | Avg Sharpe: {bt[1]:.2f} | Max: {bt[2]:.2f}")
print(f"   Avg MDD: {bt[3]:.2f}%")
print(f"   高信心修正: {high} 筆")

# 掃描主要 ETF
etfs = ['VTI', 'VOO', 'QQQ', 'BND', 'VEA']
print()
print(f"📋 美股 ETF 策略庫存:")
for etf in etfs:
    c.execute('SELECT COUNT(*) FROM backtest_reports WHERE symbol LIKE ?', (f'%{etf}%',))
    cnt = c.fetchone()[0]
    print(f"   {etf}: {cnt} 筆報告")

print()
print(f"📝 今日動態")
print(f"   新增 wisdom_corrections: {new_today} 筆")
print(f"   wisdom_logs 總量: {wl} 筆")

# signals_log
c.execute('SELECT COUNT(*) FROM signals_log')
sig = c.fetchone()[0]
print(f"   signals_log: {sig} 筆")

# web_source
c.execute('SELECT COUNT(*) FROM wisdom_corrections WHERE symbol="WEB_SOURCE"')
web = c.fetchone()[0]
print(f"   WEB_SOURCE: {web} 筆")

conn.close()
print()
print("✅ 報告完成")