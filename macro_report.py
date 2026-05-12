# -*- coding: utf-8 -*-
import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB = 'ray_wisdom.db'
conn = sqlite3.connect(DB)
c = conn.cursor()

print('=== 本地宏觀資料庫報告 ===')
print()

# 資料庫總覽
c.execute('SELECT name FROM sqlite_master WHERE type="table" ORDER BY name')
tables = [r[0] for r in c.fetchall()]
print(f'資料表清單 ({len(tables)} 個):')
for t in tables:
    c.execute(f'SELECT COUNT(*) FROM {t}')
    cnt = c.fetchone()[0]
    print(f'   {t}: {cnt} 筆')
print()

# wisdom_corrections 分類
c.execute('SELECT COUNT(*), AVG(confidence) FROM wisdom_corrections WHERE confidence >= 0.8')
high = c.fetchone()
c.execute('SELECT COUNT(*), AVG(confidence) FROM wisdom_corrections WHERE confidence < 0.8 AND confidence >= 0.5')
mid = c.fetchone()
c.execute('SELECT COUNT(*), AVG(confidence) FROM wisdom_corrections WHERE confidence < 0.5')
low = c.fetchone()
print('wisdom_corrections 信心分佈:')
print(f'   高信心 (>=0.8): {high[0]} 筆 (avg conf: {high[1]:.2f})')
print(f'   中信心 (0.5-0.8): {mid[0]} 筆 (avg conf: {mid[1]:.2f})')
print(f'   低信心 (<0.5): {low[0]} 筆')
print()

# meta_label 分類
c.execute('SELECT meta_label, COUNT(*) FROM wisdom_corrections GROUP BY meta_label ORDER BY COUNT(*) DESC LIMIT 10')
meta_stats = c.fetchall()
print('meta_label 分類 (Top 10):')
for row in meta_stats:
    label = str(row[0])[:50]
    print(f'   {label}: {row[1]} 筆')
print()

# backtest_reports
c.execute('SELECT COUNT(DISTINCT symbol) FROM backtest_reports')
unique_sym = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM backtest_reports WHERE sharpe_ratio > 1.0')
good_strat = c.fetchone()[0]
print('backtest_reports:')
print(f'   獨特標的: {unique_sym} 個')
print(f'   Sharpe > 1.0: {good_strat} 筆')
print()

# wisdom_logs 狀態
c.execute('SELECT COUNT(*) FROM wisdom_logs WHERE weight > 0')
active = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM wisdom_logs WHERE weight <= 0')
inactive = c.fetchone()[0]
print('wisdom_logs:')
print(f'   活躍: {active} 筆')
print(f'   衰減/失敗: {inactive} 筆')

conn.close()
print()
print('=== 報告完成 ===')