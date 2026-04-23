# -*- coding: utf-8 -*-
"""
Cycle 9 Step 3: 法人資料覆蓋缺口檢查
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import warnings
warnings.filterwarnings('ignore')
import yfinance as yf
yf.suppress_errors=True
import sqlite3
import pandas as pd

DB = r'C:\Users\USER\.openclaw\workspace\skills\stock-analyzer\scripts\tina_master.db'

# 完整候選股票池
CANDIDATES = [
    '2330','2454','3034','2379','2303','2344','2382','3231','3717','4938',
    '2317','2353','2357','2345','3017','6230','6269','3044','6213','4935',
    '4952','2401','2340','2385','3481','2409','6176','2412','3045','6239',
    '2327','2492','2356','2471','2497','5203','2881','2882','2884','2885',
    '2891','2801','2812','2834','1301','1326','2002','0050','0056','00891','00713',
    '2610','2603','2609','2630','3035','3413','2412','6505','3583','2376',
    '6282','6116','2456','2354','2201','4961','5871','6139','6415','6770','8046',
    '3532','3686','3702','4935','5215','5469','6183','6257','6477','3406',
    '5521','6153','2458','2377','6515','6533','6531','2492','2474','2615',
    '3583','3665','4977','2313','2352','1216','2207','2231','2233'
]
CANDIDATES = list(set(CANDIDATES))

print('='*60)
print(' Cycle 9 Step 3: 法人資料覆蓋缺口檢查')
print('='*60)

conn = sqlite3.connect(DB)
cur = conn.cursor()

# Check coverage for each candidate
gaps = []
full_coverage = []
partial = []

for sym in sorted(CANDIDATES):
    cur.execute('SELECT COUNT(*), MIN(date), MAX(date) FROM MarketData WHERE symbol=?', (sym,))
    r = cur.fetchone()
    cnt, mindt, maxdt = r
    if cnt == 0:
        gaps.append(sym)
    elif cnt < 450:  # less than ~2 years
        partial.append((sym, cnt, str(mindt), str(maxdt)))
    else:
        full_coverage.append(sym)

conn.close()

print(f'\n缺口 (0 筆): {len(gaps)} 檔')
for s in gaps:
    print(f'  {s} - 無法人資料')

print(f'\n部分覆蓋 (<450天): {len(partial)} 檔')
for s, cnt, m, n in partial:
    print(f'  {s}: {cnt}天 ({m} ~ {n})')

print(f'\n完整覆蓋 (>=450天): {len(full_coverage)} 檔')

print('\n--- 關鍵缺口 (Tier1/核心股) ---')
key_missing = ['3717','3045','3406','5469','6269']
for s in key_missing:
    if s in gaps:
        print(f'  ⚠️  {s} 核心股無法人資料')
