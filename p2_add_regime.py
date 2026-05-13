# -*- coding: utf-8 -*-
"""P2-1: backtest_reports 補 market_regime 欄位 + 自動分類"""
import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB = r'C:\Users\USER\.openclaw\agents\ray\ray_wisdom.db'
conn = sqlite3.connect(DB)
c = conn.cursor()

print('=== P2-1: backtest_reports regime 欄位 ===')

# 新增 regime 欄位
try:
    c.execute("ALTER TABLE backtest_reports ADD COLUMN regime TEXT DEFAULT 'unknown'")
    print('  + regime column added')
    conn.commit()
except:
    print('  regime already exists')

# 根據 sharpe_ratio + max_drawdown 自動分類 regime
# 讀取所有未分類
c.execute("SELECT id, sharpe_ratio, max_drawdown, total_return, note FROM backtest_reports WHERE regime='unknown'")
rows = c.fetchall()
print(f'  待分類: {len(rows)} rows')

def classify_regime(sharpe, mdd, total_ret, note):
    """自動分類市場 regime"""
    note_lower = (note or '').lower()
    # 文字線索
    if 'bull' in note_lower or '多頭' in note_lower:
        return 'bull'
    if 'bear' in note_lower or '空頭' in note_lower:
        return 'bear'
    if 'volatile' in note_lower or '震盪' in note_lower:
        return 'volatile'
    if 'crisis' in note_lower or '危機' in note_lower:
        return 'crisis'
    # 數值推斷
    if mdd and mdd > 20:
        return 'volatile'  # 高回撤 = 劇烈波動
    if total_ret and total_ret > 20:
        return 'bull'
    if total_ret and total_ret < -10:
        return 'bear'
    return 'neutral'

count = 0
for r in rows:
    vid, sharpe, mdd, total_ret, note = r
    regime = classify_regime(sharpe, mdd, total_ret, note)
    c.execute("UPDATE backtest_reports SET regime=? WHERE id=?", (regime, vid))
    count += 1

conn.commit()

# 統計
c.execute("SELECT regime, COUNT(*) FROM backtest_reports GROUP BY regime")
print('\nregime 分佈:')
for r in c.fetchall():
    print(f'  {r[0]}: {r[1]} rows')

conn.close()
print('\n✅ P2-1 完成')